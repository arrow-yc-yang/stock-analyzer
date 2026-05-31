"""
回测引擎
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analysis.technical_analyzer import TechnicalAnalyzer
from analysis.strategy_matcher import StrategyMatcher
from analysis.turtle_trading import TurtleTrading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital=100000):
        """
        初始化回测引擎
        
        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.technical_analyzer = TechnicalAnalyzer()
        self.strategy_matcher = StrategyMatcher()
        self.turtle_trading = TurtleTrading()
    
    def backtest_strategy(self, df, strategy_name, params=None):
        """
        回测单个策略
        
        Args:
            df: DataFrame包含历史数据
            strategy_name: 策略名称
            params: 策略参数
        
        Returns:
            dict: 回测结果
        """
        if df.empty or len(df) < 60:
            return {'error': '数据不足，无法回测'}
        
        if strategy_name == 'turtle_trading':
            return self._backtest_turtle(df, params)
        elif strategy_name == 'golden_cross':
            return self._backtest_ma_cross(df, 'golden', params)
        elif strategy_name == 'macd_divergence':
            return self._backtest_macd(df, params)
        elif strategy_name == 'rsi_reversal':
            return self._backtest_rsi(df, params)
        else:
            return {'error': f'未知的策略: {strategy_name}'}
    
    def _backtest_turtle(self, df, params=None):
        """回测海龟交易法则"""
        return self.turtle_trading.backtest(df, self.initial_capital)
    
    def _backtest_ma_cross(self, df, cross_type='golden', params=None):
        """回测均线交叉策略"""
        df = self.technical_analyzer.calculate_ma(df, [5, 10, 20])
        
        capital = self.initial_capital
        position = 0
        trades = []
        
        for i in range(20, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            # 金叉买入
            if cross_type == 'golden':
                if position == 0:
                    if (prev['MA5'] <= prev['MA10'] and current['MA5'] > current['MA10']) or \
                       (prev['MA5'] <= prev['MA20'] and current['MA5'] > current['MA20']):
                        # 买入
                        position = int(capital / current['close'] / 100) * 100
                        entry_price = current['close']
                        capital -= position * entry_price
                        
                        trades.append({
                            'type': 'buy',
                            'date': str(current.get('trade_date', i)),
                            'price': entry_price,
                            'position': position,
                            'capital': capital
                        })
                
                elif position > 0:
                    # 死叉卖出
                    if prev['MA5'] >= prev['MA10'] and current['MA5'] < current['MA10']:
                        exit_price = current['close']
                        pnl = (exit_price - entry_price) * position
                        capital += position * exit_price
                        
                        trades.append({
                            'type': 'sell',
                            'date': str(current.get('trade_date', i)),
                            'price': exit_price,
                            'pnl': pnl,
                            'capital': capital
                        })
                        
                        position = 0
        
        # 计算结果
        final_value = capital + position * df.iloc[-1]['close'] if position > 0 else capital
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        return self._calculate_backtest_metrics(trades, total_return)
    
    def _backtest_macd(self, df, params=None):
        """回测MACD策略"""
        df = self.technical_analyzer.calculate_macd(df)
        
        capital = self.initial_capital
        position = 0
        trades = []
        
        for i in range(26, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            if position == 0:
                # MACD金叉买入
                if prev['MACD_DIF'] <= prev['MACD_DEA'] and current['MACD_DIF'] > current['MACD_DEA']:
                    position = int(capital / current['close'] / 100) * 100
                    entry_price = current['close']
                    capital -= position * entry_price
                    
                    trades.append({
                        'type': 'buy',
                        'date': str(current.get('trade_date', i)),
                        'price': entry_price,
                        'position': position,
                        'capital': capital
                    })
            
            elif position > 0:
                # MACD死叉卖出
                if prev['MACD_DIF'] >= prev['MACD_DEA'] and current['MACD_DIF'] < current['MACD_DEA']:
                    exit_price = current['close']
                    pnl = (exit_price - entry_price) * position
                    capital += position * exit_price
                    
                    trades.append({
                        'type': 'sell',
                        'date': str(current.get('trade_date', i)),
                        'price': exit_price,
                        'pnl': pnl,
                        'capital': capital
                    })
                    
                    position = 0
        
        final_value = capital + position * df.iloc[-1]['close'] if position > 0 else capital
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        return self._calculate_backtest_metrics(trades, total_return)
    
    def _backtest_rsi(self, df, params=None):
        """回测RSI策略"""
        df = self.technical_analyzer.calculate_rsi(df)
        
        capital = self.initial_capital
        position = 0
        trades = []
        
        oversold = 30
        overbought = 70
        
        for i in range(14, len(df)):
            current = df.iloc[i]
            
            if position == 0:
                # RSI超卖买入
                if current['RSI'] < oversold:
                    position = int(capital / current['close'] / 100) * 100
                    entry_price = current['close']
                    capital -= position * entry_price
                    
                    trades.append({
                        'type': 'buy',
                        'date': str(current.get('trade_date', i)),
                        'price': entry_price,
                        'position': position,
                        'capital': capital
                    })
            
            elif position > 0:
                # RSI超买卖出
                if current['RSI'] > overbought:
                    exit_price = current['close']
                    pnl = (exit_price - entry_price) * position
                    capital += position * exit_price
                    
                    trades.append({
                        'type': 'sell',
                        'date': str(current.get('trade_date', i)),
                        'price': exit_price,
                        'pnl': pnl,
                        'capital': capital
                    })
                    
                    position = 0
        
        final_value = capital + position * df.iloc[-1]['close'] if position > 0 else capital
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        return self._calculate_backtest_metrics(trades, total_return)
    
    def _calculate_backtest_metrics(self, trades, total_return):
        """计算回测指标"""
        closed_trades = [t for t in trades if 'pnl' in t]
        
        if not closed_trades:
            return {
                'initial_capital': self.initial_capital,
                'total_return': 0,
                'total_trades': 0,
                'win_rate': 0,
                'trades': trades
            }
        
        winning_trades = [t for t in closed_trades if t['pnl'] > 0]
        losing_trades = [t for t in closed_trades if t['pnl'] <= 0]
        
        win_rate = len(winning_trades) / len(closed_trades) * 100
        
        avg_profit = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
        
        profit_factor = abs(sum(t['pnl'] for t in winning_trades) / sum(t['pnl'] for t in losing_trades)) if losing_trades and sum(t['pnl'] for t in losing_trades) != 0 else float('inf')
        
        # 计算最大回撤
        capital_curve = []
        current_capital = self.initial_capital
        for trade in trades:
            if 'pnl' in trade:
                current_capital += trade['pnl']
            capital_curve.append(current_capital)
        
        max_drawdown = 0
        peak = self.initial_capital
        for capital in capital_curve:
            if capital > peak:
                peak = capital
            drawdown = (peak - capital) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        return {
            'initial_capital': self.initial_capital,
            'total_return': round(total_return, 2),
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate, 2),
            'avg_profit': round(avg_profit, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'max_drawdown': round(max_drawdown * 100, 2),
            'trades': trades
        }
    
    def compare_strategies(self, df, strategies=None):
        """
        对比多个策略
        
        Args:
            df: DataFrame
            strategies: 策略列表
        
        Returns:
            dict: 对比结果
        """
        if strategies is None:
            strategies = ['turtle_trading', 'golden_cross', 'macd_divergence', 'rsi_reversal']
        
        results = {}
        for strategy in strategies:
            logger.info(f"回测策略: {strategy}")
            result = self.backtest_strategy(df, strategy)
            results[strategy] = result
        
        # 找出最佳策略
        best_strategy = max(results.items(), key=lambda x: x[1].get('total_return', -999))
        
        return {
            'comparison': results,
            'best_strategy': best_strategy[0],
            'best_return': best_strategy[1].get('total_return', 0),
            'summary': self._generate_comparison_summary(results)
        }
    
    def _generate_comparison_summary(self, results):
        """生成对比总结"""
        summary = []
        
        for strategy, result in results.items():
            if 'error' in result:
                summary.append(f"{strategy}: 回测失败 - {result['error']}")
            else:
                summary.append(
                    f"{strategy}: 收益率{result.get('total_return', 0):.2f}%, "
                    f"胜率{result.get('win_rate', 0):.1f}%, "
                    f"最大回撤{result.get('max_drawdown', 0):.2f}%"
                )
        
        return '\n'.join(summary)
    
    def portfolio_backtest(self, stock_data_dict, strategy_name, allocation='equal'):
        """
        组合回测
        
        Args:
            stock_data_dict: {ts_code: df} 字典
            strategy_name: 策略名称
            allocation: 资金分配方式
        
        Returns:
            dict: 组合回测结果
        """
        n_stocks = len(stock_data_dict)
        capital_per_stock = self.initial_capital / n_stocks
        
        all_results = {}
        total_return = 0
        
        for ts_code, df in stock_data_dict.items():
            result = self.backtest_strategy(df, strategy_name)
            if 'error' not in result:
                all_results[ts_code] = result
                total_return += result.get('total_return', 0) / n_stocks
        
        return {
            'strategy': strategy_name,
            'stocks_tested': len(all_results),
            'avg_return': round(total_return, 2),
            'individual_results': all_results
        }
