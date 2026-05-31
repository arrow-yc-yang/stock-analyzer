"""
分析结果模型
"""
from datetime import datetime
from . import db

class AnalysisResult(db.Model):
    """分析结果表"""
    __tablename__ = 'analysis_results'
    
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False, index=True)
    ts_code = db.Column(db.String(20), nullable=False, index=True)
    analysis_date = db.Column(db.String(20), nullable=False, index=True)  # 分析日期
    
    # 趋势分析
    short_trend = db.Column(db.String(20))  # 短期趋势：up/down/sideways
    mid_trend = db.Column(db.String(20))  # 中期趋势
    long_trend = db.Column(db.String(20))  # 长期趋势
    trend_strength = db.Column(db.Float)  # 趋势强度 0-100
    
    # 技术指标
    ma5 = db.Column(db.Float)  # 5日均线
    ma10 = db.Column(db.Float)  # 10日均线
    ma20 = db.Column(db.Float)  # 20日均线
    ma60 = db.Column(db.Float)  # 60日均线
    rsi = db.Column(db.Float)  # RSI指标
    macd_dif = db.Column(db.Float)  # MACD DIF
    macd_dea = db.Column(db.Float)  # MACD DEA
    macd_hist = db.Column(db.Float)  # MACD柱状图
    boll_upper = db.Column(db.Float)  # 布林带上轨
    boll_mid = db.Column(db.Float)  # 布林带中轨
    boll_lower = db.Column(db.Float)  # 布林带下轨
    atr = db.Column(db.Float)  # ATR指标
    
    # 战法匹配
    matched_strategies = db.Column(db.Text)  # 匹配的战法列表（JSON格式）
    strategy_scores = db.Column(db.Text)  # 战法评分（JSON格式）
    
    # 概率预测
    up_probability = db.Column(db.Float)  # 上涨概率
    down_probability = db.Column(db.Float)  # 下跌概率
    sideways_probability = db.Column(db.Float)  # 横盘概率
    
    # 买卖建议
    recommendation = db.Column(db.String(20))  # 建议：buy/sell/hold/wait
    confidence = db.Column(db.Float)  # 置信度 0-100
    entry_price = db.Column(db.Float)  # 建议买入价
    stop_loss = db.Column(db.Float)  # 止损价
    take_profit = db.Column(db.Float)  # 止盈价
    risk_reward_ratio = db.Column(db.Float)  # 盈亏比
    
    # 海龟交易信号
    turtle_signal = db.Column(db.String(20))  # 海龟信号：long/short/exit/none
    turtle_entry_price = db.Column(db.Float)  # 海龟入场价
    turtle_stop_price = db.Column(db.Float)  # 海龟止损价
    turtle_unit_size = db.Column(db.Integer)  # 海龟仓位单位
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AnalysisResult {self.ts_code} {self.analysis_date}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'ts_code': self.ts_code,
            'analysis_date': self.analysis_date,
            'short_trend': self.short_trend,
            'mid_trend': self.mid_trend,
            'long_trend': self.long_trend,
            'trend_strength': self.trend_strength,
            'indicators': {
                'ma5': self.ma5,
                'ma10': self.ma10,
                'ma20': self.ma20,
                'ma60': self.ma60,
                'rsi': self.rsi,
                'macd': {
                    'dif': self.macd_dif,
                    'dea': self.macd_dea,
                    'hist': self.macd_hist
                },
                'bollinger': {
                    'upper': self.boll_upper,
                    'mid': self.boll_mid,
                    'lower': self.boll_lower
                },
                'atr': self.atr
            },
            'matched_strategies': self.matched_strategies,
            'strategy_scores': self.strategy_scores,
            'probability': {
                'up': self.up_probability,
                'down': self.down_probability,
                'sideways': self.sideways_probability
            },
            'recommendation': {
                'action': self.recommendation,
                'confidence': self.confidence,
                'entry_price': self.entry_price,
                'stop_loss': self.stop_loss,
                'take_profit': self.take_profit,
                'risk_reward_ratio': self.risk_reward_ratio
            },
            'turtle_trading': {
                'signal': self.turtle_signal,
                'entry_price': self.turtle_entry_price,
                'stop_price': self.turtle_stop_price,
                'unit_size': self.turtle_unit_size