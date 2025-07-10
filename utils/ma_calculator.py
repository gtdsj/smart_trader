# -*- coding: utf-8 -*-
"""
移动平均线计算工具类
提供统一的均线计算和角度计算功能
"""

import pandas as pd
import numpy as np
from typing import List, Optional
from loguru import logger


class MovingAverageCalculator:
    """移动平均线计算工具类"""
    
    @staticmethod
    def calculate_ma(data: pd.Series, period: int) -> pd.Series:
        """
        计算移动平均线
        
        Args:
            data: 价格数据序列
            period: 均线周期
            
        Returns:
            移动平均线序列
        """
        if len(data) < period:
            return pd.Series(dtype=float)
        
        return data.rolling(window=period, min_periods=period).mean()
    
    @staticmethod
    def calculate_ma_angle(ma_series: pd.Series, index: int = -1) -> float:
        """
        计算均线角度（斜率转角度）
        
        Args:
            ma_series: 均线数据序列
            index: 计算角度的位置索引，默认-1（最新）
            
        Returns:
            角度值（度数）
        """
        try:
            if len(ma_series) < 2:
                return 0.0
            
            # 处理负索引
            if index < 0:
                index = len(ma_series) + index
            
            # 确保索引有效
            if index < 1 or index >= len(ma_series):
                return 0.0
            
            current_ma = ma_series.iloc[index]
            previous_ma = ma_series.iloc[index - 1]
            
            if pd.notna(current_ma) and pd.notna(previous_ma):
                slope = current_ma - previous_ma
                angle = np.arctan(slope) * 180 / np.pi
                return float(angle)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"计算均线角度失败: {e}")
            return 0.0
    
    @staticmethod
    def calculate_consecutive_angles(ma_series: pd.Series, days: int) -> List[float]:
        """
        计算连续N天的均线角度
        
        Args:
            ma_series: 均线数据序列
            days: 连续天数
            
        Returns:
            连续N天的角度列表
        """
        try:
            if len(ma_series) < days + 1:
                return []
            
            angles = []
            # 计算最近days天的角度
            start_index = len(ma_series) - days
            
            for i in range(start_index, len(ma_series)):
                angle = MovingAverageCalculator.calculate_ma_angle(ma_series, i)
                angles.append(angle)
            
            return angles
            
        except Exception as e:
            logger.error(f"计算连续均线角度失败: {e}")
            return []
    
    @staticmethod
    def calculate_all_angles(ma_series: pd.Series) -> List[float]:
        """
        计算所有可能位置的均线角度
        
        Args:
            ma_series: 均线数据序列
            
        Returns:
            所有角度的列表
        """
        try:
            if len(ma_series) < 2:
                return []
            
            angles = []
            for i in range(1, len(ma_series)):
                angle = MovingAverageCalculator.calculate_ma_angle(ma_series, i)
                angles.append(angle)
            
            return angles
            
        except Exception as e:
            logger.error(f"计算所有均线角度失败: {e}")
            return []
    
    @staticmethod
    def check_consecutive_condition(angles: List[float], threshold: float, 
                                  consecutive_days: int, condition_type: str = "all") -> dict:
        """
        检查连续条件是否满足
        
        Args:
            angles: 角度列表
            threshold: 阈值
            consecutive_days: 需要连续的天数
            condition_type: 条件类型 ("all": 全部满足, "any": 任意满足, "count": 计数)
            
        Returns:
            包含检查结果的字典
        """
        try:
            if len(angles) < consecutive_days:
                return {
                    "satisfied": False,
                    "count": 0,
                    "percentage": 0.0,
                    "details": "数据不足"
                }
            
            # 检查最近consecutive_days天的角度
            recent_angles = angles[-consecutive_days:] if len(angles) >= consecutive_days else angles
            
            # 计算满足条件的天数
            satisfied_count = sum(1 for angle in recent_angles if angle > threshold)
            total_days = len(recent_angles)
            percentage = (satisfied_count / total_days) * 100 if total_days > 0 else 0
            
            # 根据条件类型判断是否满足
            if condition_type == "all":
                satisfied = satisfied_count == total_days
            elif condition_type == "any":
                satisfied = satisfied_count > 0
            elif condition_type == "count":
                satisfied = True  # 对于计数类型，总是返回True，由调用者判断计数是否满足要求
            else:
                satisfied = False
            
            return {
                "satisfied": satisfied,
                "count": satisfied_count,
                "total": total_days,
                "percentage": percentage,
                "threshold": threshold,
                "angles": recent_angles,
                "details": f"{satisfied_count}/{total_days} 天满足条件 (>{threshold}度)"
            }
            
        except Exception as e:
            logger.error(f"检查连续条件失败: {e}")
            return {
                "satisfied": False,
                "count": 0,
                "percentage": 0.0,
                "details": f"检查失败: {e}"
            }
    
    @staticmethod
    def get_ma_summary(stock_data: pd.DataFrame, periods: List[int] = None) -> dict:
        """
        获取多个周期均线的汇总信息
        
        Args:
            stock_data: 股票数据
            periods: 均线周期列表，默认[5, 10, 20, 30]
            
        Returns:
            均线汇总信息字典
        """
        try:
            if periods is None:
                periods = [5, 10, 20, 30]
            
            if 'close_price' not in stock_data.columns:
                return {"error": "缺少close_price字段"}
            
            summary = {
                "periods": periods,
                "ma_values": {},
                "ma_angles": {},
                "latest_price": float(stock_data['close_price'].iloc[-1]) if len(stock_data) > 0 else 0
            }
            
            for period in periods:
                ma_series = MovingAverageCalculator.calculate_ma(stock_data['close_price'], period)
                
                if len(ma_series) > 0 and pd.notna(ma_series.iloc[-1]):
                    summary["ma_values"][f"ma{period}"] = float(ma_series.iloc[-1])
                    
                    # 计算最新角度
                    angle = MovingAverageCalculator.calculate_ma_angle(ma_series, -1)
                    summary["ma_angles"][f"ma{period}_angle"] = angle
                else:
                    summary["ma_values"][f"ma{period}"] = None
                    summary["ma_angles"][f"ma{period}_angle"] = 0.0
            
            return summary
            
        except Exception as e:
            logger.error(f"获取均线汇总信息失败: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def calculate_ma_angle_latest(stock_data: pd.DataFrame, ma_period: int = 5) -> float:
        """计算指定周期均线的最新角度
        
        Args:
            stock_data: 股票数据
            ma_period: 均线周期
            
        Returns:
            最新角度（度数）
        """
        try:
            # 确定价格字段
            price_field = 'close_price' if 'close_price' in stock_data.columns else 'close'
            
            if price_field not in stock_data.columns:
                logger.error(f"股票数据中缺少价格字段: {list(stock_data.columns)}")
                return 0.0
            
            ma_series = MovingAverageCalculator.calculate_ma(stock_data[price_field], ma_period)
            return MovingAverageCalculator.calculate_ma_angle(ma_series, -1)
            
        except Exception as e:
            logger.error(f"计算MA{ma_period}最新角度失败: {e}")
            return 0.0
    
    @staticmethod
    def calculate_ma_angles_consecutive(stock_data: pd.DataFrame, ma_period: int = 5, 
                                      consecutive_days: int = 3) -> List[float]:
        """计算指定周期均线连续N天的角度
        
        Args:
            stock_data: 股票数据
            ma_period: 均线周期
            consecutive_days: 连续天数
            
        Returns:
            连续N天的角度列表
        """
        try:
            # 确定价格字段
            price_field = 'close_price' if 'close_price' in stock_data.columns else 'close'
            
            if price_field not in stock_data.columns:
                logger.error(f"股票数据中缺少价格字段: {list(stock_data.columns)}")
                return []
            
            ma_series = MovingAverageCalculator.calculate_ma(stock_data[price_field], ma_period)
            return MovingAverageCalculator.calculate_consecutive_angles(ma_series, consecutive_days)
            
        except Exception as e:
            logger.error(f"计算MA{ma_period}连续{consecutive_days}天角度失败: {e}")
            return []
    
    @staticmethod
    def check_ma_consecutive_condition(stock_data: pd.DataFrame, ma_period: int = 5,
                                     consecutive_days: int = 3, threshold: float = 0.0) -> bool:
        """检查均线连续N天是否都满足角度条件
        
        Args:
            stock_data: 股票数据
            ma_period: 均线周期
            consecutive_days: 连续天数
            threshold: 角度阈值
            
        Returns:
            是否满足条件
        """
        try:
            angles = MovingAverageCalculator.calculate_ma_angles_consecutive(
                stock_data, ma_period, consecutive_days
            )
            
            if not angles or len(angles) < consecutive_days:
                return False
            
            # 检查是否所有角度都大于阈值
            return all(angle > threshold for angle in angles)
            
        except Exception as e:
            logger.error(f"检查MA{ma_period}连续条件失败: {e}")
            return False


# 便捷函数
def calculate_ma5_angle_latest(stock_data: pd.DataFrame) -> float:
    """计算MA5最新角度的便捷函数"""
    ma5 = MovingAverageCalculator.calculate_ma(stock_data['close_price'], 5)
    return MovingAverageCalculator.calculate_ma_angle(ma5, -1)


def calculate_ma5_consecutive_angles(stock_data: pd.DataFrame, days: int = 3) -> List[float]:
    """计算MA5连续N天角度的便捷函数"""
    ma5 = MovingAverageCalculator.calculate_ma(stock_data['close_price'], 5)
    return MovingAverageCalculator.calculate_consecutive_angles(ma5, days)


def check_ma5_consecutive_condition(stock_data: pd.DataFrame, threshold: float = 20, 
                                   consecutive_days: int = 3, condition_type: str = "all") -> dict:
    """检查MA5连续条件的便捷函数"""
    angles = calculate_ma5_consecutive_angles(stock_data, consecutive_days)
    return MovingAverageCalculator.check_consecutive_condition(
        angles, threshold, consecutive_days, condition_type
    )