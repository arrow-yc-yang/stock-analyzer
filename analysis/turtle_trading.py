"""
海龟交易法则实现
"""
import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TurtleTrading:
    """海龟交易系统"""
    
    def __init__(self, entry_days=20, exit_days=10, atr_days=20, risk_percent=0.01):
        """
        初始化海龟交易系统
        
        Args:
            entry_days: 入场周期（20日高点）
            exit_days: 出场周期（10日低点）
            atr_days: ATR计算周期
            risk_percent: 单笔风险比例（1%）
        """
        self.entry_days = entry_days
        self.exit_days = exit_days
        self.atr_days = atr_days
        self.risk_percent = risk_percent
    
    def calculate_donchian_channel(self, df):
        """
        计算唐奇安通道
        
        Args:
            df: DataFrame包含high, low, close列
        
        Returns:
            DataFrame: 添加了唐奇安通道
        """
        df = df.copy()
        
        # 上轨：N日最高价
        df['DC_UPPER'] = df['high'].rolling(window=self.entry_days).max()
        # 下轨：N日最低价
        df['DC_LOWER'] = df['low'].rolling(window=self.entry_days).min()
        # 中轨
        df['DC_MID'] = (df['DC_UPPER'] + df['DC_LOWER']) / 2
        
        # 出场通道
        df['EXIT_UPPER'] = df['high'].rolling(window=self.exit_days).max()
        df['EXIT_LOWER'] = df['low'].rolling(window=self.exit_days).min()
        
        return df
    
    def calculate_atr(self, df):
        """
        计算ATR（平均真实波幅）
        
        Args:
            df: DataFrame包含high, low, close列
        
        Returns:
            DataFrame: 添加了ATR
        """
        df = df.copy()
        
        # 真实波幅
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        
        # ATR
        df['ATR'] = true_range.rolling(window=self.atr_days).mean()
        df['TR'] = true_range
        
        return df
    
    def calculate_position_size(self, capital, atr, price):
        """
        计算仓位大小（单位）
        
        Args:
            capital: 总资金
            atr: ATR值
            price: 当前价格
        
        Returns:
            int: 交易单位（股数）
        """
        if atr == 0 or pd.isna(atr):
            return 0
        
        # 风险金额
        risk_amount = capital * self.risk_percent
        
        # 每单位风险（1个ATR）
        risk_per_unit = atr
        
        # 单位大小
        unit_size = risk_amount / risk_per_unit
        
        # 转换为股数（A股100股为一手）
        shares = int(unit_size / 100) * 100
        
        return max(shares, 0)
    
    def generate_signals(self, df, capital=100000):
        """
        生成海龟交易信号
        
        Args:
            df: DataFrame包含ohlcv数据
            capital: 可用资金
        
        Returns:
            dict: 交易信号
        """
        if len(df) < self.entry_days + 10:
            return {'error': '数据不足'}
        
        # 计算指标
        df = self.calculate_donchian_channel(df)
        df = self.calculate_atr(df)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        current_price = latest['close']
        atr = latest['ATR']
        
        # 计算仓位大小
        unit_size = self.calculate_position_size(capital, atr, current_price)
        
        signal = {
            'signal': 'none',
            'direction': None,
            'entry_price': None,
            'stop_loss': None,
            'unit_size': unit_size,
            'atr': atr,
            'donchian': {
                'upper': latest['DC_UPPER'],
                'lower': latest['DC_LOWER'],
                'mid': latest['DC_MID']
            }
        }
        
        # 检查入场信号
        # 多头入场：突破20日高点
        if current_price > latest['DC_UPPER'] and prev['close'] <= prev['DC_UPPER']:
            signal['signal'] = 'long_entry'
            signal['direction'] = 'long'
            signal['entry_price'] = current_price
            signal['stop_loss'] = current_price - 2 * atr  # 2倍ATR止损
        
        # 空头入场：跌破20日低点
        elif current_price < latest['DC_LOWER'] and prev['close'] >= prev['DC_LOWER']:
            signal['signal'] = 'short_entry'
            signal['direction'] = 'short'
            signal['entry_price'] = current_price
            signal['stop_loss'] = current_price + 2 * atr  # 2倍ATR止损
        
        # 检查出场信号
        # 多头出场：跌破10日低点
        elif current_price < latest['EXIT_LOWER']:
            signal['signal'] = 'long_exit'
            signal['direction'] = 'exit'
        
        # 空头出场：突破10日高点
        elif current_price > latest['EXIT_UPPER']:
            signal['signal'] = 'short_exit'
            signal['direction'] = 'exit'
        
        # 计算加仓点（每0.5个ATR加仓一次）
        if signal['direction'] == 'long':
            signal['add_positions'] = [
                signal['entry_price'] + 0.5 * atr * i
                for i in range(1, 5)
            ]
        elif signal['direction'] == 'short':
            signal['add_positions'] = [
                signal['entry_price'] - 0.5 * atr * i
                for i in range(1, 5)
            ]
        
        return signal
    
    def backtest(self, df, initial_capital=100000):
        """
        海龟交易回测
        
        Args:
            df: DataFrame包含ohlcv数据
            initial_capital: 初始资金
        
        Returns:
            dict: 回测结果
        """
        if len(df) < self.entry_days + 10:
            return {'error': '数据不足'}
        
        # 计算指标
        df = self.calculate_donchian_channel(df)
        df = self.calculate_atr(df)
        
        # 回测状态
        capital = initial_capital
        position = 0  # 持仓数量
        entry_price = 0
        stop_loss = 0
        trades = []
        
        for i in range(self.entry_days, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            # 有多头持仓
            if position > 0:
                # 检查止损
                if current['low'] <= stop_loss:
                    # 止损出场
                    exit_price = stop_loss
                    pnl = (exit_price - entry_price) * position
                    capital += pnl
                    
                    trades.append({
                        'type': 'long_exit',
                        'reason': 'stop_loss',
                        'date': current.name if hasattr(current, 'name') else i,
                        'price': exit_price,
                        'pnl': pnl,
                        'capital': capital
                    })
                    
                    position = 0
                    entry_price = 0
                    stop_loss = 0
                
                # 检查10日低点出场
                elif current['close'] < current['EXIT_LOWER']:
                    exit_price = current['close']
                    pnl = (exit_price - entry_price) * position
                    capital += pnl
                    
                    trades.append({
                        'type': 'long_exit',
                        'reason': 'exit_signal',
                        'date': current.name if hasattr(current, 'name') else i,
                        'price': exit_price,
                        'pnl': pnl,
                        'capital': capital
                    })
                    
                    position = 0
                    entry_price = 0
                    stop_loss = 0
            
            # 无持仓，检查入场信号
            elif position == 0:
                # 多头入场：突破20日高点
                if current['close'] > current['DC_UPPER'] and prev['close'] <= prev['DC_UPPER']:
                    entry_price = current['close']
                    atr = current['ATR']
                    stop_loss = entry_price - 2 * atr
                    
                    unit_size = self.calculate_position_size(capital, atr, entry_price)
                    position = unit_size
                    
                    trades.append({
                        'type': 'long_entry',
                        'date': current.name if hasattr(current, 'name') else i,
                        'price': entry_price,
                        'position': position,
                        'stop_loss': stop_loss,
                        'capital': capital
                    })
        
        # 计算回测结果
        total_return = (capital - initial_capital) / initial_capital * 100
        
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
        
        win_rate = len(winning_trades) / len([t for t in trades if 'pnl' in t]) * 100 if trades else 0
        
        return {
            'initial_capital': initial_capital,
            'final_capital': capital,
            'total_return': total_return,
            'total_trades': len([t for t in trades if 'pnl' in t]),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'trades': trades
        }
    
    def get_current_recommendation(self, df, capital=100000):
        """
        获取当前交易建议
        
        Args:
            df: DataFrame
            capital: 可用资金
        
        Returns:
            dict: 交易建议
        """
        signal = self.generate_signals(df, capital)
        
        if 'error' in signal:
            return signal
        
        recommendation = {
            'strategy': 'turtle_trading',
            'current_price': df.iloc[-1]['close'],
            'signal': signal['signal'],
            'direction': signal['direction'],
            'confidence': 70 if signal['signal'] != 'none' else 50
        }
        
        if signal['direction'] == 'long':
            recommendation['action'] = 'buy'
            recommendation['entry_price'] = signal['entry_price']
            recommendation['stop_loss'] = signal['stop_loss']
            recommendation['take_profit'] = signal['entry_price'] + 4 * signal['atr']  # 4倍ATR止盈
            recommendation['unit_size'] = signal['unit_size']
            recommendation['risk_reward_ratio'] = 2.0
            recommendation['description'] = f'海龟交易法多头信号，突破{self.entry_days}日高点入场'
        
        elif signal['direction'] == 'short':
            recommendation['action'] = 'sell'
            recommendation['entry_price'] = signal['entry_price']
            recommendation['stop_loss'] = signal['stop_loss']
            recommendation['take_profit'] = signal['entry_price'] - 4 * signal['atr']
            recommendation['unit_size'] = signal['unit_size']
            recommendation['risk_reward_ratio'] = 2.0
            recommendation['description'] = f'海龟交易法空头信号，跌破{self.entry_days}日低点入场'
        
        else:
            recommendation['action'] = 'wait'
            recommendation['description'] = '无明确信号，等�