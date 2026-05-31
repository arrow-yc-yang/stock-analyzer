"""
K线数据模型
"""
from datetime import datetime
from . import db

class KLineData(db.Model):
    """K线数据表"""
    __tablename__ = 'kline_data'
    
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False, index=True)
    ts_code = db.Column(db.String(20), nullable=False, index=True)
    trade_date = db.Column(db.String(20), nullable=False, index=True)  # 交易日期
    freq = db.Column(db.String(10), nullable=False, index=True)  # 频率：D/W/M（日/周/月）
    
    # 价格数据
    open_price = db.Column(db.Float, nullable=False)  # 开盘价
    high_price = db.Column(db.Float, nullable=False)  # 最高价
    low_price = db.Column(db.Float, nullable=False)  # 最低价
    close_price = db.Column(db.Float, nullable=False)  # 收盘价
    pre_close = db.Column(db.Float)  # 昨收价
    
    # 成交量数据
    volume = db.Column(db.BigInteger)  # 成交量（手）
    amount = db.Column(db.Float)  # 成交额（千元）
    
    # 涨跌幅
    change = db.Column(db.Float)  # 涨跌额
    pct_change = db.Column(db.Float)  # 涨跌幅(%)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('ts_code', 'trade_date', 'freq', name='uix_kline'),
    )
    
    def __repr__(self):
        return f'<KLineData {self.ts_code} {self.trade_date} {self.freq}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'ts_code': self.ts_code,
            'trade_date': self.trade_date,
            'freq': self.freq,
            'open': self.open_price,
            'high': self.high_price,
            'low': self.low_price,
            'close': self.close_price,
            'pre_close': self.pre_close,
            'volume': self.volume,
            'amount': self.amount,
            'change': self.change,