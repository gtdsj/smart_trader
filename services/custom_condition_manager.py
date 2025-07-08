# -*- coding: utf-8 -*-
"""
自定义条件管理器
处理所有custom类型的条件筛选逻辑
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Callable, Optional
from loguru import logger
from abc import ABC, abstractmethod


class CustomConditionBase(ABC):
    """自定义条件基类"""
    
    @abstractmethod
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> Any:
        """计算指标值"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """获取条件名称"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """获取条件描述"""
        pass


class ConsecutiveCloseAboveMA5Condition(CustomConditionBase):
    """连续N个交易日收盘价不低于5日均线"""
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> bool:
        try:
            ma_period = parameters.get('ma_period', 5) if parameters else 5
            consecutive_days = parameters.get('consecutive_days', 3) if parameters else 3
            
            if len(stock_data) < max(ma_period, consecutive_days):
                return False
            
            # 计算5日均线
            ma5 = stock_data['close_price'].rolling(window=ma_period).mean()
            
            # 检查最近consecutive_days天收盘价是否都不低于5日均线
            recent_data = stock_data.tail(consecutive_days)
            recent_ma5 = ma5.tail(consecutive_days)
            
            return all(recent_data['close_price'] >= recent_ma5)
            
        except Exception as e:
            logger.error(f"计算连续收盘价高于MA5失败: {e}")
            return False
    
    def get_name(self) -> str:
        return "consecutive_close_above_ma5"
    
    def get_description(self) -> str:
        return "连续N个交易日收盘价不低于5日均线"


class IsKCBStockCondition(CustomConditionBase):
    """判断是否为科创板股票"""
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> bool:
        try:
            # 从stock_data的index或者额外参数获取股票代码
            stock_code = parameters.get('stock_code', '') if parameters else ''
            if not stock_code and hasattr(stock_data, 'attrs') and 'stock_code' in stock_data.attrs:
                stock_code = stock_data.attrs['stock_code']
            
            # 科创板股票代码以688开头
            return stock_code.startswith('688')
            
        except Exception as e:
            logger.error(f"判断科创板股票失败: {e}")
            return False
    
    def get_name(self) -> str:
        return "is_kcb_stock"
    
    def get_description(self) -> str:
        return "判断是否为科创板股票"


class IsBSEStockCondition(CustomConditionBase):
    """判断是否为北交所股票"""
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> bool:
        try:
            stock_code = parameters.get('stock_code', '') if parameters else ''
            if not stock_code and hasattr(stock_data, 'attrs') and 'stock_code' in stock_data.attrs:
                stock_code = stock_data.attrs['stock_code']
            
            # 北交所股票代码以8开头且为3位数字
            return stock_code.startswith('8') and len(stock_code) >= 6 and stock_code[:3].isdigit()
            
        except Exception as e:
            logger.error(f"判断北交所股票失败: {e}")
            return False
    
    def get_name(self) -> str:
        return "is_bse_stock"
    
    def get_description(self) -> str:
        return "判断是否为北交所股票"


class IsSTStockCondition(CustomConditionBase):
    """判断是否为ST股票"""
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> bool:
        try:
            stock_name = parameters.get('stock_name', '') if parameters else ''
            
            # ST股票名称包含ST、*ST等标识
            st_keywords = ['ST', '*ST', 'S*ST', 'SST']
            return any(keyword in stock_name.upper() for keyword in st_keywords)
            
        except Exception as e:
            logger.error(f"判断ST股票失败: {e}")
            return False
    
    def get_name(self) -> str:
        return "is_st_stock"
    
    def get_description(self) -> str:
        return "判断是否为ST股票"


class ConsecutiveCloseAboveOpenCondition(CustomConditionBase):
    """连续N个交易日收盘价都高于开盘价"""
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> bool:
        try:
            consecutive_days = parameters.get('consecutive_days', 2) if parameters else 2
            
            if len(stock_data) < consecutive_days:
                return False
            
            # 检查最近consecutive_days天收盘价是否都高于开盘价
            recent_data = stock_data.tail(consecutive_days)
            return all(recent_data['close_price'] > recent_data['open_price'])
            
        except Exception as e:
            logger.error(f"计算连续收盘价高于开盘价失败: {e}")
            return False
    
    def get_name(self) -> str:
        return "consecutive_close_above_open"
    
    def get_description(self) -> str:
        return "连续N个交易日收盘价都高于开盘价"


class MA5AngleConsecutiveCondition(CustomConditionBase):
    """连续N个交易日五日均线角度大于阈值"""
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> bool:
        try:
            ma_period = parameters.get('ma_period', 5) if parameters else 5
            consecutive_days = parameters.get('consecutive_days', 3) if parameters else 3
            min_angle = parameters.get('min_angle', 20) if parameters else 20
            
            if len(stock_data) < ma_period + consecutive_days:
                return False
            
            # 计算5日均线
            ma5 = stock_data['close_price'].rolling(window=ma_period).mean()
            
            # 计算均线角度（斜率转角度）
            angles = []
            for i in range(len(ma5) - 1):
                if pd.notna(ma5.iloc[i]) and pd.notna(ma5.iloc[i + 1]):
                    slope = ma5.iloc[i + 1] - ma5.iloc[i]
                    angle = np.arctan(slope) * 180 / np.pi
                    angles.append(angle)
                else:
                    angles.append(0)
            
            # 检查最近consecutive_days天的角度是否都大于阈值
            if len(angles) < consecutive_days:
                return False
            
            recent_angles = angles[-consecutive_days:]
            return all(angle > min_angle for angle in recent_angles)
            
        except Exception as e:
            logger.error(f"计算MA5连续角度失败: {e}")
            return False
    
    def get_name(self) -> str:
        return "ma5_angle_consecutive"
    
    def get_description(self) -> str:
        return "连续N个交易日五日均线角度大于阈值"


class MA5AngleLatestCondition(CustomConditionBase):
    """最近一个交易日五日均线角度大于阈值"""
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> float:
        try:
            ma_period = parameters.get('ma_period', 5) if parameters else 5
            
            if len(stock_data) < ma_period + 1:
                return 0
            
            # 计算5日均线
            ma5 = stock_data['close_price'].rolling(window=ma_period).mean()
            
            # 计算最新的角度
            if len(ma5) >= 2 and pd.notna(ma5.iloc[-1]) and pd.notna(ma5.iloc[-2]):
                slope = ma5.iloc[-1] - ma5.iloc[-2]
                angle = np.arctan(slope) * 180 / np.pi
                return angle
            
            return 0
            
        except Exception as e:
            logger.error(f"计算MA5最新角度失败: {e}")
            return 0
    
    def get_name(self) -> str:
        return "ma5_angle_latest"
    
    def get_description(self) -> str:
        return "最近一个交易日五日均线角度"


class MA10AngleConsecutiveCondition(CustomConditionBase):
    """连续N个交易日十日均线角度大于阈值"""
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> bool:
        try:
            ma_period = parameters.get('ma_period', 10) if parameters else 10
            consecutive_days = parameters.get('consecutive_days', 3) if parameters else 3
            min_angle = parameters.get('min_angle', 10) if parameters else 10
            
            if len(stock_data) < ma_period + consecutive_days:
                return False
            
            # 计算10日均线
            ma10 = stock_data['close_price'].rolling(window=ma_period).mean()
            
            # 计算均线角度
            angles = []
            for i in range(len(ma10) - 1):
                if pd.notna(ma10.iloc[i]) and pd.notna(ma10.iloc[i + 1]):
                    slope = ma10.iloc[i + 1] - ma10.iloc[i]
                    angle = np.arctan(slope) * 180 / np.pi
                    angles.append(angle)
                else:
                    angles.append(0)
            
            # 检查最近consecutive_days天的角度是否都大于阈值
            if len(angles) < consecutive_days:
                return False
            
            recent_angles = angles[-consecutive_days:]
            return all(angle > min_angle for angle in recent_angles)
            
        except Exception as e:
            logger.error(f"计算MA10连续角度失败: {e}")
            return False
    
    def get_name(self) -> str:
        return "ma10_angle_consecutive"
    
    def get_description(self) -> str:
        return "连续N个交易日十日均线角度大于阈值"


class IsBreakBoardCondition(CustomConditionBase):
    """判断是否为破板股"""
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> bool:
        try:
            # 简化实现：检查是否有涨停后回落的情况
            # 这里需要更复杂的逻辑来判断破板，暂时返回False
            # TODO: 需要涨停板数据来准确判断
            return False
            
        except Exception as e:
            logger.error(f"判断破板股失败: {e}")
            return False
    
    def get_name(self) -> str:
        return "is_break_board"
    
    def get_description(self) -> str:
        return "判断是否为破板股"


class MainFundInflowCondition(CustomConditionBase):
    """主力资金净流入"""
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> bool:
        try:
            # 简化实现：基于成交量和价格变化估算资金流向
            # TODO: 需要真实的资金流数据
            if len(stock_data) < 2:
                return False
            
            # 简单估算：价格上涨且成交量放大
            latest = stock_data.iloc[-1]
            previous = stock_data.iloc[-2]
            
            price_up = latest['close_price'] > previous['close_price']
            volume_up = latest['volume'] > previous['volume']
            
            return price_up and volume_up
            
        except Exception as e:
            logger.error(f"计算主力资金流入失败: {e}")
            return False
    
    def get_name(self) -> str:
        return "main_fund_inflow"
    
    def get_description(self) -> str:
        return "主力资金净流入"


class LowAboveMA5Condition(CustomConditionBase):
    """最近一个交易日最低股价高于五日均线"""
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> bool:
        try:
            ma_period = parameters.get('ma_period', 5) if parameters else 5
            
            if len(stock_data) < ma_period:
                return False
            
            # 计算5日均线
            ma5 = stock_data['close_price'].rolling(window=ma_period).mean()
            
            # 检查最新一天的最低价是否高于5日均线
            latest_low = stock_data['low_price'].iloc[-1]
            latest_ma5 = ma5.iloc[-1]
            
            return latest_low > latest_ma5
            
        except Exception as e:
            logger.error(f"计算最低价高于MA5失败: {e}")
            return False
    
    def get_name(self) -> str:
        return "low_above_ma5"
    
    def get_description(self) -> str:
        return "最近一个交易日最低股价高于五日均线"


class CustomConditionManager:
    """自定义条件管理器"""
    
    def __init__(self):
        self._conditions: Dict[str, CustomConditionBase] = {}
        self._register_default_conditions()
    
    def _register_default_conditions(self):
        """注册默认的自定义条件"""
        default_conditions = [
            ConsecutiveCloseAboveMA5Condition(),
            IsKCBStockCondition(),
            IsBSEStockCondition(),
            IsSTStockCondition(),
            ConsecutiveCloseAboveOpenCondition(),
            MA5AngleConsecutiveCondition(),
            MA5AngleLatestCondition(),
            MA10AngleConsecutiveCondition(),
            IsBreakBoardCondition(),
            MainFundInflowCondition(),
            LowAboveMA5Condition()
        ]
        
        for condition in default_conditions:
            self.register_condition(condition)
    
    def register_condition(self, condition: CustomConditionBase):
        """注册自定义条件"""
        self._conditions[condition.get_name()] = condition
        logger.info(f"注册自定义条件: {condition.get_name()} - {condition.get_description()}")
    
    def unregister_condition(self, condition_name: str):
        """注销自定义条件"""
        if condition_name in self._conditions:
            del self._conditions[condition_name]
            logger.info(f"注销自定义条件: {condition_name}")
    
    def get_condition(self, condition_name: str) -> Optional[CustomConditionBase]:
        """获取自定义条件"""
        return self._conditions.get(condition_name)
    
    def list_conditions(self) -> List[Dict[str, str]]:
        """列出所有注册的自定义条件"""
        return [
            {
                "name": name,
                "description": condition.get_description()
            }
            for name, condition in self._conditions.items()
        ]
    
    def calculate_condition(self, condition_name: str, stock_data: pd.DataFrame, 
                          parameters: Dict[str, Any] = None, stock_code: str = None) -> Any:
        """计算自定义条件"""
        condition = self.get_condition(condition_name)
        if not condition:
            logger.error(f"未找到自定义条件: {condition_name}")
            return None
        
        # 为股票数据添加股票代码信息
        if stock_code and hasattr(stock_data, 'attrs'):
            stock_data.attrs['stock_code'] = stock_code
        elif stock_code and parameters:
            if parameters is None:
                parameters = {}
            parameters['stock_code'] = stock_code
        
        try:
            return condition.calculate(stock_data, parameters)
        except Exception as e:
            logger.error(f"计算自定义条件 {condition_name} 失败: {e}")
            return None
    
    def evaluate_custom_condition(self, condition_dict: Dict[str, Any], stock_data: pd.DataFrame, 
                                stock_code: str = None) -> bool:
        """评估自定义条件"""
        try:
            indicator = condition_dict.get("indicator")
            operator = condition_dict.get("operator")
            value = condition_dict.get("value")
            parameters = condition_dict.get("parameters", {})
            
            # 计算指标值
            indicator_value = self.calculate_condition(indicator, stock_data, parameters, stock_code)
            
            if indicator_value is None:
                return False
            
            # 评估条件
            if operator == "==":
                return indicator_value == value
            elif operator == "!=":
                return indicator_value != value
            elif operator == ">":
                return indicator_value > value
            elif operator == ">=":
                return indicator_value >= value
            elif operator == "<":
                return indicator_value < value
            elif operator == "<=":
                return indicator_value <= value
            elif operator == "between":
                if isinstance(value, dict) and "min" in value and "max" in value:
                    return value["min"] <= indicator_value <= value["max"]
            elif operator == "in":
                if isinstance(value, list):
                    return indicator_value in value
            elif operator == "not_in":
                if isinstance(value, list):
                    return indicator_value not in value
            
            return False
            
        except Exception as e:
            logger.error(f"评估自定义条件失败: {e}")
            return False


# 全局单例
_custom_condition_manager = None


def get_custom_condition_manager() -> CustomConditionManager:
    """获取自定义条件管理器单例"""
    global _custom_condition_manager
    if _custom_condition_manager is None:
        _custom_condition_manager = CustomConditionManager()
    return _custom_condition_manager