"""
买卖建议引擎
"""
import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecommendationEngine:
    """买卖建议引擎"""
    
    def __init__(self):
        """初始化建议引擎"""
        pass
    
    def generate_recommendation(self, df, analysis_result, strategy_result, probability_result, turtle_result):
        """
        生成综合买卖建议
        
        Args:
            df: DataFrame
            analysis_result: 技术分析结果
            strategy_result: 战法匹配结果
            probability_result: 概率预测结果
            turtle_result: 海龟交易结果
        
        Returns:
            dict: 买卖建议
        """
        latest = df.iloc[-1]
        current_price = latest['close']
        
        # 综合评分
        scores = self._calculate_composite_score(
            analysis_result, 
            strategy_result, 
            probability_result, 
            turtle_result
        )
        
        # 确定操作建议
        action = self._determine_action(scores, analysis_result)
        
        # 计算入场价位
        entry_levels = self._calculate_entry_levels(df, analysis_result, action)
        
        # 计算止盈止损
        risk_management = self._calculate_risk_management(df, analysis_result, action, current_price)
        
        # 生成建议描述
        description = self._generate_description(
            action, scores, analysis_result, strategy_result, turtle_result
        )
        
        return {
            'action': action['action'],
            'confidence': round(action['confidence'], 1),
            'urgency': action['urgency'],
            'current_price': round(current_price, 2),
            'entry_levels': entry_levels,
            'risk_management': risk_management,
            'description': description,
            'scores': scores,
            'timeframe': self._determine_timeframe(analysis_result),
            'warnings': self._generate_warnings(analysis_result, probability_result)
        }
    
    def _calculate_composite_score(self, analysis_result, strategy_result, probability_result, turtle_result):
        """计算综合评分"""
        scores = {
            'technical': 50,
            'trend': 50,
            'pattern': 50,
            'turtle': 50,
            'probability': 50
        }
        
        # 技术面评分
        trend = analysis_result.get('trend', {})
        if trend.get('short_trend') == 'up':
            scores['technical'] += 20
        elif trend.get('short_trend') == 'down':
            scores['technical'] -= 20
        
        trend_strength = trend.get('trend_strength', 50)
        scores['technical'] += (trend_strength - 50) / 2
        
        # 趋势评分
        if trend.get('short_trend') == trend.get('mid_trend') == trend.get('long_trend') == 'up':
            scores['trend'] = 85
        elif trend.get('short_trend') == trend.get('mid_trend') == trend.get('long_trend') == 'down':
            scores['trend'] = 15
        elif trend.get('short_trend') == trend.get('mid_trend') == 'up':
            scores['trend'] = 70
        elif trend.get('short_trend') == trend.get('mid_trend') == 'down':
            scores['trend'] = 30
        
        # 战法评分
        if strategy_result.get('matched_strategies'):
            primary = strategy_result.get('primary_strategy', {})
            if primary.get('signal') == 'buy':
                scores['pattern'] = 60 + primary.get('confidence', 50) / 5
            elif primary.get('signal') == 'sell':
                scores['pattern'] = 40 - primary.get('confidence', 50) / 5
        
        # 海龟交易评分
        if turtle_result.get('direction') == 'long':
            scores['turtle'] = 75
        elif turtle_result.get('direction') == 'short':
            scores['turtle'] = 25
        
        # 概率评分
        up_prob = probability_result.get('up_probability', 33)
        down_prob = probability_result.get('down_probability', 33)
        scores['probability'] = up_prob
        
        # 综合评分
        weights = {
            'technical': 0.25,
            'trend': 0.25,
            'pattern': 0.20,
            'turtle': 0.15,
            'probability': 0.15
        }
        
        composite = sum(scores[k] * weights[k] for k in scores)
        scores['composite'] = round(composite, 1)
        
        return scores
    
    def _determine_action(self, scores, analysis_result):
        """确定操作建议"""
        composite = scores['composite']
        
        if composite >= 65:
            action = 'buy'
            confidence = composite
            urgency = 'high' if composite >= 80 else 'medium'
        elif composite <= 35:
            action = 'sell'
            confidence = 100 - composite
            urgency = 'high' if composite <= 20 else 'medium'
        elif 40 <= composite <= 60:
            action = 'hold'
            confidence = 50
            urgency = 'low'
        else:
            action = 'wait'
            confidence = abs(composite - 50) + 50
            urgency = 'low'
        
        return {
            'action': action,
            'confidence': confidence,
            'urgency': urgency,
            'composite_score': composite
        }
    
    def _calculate_entry_levels(self, df, analysis_result, action):
        """计算入场价位"""
        latest = df.iloc[-1]
        current_price = latest['close']
        sr = analysis_result.get('support_resistance', {})
        
        if action['action'] == 'buy':
            # 买入价位建议
            aggressive = current_price  # 激进：现价买入
            moderate = sr.get('support', current_price * 0.98)  # 稳健：支撑位附近
            conservative = latest.get('MA20', current_price * 0.95)  # 保守：MA20附近
            
            return {
                'aggressive': round(aggressive, 2),
                'moderate': round(moderate, 2),
                'conservative': round(conservative, 2),
                'recommended': 'moderate'
            }
        
        elif action['action'] == 'sell':
            # 卖出价位建议
            aggressive = current_price  # 激进：现价卖出
            moderate = sr.get('resistance', current_price * 1.02)  # 稳健：阻力位附近
            conservative = latest.get('MA20', current_price * 1.05)  # 保守：MA20附近
            
            return {
                'aggressive': round(aggressive, 2),
                'moderate': round(moderate, 2),
                'conservative': round(conservative, 2),
                'recommended': 'moderate'
            }
        
        else:  # hold 或 wait
            # 观察价位
            return {
                'buy_trigger': round(sr.get('support', current_price * 0.97), 2),
                'sell_trigger': round(sr.get('resistance', current_price * 1.03), 2),
                'note': '等待价格到达触发价位再操作'
            }
    
    def _calculate_risk_management(self, df, analysis_result, action, current_price):
        """计算风险管理参数"""
        latest = df.iloc[-1]
        atr = latest.get('ATR', current_price * 0.02)
        sr = analysis_result.get('support_resistance', {})
        
        if action['action'] == 'buy':
            # 买入后的止盈止损
            stop_loss = max(
                sr.get('support', current_price * 0.95),
                current_price - 2 * atr
            )
            
            take_profit_1 = current_price + 2 * atr  # 第一目标
            take_profit_2 = sr.get('resistance', current_price * 1.08)  # 第二目标
            take_profit_3 = current_price + 4 * atr  # 第三目标
            
            risk = current_price - stop_loss
            reward = take_profit_1 - current_price
            risk_reward = reward / risk if risk > 0 else 0
            
            return {
                'stop_loss': round(stop_loss, 2),
                'take_profit_1': round(take_profit_1, 2),
                'take_profit_2': round(take_profit_2, 2),
                'take_profit_3': round(take_profit_3, 2),
                'risk_amount': round(risk, 2),
                'risk_percent': round(risk / current_price * 100, 2),
                'risk_reward_ratio': round(risk_reward, 2),
                'position_size': self._suggest_position_size(risk_reward)
            }
        
        elif action['action'] == 'sell':
            # 卖出后的回补或做空参数
            stop_loss = min(
                sr.get('resistance', current_price * 1.05),
                current_price + 2 * atr
            )
            
            take_profit_1 = current_price - 2 * atr
            take_profit_2 = sr.get('support', current_price * 0.92)
            
            risk = stop_loss - current_price
            reward = current_price - take_profit_1
            risk_reward = reward / risk if risk > 0 else 0
            
            return {
                'stop_loss': round(stop_loss, 2),
                'take_profit_1': round(take_profit_1, 2),
                'take_profit_2': round(take_profit_2, 2),
                'risk_amount': round(risk, 2),
                'risk_percent': round(risk / current_price * 100, 2),
                'risk_reward_ratio': round(risk_reward, 2)
            }
        
        return {
            'note': '当前不建议操作，暂不设置止盈止损',
            'watch_levels': {
                'support': round(sr.get('support', current_price * 0.95), 2),
                'resistance': round(sr.get('resistance', current_price * 1.05), 2)
            }
        }
    
    def _suggest_position_size(self, risk_reward_ratio):
        """建议仓位大小"""
        if risk_reward_ratio >= 2:
            return 'full'  # 全仓
        elif risk_reward_ratio >= 1.5:
            return 'half'  # 半仓
        elif risk_reward_ratio >= 1:
            return 'quarter'  # 四分之一仓
        else:
            return 'none'  # 不建议
    
    def _generate_description(self, action, scores, analysis_result, strategy_result, turtle_result):
        """生成建议描述"""
        descriptions = []
        
        action_desc = {
            'buy': '建议买入',
            'sell': '建议卖出',
            'hold': '建议持有',
            'wait': '建议观望'
        }
        
        descriptions.append(f"【操作】{action_desc.get(action['action'], '观望')}")
        descriptions.append(f"【信心度】{action['confidence']:.0f}%")
        descriptions.append(f"【紧急程度】{'高' if action['urgency'] == 'high' else '中' if action['urgency'] == 'medium' else '低'}")
        
        # 趋势描述
        trend = analysis_result.get('trend', {})
        trend_desc = f"【趋势】短期{trend.get('short_trend', '震荡')}，中期{trend.get('mid_trend', '震荡')}，长期{trend.get('long_trend', '震荡')}"
        descriptions.append(trend_desc)
        
        # 战法描述
        if strategy_result.get('matched_strategies'):
            primary = strategy_result.get('primary_strategy', {})
            descriptions.append(f"【战法】{primary.get('description', '')}")
        
        # 海龟交易描述
        if turtle_result.get('direction') and turtle_result['direction'] != 'none':
            descriptions.append(f"【海龟信号】{turtle_result.get('description', '')}")
        
        return '\n'.join(descriptions)
    
    def _determine_timeframe(self, analysis_result):
        """确定操作周期"""
        trend = analysis_result.get('trend', {})
        
        if trend.get('short_trend') == trend.get('mid_trend'):
            if trend.get('short_trend') == 'up':
                return {
                    'primary': 'short_term',
                    'description': '短线为主，可持仓1-5天',
                    'hold_period': '1-5天'
                }
            else:
                return {
                    'primary': 'short_term',
                    'description': '短线为主，建议减仓或观望',
                    'hold_period': '1-3天'
                }
        
        return {
            'primary': 'swing',
            'description': '波段操作为主，可持仓1-4周',
            'hold_period': '1-4周'
        }
    
    def _generate_warnings(self, analysis_result, probability_result):
        """生成风险提示"""
        warnings = []
        
        # RSI警告
        indicators = analysis_result.get('indicators', {})
        rsi = indicators.get('rsi', 50)
        if rsi > 75:
            warnings.append('RSI超买，注意回调风险')
        elif rsi < 25:
            warnings.append('RSI超卖，可能反弹但需谨慎')
        
        # 概率警告
        confidence = probability_result.get('confidence', 50)
        if co