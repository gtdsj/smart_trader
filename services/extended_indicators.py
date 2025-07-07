# -*- coding: utf-8 -*-
"""
扩展指标计算模块
提供策略所需的特殊指标计算功能
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from loguru import logger


class ExtendedIndicators:
    """扩展指标计算器"""
    
    def __init__(self):
        pass
    
    def calculate_ma_angle(self, df: pd.DataFrame, period: int = 5, 
                          window: int = 3) -> pd.Series:
        """
        计算移动平均线角度
        
        Args:
            df: 包含价格数据的DataFrame
            period: 移动平均线周期
            window: 计算角度的窗口期
            
        Returns:
            移动平均线角度序列
        """
        try:
            # 计算移动平均线
            ma = df['close'].rolling(window=period).mean()
            
            # 计算角度（使用斜率近似）
            angles = []
            for i in range(len(ma)):
                if i < window:
                    angles.append(np.nan)
                else:
                    # 取最近window个点计算斜率
                    y_values = ma.iloc[i-window+1:i+1].values
                    x_values = np.arange(window)
                    
                    # 计算线性回归斜率
                    if len(y_values) == window and not np.isnan(y_values).any():
                        slope = np.polyfit(x_values, y_values, 1)[0]
                        # 转换为角度（度数）
                        angle = np.arctan(slope) * 180 / np.pi
                        angles.append(angle)
                    else:
                        angles.append(np.nan)
            
            return pd.Series(angles, index=df.index)
            
        except Exception as e:
            logger.error(f"计算移动平均线角度失败: {e}")
            return pd.Series([np.nan] * len(df), index=df.index)
    
    def check_consecutive_condition(self, series: pd.Series, condition_func, 
                                  days: int = 3) -> pd.Series:
        """
        检查连续N天满足条件
        
        Args:
            series: 数据序列
            condition_func: 条件函数
            days: 连续天数
            
        Returns:
            布尔序列，表示是否满足连续条件
        """
        try:
            condition_met = condition_func(series)
            result = []
            
            for i in range(len(condition_met)):
                if i < days - 1:
                    result.append(False)
                else:
                    # 检查最近days天是否都满足条件
                    recent_conditions = condition_met.iloc[i-days+1:i+1]
                    result.append(recent_conditions.all())
            
            return pd.Series(result, index=series.index)
            
        except Exception as e:
            logger.error(f"检查连续条件失败: {e}")
            return pd.Series([False] * len(series), index=series.index)
    
    def check_price_above_ma(self, df: pd.DataFrame, ma_period: int = 5) -> pd.Series:
        """
        检查收盘价是否高于移动平均线
        
        Args:
            df: 包含价格数据的DataFrame
            ma_period: 移动平均线周期
            
        Returns:
            布尔序列
        """
        try:
            ma = df['close'].rolling(window=ma_period).mean()
            return df['close'] > ma
        except Exception as e:
            logger.error(f"检查价格高于均线失败: {e}")
            return pd.Series([False] * len(df), index=df.index)
    
    def check_close_above_open(self, df: pd.DataFrame) -> pd.Series:
        """
        检查收盘价是否高于开盘价
        
        Args:
            df: 包含价格数据的DataFrame
            
        Returns:
            布尔序列
        """
        try:
            return df['close'] > df['open']
        except Exception as e:
            logger.error(f"检查收盘价高于开盘价失败: {e}")
            return pd.Series([False] * len(df), index=df.index)
    
    def check_low_above_ma(self, df: pd.DataFrame, ma_period: int = 5) -> pd.Series:
        """
        检查最低价是否高于移动平均线
        
        Args:
            df: 包含价格数据的DataFrame
            ma_period: 移动平均线周期
            
        Returns:
            布尔序列
        """
        try:
            ma = df['close'].rolling(window=ma_period).mean()
            return df['low'] > ma
        except Exception as e:
            logger.error(f"检查最低价高于均线失败: {e}")
            return pd.Series([False] * len(df), index=df.index)
    
    def calculate_price_change_pct(self, df: pd.DataFrame) -> pd.Series:
        """
        计算价格变化百分比
        
        Args:
            df: 包含价格数据的DataFrame
            
        Returns:
            价格变化百分比序列
        """
        try:
            return df['close'].pct_change() * 100
        except Exception as e:
            logger.error(f"计算价格变化百分比失败: {e}")
            return pd.Series([np.nan] * len(df), index=df.index)
    
    def check_stock_board_type(self, stock_code: str) -> Dict[str, bool]:
        """
        检查股票板块类型
        
        Args:
            stock_code: 股票代码
            
        Returns:
            包含板块信息的字典
        """
        try:
            # 根据股票代码判断板块
            result = {
                'is_kcb': False,  # 科创板
                'is_bse': False,  # 北交所
                'is_st': False    # ST股
            }
            
            # 科创板：688开头
            if stock_code.startswith('688'):
                result['is_kcb'] = True
            
            # 北交所：43、83、87开头
            if stock_code.startswith(('43', '83', '87')):
                result['is_bse'] = True
            
            # ST股：通过股票名称判断（这里简化处理，实际需要查询股票名称）
            # 在实际应用中，需要从数据源获取股票名称进行判断
            
            return result
            
        except Exception as e:
            logger.error(f"检查股票板块类型失败: {e}")
            return {'is_kcb': False, 'is_bse': False, 'is_st': False}
    
    def check_main_fund_flow(self, df: pd.DataFrame) -> pd.Series:
        """
        检查主力资金流向（模拟实现）
        
        注意：这是一个模拟实现，实际需要接入真实的资金流数据
        
        Args:
            df: 包含交易数据的DataFrame
            
        Returns:
            主力资金净流入布尔序列
        """
        try:
            # 这里使用成交量和价格变化作为主力资金流向的简单估算
            # 实际应用中需要接入专业的资金流数据
            price_change = df['close'].pct_change()
            volume_ma = df['volume'].rolling(window=5).mean()
            
            # 简单规则：价格上涨且成交量放大
            main_inflow = (price_change > 0) & (df['volume'] > volume_ma)
            
            logger.warning("主力资金流向使用模拟数据，实际应用需接入真实资金流数据")
            return main_inflow
            
        except Exception as e:
            logger.error(f"检查主力资金流向失败: {e}")
            return pd.Series([False] * len(df), index=df.index)
    
    def check_break_board(self, df: pd.DataFrame) -> pd.Series:
        """
        检查是否为破板股（模拟实现）
        
        注意：这是一个模拟实现，实际需要接入涨停板数据
        
        Args:
            df: 包含交易数据的DataFrame
            
        Returns:
            是否破板的布尔序列
        """
        try:
            # 简单规则：当日最高价接近涨停但收盘价明显回落
            price_change = df['close'].pct_change() * 100
            high_change = ((df['high'] - df['close'].shift(1)) / df['close'].shift(1)) * 100
            
            # 假设涨停为10%，破板定义为最高价接近涨停但收盘价回落较多
            is_break_board = (high_change > 8) & (price_change < 5)
            
            logger.warning("破板股检查使用模拟数据，实际应用需接入涨停板数据")
            return is_break_board
            
        except Exception as e:
            logger.error(f"检查破板股失败: {e}")
            return pd.Series([False] * len(df), index=df.index)