"""
回测结果模型
"""
from datetime import datetime
from . import db

class BacktestResult(db.Model):
    """回测结果表"""
    __tablename__ = 'backtest_results'
    
    id = db.Column(db.Integer, primary_key=True)
    strategy_name = db.Column(db.String(100), nullable=False, index=True)  # 策略名称
    ts_code = db.Column(db.String(20), nullable=False, index=True)  # 股票代码（all表示全市场）
    
    # 回测参数
    start_date = db.Column(db.String(20), nullable=False)  # 开始日期
    end_date = db.Column(db.String(20), nullable=False)  # 结束日期
    initial_capital = db.Column(db.Float, default=100000)  # 初始资金
    
    # 回测结果
    final_capital = db.Column(db.Float)  # 最终资金
    total_return = db.Column(db.Float)  # 总收益率(%)
    annual_return = db.Column(db.Float)  # 年化收益率(%)
    max_drawdown = db.Column(db.Float)  # 最大回撤(%)
    sharpe_ratio = db.Column(db.Float)  # 夏普比率
    
    # 交易统计
    total_trades = db.Column(db.Integer)  # 总交易次数
    winning_trades = db.Column(db.Integer)  # 盈利次数
    losing_trades = db.Column(db.Integer)  # 亏损次数
    win_rate = db.Column(db.Float)  # 胜率(%)
    avg_profit = db.Column(db.Float)  # 平均盈利
    avg_loss = db.Column(db.Float)  # 平均亏损
    profit_factor = db.Column(db.Float)  # 盈亏比
    
    # 详细交易记录（JSON格式）
    trade_records = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<BacktestResult {self.strategy_name} {self.ts_code}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'strategy_name': self.strategy_name,
            'ts_code': self.ts_code,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'avg_profit': self.avg_profit,
            'avg_loss': self.avg_loss,
            'profit_factor': self.profit_factor,
            'trade_records': self.trade_records,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
