"""
股票基本信息模型
"""
from datetime import datetime
from . import db

class Stock(db.Model):
    """股票基本信息表"""
    __tablename__ = 'stocks'
    
    id = db.Column(db.Integer, primary_key=True)
    ts_code = db.Column(db.String(20), unique=True, nullable=False, index=True)  # Tushare代码
    symbol = db.Column(db.String(20), nullable=False)  # 股票代码
    name = db.Column(db.String(100), nullable=False)  # 股票名称
    area = db.Column(db.String(50))  # 地区
    industry = db.Column(db.String(50))  # 行业
    market = db.Column(db.String(20))  # 市场类型（主板/创业板/科创板）
    list_date = db.Column(db.String(20))  # 上市日期
    is_hs300 = db.Column(db.Boolean, default=False)  # 是否沪深300成分股
    is_custom = db.Column(db.Boolean, default=False)  # 是否自选
    stock_type = db.Column(db.String(20), default='stock')  # 类型：stock/index/etf
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    kline_data = db.relationship('KLineData', backref='stock', lazy=True, cascade='all, delete-orphan')
    analysis_results = db.relationship('AnalysisResult', backref='stock', lazy=True, cascade='all, delete-orphan')
    
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
