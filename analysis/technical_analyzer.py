"""
技术分析引擎
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TechnicalAnalyzer:
    """技术分析引擎"""
    
    def __init__(self):
        """初始化技术分析器"""
        pass
    
    def calculate_ma(self, df, periods=[5, 10, 20, 60, 120, 250]):
        """
        计算移动平均线
        
        Args:
            df: DataFrame包含close列
            periods: 周期列表
        
        Returns:
            DataFrame: 添加了MA列
        """
        df = df.copy()
        for period in periods:
            df[f'MA{period}'] = df['close'].rolling(window=period).mean()
        return df
    
    def calculate_ema(self, df, periods=[12, 26]):
        """计算指数移动平均线"""
        df = df.copy()
        for period in periods:
            df[f'EMA{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        return df
    
    def calculate_macd(self, df, fast=12, slow=26, signal=9):
        """
        计算MACD指标
        
        Args:
            df: DataFrame包含close列
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
        """
        df = df.copy()
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        
        df['MACD_DIF'] = ema_fast - ema_slow
        df['MACD_DEA'] = df['MACD_DIF'].ewm(span=signal, adjust=False).mean()
        df['MACD_HIST'] = 2 * (df['MACD_DIF'] - df['MACD_DEA'])
        
        return df
    
    def calculate_rsi(self, df, period=14):
        """
        计算RSI指标
        
        Args:
            df: DataFrame包含close列
            period: RSI周期
        """
        df = df.copy()
        delta = df['close'].diff()
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df
    
    def calculate_kdj(self, df, n=9, m1=3, m2=3):
        """
        计算KDJ指标
        
        Args:
            df: DataFrame包含high, low, close列
            n: RSV周期
            m1: K值平滑系数
            m2: D值平滑系数
        """
        df = df.copy()
        
        low_list = df['low'].rolling(window=n, min_periods=n).min()
        high_list = df['high'].rolling(window=n, min_periods=n).max()
        rsv = (df['close'] - low_list) / (high_list - low_list) * 100
        
        df['K'] = rsv.ewm(com=m1-1, adjust=False).mean()
        df['D'] = df['K'].ewm(com=m2-1, adjust=False).mean()
        df['J'] = 3 * df['K'] - 2 * df['D']
        
        return df
    
    def calculate_bollinger(self, df, period=20, std_dev=2):
        """
        计算布林带指标
        
        Args:
            df: DataFrame包含close列
            period: 周期
            std_dev: 标准差倍数
        """
        df = df.copy()
        df['BOLL_MID'] = df['close'].rolling(window=period).mean()
        df['BOLL_STD'] = df['close'].rolling(window=period).std()
        df['BOLL_UPPER'] = df['BOLL_MID'] + (df['BOLL_STD'] * std_dev)
        df['BOLL_LOWER'] = df['BOLL_MID'] - (df['BOLL_STD'] * std_dev)
        
        return df
    
    def calculate_atr(self, df, period=14):
        """
        计算ATR（平均真实波幅）
        
        Args:
            df: DataFrame包含high, low, close列
            period: ATR周期
        """
        df = df.copy()
        
        # 计算真实波幅
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        
        df['ATR'] = true_range.rolling(window=period).mean()
        
        return df
    
    def calculate_volume_ma(self, df, periods=[5, 10, 20]):
        """计算成交量均线"""
        df = df.copy()
        for period in periods:
            df[f'VOL_MA{period}'] = df['volume'].rolling(window=period).mean()
        return df
    
    def analyze_trend(self, df):
        """
        分析趋势 - 使用价格相对于均线的位置和均线斜率综合判断
        
        Returns:
            dict: 趋势分析结果
        """
        if len(df) < 60:
            return {'error': '数据不足，无法分析趋势'}
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # 辅助函数：判断均线是否在上升（斜率为正）
        def is_rising(ma_col, lookback=5):
            if ma_col not in df.columns:
                return False
            recent = df[ma_col].dropna().tail(lookback + 1)
            if len(recent) < lookback + 1:
                return False
            return recent.iloc[-1] > recent.iloc[0]
        
        # 辅助函数：判断均线是否在下降（斜率为负）
        def is_falling(ma_col, lookback=5):
            if ma_col not in df.columns:
                return False
            recent = df[ma_col].dropna().tail(lookback + 1)
            if len(recent) < lookback + 1:
                return False
            return recent.iloc[-1] < recent.iloc[0]
        
        close = latest['close']
        ma5 = latest.get('MA5', close)
        ma10 = latest.get('MA10', close)
        ma20 = latest.get('MA20', close)
        ma60 = latest.get('MA60', close)
        ma120 = latest.get('MA120', close)
        ma250 = latest.get('MA250', close)
        
        # 短期趋势（基于MA5和MA20的关系 + 价格位置 + MA斜率）
        short_score = 0  # 正=上涨，负=下跌
        if close > ma5: short_score += 1
        else: short_score -= 1
        if ma5 > ma20: short_score += 1
        else: short_score -= 1
        if is_rising('MA5'): short_score += 1
        else: short_score -= 1
        
        if short_score >= 2:
            short_trend = 'up'
        elif short_score <= -2:
            short_trend = 'down'
        else:
            short_trend = 'sideways'
        
        # 中期趋势（基于MA20和MA60的关系 + 价格位置 + MA斜率）
        mid_score = 0
        if close > ma20: mid_score += 1
        else: mid_score -= 1
        if ma20 > ma60: mid_score += 1
        else: mid_score -= 1
        if is_rising('MA20'): mid_score += 1
        else: mid_score -= 1
        
        if mid_score >= 2:
            mid_trend = 'up'
        elif mid_score <= -2:
            mid_trend = 'down'
        else:
            mid_trend = 'sideways'
        
        # 长期趋势（基于MA60和MA120/MA250的关系 + MA斜率）
        long_score = 0
        if ma60 > ma120: long_score += 1
        else: long_score -= 1
        if ma120 > ma250 if pd.notna(ma250) and ma250 > 0 else True: long_score += 1
        else: long_score -= 1
        if is_rising('MA60'): long_score += 1
        else: long_score -= 1
        
        if long_score >= 2:
            long_trend = 'up'
        elif long_score <= -2:
            long_trend = 'down'
        else:
            long_trend = 'sideways'
        
        # 计算趋势强度（0-100）
        trend_strength = 50
        if short_trend == mid_trend == long_trend == 'up':
            trend_strength = 90
        elif short_trend == mid_trend == long_trend == 'down':
            trend_strength = 10
        elif short_trend == 'up' and mid_trend == 'up':
            trend_strength = 70
        elif short_trend == 'down' and mid_trend == 'down':
            trend_strength = 30
        elif short_trend == 'up' and mid_trend == 'sideways':
            trend_strength = 60
        elif short_trend == 'down' and mid_trend == 'sideways':
            trend_strength = 40
        
        return {
            'short_trend': short_trend,
            'mid_trend': mid_trend,
            'long_trend': long_trend,
            'trend_strength': trend_strength,
            'current_price': close,
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'ma60': ma60,
            'ma120': ma120,
            'ma250': ma250
        }
    
    def analyze_support_resistance(self, df, window=20):
        """
        分析支撑阻力位
        
        Args:
            df: DataFrame
            window: 观察窗口
        
        Returns:
            dict: 支撑阻力位
        """
        if len(df) < window:
            return {'error': '数据不足'}
        
        recent = df.tail(window)
        
        # 简单支撑阻力（近期高低点）
        resistance = recent['high'].max()
        support = recent['low'].min()
        
        # 基于成交量的支撑阻力
        vol_weighted_high = (recent['high'] * recent['volume']).sum() / recent['volume'].sum()
        vol_weighted_low = (recent['low'] * recent['volume']).sum() / recent['volume'].sum()
        
        return {
            'resistance': resistance,
            'support': support,
            'vol_weighted_resistance': vol_weighted_high,
            'vol_weighted_support': vol_weighted_low,
            'price_range': resistance - support,
            'current_position': (df.iloc[-1]['close'] - support) / (resistance - support) if resistance != support else 0.5
        }
    
    def full_analysis(self, df):
        """
        完整技术分析
        
        Args:
            df: DataFrame包含ohlcv数据
        
        Returns:
            dict: 完整分析结果
        """
        if df.empty or len(df) < 20:
            return {'error': '数据不足'}
        
        # 计算所有指标
        df = self.calculate_ma(df)
        df = self.calculate_macd(df)
        df = self.calculate_rsi(df)
        df = self.calculate_kdj(df)
        df = self.calculate_bollinger(df)
        df = self.calculate_atr(df)
        df = self.calculate_volume_ma(df)
        
        # 趋势分析
        trend = self.analyze_trend(df)
        
        # 支撑阻力分析
        sr = self.analyze_support_resistance(df)
        
        latest = df.iloc[-1]
        
        return {
            'trend': trend,
            'support_resistance': sr,
            'indicators': {
                'rsi': latest.get('RSI'),
                'macd': {
                    'dif': latest.get('MACD_DIF'),
                    'dea': latest.get('MACD_DEA'),
                    'hist': latest.get('MACD_HIST')
                },
                'kdj': {
                    'k': latest.get('K'),
                    'd': latest.get('D'),
                    'j': latest.get('J')
                },
                'bollinger': {
                    'upper': latest.get('BOLL_UPPER'),
                    'mid': latest.get('BOLL_MID'),
                    'lower': latest.get('BOLL_LOWER')
                },
                'atr': latest.get('ATR'),
                'volume_ratio': latest['volume'] / latest.get('VOL_MA5', latest['volume']) if latest.get('VOL_MA5') else 1
            },
            'data': df
        }
