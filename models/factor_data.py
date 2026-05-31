"""
因子数据模型
"""
from datetime import datetime
from . import db

class FactorData(db.Model):
    """因子数据表"""
    __tablename__ = 'factor_data'

    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False, index=True)
    stock = db.relationship('Stock', backref='factor_data')
    ts_code = db.Column(db.String(20), nullable=False, index=True)
    trade_date = db.Column(db.String(20), nullable=False, index=True)

    pe_ttm = db.Column(db.Float)
    pb = db.Column(db.Float)
    ps_ttm = db.Column(db.Float)
    total_mv = db.Column(db.Float)
    circ_mv = db.Column(db.Float)
    dv_ratio = db.Column(db.Float)
    turnover_rate = db.Column(db.Float)

    revenue_yoy = db.Column(db.Float)
    profit_yoy = db.Column(db.Float)
    roe_yoy = db.Column(db.Float)
    eps_yoy = db.Column(db.Float)

    roe = db.Column(db.Float)
    roa = db.Column(db.Float)
    grossprofit_margin = db.Column(db.Float)
    netprofit_margin = db.Column(db.Float)

    debt_to_assets = db.Column(db.Float)
    current_ratio = db.Column(db.Float)
    quick_ratio = db.Column(db.Float)

    composite_score = db.Column(db.Float)
    value_score = db.Column(db.Float)
    growth_score = db.Column(db.Float)
    quality_score = db.Column(db.Float)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('ts_code', 'trade_date', name='uix_factor'),
    )

    def __repr__(self):
        return f'<FactorData {self.ts_code} {self.trade_date}>'

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