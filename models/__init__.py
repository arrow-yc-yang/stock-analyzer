"""
数据模型模块
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .stock import Stock
from .kline import KLineData
from .analysis import AnalysisResult
from .backtest import BacktestResult
from .factor_data import FactorData

__all__ = ['Stock', 'KLineData', 'AnalysisResult', 'BacktestResult', 'FactorData']
