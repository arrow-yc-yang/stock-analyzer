"""
股票分析系统启动脚本
"""
import os
import sys
import argparse
from datetime import datetime

def init_db():
    """初始化数据库"""
    print("正在初始化数据库...")
    from app import app, db
    with app.app_context():
        db.create_all()
    print("数据库初始化完成！")

def sync_data(pool='hs300'):
    """同步数据"""
    print(f"正在同步{pool}股票数据...")
    from app import app
    from data_sync import DataUpdater
    from config import TUSHARE_TOKEN
    
    with app.app_context():
        updater = DataUpdater(TUSHARE_TOKEN)
        count = updater.sync_stock_basic(pool)
        print(f"已同步 {count} 只股票基础信息")
        
        # 同步K线数据
        print("正在同步K线数据...")
        kline_count = updater.sync_all_kline(pool, 'D')
        print(f"已同步 {kline_count} 条K线数据")

def run_server(host='0.0.0.0', port=5000, debug=False):
    """运行服务器"""
    print(f"启动服务器: http://{host}:{port}")
    from app import app
    app.run(host=host, port=port, debug=debug)

def analyze_stock(ts_code):
    """分析单个股票"""
    print(f"正在分析股票: {ts_code}")
    from app import app
    import requests
    
    with app.app_context():
        # 调用API进行分析
        base_url = "http://localhost:5000"
        try:
            response = requests.get(f"{base_url}/api/analysis/{ts_code}")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    result = data['data']
                    print("\n" + "="*50)
                    print(f"股票分析结果: {ts_code}")
                    print("="*50)
                    
                    # 趋势分析
                    trend = result.get('trend', {})
                    print(f"\n【趋势分析】")
                    print(f"短期趋势: {trend.get('short_trend', '未知')}")
                    print(f"中期趋势: {trend.get('mid_trend', '未知')}")
                    print(f"长期趋势: {trend.get('long_trend', '未知')}")
                    print(f"趋势强度: {trend.get('trend_strength', 0)}%")
                    
                    # 操作建议
                    rec = result.get('recommendation', {})
                    print(f"\n【操作建议】")
                    print(f"操作: {rec.get('action', '观望')}")
                    print(f"信心度: {rec.get('confidence', 0)}%")
                    
                    if rec.get('entry_levels'):
                        levels = rec['entry_levels']
                        if levels.get('moderate'):
                            print(f"建议买入价: ¥{levels['moderate']}")
                    
                    if rec.get('risk_management'):
                        rm = rec['risk_management']
                        if rm.get('stop_loss'):
                            print(f"止损价: ¥{rm['stop_loss']}")
                        if rm.get('take_profit_1'):
                            print(f"止盈价: ¥{rm['take_profit_1']}")
                    
                    # 概率预测
                    prob = result.get('probability', {})
                    print(f"\n【概率预测】")
                    print(f"上涨概率: {prob.get('up_probability', 0)}%")
                    print(f"下跌概率: {prob.get('down_probability', 0)}%")
                    print(f"横盘概率: {prob.get('sideways_probability', 0)}%")
                    
                    # 海龟交易
                    turtle = result.get('turtle_trading', {})
                    print(f"\n【海龟交易】")
                    print(f"信号: {turtle.get('direction', '无')}")
                    if turtle.get('entry_price'):
                        print(f"入场价: ¥{turtle['entry_price']}")
                    if turtle.get('stop_loss'):
                        print(f"止损价: ¥{turtle['stop_loss']}")
                    
                    print("\n" + "="*50)
                else:
                    print(f"分析失败: {data.get('error')}")
            else:
                print(f"请求失败: HTTP {response.status_code}")
        except Exception as e:
            print(f"分析失败: {e}")

def backtest_stock(ts_code, strategy='turtle_trading'):
    """回测股票"""
    print(f"正在回测股票: {ts_code}, 策略: {strategy}")
    from app import app
    import requests
    
    with app.app_context():
        base_url = "http://localhost:5000"
        try:
            response = requests.get(f"{base_url}/api/backtest/{ts_code}?strategy={strategy}")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    result = data['data']
                    print("\n" + "="*50)
                    print(f"回测结果: {ts_code} - {strategy}")
                    print("="*50)
                    
                    if result.get('error'):
                        print(f"回测失败: {result['error']}")
                    else:
                        print(f"\n总收益率: {result['total_return']:.2f}%")
                        print(f"胜率: {result['win_rate']:.1f}%")
                        print(f"最大回撤: {result['max_drawdown']:.2f}%")
                        print(f"交易次数: {result['total_trades']}")
                        print(f"盈亏比: {result['profit_factor']:.2f}")
                        print(f"\n初始资金: ¥{result['initial_capital']:,.0f}")
                        print(f"最终资金: ¥{result['final_capital']:,.0f}")
                    
                    print("\n" + "="*50)
                else:
                    print(f"回测失败: {data.get('error')}")
            else:
                print(f"请求失败: HTTP {response.status_code}")
        except Exception as e:
            print(f"回测失败: {e}")

def generate_report():
    """生成每日报告"""
    print("正在生成每日报告...")
    from app import app
    from models import Stock, AnalysisResult
    from datetime import datetime
    
    with app.app_context():
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 获取今日买入信号
        buy_signals = AnalysisResult.query.filter_by(
            analysis_date=today,
            recommendation='buy'
        ).order_by(AnalysisResult.confidence.desc()).all()
        
        print(f"\n{'='*60}")
        print(f"股票分析系统 - 每日报告 ({today})")
        print(f"{'='*60}")
        
        print(f"\n【买入信号】共 {len(buy_signals)} 只")
        if buy_signals:
            print(f"{'股票代码':<12} {'股票名称':<10} {'信心度':<8} {'入场价':<10} {'止损价':<10}")
            print("-" * 60)
            for signal in buy_signals[:10]:  # 显示前10个
                stock = signal.stock
                print(f"{signal.ts_code:<12} {stock.name if stock else '':<10} {signal.confidence:>6.1f}%  ¥{signal.entry_price:<9.2f} ¥{signal.stop_loss:<9.2f}")
        else:
            print("今日暂无买入信号")
        
        print(f"\n{'='*60}")

def main():
    parser = argparse.ArgumentParser(description='股票分析系统')
    parser.add_argument('command', choices=[
        'init', 'sync', 'server', 'analyze', 'backtest', 'report'
    ], help='要执行的命令')
    parser.add_argument('--pool', default='hs300', help='股票池 (hs300/all)')
    parser.add_argument('--code', help='股票代码')
    parser.add_argument('--strategy', default='turtle_trading', help='策略名称')
    parser.add_argument('--host', default='0.0.0.0', help='服务器主机')
    parser.add_argument('--port', type=int, default=5000, help='服务器端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        init_db()
    elif args.command == 'sync':
        sync_data(args.pool)
    elif args.command == 'server':
        run_server(args.host, args.port, args.debug)
    elif args.command == 'analyze':
        if not args.code:
            print("请使用 --code 指定股票代码")
            sys.exit(1)
        analyze_stock(args.code)
    elif args.command == 'backtest':
        if not args.code:
            print("请使�