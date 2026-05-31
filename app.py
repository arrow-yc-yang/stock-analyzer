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
        ).order_by(AnalysisResult.confidence.desc()).limit(10).all()
        
        return jsonify({
            'success': True,
            'data': {
                'stats': {
                    'total_stocks': total_stocks,
                    'hs300_count': hs300_count,
                    'custom_count': custom_count,
                    'today_analysis': today_analysis
                },
                'buy_signals': [{
                    'ts_code': r.ts_code,
                    'stock_name': r.stock.name if r.stock else '',
                    'confidence': r.confidence,
                    'entry_price': r.entry_price,
                    'stop_loss': r.stop_loss,
                    'take_profit': r.take_profit
                } for r in buy_signals]
            }
        })
    except Exception as e:
        logger.error(f"获取仪表盘数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/report')
def get_report():
    """获取股票建议报表"""
    try:
        action = request.args.get('action', 'all')  # all, buy, hold, sell, wait
        sort_by = request.args.get('sort_by', 'confidence')  # confidence, price, name

        query = db.session.query(AnalysisResult, Stock).join(Stock, AnalysisResult.ts_code == Stock.ts_code)

        if action != 'all':
            query = query.filter(AnalysisResult.recommendation == action)

        if sort_by == 'confidence':
            query = query.order_by(AnalysisResult.confidence.desc())
        elif sort_by == 'price':
            query = query.order_by(Stock.name)

        results = query.all()

        data = []
        for r, s in results:
            data.append({
                'ts_code': r.ts_code,
                'name': s.name,
                'recommendation': r.recommendation,
                'confidence': r.confidence,
                'current_price': r.entry_price or 0,
                'short_trend': r.short_trend,
                'mid_trend': r.mid_trend,
                'long_trend': r.long_trend,
                'rsi': r.rsi,
                'up_probability': r.up_probability,
                'down_probability': r.down_probability,
                'stop_loss': r.stop_loss,
                'take_profit': r.take_profit,
                'turtle_signal': r.turtle_signal,
                'analysis_date': r.analysis_date
            })

        # 统计
        # 统计始终基于全量数据
        all_stats = db.session.query(
            AnalysisResult.recommendation,
            db.func.count(AnalysisResult.id)
        ).group_by(AnalysisResult.recommendation).all()
        
        stats_map = {row[0]: row[1] for row in all_stats}
        stats = {
            'buy': stats_map.get('buy', 0),
            'hold': stats_map.get('hold', 0),
            'sell': stats_map.get('sell', 0),
            'wait': stats_map.get('wait', 0),
        }

        return jsonify({
            'success': True,
            'data': data,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"获取报表数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/api/factor/sync', methods=['POST'])
def sync_factor_data():
    """同步因子数据"""
    try:
        stock_pool = request.json.get('pool', 'hs300')
        trade_date = request.json.get('trade_date', datetime.now().strftime('%Y%m%d'))

        # 获取股票列表
        if stock_pool == 'hs300':
            stocks = Stock.query.filter_by(is_hs300=True).all()
        elif stock_pool == 'custom':
            stocks = Stock.query.filter_by(is_custom=True).all()
        else:
            stocks = Stock.query.all()

        count = 0
        for stock in stocks:
            try:
                # 获取每日指标
                basic_df = tushare_client.get_daily_basic(ts_code=stock.ts_code, trade_date=trade_date)
                if basic_df.empty:
                    continue

                row = basic_df.iloc[0]

                # 获取财务指标（最近一期）
                fina_df = tushare_client.get_fina_indicator(ts_code=stock.ts_code)
                fina_row = fina_df.iloc[-1] if not fina_df.empty else {}

                # 检查是否已存在
                existing = FactorData.query.filter_by(
                    ts_code=stock.ts_code,
                    trade_date=trade_date
                ).first()

                factor_data = {
                    'pe_ttm': _safe_float(row.get('pe_ttm')),
                    'pb': _safe_float(row.get('pb')),
                    'ps_ttm': _safe_float(row.get('ps_ttm')),
                    'total_mv': _safe_float(row.get('total_mv')),
                    'circ_mv': _safe_float(row.get('circ_mv')),
                    'dv_ratio': _safe_float(row.get('dv_ratio')),
                    'turnover_rate': _safe_float(row.get('turnover_rate')),
                    'revenue_yoy': _safe_float(fina_row.get('or_yoy')),
                    'profit_yoy': _safe_float(fina_row.get('op_yoy_f')),
                    'roe_yoy': _safe_float(fina_row.get('roe_yoy')),
                    'eps_yoy': _safe_float(fina_row.get('eps_yoy')),
                    'roe': _safe_float(fina_row.get('roe')),
                    'roa': _safe_float(fina_row.get('roa')),
                    'grossprofit_margin': _safe_float(fina_row.get('grossprofit_margin')),
                    'netprofit_margin': _safe_float(fina_row.get('netprofit_margin')),
                    'debt_to_assets': _safe_float(fina_row.get('debt_to_assets')),
                    'current_ratio': _safe_float(fina_row.get('current_ratio')),
                    'quick_ratio': _safe_float(fina_row.get('quick_ratio')),
                }

                if existing:
                    for key, value in factor_data.items():
                        setattr(existing, key, value)
                else:
                    record = FactorData(
                        stock_id=stock.id,
                        ts_code=stock.ts_code,
                        trade_date=trade_date,
                        **factor_data
                    )
                    db.session.add(record)

                count += 1
                if count % 50 == 0:
                    db.session.commit()
                    logger.info(f"已同步 {count} 只股票因子数据")

            except Exception as e:
                logger.error(f"同步 {stock.ts_code} 因子数据失败: {e}")
                db.session.rollback()
                continue

        db.session.commit()

        # 计算因子得分
        _update_factor_scores(trade_date)

        return jsonify({
            'success': True,
            'message': f'成功同步 {count} 只股票的因子数据'
        })
    except Exception as e:
        logger.error(f"同步因子数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def _safe_float(value):
    """安全转换为float"""
    if value is None:
        return None
    try:
        v = float(value)
        if np.isnan(v) or np.isinf(v):
            return None
        return v
    except (ValueError, TypeError):
        return None


def _update_factor_scores(trade_date):
    """更新因子得分"""
    try:
        # 获取所有因子数据
        factor_records = FactorData.query.filter_by(trade_date=trade_date).all()
        if not factor_records:
            return

        # 构建DataFrame
        data = []
        stock_info = {}
        for r in factor_records:
            stock = Stock.query.filter_by(ts_code=r.ts_code).first()
            stock_info[r.ts_code] = {'name': stock.name if stock else '', 'industry': stock.industry if stock else ''}
            data.append({
                'ts_code': r.ts_code,
                'pe_ttm': r.pe_ttm,
                'pb': r.pb,
                'ps_ttm': r.ps_ttm,
                'dv_ratio': r.dv_ratio,
                'revenue_yoy': r.revenue_yoy,
                'profit_yoy': r.profit_yoy,
                'roe_yoy': r.roe_yoy,
                'eps_yoy': r.eps_yoy,
                'roe': r.roe,
                'grossprofit_margin': r.grossprofit_margin,
                'netprofit_margin': r.netprofit_margin,
                'debt_to_assets': r.debt_to_assets,
                'total_mv': r.total_mv,
                'circ_mv': r.circ_mv,
                'turnover_rate': r.turnover_rate,
            })

        df = pd.DataFrame(data)
        # 添加名称和行业
        df['name'] = df['ts_code'].map(lambda x: stock_info.get(x, {}).get('name', ''))
        df['industry'] = df['ts_code'].map(lambda x: stock_info.get(x, {}).get('industry', ''))

        # 计算得分
        result = factor_screener.screen_stocks(df, top_n=len(df))

        # 更新数据库
        for stock_data in result['stocks']:
            ts_code = stock_data['ts_code']
            record = FactorData.query.filter_by(ts_code=ts_code, trade_date=trade_date).first()
            if record:
                record.composite_score = stock_data.get('composite_score')
                record.value_score = stock_data.get('value_score')
                record.growth_score = stock_data.get('growth_score')
                record.quality_score = stock_data.get('quality_score')

        db.session.commit()
        logger.info(f"因子得分更新完成，共 {len(result['stocks'])} 只股票")
    except Exception as e:
        logger.error(f"更新因子得分失败: {e}")
        db.session.rollback()


@app.route('/api/factor/screen')
def screen_stocks():
    """多因子选股"""
    try:
        top_n = int(request.args.get('top_n', 20))
        sort_by = request.args.get('sort_by', 'composite_score')

        # 获取最新的因子数据
        latest_date = db.session.query(
            db.func.max(FactorData.trade_date)
        ).scalar()

        if not latest_date:
            return jsonify({
                'success': False,
                'error': '暂无因子数据，请先同步因子数据'
            })

        # 构建查询
        query = db.session.query(FactorData, Stock).join(Stock, FactorData.ts_code == Stock.ts_code).filter(
            FactorData.trade_date == latest_date
        )

        # 应用过滤条件
        filters = {}
        pe_max = request.args.get('pe_ttm_max')
        if pe_max:
            query = query.filter(FactorData.pe_ttm <= float(pe_max))
            filters['pe_ttm_max'] = float(pe_max)

        pb_max = request.args.get('pb_max')
        if pb_max:
            query = query.filter(FactorData.pb <= float(pb_max))
            filters['pb_max'] = float(pb_max)

        roe_min = request.args.get('roe_min')
        if roe_min:
            query = query.filter(FactorData.roe >= float(roe_min))
            filters['roe_min'] = float(roe_min)

        revenue_min = request.args.get('revenue_yoy_min')
        if revenue_min:
            query = query.filter(FactorData.revenue_yoy >= float(revenue_min))
            filters['revenue_yoy_min'] = float(revenue_min)

        industry = request.args.get('industry')
        if industry:
            query = query.filter(Stock.industry == industry)
            filters['industry'] = industry

        results = query.all()

        if not results:
            return jsonify({
                'success': False,
                'error': '无符合条件的股票'
            })

        # 构建DataFrame
        data = []
        for r, s in results:
            data.append({
                'ts_code': r.ts_code,
                'name': s.name,
                'industry': s.industry,
                'pe_ttm': r.pe_ttm,
                'pb': r.pb,
                'ps_ttm': r.ps_ttm,
                'dv_ratio': r.dv_ratio,
                'turnover_rate': r.turnover_rate,
                'revenue_yoy': r.revenue_yoy,
                'profit_yoy': r.profit_yoy,
                'roe_yoy': r.roe_yoy,
                'eps_yoy': r.eps_yoy,
                'roe': r.roe,
                'roa': r.roa,
                'grossprofit_margin': r.grossprofit_margin,
                'netprofit_margin': r.netprofit_margin,
                'debt_to_assets': r.debt_to_assets,
                'total_mv': r.total_mv,
                'circ_mv': r.circ_mv,
                'composite_score': r.composite_score,
                'value_score': r.value_score,
                'growth_score': r.growth_score,
                'quality_score': r.quality_score,
            })

        df = pd.DataFrame(data)

        # 使用因子引擎排序
        screen_result = factor_screener.screen_stocks(df, top_n=top_n, sort_by=sort_by)

        # 获取行业分布
        industry_dist = factor_screener.get_industry_distribution(screen_result['stocks'])

        return jsonify({
            'success': True,
            'data': screen_result,
            'industry_distribution': industry_dist,
            'latest_date': latest_date
        })
    except Exception as e:
        logger.error(f"多因子选股失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/factor/ranking')
def get_factor_ranking():
    """获取单因子排名"""
    try:
        factor_name = request.args.get('factor', 'composite_score')
        top_n = int(request.args.get('top_n', 20))
        ascending = request.args.get('ascending', 'true').lower() == 'true'

        latest_date = db.session.query(db.func.max(FactorData.trade_date)).scalar()
        if not latest_date:
            return jsonify({'success': False, 'error': '暂无因子数据'})

        # 查询因子数据
        records = db.session.query(FactorData, Stock).join(
            Stock, FactorData.ts_code == Stock.ts_code
        ).filter(FactorData.trade_date == latest_date).all()

        data = []
        for r, s in records:
            row_dict = r.to_dict()
            row_dict['name'] = s.name
            row_dict['industry'] = s.industry
            data.append(row_dict)

        df = pd.DataFrame(data)
        ranking = factor_screener.get_factor_ranking(df, factor_name, top_n, ascending)

        return jsonify({
            'success': True,
            'data': ranking,
            'factor': factor_name,
            'latest_date': latest_date
        })
    except Exception as e:
        logger.error(f"获取因子排名失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/factor/correlation')
def get_factor_correlation():
    """获取因子相关性"""
    try:
        latest_date = db.session.query(db.func.max(FactorData.trade_date)).scalar()
        if not latest_date:
            return jsonify({'success': False, 'error': '暂无因子数据'})

        records = db.session.query(FactorData).filter(
            FactorData.trade_date == latest_date
        ).all()

        data = [r.to_dict() for r in records]
        df = pd.DataFrame(data)

        correlation = factor_screener.get_factor_correlation(df)

        return jsonify({
            'success': True,
            'data': correlation,
            'latest_date': latest_date
        })
    except Exception as e:
        logger.error(f"获取因子相关性失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/factor/industries')
def get_factor_industries():
    """获取因子数据中的行业列表"""
    try:
        latest_date = db.session.query(db.func.max(FactorData.trade_date)).scalar()
        if not latest_date:
            return jsonify({'success': False, 'error': '暂无因子数据'})

        industries = db.session.query(Stock.industry).join(
            FactorData, FactorData.ts_code == Stock.ts_code
        ).filter(
            FactorData.trade_date == latest_date,
            Stock.industry.isnot(None),
            Stock.industry != ''
        ).distinct().all()

        return jsonify({
            'success': True,
            'data': [ind[0] for ind in industries if ind[0]]
        })
    except Exception as e:
        logger.error(f"获取行业列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============ 定时任务 ============

def init_scheduler():
    """初始化定时任务"""
    scheduler = BackgroundScheduler()
    
    # 每日收盘后更新数据
    scheduler.add_job(
        scheduled_data_update,
        'cron',
        hour=15,
        minute=30,
        id='daily_data_update'
    )
    
    # 每日盘后分析
    scheduler.add_job(
        scheduled_daily_analysis,
        'cron',
        hour=16,
        minute=0,
        id='daily_analysis'
    )
    
    scheduler.start()
    logger.info("定时任务已启动")
    return scheduler

def scheduled_data_update():
    """定时更新数据"""
    with app.app_context():
        try:
            logger.info("开始定时数据更新")
            data_updater.update_realtime_data()
            logger.info("定时数据更新完成")
        except Exception as e:
            logger.error(f"定时数据更新失败: {e}")

def scheduled_daily_analysis():
    """定时每日分析"""
    with app.app_context():
        try:
            logger.info("开始定时每日分析")
            stocks = Stock.query.filter_by(is_hs300=True).all()
            
            for stock in stocks:
                try:
                    # 获取K线数据
                    klines = KLineData.query.filter_by(ts_code=stock.ts_code, freq='D').order_by(KLineData.trade_date).all()
                    
                    if len(klines) < 60:
                        continue
                    
                    # 分析
                    df = pd.DataFrame([k.to_dict() for k in klines])
                    df['trade_date'] = pd.to_datetime(df['trade_date'])
                    df.set_index('trade_date', inplace=True)
                    
                    analysis_result = technical_analyzer.full_analysis(df)
                    strategy_result = strategy_matcher.match_all_strategies(analysis_result['data'], analysis_result)
                    probability_result = probability_predictor.predict_trend_probability(df, analysis_result)
                    turtle_result = turtle_trading.get_current_recommendation(analysis_result['data'])
                    recommendation = recommendation_engine.generate_recommendation(
                        df, analysis_result, strategy_result, probability_result, turtle_result
                    )
                    
                    save_analysis_result(stock.ts_code, analysis_result, strategy_result, probability_result, turtle_result, recommendation)
                    
                except Exception as e:
                    logger.error(f"分析 {stock.ts_code} 失败: {e}")
                    continue
            
            logger.info("定时每日分析完成")
        except Exception as e:
            logger.error(f"定时每日分析失败: {e}")

# 启动定时任务
scheduler = init_scheduler()

if __name__ == '__main__':
    app.run(host=API_HOST, port=API_PORT, debug=API_DEBUG)
