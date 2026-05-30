"""
Tushare数据客户端
"""
import tushare as ts
import pandas as pd
from datetime import datetime, timedelta
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TushareClient:
    """Tushare API客户端封装"""
    
    def __init__(self, token):
        """初始化Tushare客户端"""
        self.token = token
        self.pro = ts.pro_api(token)
        logger.info("Tushare客户端初始化成功")
    
    def get_stock_basic(self, exchange='', list_status='L', fields=''):
        """
        获取股票基础信息
        
        Args:
            exchange: 交易所 SSE上交所 SZSE深交所 BSE北交所
            list_status: 上市状态 L上市 D退市 P暂停上市
            fields: 返回字段
        
        Returns:
            DataFrame: 股票基础信息
        """
        try:
            df = self.pro.stock_basic(
                exchange=exchange,
                list_status=list_status,
                fields=fields or 'ts_code,symbol,name,area,industry,market,list_date'
            )
            logger.info(f"获取到 {len(df)} 只股票基础信息")
            return df
        except Exception as e:
            logger.error(f"获取股票基础信息失败: {e}")
            return pd.DataFrame()
    
    def get_hs300_stocks(self):
        """获取沪深300成分股（批量获取，避免频率限制）"""
        try:
            # 1. 获取沪深300成分股代码列表
            weight_df = self.pro.index_weight(index_code='000300.SH')
            if weight_df.empty:
                logger.warning("获取沪深300成分股列表失败")
                return pd.DataFrame()
            
            con_codes = weight_df['con_code'].unique().tolist()
            logger.info(f"获取到 {len(con_codes)} 个沪深300成分股代码")
            
            # 2. 一次性获取所有股票基础信息
            all_stocks_df = self.pro.stock_basic(
                fields='ts_code,symbol,name,area,industry,market,list_date'
            )
            
            if all_stocks_df.empty:
                logger.warning("获取股票基础信息失败")
                return pd.DataFrame()
            
            # 3. 筛选出沪深300成分股
            hs300_df = all_stocks_df[all_stocks_df['ts_code'].isin(con_codes)].copy()
            hs300_df['is_hs300'] = True
            
            logger.info(f"匹配到 {len(hs300_df)} 只沪深300成分股")
            return hs300_df
        except Exception as e:
            logger.error(f"获取沪深300成分股失败: {e}")
            return pd.DataFrame()
    
    def get_daily_kline(self, ts_code, start_date=None, end_date=None):
        """
        获取日线数据
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            DataFrame: 日线数据
        """
        try:
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            if df.empty:
                return df
            
            # 添加频率标识
            df['freq'] = 'D'
            df = df.sort_values('trade_date')
            
            logger.info(f"获取 {ts_code} 日线数据 {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取 {ts_code} 日线数据失败: {e}")
            return pd.DataFrame()
    
    def get_weekly_kline(self, ts_code, start_date=None, end_date=None):
        """获取周线数据"""
        try:
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365*2)).strftime('%Y%m%d')
            
            df = self.pro.weekly(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            if df.empty:
                return df
            
            df['freq'] = 'W'
            df = df.sort_values('trade_date')
            
            logger.info(f"获取 {ts_code} 周线数据 {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取 {ts_code} 周线数据失败: {e}")
            return pd.DataFrame()
    
    def get_monthly_kline(self, ts_code, start_date=None, end_date=None):
        """获取月线数据"""
        try:
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365*5)).strftime('%Y%m%d')
            
            df = self.pro.monthly(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            if df.empty:
                return df
            
            df['freq'] = 'M'
            df = df.sort_values('trade_date')
            
            logger.info(f"获取 {ts_code} 月线数据 {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取 {ts_code} 月线数据失败: {e}")
            return pd.DataFrame()
    
    def get_realtime_quotes(self, ts_code):
        """获取实时行情（使用日线最新数据模拟）"""
        try:
            df = self.pro.daily(ts_code=ts_code, limit=1)
            return df
        except Exception as e:
            logger.error(f"获取 {ts_code} 实时行情失败: {e}")
            return pd.DataFrame()
    
    def get_index_basic(self):
        """获取指数基础信息"""
        try:
            df = self.pro.index_basic(market='SW')
            logger.info(f"获取到 {len(df)} 条指数信息")
            return df
        except Exception as e:
            logger.error(f"获取指数信息失败: {e}")
            return pd.DataFrame()
    
    def get_etf_basic(self):
        """获取ETF基础信息"""
        try:
            df = self.pro.fund_basic(market='E')
            logger.info(f"获取到 {len(df)} 条ETF信息")
            return df
        except Exception as e:
            logger.error(f"获取ETF信息失败: {e}")
            return pd.DataFrame()
    
    def get_trade_calendar(self, start_date=None, end_date=None):
        """获取交易日历"""
        try:
            if not start_date:
                start_date = datetime.now().strftime('%Y%m%d')
            if not end_date:
                end_date = (datetime.now() + timedelta(days=30)).strftime('%Y%m%d')
            
            df = self.pro.trade_cal(
                exchange='SSE',
                start_date=start_date,
                end_date=end_date
            )
            return df
        except Exception as e:
            logger.error(f"获取交易日历失败: {e}")
            return pd.DataFrame()
    
    def get_holder_number(self, ts_code):
        """
        获取�