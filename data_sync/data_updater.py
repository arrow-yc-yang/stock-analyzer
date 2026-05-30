"""
数据更新管理器
"""
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import func
import logging
import time

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import db, Stock, KLineData
from data_sync.tushare_client import TushareClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataUpdater:
    """数据更新管理器"""
    
    def __init__(self, tushare_token):
        """初始化数据更新器"""
        self.client = TushareClient(tushare_token)
    
    def sync_stock_basic(self, stock_pool='hs300'):
        """
        同步股票基础信息
        
        Args:
            stock_pool: 股票池类型 'hs300'/'all'/'custom'
        """
        logger.info(f"开始同步股票基础信息，股票池: {stock_pool}")
        
        if stock_pool == 'hs300':
            df = self.client.get_hs300_stocks()
        elif stock_pool == 'all':
            df = self.client.get_stock_basic()
        else:
            logger.warning(f"未知的股票池类型: {stock_pool}")
            return 0
        
        if df.empty:
            logger.warning("未获取到股票数据")
            return 0
        
        count = 0
        for _, row in df.iterrows():
            try:
                # 检查是否已存在
                existing = Stock.query.filter_by(ts_code=row['ts_code']).first()
                
                if existing:
                    # 更新现有记录
                    existing.name = row['name']
                    existing.area = row.get('area', '')
                    existing.industry = row.get('industry', '')
                    existing.market = row.get('market', '')
                    existing.list_date = str(row.get('list_date', ''))
                    existing.is_hs300 = row.get('is_hs300', False)
                else:
                    # 创建新记录
                    stock = Stock(
                        ts_code=row['ts_code'],
                        symbol=row['symbol'],
                        name=row['name'],
                        area=row.get('area', ''),
                        industry=row.get('industry', ''),
                        market=row.get('market', ''),
                        list_date=str(row.get('list_date', '')),
                        is_hs300=row.get('is_hs300', False),
                        stock_type='stock'
                    )
                    db.session.add(stock)
                
                count += 1
                if count % 100 == 0:
                    db.session.commit()
                    logger.info(f"已同步 {count} 只股票")
                
            except Exception as e:
                logger.error(f"同步股票 {row.get('ts_code')} 失败: {e}")
                db.session.rollback()
                continue
        
        db.session.commit()
        logger.info(f"股票基础信息同步完成，共 {count} 只")
        return count
    
    def sync_kline_data(self, ts_code, freq='D', start_date=None, end_date=None):
        """
        同步K线数据
        
        Args:
            ts_code: 股票代码
            freq: 频率 D/W/M
            start_date: 开始日期
            end_date: 结束日期
        """
        logger.info(f"开始同步 {ts_code} {freq}线数据")
        
        # 获取数据
        if freq == 'D':
            df = self.client.get_daily_kline(ts_code, start_date, end_date)
        elif freq == 'W':
            df = self.client.get_weekly_kline(ts_code, start_date, end_date)
        elif freq == 'M':
            df = self.client.get_monthly_kline(ts_code, start_date, end_date)
        else:
            logger.error(f"不支持的频率: {freq}")
            return 0
        
        if df.empty:
            logger.warning(f"未获取到 {ts_code} {freq}线数据")
            return 0
        
        # 获取股票ID
        stock = Stock.query.filter_by(ts_code=ts_code).first()
        if not stock:
            logger.warning(f"股票 {ts_code} 不存在于数据库")
            return 0
        
        count = 0
        for _, row in df.iterrows():
            try:
                # 检查是否已存在
                existing = KLineData.query.filter_by(
                    ts_code=ts_code,
                    trade_date=str(row['trade_date']),
                    freq=freq
                ).first()
                
                if existing:
                    # 更新现有记录
                    existing.open_price = float(row['open'])
                    existing.high_price = float(row['high'])
                    existing.low_price = float(row['low'])
                    existing.close_price = float(row['close'])
                    existing.pre_close = float(row.get('pre_close', 0))
                    existing.volume = int(row.get('vol', 0))
                    existing.amount = float(row.get('amount', 0))
                    existing.change = float(row.get('change', 0))
                    existing.pct_change = float(row.get('pct_chg', 0))
                else:
                    # 创建新记录
                    kline = KLineData(
                        stock_id=stock.id,
                        ts_code=ts_code,
                        trade_date=str(row['trade_date']),
                        freq=freq,
                        open_price=float(row['open']),
                        high_price=float(row['high']),
                        low_price=float(row['low']),
                        close_price=float(row['close']),
                        pre_close=float(row.get('pre_close', 0)),
                        volume=int(row.get('vol', 0)),
                        amount=float(row.get('amount', 0)),
                        change=float(row.get('change', 0)),
                        pct_change=float(row.get('pct_chg', 0))
                    )
                    db.session.add(kline)
                
                count += 1
                if count % 100 == 0:
                    db.session.commit()
                
            except Exception as e:
                logger.error(f"同步K线数据失败 {ts_code} {row.get('trade_date')}: {e}")
                db.session.rollback()
                continue
        
        db.session.commit()
        logger.info(f"{ts_code} {freq}线数据同步完成，共 {count} 条")
        return count
    
    def sync_all_kline(self, stock_pool='hs300', freq='D'):
        """
        同步所有股票的K线数据
        
        Args:
            stock_pool: 股票池
            freq: 频率
        """
        # 获取需要同步的股票列表
        if stock_pool == 'hs300':
            stocks = Stock.query.filter_by(is_hs300=True).all()
        elif stock_pool == 'all':
            stocks = Stock.query.all()
        else:
            stocks = Stock.query.filter_by(is_custom=True).all()
        
        logger.info(f"开始同步 {len(stocks)} 只股票的 {freq}线数据")
        
        total_count = 0
        for i, stock in enumerate(stocks):
            try:
                count = self.sync_kline_data(stock.ts_code, freq)
                total_count += count
                
                # 每10只股票暂停一下，避免请求过快
                if (i + 1) % 10 == 0:
                    logger.info(f"已同步 {i+1}/{len(stocks)} 只股票，暂停1秒...")
                    time.sleep(1)
                else:
                    time.sleep(0.2)  # 每次请求间隔200ms
                    
            except Exception as e:
                logger.error(f"同步股票 {stock.ts_code} 数据失败: {e}")
                continue
        
        logger.info(f"全部K线数据同步完成，共 {total_count} 条")
        return total_count
    
    def update_realtime_data(self, ts_codes=None):
        """
        更新实时数据（获取最新日线）
        
        Args:
            ts_codes: 股票代码列表，None则更新所有
        """
        if ts_codes is None:
            stocks = Stock.query.filter_by(is_hs300=True).all()
            ts_codes = [s.ts_code for s in stocks]
        
        logger.info(f"开始更新 {len(ts_codes)} 只股票的实时数据")
        
        today = datetime.now().strftime('%Y%m%d')
        count = 0
        
        for ts_code in ts_codes:
            try:
                self.sync_kline_data(ts_code, 'D', today, today)
                count += 1
                time.sleep(0.1)  # 避免请求过快
            except Exception as e:
                logger.error(f"更新 {ts_code} 实时数据失败: {e}")
                continue
        
        logger.info(f"实时数据更新完成，共 {count} 只股票")
        return count
    
    def get_last_update_time(self, ts_code, freq='D'):
        """获取某只股票某频率的最后更新时间"""
        last_record = KLineData.query.filter_by(
            ts_code=ts_code,
            freq=freq
        ).order_by(KLineData.trade_date.desc()).first()
        
        if last_record:
            return last_record.trade_date
        return None
    
    def sync_custom_stocks(self, ts_codes):
        """
        同步自定义股票列表
        
        Args:
            ts_codes: 股票代码列表
        """
        logger.info(f"开始同步自定义股票列表，共 {len(ts_codes)} 只")
        
        for ts_code in ts_codes:
            try:
                # 检查是否已存在
                existing = Stock.query.filter_by(ts_code=ts_code).first()
                if existing:
                    existing.is_custom = True
                else:
                    # 获取股票信息
                    df = self.client.get_stock_basic(fields='ts_code,symbol,name,area,industry,market,list_date')
                    stock_info = df[df['ts_code'] == ts_code]
                    
                    if not stock_info.empty:
                        info = stock_info.iloc[0]
                        stock = Stock(
                            ts_code=info['ts_code'],
                            symbol=info['symbol'],
                            name=info['name'],
                            area=info.get('area', ''),
                            industry=info.get('industry', ''),
                            market=info.get('market', ''),
                            list_date=str(info.get('list_date', '')),
                            is_custom=True,
                            stock_type='stock'
                        )
                        db.session.add(stock)
                
                db.session.commit()
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"同步自定义股票 {ts_code} 失败: {e}")
                db.se