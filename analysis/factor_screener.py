"""
多因子选股引擎
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FactorScreener:
    """多因子选股引擎"""

    # 因子定义：名称、方向（lower_better=越小越好）、权重
    FACTOR_DEFINITIONS = {
        'value': {
            'name': '价值因子',
            'factors': {
                'pe_ttm': {'weight': 0.30, 'lower_better': True, 'name': '市盈率TTM'},
                'pb': {'weight': 0.25, 'lower_better': True, 'name': '市净率'},
                'ps_ttm': {'weight': 0.20, 'lower_better': True, 'name': '市销率TTM'},
                'dv_ratio': {'weight': 0.25, 'lower_better': False, 'name': '股息率'},
            }
        },
        'growth': {
            'name': '成长因子',
            'factors': {
                'revenue_yoy': {'weight': 0.30, 'lower_better': False, 'name': '营收增长率'},
                'profit_yoy': {'weight': 0.30, 'lower_better': False, 'name': '净利润增长率'},
                'roe_yoy': {'weight': 0.20, 'lower_better': False, 'name': 'ROE增长率'},
                'eps_yoy': {'weight': 0.20, 'lower_better': False, 'name': 'EPS增长率'},
            }
        },
        'quality': {
            'name': '质量因子',
            'factors': {
                'roe': {'weight': 0.30, 'lower_better': False, 'name': '净资产收益率'},
                'grossprofit_margin': {'weight': 0.25, 'lower_better': False, 'name': '毛利率'},
                'netprofit_margin': {'weight': 0.20, 'lower_better': False, 'name': '净利率'},
                'debt_to_assets': {'weight': 0.25, 'lower_better': True, 'name': '资产负债率'},
            }
        }
    }

    # 各维度权重
    CATEGORY_WEIGHTS = {
        'value': 0.35,
        'growth': 0.35,
        'quality': 0.30
    }

    def __init__(self):
        """初始化因子选股引擎"""
        pass

    def screen_stocks(self, factor_df, top_n=20, filters=None, sort_by='composite_score'):
        """
        多因子选股

        Args:
            factor_df: DataFrame containing factor data with columns:
                       ts_code, pe_ttm, pb, ps_ttm, dv_ratio, revenue_yoy,
                       profit_yoy, roe_yoy, eps_yoy, roe, grossprofit_margin,
                       netprofit_margin, debt_to_assets
            top_n: 返回前N只股票
            filters: dict of filters, e.g. {'pe_ttm_max': 50, 'roe_min': 10}
            sort_by: 排序字段

        Returns:
            dict: 选股结果
        """
        if factor_df is None or factor_df.empty:
            return {'stocks': [], 'total': 0, 'message': '无数据'}

        df = factor_df.copy()

        # 应用过滤器
        if filters:
            df = self._apply_filters(df, filters)

        if df.empty:
            return {'stocks': [], 'total': 0, 'message': '过滤后无符合条件的股票'}

        # 计算各维度得分
        df = self._calculate_category_scores(df)

        # 计算综合得分
        df = self._calculate_composite_score(df)

        # 排序
        if sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=False)

        # 取前N只
        result_df = df.head(top_n)

        # 格式化结果
        stocks = []
        for _, row in result_df.iterrows():
            stock = {
                'ts_code': row.get('ts_code', ''),
                'name': row.get('name', ''),
                'industry': row.get('industry', ''),
                'composite_score': round(row.get('composite_score', 0), 2),
                'value_score': round(row.get('value_score', 0), 2),
                'growth_score': round(row.get('growth_score', 0), 2),
                'quality_score': round(row.get('quality_score', 0), 2),
                'rank': int(row.get('rank', 0)),
                'factors': {
                    'pe_ttm': self._safe_round(row.get('pe_ttm')),
                    'pb': self._safe_round(row.get('pb')),
                    'ps_ttm': self._safe_round(row.get('ps_ttm')),
                    'dv_ratio': self._safe_round(row.get('dv_ratio')),
                    'revenue_yoy': self._safe_round(row.get('revenue_yoy')),
                    'profit_yoy': self._safe_round(row.get('profit_yoy')),
                    'roe': self._safe_round(row.get('roe')),
                    'grossprofit_margin': self._safe_round(row.get('grossprofit_margin')),
                    'netprofit_margin': self._safe_round(row.get('netprofit_margin')),
                    'debt_to_assets': self._safe_round(row.get('debt_to_assets')),
                    'total_mv': self._safe_round(row.get('total_mv')),
                    'circ_mv': self._safe_round(row.get('circ_mv')),
                }
            }
            stocks.append(stock)

        return {
            'stocks': stocks,
            'total': len(df),
            'filtered_total': len(result_df),
            'filters_applied': filters or {},
            'screen_date': datetime.now().strftime('%Y-%m-%d'),
            'category_weights': self.CATEGORY_WEIGHTS,
            'factor_definitions': self._get_factor_info()
        }

    def _apply_filters(self, df, filters):
        """应用过滤条件"""
        # 常用过滤条件映射
        filter_map = {
            'pe_ttm_max': ('pe_ttm', 'le'),
            'pe_ttm_min': ('pe_ttm', 'ge'),
            'pb_max': ('pb', 'le'),
            'pb_min': ('pb', 'ge'),
            'roe_min': ('roe', 'ge'),
            'revenue_yoy_min': ('revenue_yoy', 'ge'),
            'profit_yoy_min': ('profit_yoy', 'ge'),
            'total_mv_min': ('total_mv', 'ge'),
            'total_mv_max': ('total_mv', 'le'),
            'debt_to_assets_max': ('debt_to_assets', 'le'),
            'turnover_rate_min': ('turnover_rate', 'ge'),
        }

        for filter_key, (col, op) in filter_map.items():
            if filter_key in filters and filters[filter_key] is not None:
                value = filters[filter_key]
                if col in df.columns:
                    # 去除NaN
                    mask = df[col].notna()
                    if op == 'le':
                        mask &= (df[col] <= value)
                    elif op == 'ge':
                        mask &= (df[col] >= value)
                    elif op == 'eq':
                        mask &= (df[col] == value)
                    df = df[mask]

        # 行业过滤
        if 'industry' in filters and filters['industry']:
            industries = filters['industry']
            if isinstance(industries, str):
                industries = [industries]
            df = df[df['industry'].isin(industries)]

        return df

    def _calculate_category_scores(self, df):
        """计算各维度因子得分"""
        for category, category_info in self.FACTOR_DEFINITIONS.items():
            score_col = f'{category}_score'
            scores = pd.Series(0.0, index=df.index)

            for factor_name, factor_info in category_info['factors'].items():
                if factor_name not in df.columns:
                    continue

                col = df[factor_name].copy()
                # 去除NaN和极端值
                valid_mask = col.notna() & (col != 0) & (np.abs(col) < col.median() * 10 if col.median() != 0 else True)

                if valid_mask.sum() < 5:
                    continue

                # 标准化：排名百分位
                ranked = col[valid_mask].rank(pct=True)

                # 如果是越小越好，反转排名
                if factor_info['lower_better']:
                    ranked = 1 - ranked

                # 归一化到0-100
                normalized = ranked * 100

                # 加权
                scores = scores.add(normalized.reindex(df.index).fillna(50) * factor_info['weight'], fill_value=0)

            # 归一化维度得分到0-100
            max_score = scores.max()
            if max_score > 0:
                df[score_col] = (scores / max_score * 100).round(2)
            else:
                df[score_col] = 50.0

        return df

    def _calculate_composite_score(self, df):
        """计算综合得分"""
        composite = pd.Series(0.0, index=df.index)

        for category, weight in self.CATEGORY_WEIGHTS.items():
            score_col = f'{category}_score'
            if score_col in df.columns:
                composite = composite.add(df[score_col] * weight, fill_value=0)

        df['composite_score'] = composite.round(2)

        # 添加排名
        df['rank'] = df['composite_score'].rank(ascending=False, method='min').astype(int)

        return df

    def get_factor_ranking(self, factor_df, factor_name, top_n=20, ascending=True):
        """
        获取单因子排名

        Args:
            factor_df: DataFrame
            factor_name: 因子名称
            top_n: 前N只
            ascending: 是否升序

        Returns:
            list: 排名结果
        """
        if factor_df is None or factor_df.empty or factor_name not in factor_df.columns:
            return []

        df = factor_df[factor_df[factor_name].notna()].copy()
        df = df.sort_values(factor_name, ascending=ascending).head(top_n)

        results = []
        for rank, (_, row) in enumerate(df.iterrows(), 1):
            results.append({
                'rank': rank,
                'ts_code': row.get('ts_code', ''),
                'name': row.get('name', ''),
                'industry': row.get('industry', ''),
                'value': round(row.get(factor_name, 0), 2)
            })

        return results

    def get_industry_distribution(self, stocks):
        """
        获取选股结果的行业分布

        Args:
            stocks: list of stock dicts with 'industry' key

        Returns:
            dict: 行业分布统计
        """
        industries = {}
        for stock in stocks:
            ind = stock.get('industry', '未知')
            industries[ind] = industries.get(ind, 0) + 1

        # 排序
        sorted_industries = sorted(industries.items(), key=lambda x: x[1], reverse=True)

        return {
            'distribution': [
                {'industry': ind, 'count': count, 'percent': round(count / len(stocks) * 100, 1)}
                for ind, count in sorted_industries
            ],
            'total_industries': len(industries)
        }

    def get_factor_correlation(self, factor_df):
        """
        计算因子间相关性

        Args:
            factor_df: DataFrame

        Returns:
            dict: 因子相关性矩阵
        """
        factor_cols = [
            'pe_ttm', 'pb', 'ps_ttm', 'dv_ratio',
            'revenue_yoy', 'profit_yoy', 'roe_yoy', 'eps_yoy',
            'roe', 'grossprofit_margin', 'netprofit_margin', 'debt_to_assets'
        ]

        available_cols = [c for c in factor_cols if c in factor_df.columns]
        if len(available_cols) < 2:
            return {'matrix': {}, 'factors': []}

        corr_matrix = factor_df[available_cols].corr()

        # 转换为字典格式
        matrix = {}
        for col in corr_matrix.columns:
            matrix[col] = {row: round(corr_matrix.loc[row, col], 3) for row in corr_matrix.index}

        return {
            'matrix': matrix,
            'factors': available_cols
        }

    def _safe_round(self, value, decimals=2):
        """安全四舍五入"""
        if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
            return None
        try:
            return round(float(value), decimals)
        except (ValueError, TypeError):
            return None

    def _get_factor_info(self):
        """获取因子定义信息"""
        info = {}
        for category, cat_info in self.FACTOR_DEFINITIONS.items():
            info[category] = {
                'name': cat_info['name'],
                'weight': self.CATEGORY_WEIGHTS[category],
                'factors': {
                    fname: {
                        'name': finfo['name'],
                        'weight': finfo['weight'],
                        'lower_better': finfo['lower_better']
                    }
                    for fname, finfo in cat_info['factors'].items()
                }
            }
        return info
