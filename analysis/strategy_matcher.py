"""
战法匹配系统
"""
import pandas as pd
import numpy as np
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StrategyMatcher:
    """战法匹配系统"""
    
    def __init__(self):
        """初始化战法匹配器"""
        self.strategies = {
            'golden_cross': self.check_golden_cross,
            'death_cross': self.check_death_cross,
            'macd_divergence': self.check_macd_divergence,
            'breakout': self.check_breakout,
            'pullback': self.check_pullback,
            'volume_price_divergence': self.check_volume_price_divergence,
            'rsi_reversal': self.check_rsi_reversal,
            'bollinger_squeeze': self.check_bollinger_squeeze,
            'head_and_shoulders': self.check_head_and_shoulders,
            'double_bottom': self.check_double_bottom,
            'ascending_triangle': self.check_ascending_triangle,
            'flag_pattern': self.check_flag_pattern
        }
    
    def match_all_strategies(self, df, analysis_result):
        """
        匹配所有战法
        
        Args:
            df: DataFrame包含技术指标
            analysis_result: 技术分析结果
        
        Returns:
            list: 匹配的战法列表
        """
        matched = []
        scores = {}
        
        for strategy_name, strategy_func in self.strategies.items():
            try:
                result = strategy_func(df, analysis_result)
                if result['matched']:
                    matched.append({
                        'name': strategy_name,
                        'signal': result.get('signal', 'neutral'),
                        'description': result.get('description', ''),
                        'confidence': result.get('confidence', 50)
                    })
                    scores[strategy_name] = result.get('confidence', 50)
            except Exception as e:
                logger.warning(f"战法 {strategy_name} 匹配失败: {e}")
                continue
        
        return {
            'matched_strategies': matched,
            'strategy_scores': scores,
            'primary_strategy': matched[0] if matched else None,
            'strategy_count': len(matched)
        }
    
    def check_golden_cross(self, df, analysis):
        """检查金叉战法（MA5上穿MA10或MA20）"""
        if len(df) < 3:
            return {'matched': False}
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # MA5上穿MA10
        ma5_cross = prev.get('MA5', 0) <= prev.get('MA10', 0) and latest.get('MA5', 0) > latest.get('MA10', 0)
        # MA5上穿MA20
        ma20_cross = prev.get('MA5', 0) <= prev.get('MA20', 0) and latest.get('MA5', 0) > latest.get('MA20', 0)
        
        if ma5_cross or ma20_cross:
            confidence = 70 if ma5_cross and ma20_cross else 60
            return {
                'matched': True,
                'signal': 'buy',
                'description': f'{"双重" if ma5_cross and ma20_cross else ""}均线金叉，短期趋势转强',
                'confidence': confidence
            }
        
        return {'matched': False}
    
    def check_death_cross(self, df, analysis):
        """检查死叉战法（MA5下穿MA10或MA20）"""
        if len(df) < 3:
            return {'matched': False}
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        ma5_cross = prev.get('MA5', 0) >= prev.get('MA10', 0) and latest.get('MA5', 0) < latest.get('MA10', 0)
        ma20_cross = prev.get('MA5', 0) >= prev.get('MA20', 0) and latest.get('MA5', 0) < latest.get('MA20', 0)
        
        if ma5_cross or ma20_cross:
            confidence = 70 if ma5_cross and ma20_cross else 60
            return {
                'matched': True,
                'signal': 'sell',
                'description': f'{"双重" if ma5_cross and ma20_cross else ""}均线死叉，短期趋势转弱',
                'confidence': confidence
            }
        
        return {'matched': False}
    
    def check_macd_divergence(self, df, analysis):
        """检查MACD背离战法"""
        if len(df) < 20:
            return {'matched': False}
        
        # 检查顶背离（价格新高，MACD未新高）
        recent = df.tail(20)
        price_high_idx = recent['close'].idxmax()
        macd_high_idx = recent['MACD_DIF'].idxmax()
        
        top_divergence = price_high_idx != macd_high_idx and recent.loc[price_high_idx, 'close'] > recent.loc[macd_high_idx, 'close']
        
        # 检查底背离（价格新低，MACD未新低）
        price_low_idx = recent['close'].idxmin()
        macd_low_idx = recent['MACD_DIF'].idxmin()
        
        bottom_divergence = price_low_idx != macd_low_idx and recent.loc[price_low_idx, 'close'] < recent.loc[macd_low_idx, 'close']
        
        if top_divergence:
            return {
                'matched': True,
                'signal': 'sell',
                'description': 'MACD顶背离，价格与指标背离，注意回调风险',
                'confidence': 75
            }
        elif bottom_divergence:
            return {
                'matched': True,
                'signal': 'buy',
                'description': 'MACD底背离，价格与指标背离，可能反弹',
                'confidence': 75
            }
        
        return {'matched': False}
    
    def check_breakout(self, df, analysis):
        """检查突破战法"""
        if len(df) < 20:
            return {'matched': False}
        
        latest = df.iloc[-1]
        prev_high = df['high'].tail(20).iloc[:-1].max()
        prev_low = df['low'].tail(20).iloc[:-1].min()
        
        # 向上突破
        if latest['close'] > prev_high and latest['volume'] > latest.get('VOL_MA5', latest['volume']) * 1.5:
            return {
                'matched': True,
                'signal': 'buy',
                'description': f'放量突破前期高点{prev_high:.2f}，趋势可能延续',
                'confidence': 80
            }
        
        # 向下突破
        if latest['close'] < prev_low and latest['volume'] > latest.get('VOL_MA5', latest['volume']) * 1.5:
            return {
                'matched': True,
                'signal': 'sell',
                'description': f'放量跌破前期低点{prev_low:.2f}，注意止损',
                'confidence': 80
            }
        
        return {'matched': False}
    
    def check_pullback(self, df, analysis):
        """检查回调战法（上升趋势中的回调买入）"""
        if len(df) < 30:
            return {'matched': False}
        
        latest = df.iloc[-1]
        
        # 判断上升趋势
        is_uptrend = latest.get('MA20', 0) > latest.get('MA60', 0)
        
        # 判断回调（价格在MA20附近，RSI从超买区回落）
        near_ma20 = abs(latest['close'] - latest.get('MA20', latest['close'])) / latest['close'] < 0.02
        rsi_pullback = 40 < latest.get('RSI', 50) < 60
        
        if is_uptrend and near_ma20 and rsi_pullback:
            return {
                'matched': True,
                'signal': 'buy',
                'description': '上升趋势中的健康回调，可考虑逢低买入',
                'confidence': 65
            }
        
        return {'matched': False}
    
    def check_volume_price_divergence(self, df, analysis):
        """检查量价背离战法"""
        if len(df) < 10:
            return {'matched': False}
        
        recent = df.tail(5)
        
        # 价涨量缩（上涨乏力）
        price_up_vol_down = (recent['close'].iloc[-1] > recent['close'].iloc[0] and 
                            recent['volume'].mean() < df['volume'].tail(20).iloc[:-5].mean() * 0.8)
        
        # 价跌量缩（下跌趋缓）
        price_down_vol_down = (recent['close'].iloc[-1] < recent['close'].iloc[0] and 
                              recent['volume'].mean() < df['volume'].tail(20).iloc[:-5].mean() * 0.8)
        
        if price_up_vol_down:
            return {
                'matched': True,
                'signal': 'sell',
                'description': '价涨量缩，上涨动能不足，注意回调',
                'confidence': 70
            }
        elif price_down_vol_down:
            return {
                'matched': True,
                'signal': 'buy',
                'description': '价跌量缩，抛压减轻，可能企稳',
                'confidence': 65
            }
        
        return {'matched': False}
    
    def check_rsi_reversal(self, df, analysis):
        """检查RSI反转战法"""
        if len(df) < 3:
            return {'matched': False}
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 超卖反弹
        oversold_bounce = prev.get('RSI', 50) < 30 and latest.get('RSI', 50) > prev.get('RSI', 50)
        
        # 超买回调
        overbought_pullback = prev.get('RSI', 50) > 70 and latest.get('RSI', 50) < prev.get('RSI', 50)
        
        if oversold_bounce:
            return {
                'matched': True,
                'signal': 'buy',
                'description': f'RSI超卖反弹（RSI: {latest.get("RSI", 0):.1f}），短期可能反弹',
                'confidence': 70
            }
        elif overbought_pullback:
            return {
                'matched': True,
                'signal': 'sell',
                'description': f'RSI超买回调（RSI: {latest.get("RSI", 0):.1f}），注意获利了结',
                'confidence': 70
            }
        
        return {'matched': False}
    
    def check_bollinger_squeeze(self, df, analysis):
        """检查布林带挤压战法（波动率收缩后扩张）"""
        if len(df) < 30:
            return {'matched': False}
        
        recent = df.tail(20)
        
        # 计算布林带宽度
        recent['boll_width'] = (recent['BOLL_UPPER'] - recent['BOLL_LOWER']) / recent['BOLL_MID']
        
        # 检查是否处于挤压状态（带宽处于近期低位）
        current_width = recent['boll_width'].iloc[-1]
        avg_width = recent['boll_width'].mean()
        
        if current_width < avg_width * 0.8:
            latest = df.iloc[-1]
            
            # 判断突破方向
            if latest['close'] > latest['BOLL_UPPER']:
                return {
                    'matched': True,
                    'signal': 'buy',
                    'description': '布林带挤压后向上突破，波动率扩张，趋势启动',
                    'confidence': 75
                }
            elif latest['close'] < latest['BOLL_LOWER']:
                return {
                    'matched': True,
                    'signal': 'sell',
                    'description': '布林带挤压后向下突破，波动率扩张，趋势启动',
                    'confidence': 75
                }
        
        return {'matched': False}
    
    def check_head_and_shoulders(self, df, analysis):
        """检查头肩顶/底形态"""
        if len(df) < 60:
            return {'matched': False}
        
        # 简化的头肩形态检测（基于局部极值）
        highs = df['high'].rolling(window=5, center=True).max()
        lows = df['low'].rolling(window=5, center=True).min()
        
        # 查找局部高点
        local_highs = df[df['high'] == highs]['high'].tail(10)
        
        if len(local_highs) >= 3:
            # 检查是否形成头肩顶（中间高，两边低且相近）
            h1, h2, h3 = local_highs.iloc[-3], local_highs.iloc[-2], local_highs.iloc[-1]
            
            if h2 > h1 and h2 > h3 and abs(h1 - h3) / h2 < 0.03:
                return {
                    'matched': True,
                    'signal': 'sell',
                    'description': '疑似头肩顶形态，注意趋势反转风险',
                    'confidence': 70
                }
        
        return {'matched': False}
    
    def check_double_bottom(self, df, analysis):
        """检查双底形态"""
        if len(df) < 60:
            return {'matched': False}
        
        lows = df['low'].rolling(window=5, center=True).min()
        local_lows = df[df['low'] == lows]['low'].tail(10)
        
        if len(local_lows) >= 2:
            l1, l2 = local_lows.iloc[-2], local_lows.iloc[-1]
            
            # 双底：两个低点相近，第二个低点后反弹
            if abs(l1 - l2) / l1 < 0.02 and df.iloc[-1]['close'] > l2 * 1.03:
                return {
                    'matched': True,
                    'signal': 'buy',
                    'description': '疑似双底形态，可能形成底部反转',
                    'confidence': 75
                }
        
        return {'matched': False}
    
    def check_ascending_triangle(self, df, analysis):
        """检查上升三角形"""
        if len(df) < 30:
            return {'matched': False}
        
        recent = df.tail(30)
        
        # 简化的上升三角形检测
        highs = recent['high'].tail(15)
        lows = recent['low'].tail(15)
        
        # 高点相对持平，低点逐步抬高
        high_flat = highs.std() / highs.mean() < 0.02
        low_rising = lows.iloc[-1] > lows.iloc[0] * 1.05
        
        if high_flat and low_rising:
            return {
                'matched': True,
                'signal': 'buy',
                'description': '疑似上升三角形，等待向上突破',
                'confidence': 65
            }
        
        return {'matched': False}
    
    def check_flag_pattern(self, df, analysis):
        """检查旗形/三角旗形态"""
        if len(df) < 40:
            return {'matched': False}
        
        # 简化的旗形检测
        recent = df.tail(40)
        
        # 检查是否有明显的趋势（旗杆）
        flagpole = recent.head(10)
        flag = recent.tail(30)
        
        # 上升趋势后的旗形
        up_trend = flagpole['close'].iloc[-1] > flagpole['close'].iloc[0] * 1.1
        consolidation = flag['high'].max() < flagpole['high'].max() and flag['low'].min() > flagpole['low'].min()
        
        if up_trend and consolidation:
            latest = df.iloc[-1]
            if latest['close'] > flag['high'].max():
                return {
                    'matched': True,
                    'signal': 'buy',
                    'description': '上升旗形突破，趋势延续',
                    'confidence': 75
                }
        
        return {'matched': False}
