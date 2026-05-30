"""
数据库模型
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Stock(db.Model):
    """股票基本信息表"""
    __tablename__ = 'stocks'
    
    id = db.Column(db.Integer, primary_key=True)
    ts_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    symbol = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    area = db.Column(db.String(50))
    industry = db.Column(db.String(50))
    market = db.Column(db.String(20))
    list_date = db.Column(db.String(20))
    is_hs300 = db.Column(db.Boolean, default=False)
    is_custom = db.Column(db.Boolean, default=False)
    stock_type = db.Column(db.String(20), default='stock')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Stock {self.ts_code}: {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'ts_code': self.ts_code,
            'symbol': self.symbol,
            'name': self.name,
            'area': self.area,
            'industry': self.industry,
            'market': self.market,
            'list_date': self.list_date,
            'is_hs300': self.is_hs300,
            'is_custom': self.is_custom,
            'stock_type': self.stock_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class KLineData(db.Model):
    """K线数据表"""
    __tablename__ = 'kline_data'
    
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False, index=True)
    ts_code = db.Column(db.String(20), nullable=False, index=True)
    trade_date = db.Column(db.String(20), nullable=False, index=True)
    freq = db.Column(db.String(10), nullable=False, index=True)
    
    open_price = db.Column(db.Float, nullable=False)
    high_price = db.Column(db.Float, nullable=False)
    low_price = db.Column(db.Float, nullable=False)
    close_price = db.Column(db.Float, nullable=False)
    pre_close = db.Column(db.Float)
    volume = db.Column(db.BigInteger)
    amount = db.Column(db.Float)
    change = db.Column(db.Float)
    pct_change = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('ts_code', 'trade_date', 'freq', name='uix_kline'),
    )
    
    def to_dict(self):
        # 格式化日期 '20260518' -> '2026-05-18'
        trade_date = self.trade_date
        if trade_date and len(str(trade_date)) == 8:
            trade_date = f"{str(trade_date)[:4]}-{str(trade_date)[4:6]}-{str(trade_date)[6:8]}"
        return {
            'id': self.id,
            'ts_code': self.ts_code,
            'trade_date': trade_date,
            'freq': self.freq,
            'open': self.open_price,
            'high': self.high_price,
            'low': self.low_price,
            'close': self.close_price,
            'pre_close': self.pre_close,
            'volume': self.volume,
            'amount': self.amount,
            'change': self.change,
            'pct_change': self.pct_change
        }

class AnalysisResult(db.Model):
    """分析结果表"""
    __tablename__ = 'analysis_results'
    
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False, index=True)
    stock = db.relationship('Stock', backref='analysis_results')
    ts_code = db.Column(db.String(20), nullable=False, index=True)
    analysis_date = db.Column(db.String(20), nullable=False, index=True)
    
    short_trend = db.Column(db.String(20))
    mid_trend = db.Column(db.String(20))
    long_trend = db.Column(db.String(20))
    trend_strength = db.Column(db.Float)
    
    ma5 = db.Column(db.Float)
    ma10 = db.Column(db.Float)
    ma20 = db.Column(db.Float)
    ma60 = db.Column(db.Float)
    rsi = db.Column(db.Float)
    macd_dif = db.Column(db.Float)
    macd_dea = db.Column(db.Float)
    macd_hist = db.Column(db.Float)
    boll_upper = db.Column(db.Float)
    boll_mid = db.Column(db.Float)
    boll_lower = db.Column(db.Float)
    atr = db.Column(db.Float)
    
    matched_strategies = db.Column(db.Text)
    strategy_scores = db.Column(db.Text)
    
    up_probability = db.Column(db.Float)
    down_probability = db.Column(db.Float)
    sideways_probability = db.Column(db.Float)
    
    recommendation = db.Column(db.String(20))
    confidence = db.Column(db.Float)
    entry_price = db.Column(db.Float)
    stop_loss = db.Column(db.Float)
    take_profit = db.Column(db.Float)
    risk_reward_ratio = db.Column(db.Float)
    
    turtle_signal = db.Column(db.String(20))
    turtle_entry_price = db.Column(db.Float)
    turtle_stop_price = db.Column(db.Float)
    turtle_unit_size = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BacktestResult(db.Model):
    """回测结果表"""
    __tablename__ = 'backtest_results'
    
    id = db.Column(db.Integer, primary_key=True)
    strategy_name = db.Column(db.String(100), nullable=False, index=True)
    ts_code = db.Column(db.String(20), nullable=False, index=True)
    
    start_date = db.Column(db.String(20), nullable=False)
    end_date = db.Column(db.String(20), nullable=False)
    initial_capital = db.Column(db.Float, default=100000)
    
    final_capital = db.Column(db.Float)
    total_return = db.Column(db.Float)
    annual_return = db.Column(db.Float)
    max_drawdown = db.Column(db.Float)
    sharpe_ratio = db.Column(db.Float)
    
    total_trades = db.Column(db.Integer)
    winning_trades = db.Column(db.Integer)
    losing_trades = db.Column(db.Integer)
    win_rate = db.Column(db.Float)
    avg_profit = db.Column(db.Float)
    avg_loss = db.Column(db.Float)
    profit_factor = db.Column(db.Float)
    
    trade_records = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FactorData(db.Model):
    """因子数据表"""
    __tablename__ = 'factor_data'

    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False, index=True)
    stock = db.relationship('Stock', backref='factor_data')
    ts_code = db.Column(db.String(20), nullable=False, index=True)
    trade_date = db.Column(db.String(20), nullable=False, index=True)

    # 估值因子
    pe_ttm = db.Column(db.Float)          # 市盈率TTM
    pb = db.Column(db.Float)              # 市净率
    ps_ttm = db.Column(db.Float)          # 市销率TTM
    total_mv = db.Column(db.Float)        # 总市值（万元）
    circ_mv = db.Column(db.Float)         # 流通市值（万元）
    dv_ratio = db.Column(db.Float)        # 股息率
    turnover_rate = db.Column(db.Float)   # 换手率

    # 成长因子
    revenue_yoy = db.Column(db.Float)     # 营收同比增长率(%)
    profit_yoy = db.Column(db.Float)      # 净利润同比增长率(%)
    roe_yoy = db.Column(db.Float)         # ROE同比增长率(%)
    eps_yoy = db.Column(db.Float)         # EPS同比增长率(%)

    # 盈利因子
    roe = db.Column(db.Float)             # 净资产收益率(%)
    roa = db.Column(db.Float)             # 总资产收益率(%)
    grossprofit_margin = db.Column(db.Float)  # 毛利率(%)
    netprofit_margin = db.Column(db.Float)    # 净利率(%)

    # 质量因子
    debt_to_assets = db.Column(db.Float)  # 资产负债率(%)
    current_ratio = db.Column(db.Float)   # 流动比率
    quick_ratio = db.Column(db.Float)     # 速动比率

    # 综合评分
    composite_score = db.Column(db.Float) # 综合因子得分
    value_score = db.Column(db.Float)     # 价值因子得分
    growth_score = db.Column(db.Float)    # 成长因子得分
    quality_score = db.Column(db.Float)   # 质量因子得分

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('ts_code', 'trade_date', name='uix_factor_data'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'ts_code': self.ts_code,
            'trade_date': self.trade_date,
            'pe_ttm': self.pe_ttm,
            'pb': self.pb,
            'ps_ttm': self.ps_ttm,
            'total_mv': self.total_mv,
            'circ_mv': self.circ_mv,
            'dv_ratio': self.dv_ratio,
            'turnover_rate': self.turnover_rate,
            'revenue_yoy': self.revenue_yoy,
            'profit_yoy': self.profit_yoy,
            'roe_yoy': self.roe_yoy,
            'eps_yoy': self.eps_yoy,
            'roe': self.roe,
            'roa': self.roa,
            'grossprofit_margin': self.grossprofit_margin,
            'netprofit_margin': self.netprofit_margin,
            'debt_to_assets': self.debt_to_assets,
            'current_ratio': self.current_ratio,
            'quick_ratio': self.quick_ratio,
            'composite_score': self.composite_score,
            'value_score': self.value_score,
            'growth_score': self.growth_score,
            'quality_score': self.quality_score,
        }


def init_db(app):
    """初始化数据库"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
