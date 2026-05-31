"""
走势概率预测模块
"""
import pandas as pd
import numpy as np
from scipy import stats
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProbabilityPredictor:
    """走势概率预测器"""
    
    def __init__(self):
        """初始化预测器"""
        pass
    
    def predict_trend_probability(self, df, analysis_result, days_forward=5):
        """
        预测未来走势概率
        
        Args:
            df: DataFrame包含历史数据
            analysis_result: 技术分析结果
            days_forward: 预测未来天数
        
        Returns:
            dict: 概率预测结果
        """
        if len(df) < 60:
            return {
                'up_probability': 33.3,
                'down_probability': 33.3,
                'sideways_probability': 33.4,
                'confidence': 30,
                'note': '数据不足，预测可靠性低'
            }
        
        latest = df.iloc[-1]
        current_price = latest['close']
        
        # 基于技术指标计算概率
        probabilities = self._calculate_indicator_based_probability(df, analysis_result)
        
        # 基于历史模式匹配计算概率
        pattern_probs = self._calculate_pattern_based_probability(df, days_forward)
        
        # 基于波动率计算概率
        volatility_probs = self._calculate_volatility_based_probability(df)
        
        # 综合概率（加权平均）
        weights = {
            'indicator': 0.4,
            'pattern': 0.35,
            'volatility': 0.25
        }
        
        up_prob = (
            probabilities['up'] * weights['indicator'] +
            pattern_probs['up'] * weights['pattern'] +
            volatility_probs['up'] * weights['volatility']
        )
        
        down_prob = (
            probabilities['down'] * weights['indicator'] +
            pattern_probs['down'] * weights['pattern'] +
            volatility_probs['down'] * weights['volatility']
        )
        
        sideways_prob = 100 - up_prob - down_prob
        
        # 确保概率在合理范围内
        up_prob = max(10, min(80, up_prob))
        down_prob = max(10, min(80, down_prob))
        sideways_prob = max(5, min(60, sideways_prob))
        
        # 归一化
        total = up_prob + down_prob + sideways_prob
        up_prob = up_prob / total * 100
        down_prob = down_prob / total * 100
        sideways_prob = sideways_prob / total * 100
        
        # 计算置信度
        confidence = self._calculate_confidence(df, analysis_result)
        
        # 预测目标价位
        price_targets = self._calculate_price_targets(df, up_prob, down_prob, days_forward)
        
        return {
            'up_probability': round(up_prob, 1),
            'down_probability': round(down_prob, 1),
            'sideways_probability': round(sideways_prob, 1),
            'confidence': round(confidence, 1),
            'price_targets': price_targets,
            'factors': {
                'technical_score': round(probabilities['up'] - probabilities['down'], 1),
                'pattern_match': pattern_probs.get('pattern_name', 'none'),
                'volatility_regime': volatility_probs.get('regime', 'normal')
            }
        }
    
    def _calculate_indicator_based_probability(self, df, analysis_result):
        """基于技术指标计算概率"""
        latest = df.iloc[-1]
        
        up_score = 50
        down_score = 50
        
        # RSI因素
        rsi = latest.get('RSI', 50)
        if rsi < 30:
            up_score += 15
            down_score -= 10
        elif rsi > 70:
            up_score -= 10
            down_score += 15
        elif 40 <= rsi <= 60:
            up_score += 5
            down_score += 5
        
        # MACD因素
        macd_hist = latest.get('MACD_HIST', 0)
        if macd_hist > 0:
            up_score += 10
            down_score -= 5
        else:
            up_score -= 5
            down_score += 10
        
        # 均线排列
        ma5 = latest.get('MA5', 0)
        ma10 = latest.get('MA10', 0)
        ma20 = latest.get('MA20', 0)
        
        if ma5 > ma10 > ma20:
            up_score += 15
            down_score -= 10
        elif ma5 < ma10 < ma20:
            up_score -= 10
            down_score += 15
        
        # 布林带位置
        boll_upper = latest.get('BOLL_UPPER', 0)
        boll_lower = latest.get('BOLL_LOWER', 0)
        boll_mid = latest.get('BOLL_MID', 0)
        
        if latest['close'] > boll_upper:
            up_score -= 5
            down_score += 10
        elif latest['close'] < boll_lower:
            up_score += 10
            down_score -= 5
        
        # 趋势强度
        trend_strength = analysis_result.get('trend', {}).get('trend_strength', 50)
        trend = analysis_result.get('trend', {}).get('short_trend', 'sideways')
        
        if trend == 'up':
            up_score += (trend_strength - 50) / 5
        elif trend == 'down':
            down_score += (100 - trend_strength) / 5
        
        # 归一化
        total = up_score + down_score
        up_prob = up_score / total * 100
        down_prob = down_score / total * 100
        
        return {
            'up': up_prob,
            'down': down_prob
        }
    
    def _calculate_pattern_based_probability(self, df, days_forward):
        """基于历史模式匹配计算概率"""
        if len(df) < 30:
            return {'up': 33.3, 'down': 33.3, 'pattern_name': 'none'}
        
        # 获取最近的价格走势特征
        recent = df.tail(10)
        current_pattern = {
            'trend': 'up' if recent['close'].iloc[-1] > recent['close'].iloc[0] else 'down',
            'volatility': recent['close'].std() / recent['close'].mean(),
            'volume_trend': 'up' if recent['volume'].iloc[-1] > recent['volume'].mean() else 'down'
        }
        
        # 在历史数据中寻找相似模式
        similar_outcomes = []
        
        for i in range(30, len(df) - days_forward):
            window = df.iloc[i-10:i]
            
            pattern = {
                'trend': 'up' if window['close'].iloc[-1] > window['close'].iloc[0] else 'down',
                'volatility': window['close'].std() / window['close'].mean(),
                'volume_trend': 'up' if window['volume'].iloc[-1] > window['volume'].mean() else 'down'
            }
            
            # 简单相似度判断
            if pattern['trend'] == current_pattern['trend'] and pattern['volume_trend'] == current_pattern['volume_trend']:
                # 查看后续走势
                future = df.iloc[i:i+days_forward]
                price_change = (future['close'].iloc[-1] - window['close'].iloc[-1]) / window['close'].iloc[-1]
                similar_outcomes.append(price_change)
        
        if not similar_outcomes:
            return {'up': 33.3, 'down': 33.3, 'pattern_name': 'no_similar'}
        
        # 统计相似模式的后续走势
        up_count = sum(1 for x in similar_outcomes if x > 0.01)
        down_count = sum(1 for x in similar_outcomes if x < -0.01)
        total = len(similar_outcomes)
        
        up_prob = up_count / total * 100
        down_prob = down_count / total * 100
        
        return {
            'up': up_prob,
            'down': down_prob,
            'pattern_name': f'similar_{len(similar_outcomes)}',
            'avg_change': np.mean(similar_outcomes) * 100
        }
    
    def _calculate_volatility_based_probability(self, df):
        """基于波动率计算概率"""
        if len(df) < 20:
            return {'up': 33.3, 'down': 33.3, 'regime': 'unknown'}
        
        # 计算历史波动率
        returns = df['close'].pct_change().dropna()
        current_vol = returns.tail(20).std() * np.sqrt(252)  # 年化波动率
        hist_vol = returns.std() * np.sqrt(252)
        
        # 判断波动率状态
        if current_vol > hist_vol * 1.3:
            regime = 'high_volatility'
            # 高波动率时，趋势延续概率降低，反转概率增加
            up_prob = 35
            down_prob = 35
        elif current_vol < hist_vol * 0.7:
            regime = 'low_volatility'
            # 低波动率时，可能即将突破
            up_prob = 40
            down_prob = 30
        else:
            regime = 'normal'
            up_prob = 40
            down_prob = 35
        
        return {
            'up': up_prob,
            'down': down_prob,
            'regime': regime,
            'current_vol': round(current_vol * 100, 2),
            'hist_vol': round(hist_vol * 100, 2)
        }
    
    def _calculate_confidence(self, df, analysis_result):
        """计算预测置信度"""
        confidence = 50
        
        # 数据量
        if len(df) >= 250:
            confidence += 10
        elif len(df) >= 120:
            confidence += 5
        
        # 趋势一致性
        trend = analysis_result.get('trend', {})
        if trend.get('short_trend') == trend.get('mid_trend') == trend.get('long_trend'):
            confidence += 15
        elif trend.get('short_trend') == trend.get('mid_trend'):
            confidence += 8
        
        # 指标一致性
        indicators = analysis_result.get('indicators', {})
        rsi = indicators.get('rsi', 50)
        macd_hist = indicators.get('macd', {}).get('hist', 0)
        
        # RSI和MACD同向
        if (rsi < 40 and macd_hist > 0) or (rsi > 60 and macd_hist < 0):
            confidence += 10
        
        return min(95, confidence)
    
    def _calculate_price_targets(self, df, up_prob, down_prob, days_forward):
        """计算目标价位"""
        latest = df.iloc[-1]
        current_price = latest['close']
        atr = latest.get('ATR', current_price * 0.02)
        
        # 基于ATR和概率计算目标价位
        volatility_factor = atr * np.sqrt(days_forward)
        
        # 上涨目标
        if up_prob > 50:
            up_target = current_price + volatility_factor * (up_prob / 50)
        else:
            up_target = current_price + volatility_factor * 0.5
        
        # 下跌目标
        if down_prob > 50:
            down_target = current_price - volatility_factor * (down_prob / 50)
        else:
            down_target = current_price - volatility_factor * 0.5
        
        # 横盘区间
        sideways_range = volatility_factor * 0.5
        
        return {
            'current_price': round(current_price, 2),
            'up_target': round(up_target, 2),
            'down_target': round(down_target, 2),
            'sideways_upper': round(current_price + sideways_range, 2),
            'sideways_lower': round(current_price - sideways_range, 2),
            'expected_move': round((up_prob/100 * (up_target - current_price) + 
                                   down_prob/100 * (down_target - current_price)) / current_price * 100, 2)
        }
    
    def predict_scenarios(self, df, days_forward=5):
        """
        预测多种情景
        
        Returns:
            dict: 多种情景预测
        """
        base_prediction = self.predict_trend_probability(df, {}, days_forward)
        
        scenarios = {
            'bullish': {
                'description': '乐观情景',
                'probability': base_prediction['up_probability'] * 1.2,
                'price_change': '+5% ~ +10%',
                'conditions': '市场情绪和资金面配合，突破关键阻力位'
            },
            'base': {
                'description': '基准情景',
                'probability': 50,
                'price_change': f"{base_prediction['price_targets']['expected_move']}%",
                'conditions': '按当前趋势和技术面正常发展