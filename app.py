"""
Flask Web应用主文件
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import logging
import os

from config import TUSHARE_TOKEN, DATABASE_URL, API_HOST, API_PORT, API_DEBUG
from models import db, Stock, KLineData, AnalysisResult, BacktestResult, FactorData
from data_sync import TushareClient, DataUpdater
from analysis import TechnicalAnalyzer, StrategyMatcher, ProbabilityPredictor, TurtleTrading, FactorScreener
from analysis.recommendation_engine import RecommendationEngine
from backtest import BacktestEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 自定义JSON编码器，处理numpy类型
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj) if not np.isnan(obj) and not np.isinf(obj) else None
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.Timestamp):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, float):
            if np.isnan(obj) or np.isinf(obj):
                return None
        return super().default(obj)

def clean_nan(obj):
    """递归清理NaN和Inf值"""
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan(item) for item in obj]
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    elif isinstance(obj, np.floating):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return clean_nan(obj.tolist())
    return obj

# 创建Flask应用
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False
app.json_encoder = NumpyEncoder  # 使用自定义JSON编码器

# 初始化扩展
CORS(app)
db.init_app(app)

# 初始化组件
tushare_client = TushareClient(TUSHARE_TOKEN)
data_updater = DataUpdater(TUSHARE_TOKEN)
technical_analyzer = TechnicalAnalyzer()
strategy_matcher = StrategyMatcher()
probability_predictor = ProbabilityPredictor()
turtle_trading = TurtleTrading()
recommendation_engine = RecommendationEngine()
backtest_engine = BacktestEngine()
factor_screener = FactorScreener()

# 创建数据库表
with app.app_context():
    db.create_all()
    logger.info("数据库表创建完成")

# ============ 页面路由 ============

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/stocks')
def stocks_page():
    """股票列表页面"""
    return render_template('stocks.html')

@app.route('/analysis/<ts_code>')
def analysis_page(ts_code):
    """分析页面"""
    return render_template('analysis.html', ts_code=ts_code)

@app.route('/backtest')
def backtest_page():
    """回测页面"""
    return render_template('backtest.html')

@app.route('/custom_stocks')
def custom_stocks_page():
    """自选股票页面"""
    return render_template('custom_stocks.html')

@app.route('/report')
def report_page():
    return render_template('report.html')

@app.route('/factor_screen')
def factor_screen_page():
    """多因子选股页面"""
    return render_template('factor_screen.html')

# ============ API路由 ============

@app.route('/api/stocks')
def get_stocks():
    """获取股票列表"""
    try:
        stock_type = request.args.get('type', 'all')
        
        query = Stock.query
        
        if stock_type == 'hs300':
            query = query.filter_by(is_hs300=True)
        elif stock_type == 'custom':
            query = query.filter_by(is_custom=True)
        
        stocks = query.all()
        return jsonify({
            'success': True,
            'data': [s.to_dict() for s in stocks]
        })
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stocks/search')
def search_stocks():
    """搜索股票"""
    try:
        keyword = request.args.get('keyword', '')
        if not keyword:
            return jsonify({'success': False, 'error': '请输入搜索关键词'})
        
        stocks = Stock.query.filter(
            db.or_(
                Stock.ts_code.like(f'%{keyword}%'),
                Stock.name.like(f'%{keyword}%'),
                Stock.symbol.like(f'%{keyword}%')
            )
        ).limit(20).all()
        
        return jsonify({
            'success': True,
            'data': [s.to_dict() for s in stocks]
        })
    except Exception as e:
        logger.error(f"搜索股票失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stocks/custom', methods=['POST'])
def add_custom_stock():
    """添加自选股票"""
    try:
        data = request.get_json()
        ts_code = data.get('ts_code')
        
        if not ts_code:
            return jsonify({'success': False, 'error': '请提供股票代码'})
        
        # 检查是否已存在
        stock = Stock.query.filter_by(ts_code=ts_code).first()
        
        if stock:
            stock.is_custom = True
        else:
            # 从Tushare获取信息
            df = tushare_client.get_stock_basic()
            stock_info = df[df['ts_code'] == ts_code]
            
            if stock_info.empty:
                return jsonify({'success': False, 'error': '股票代码不存在'})
            
            info = stock_info.iloc[0]
            stock = Stock(
                ts_code=info['ts_code'],
                symbol=info['symbol'],
                name=info['name'],
                area=info.get('area', ''),
                industry=info.get('industry', ''),
                market=info.get('market', ''),
                list_date=str(info.get('list_date', '')),
                is_custom=True,
                stock_type='stock'
            )
            db.session.add(stock)
        
        db.session.commit()
        
        # 同步K线数据
        data_updater.sync_kline_data(ts_code, 'D')
        
        return jsonify({
            'success': True,
            'message': f'已添加 {stock.name} 到自选',
            'data': stock.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"添加自选股票失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stocks/custom/<ts_code>', methods=['DELETE'])
def remove_custom_stock(ts_code):
    """删除自选股票"""
    try:
        stock = Stock.query.filter_by(ts_code=ts_code).first()
        
        if stock:
            stock.is_custom = False
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'已从自选移除 {stock.name}'
            })
        else:
            return jsonify({'success': False, 'error': '股票不存在'}), 404
    except Exception as e:
        db.session.rollback()
        logger.error(f"删除自选股票失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kline/<ts_code>')
def get_kline(ts_code):
    """获取K线数据"""
    try:
        freq = request.args.get('freq', 'D')
        limit = int(request.args.get('limit', 250))
        
        klines = KLineData.query.filter_by(
            ts_code=ts_code,
            freq=freq
        ).order_by(KLineData.trade_date.desc()).limit(limit).all()
        
        return jsonify({
            'success': True,
            'data': [k.to_dict() for k in reversed(klines)]
        })
    except Exception as e:
        logger.error(f"获取K线数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/holder_number/<ts_code>')
def get_holder_number(ts_code):
    """获取股东户数数据"""
    try:
        df = tushare_client.get_holder_number(ts_code)
        
        if df.empty:
            return jsonify({
                'success': False,
                'error': '暂无股东户数数据'
            })
        
        # 转换为列表格式
        data = []
        for _, row in df.iterrows():
            data.append({
                'end_date': str(row.get('end_date', '')),
                'holder_num': int(row.get('holder_num', 0)) if pd.notna(row.get('holder_num')) else 0,
                'total_share': float(row.get('total_share', 0)) if pd.notna(row.get('total_share')) else 0,
                'free_share': float(row.get('free_share', 0)) if pd.notna(row.get('free_share')) else 0,
                'avg_hold_amount': float(row.get('avg_hold_amount', 0)) if pd.notna(row.get('avg_hold_amount')) else 0,
            })
        
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"获取股东户数数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analysis/<ts_code>')
def analyze_stock(ts_code):
    """分析股票"""
    try:
        # 获取股票信息
        stock = Stock.query.filter_by(ts_code=ts_code).first()
        stock_name = stock.name if stock else ''
        
        # 获取K线数据
        klines = KLineData.query.filter_by(ts_code=ts_code, freq='D').order_by(KLineData.trade_date).all()
        
        if len(klines) < 60:
            return jsonify({
                'success': False,
                'error': '数据不足，无法分析（需要至少60个交易日数据）'
            })
        
        # 获取最新价格
        latest_kline = klines[-1]
        current_price = latest_kline.close_price
        
        # 转换为DataFrame
        df = pd.DataFrame([k.to_dict() for k in klines])
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df.set_index('trade_date', inplace=True)
        
        # 1. 技术分析
        analysis_result = technical_analyzer.full_analysis(df)
        
        # 2. 战法匹配
        strategy_result = strategy_matcher.match_all_strategies(analysis_result['data'], analysis_result)
        
        # 3. 概率预测
        probability_result = probability_predictor.predict_trend_probability(df, analysis_result)
        
        # 4. 海龟交易信号
        turtle_result = turtle_trading.get_current_recommendation(analysis_result['data'])
        
        # 5. 买卖建议
        recommendation = recommendation_engine.generate_recommendation(
            df, analysis_result, strategy_result, probability_result, turtle_result
        )
        # 添加当前价格到建议中
        recommendation['current_price'] = current_price
        
        # 保存分析结果到数据库
        save_analysis_result(ts_code, analysis_result, strategy_result, probability_result, turtle_result, recommendation)
        
        # 清理NaN值后返回
        response_data = {
            'ts_code': ts_code,
            'stock_name': stock_name,
            'current_price': current_price,
            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
            'trend': analysis_result['trend'],
            'support_resistance': analysis_result['support_resistance'],
            'indicators': analysis_result['indicators'],
            'strategies': strategy_result,
            'probability': probability_result,
            'turtle_trading': turtle_result,
            'recommendation': recommendation
        }
        
        return jsonify({
            'success': True,
            'data': clean_nan(response_data)
        })
    except Exception as e:
        logger.error(f"分析股票失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def save_analysis_result(ts_code, analysis_result, strategy_result, probability_result, turtle_result, recommendation):
    """保存分析结果"""
    try:
        stock = Stock.query.filter_by(ts_code=ts_code).first()
        if not stock:
            return
        
        # 删除旧记录
        AnalysisResult.query.filter_by(ts_code=ts_code).delete()
        
        # 创建新记录
        latest = analysis_result['data'].iloc[-1]
        
        result = AnalysisResult(
            stock_id=stock.id,
            ts_code=ts_code,
            analysis_date=datetime.now().strftime('%Y-%m-%d'),
            short_trend=analysis_result['trend'].get('short_trend'),
            mid_trend=analysis_result['trend'].get('mid_trend'),
            long_trend=analysis_result['trend'].get('long_trend'),
            trend_strength=analysis_result['trend'].get('trend_strength'),
            ma5=latest.get('MA5'),
            ma10=latest.get('MA10'),
            ma20=latest.get('MA20'),
            ma60=latest.get('MA60'),
            rsi=latest.get('RSI'),
            macd_dif=latest.get('MACD_DIF'),
            macd_dea=latest.get('MACD_DEA'),
            macd_hist=latest.get('MACD_HIST'),
            boll_upper=latest.get('BOLL_UPPER'),
            boll_mid=latest.get('BOLL_MID'),
            boll_lower=latest.get('BOLL_LOWER'),
            atr=latest.get('ATR'),
            matched_strategies=json.dumps(strategy_result.get('matched_strategies', [])),
            strategy_scores=json.dumps(strategy_result.get('strategy_scores', {})),
            up_probability=probability_result.get('up_probability'),
            down_probability=probability_result.get('down_probability'),
            sideways_probability=probability_result.get('sideways_probability'),
            recommendation=recommendation.get('action'),
            confidence=recommendation.get('confidence'),
            entry_price=recommendation.get('entry_levels', {}).get('moderate'),
            stop_loss=recommendation.get('risk_management', {}).get('stop_loss'),
            take_profit=recommendation.get('risk_management', {}).get('take_profit_1'),
            risk_reward_ratio=recommendation.get('risk_management', {}).get('risk_reward_ratio'),
            turtle_signal=turtle_result.get('direction'),
            turtle_entry_price=turtle_result.get('entry_price'),
            turtle_stop_price=turtle_result.get('stop_loss'),
            turtle_unit_size=turtle_result.get('unit_size')
        )
        
        db.session.add(result)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"保存分析结果失败: {e}")

@app.route('/api/backtest/<ts_code>')
def backtest_stock(ts_code):
    """回测股票"""
    try:
        strategy = request.args.get('strategy', 'turtle_trading')
        
        # 获取K线数据
        klines = KLineData.query.filter_by(ts_code=ts_code, freq='D').order_by(KLineData.trade_date).all()
        
        if len(klines) < 60:
            return jsonify({
                'success': False,
                'error': '数据不足，无法回测'
            })
        
        # 转换为DataFrame
        df = pd.DataFrame([k.to_dict() for k in klines])
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df.set_index('trade_date', inplace=True)
        
        # 执行回测
        result = backtest_engine.backtest_strategy(df, strategy)
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"回测失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/backtest/compare/<ts_code>')
def compare_strategies(ts_code):
    """对比策略"""
    try:
        # 获取K线数据
        klines = KLineData.query.filter_by(ts_code=ts_code, freq='D').order_by(KLineData.trade_date).all()
        
        if len(klines) < 60:
            return jsonify({
                'success': False,
                'error': '数据不足'
            })
        
        # 转换为DataFrame
        df = pd.DataFrame([k.to_dict() for k in klines])
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df.set_index('trade_date', inplace=True)
        
        # 对比策略
        result = backtest_engine.compare_strategies(df)
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"策略对比失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sync/stocks', methods=['POST'])
def sync_stocks():
    """同步股票基础信息"""
    try:
        stock_pool = request.json.get('pool', 'hs300')
        count = data_updater.sync_stock_basic(stock_pool)
        
        return jsonify({
            'success': True,
            'message': f'成功同步 {count} 只股票信息'
        })
    except Exception as e:
        logger.error(f"同步股票信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sync/kline', methods=['POST'])
def sync_kline():
    """同步K线数据"""
    try:
        ts_code = request.json.get('ts_code')
        freq = request.json.get('freq', 'D')
        
        if ts_code:
            count = data_updater.sync_kline_data(ts_code, freq)
            message = f'成功同步 {ts_code} 的 {count} 条K线数据'
        else:
            stock_pool = request.json.get('pool', 'hs300')
            count = data_updater.sync_all_kline(stock_pool, freq)
            message = f'成功同步 {count} 条K线数据'
        
        return jsonify({
            'success': True,
            'message': message
        })
    except Exception as e:
        logger.error(f"同步K线数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard')
def get_dashboard():
    """获取仪表盘数据"""
    try:
        # 统计信息
        total_stocks = Stock.query.count()
        hs300_count = Stock.query.filter_by(is_hs300=True).count()
        custom_count = Stock.query.filter_by(is_custom=True).count()
        
        # 今日分析数量
        today = datetime.now().strftime('%Y-%m-%d')
        today_analysis = AnalysisResult.query.filter_by(analysis_date=today).count()
        
        # 最新分析结果（买入建议）
        buy_signals = AnalysisResult.query.filter(
            AnalysisResult.recommendation == 'buy'
        ).order_by(AnalysisResult.confidence.desc