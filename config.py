"""
股票分析系统配置文件
"""
import os

# Tushare API配置
TUSHARE_TOKEN = "daa6d96c4ddd44367542c19a10c6a81612b14e91ea796300ddf4f3ff"

# 数据库配置
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///stock_analyzer.db')

# 数据更新配置
UPDATE_INTERVAL_MINUTES = 5  # 实时更新间隔（分钟）
MARKET_OPEN_TIME = "09:30"
MARKET_CLOSE_TIME = "15:00"

# 分析配置
SHORT_TERM_DAYS = 20   # 短期分析天数
MID_TERM_DAYS = 60     # 中期分析天数
LONG_TERM_DAYS = 250   # 长期分析天数

# 回测配置
BACKTEST_YEARS = 3     # 回测年数
INITIAL_CAPITAL = 100000  # 初始资金

# 海龟交易法则配置
TURTLE_ENTRY_DAYS = 20    # 入场周期（20日高点）
TURTLE_EXIT_DAYS = 10     # 出场周期（10日低点）
TURTLE_ATR_DAYS = 20      # ATR计算周期
TURTLE_RISK_PERCENT = 0.01  # 单笔风险比例（1%）

# 技术分析阈值
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_SIGNAL_DAYS = 9

# 股票池配置
DEFAULT_STOCK_POOL = "hs300"  # 默认沪深300
CUSTOM_STOCKS_FILE = "custom_stocks.txt"

# API配置
API_HOST = "0.0.0.0"
API_PORT = 5000
API_DEBUG = False

# 报告配置
REPORT_OUTPUT_DIR = "reports"
REPORT_FORMATS = ["html", "pdf"]
