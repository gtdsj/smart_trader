# -*- coding: utf-8 -*-
"""
自定义条件管理器
处理所有custom类型的条件筛选逻辑
"""

import traceback
import pandas as pd
import numpy as np
import json
from typing import Dict, List, Any, Callable, Optional
from loguru import logger
from abc import ABC, abstractmethod

# 导入新的工具类
from utils.ma_calculator import MovingAverageCalculator
from services.stock_info_cache_service import StockInfoCacheService
from services.stock_info_cache_service import get_stock_cache_service

class CustomConditionBase(ABC):
    """自定义条件基类"""
    
    def __init__(self, name: str = "", description: str = "", parameters: Optional[Dict[str, Any]] = None):
        self.name = name
        self.description = description
        self.parameters = parameters or {}
        
        # 解析参数
        self._parse_parameters()
    
    def _parse_parameters(self):
        """解析参数，子类可以重写此方法来处理特定参数"""
        pass
    
    def get_parameter(self, key: str, default: Any = None) -> Any:
        """获取参数值
        
        Args:
            key: 参数键
            default: 默认值
            
        Returns:
            参数值
        """
        return self.parameters.get(key, default)
    
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
    
    def _convert_value_type(self, value: Any) -> Any:
        """智能类型转换
        
        Args:
            value: 需要转换的值
            
        Returns:
            转换后的值
        """
        if isinstance(value, str):
            # 尝试转换为数字
            try:
                # 先尝试整数
                if '.' not in value:
                    return int(value)
                else:
                    return float(value)
            except ValueError:
                # 尝试转换为布尔值
                if value.lower() in ('true', '1', 'yes', 'on'):
                    return 1
                elif value.lower() in ('false', '0', 'no', 'off'):
                    return 0
                # 保持字符串
                return value
        return value


class ConsecutiveCloseAboveMACondition(CustomConditionBase):
    """连续N个交易日收盘价高于MA"""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__("consecutive_close_above_ma", "连续N天收盘价高于MA", parameters)
    
    def _parse_parameters(self):
        """解析参数"""
        self.ma_period = self.get_parameter('ma_period', 5)
        self.consecutive_days = self.get_parameter('consecutive_days', 3)
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> int:
        try:
            ma_period = parameters.get('ma_period', 5) if parameters else 5
            consecutive_days = parameters.get('consecutive_days', 3) if parameters else 3
            
            if len(stock_data) < max(ma_period, consecutive_days):
                return 0
            
            # 计算5日均线
            ma5 = stock_data['close_price'].rolling(window=ma_period).mean()
            
            # 检查最近consecutive_days天收盘价是否都不低于5日均线
            recent_data = stock_data.tail(consecutive_days)
            recent_ma5 = ma5.tail(consecutive_days)
            return 1 if all(recent_data['close_price'] >= recent_ma5) else 0
            
        except Exception as e:
            logger.error(f"计算连续收盘价高于MA5失败: {e}")
            return 0
    
    def get_name(self) -> str:
        return "consecutive_close_above_ma"
    
    def get_description(self) -> str:
        return "连续N个交易日收盘价不低于5日均线"


class IsKCBStockCondition(CustomConditionBase):
    """判断是否为科创板股票"""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__("is_kcb_stock", "判断是否为科创板股票", parameters)
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> int:
        try:
            # 从stock_data的index或者额外参数获取股票代码
            stock_code = parameters.get('stock_code', '') if parameters else ''
            if not stock_code and hasattr(stock_data, 'attrs') and 'stock_code' in stock_data.attrs:
                stock_code = stock_data.attrs['stock_code']
            
            # 科创板股票代码以688开头
            return 1 if stock_code.startswith('688') else 0
            
        except Exception as e:
            logger.error(f"判断科创板股票失败: {e}")
            return 0
    
    def get_name(self) -> str:
        return "is_kcb_stock"
    
    def get_description(self) -> str:
        return "判断是否为科创板股票"


class IsBSEStockCondition(CustomConditionBase):
    """判断是否为北交所股票"""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__("is_bse_stock", "判断是否为北交所股票", parameters)
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> int:
        try:
            stock_code = parameters.get('stock_code', '') if parameters else ''
            if not stock_code and hasattr(stock_data, 'attrs') and 'stock_code' in stock_data.attrs:
                stock_code = stock_data.attrs['stock_code']
            
            return 1 if (stock_code[:2] in {'83', '87', '88', '92'}) else 0
            
        except Exception as e:
            logger.error(f"判断北交所股票失败: {e}")
            return 0
    
    def get_name(self) -> str:
        return "is_bse_stock"
    
    def get_description(self) -> str:
        return "判断是否为北交所股票"


class IsSTStockCondition(CustomConditionBase):
    """判断是否为ST股票"""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__("is_st_stock", "判断是否为ST股票", parameters)
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> int:
        try:
            stock_code = None
            if hasattr(stock_data, 'attrs') and 'stock_code' in stock_data.attrs:
                stock_code = stock_data.attrs['stock_code']
            elif parameters and 'stock_code' in parameters:
                stock_code = parameters['stock_code']
            if not stock_code:
                logger.warning("无法获取股票代码，无法判断ST股票")
                return 0
            
            # 通过XtQuantService获取股票基础信息
            
            stock_info_cache = get_stock_cache_service()
            stock_info = stock_info_cache.get_stock_info(stock_code)
            if not stock_info:
                logger.warning(f"IsSTStockCondition无法获取股票基础信息: {stock_code}")
                return 0
            
            if stock_info.get('is_st', False):
                return 1
            stock_name = stock_info.get('stock_name', '')
            
            # ST股票名称包含ST、*ST等标识
            st_keywords = ['ST', '*ST', 'S*ST', 'SST']
            result = 1 if any(keyword in stock_name.upper() for keyword in st_keywords) else 0
            
            logger.info(f"股票 {stock_code}({stock_name}) ST判断结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"判断ST股票失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return 0
    
    def get_name(self) -> str:
        return "is_st_stock"
    
    def get_description(self) -> str:
        return "判断是否为ST股票"


class ConsecutiveCloseAboveOpenCondition(CustomConditionBase):
    """连续N个交易日收盘价高于开盘价"""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__("consecutive_close_above_open", "连续收盘价高于开盘价", parameters)
    
    def _parse_parameters(self):
        """解析参数"""
        self.consecutive_days = self.get_parameter('consecutive_days', 3)
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> int:
        try:
            consecutive_days = parameters.get('consecutive_days', 2) if parameters else 2
            
            if len(stock_data) < consecutive_days:
                return 0
            
            # 检查最近consecutive_days天收盘价是否都高于开盘价
            recent_data = stock_data.tail(consecutive_days)
            return 1 if all(recent_data['close_price'] > recent_data['open_price']) else 0
            
        except Exception as e:
            logger.error(f"计算连续收盘价高于开盘价失败: {e}")
            return 0
    
    def get_name(self) -> str:
        return "consecutive_close_above_open"
    
    def get_description(self) -> str:
        return "连续N个交易日收盘价都高于开盘价"


class MAAngleConsecutiveCondition(CustomConditionBase):
    """连续N个交易日X日均线角度大于阈值Y"""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__("ma5_angle_consecutive", "连续N个交易日X日均线角度大于阈值", parameters)
    
    def _parse_parameters(self):
        """解析参数"""
        self.ma_period = self.get_parameter('ma_period', 5)
        self.consecutive_days = self.get_parameter('consecutive_days', 3)
        self.threshold = self.get_parameter('threshold', 0.0)
        self.return_type = self.get_parameter('return_type', 'boolean')  # 'boolean' 或 'average'
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> Any:
        """检查MA连续N天是否都满足角度条件
        
        Args:
            stock_data: 股票数据
            parameters: 参数字典（可选，会覆盖初始化参数）
            
        Returns:
            如果return_type='boolean': 返回0/1（是否连续满足条件）
            如果return_type='average': 返回连续N天的平均角度
        """
        try:
            # 检查连续N天是否都满足条件
            result = MovingAverageCalculator.check_ma_consecutive_condition(
                stock_data, 
                ma_period=self.ma_period,
                consecutive_days=self.consecutive_days,
                threshold=self.threshold
            )
            return self._convert_value_type(1 if result else 0)
            
        except Exception as e:
            logger.error(f"计算MA{self.ma_period}连续角度失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return 0 if self.return_type == 'boolean' else 0.0
    
    def get_name(self) -> str:
        return "ma_angle_consecutive"
    
    def get_description(self) -> str:
        if self.return_type == 'boolean':
            return f"检查{self.ma_period}日移动平均线连续{self.consecutive_days}天是否都大于{self.threshold}度"
        else:
            return f"计算{self.ma_period}日移动平均线连续{self.consecutive_days}天的平均角度（度数）"


class MAAngleLatestCondition(CustomConditionBase):
    """最近一个交易日五日均线角度大于阈值"""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__("ma_angle_latest", "最近一个交易日N日均线角度大于阈值X", parameters)
    
    def _parse_parameters(self):
        """解析参数"""
        self.ma_period = self.get_parameter('ma_period', 5)
        self.threshold = self.get_parameter('threshold', 0.0)
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> float:
        try:
            # 使用传入的参数或默认参数
            ma_period = parameters.get('ma_period', self.ma_period) if parameters else self.ma_period
            
            # 使用工具类计算角度
            angle = MovingAverageCalculator.calculate_ma_angle_latest(
                stock_data, ma_period=ma_period
            )
            
            return self._convert_value_type(1 if angle > self.threshold else 0)
            
        except Exception as e:
            logger.error(f"计算MA{self.ma_period}最新角度失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return 0.0
    
    def get_name(self) -> str:
        return "ma_angle_latest"
    
    def get_description(self) -> str:
        return f"计算{self.ma_period}日移动平均线的最新角度（度数）"

class IsBreakBoardCondition(CustomConditionBase):
    """判断是否为破板股"""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__("is_break_board", "判断是否为破板股", parameters)
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> int:
        try:
            if len(stock_data) < 2:
                return 0
            
            # 获取股票代码
            stock_code = None
            if hasattr(stock_data, 'attrs') and 'stock_code' in stock_data.attrs:
                stock_code = stock_data.attrs['stock_code']
            elif parameters and 'stock_code' in parameters:
                stock_code = parameters['stock_code']
            if not stock_code:
                logger.warning("无法获取股票代码，无法判断破板")
                return 0
            
            # 获取当前交易日和前一交易日数据
            current_day = stock_data.iloc[-1]
            previous_day = stock_data.iloc[-2]
            
            # 获取前一交易日收盘价
            prev_close = float(previous_day['close_price'])
            
            # 根据股票类型计算涨停价格
            limit_up_price = self._calculate_limit_up_price(stock_code, prev_close)
            
            if limit_up_price is None:
                return 0
            
            # 获取当日最高价和收盘价
            current_high = float(current_day['high_price'])
            current_close = float(current_day['close_price'])
            
            # 判断是否破板：当日最高价等于涨停价，且收盘价低于涨停价
            is_break_board = (
                abs(current_high - limit_up_price) < 0.005 and  # 最高价触及涨停价（允许0.005的误差）
                current_close < limit_up_price - 0.005  # 收盘价明显低于涨停价
            )
            
            result = self._convert_value_type(1 if is_break_board else 0)
            logger.info(f"IsBreakBoardCondition判断结果, stock_code:{stock_code}, {result}")
            return result
            
        except Exception as e:
            logger.error(f"判断破板股失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return 0
    
    def _calculate_limit_up_price(self, stock_code: str, prev_close: float) -> Optional[float]:
        """计算涨停价格
        
        Args:
            stock_code: 股票代码
            prev_close: 前一交易日收盘价
            
        Returns:
            涨停价格，如果无法计算返回None
        """
        try:
            # 获取股票基础信息
            cache_service = get_stock_cache_service()
            stock_info = cache_service.get_stock_info(stock_code)
            if not stock_info:
                logger.warning(f"IsBreakBoardCondition无法获取股票 {stock_code} 的基础信息")
                return None
            
            # 判断股票类型并确定涨跌幅限制
            limit_ratio = self._get_limit_ratio(stock_code, stock_info)
            
            # 计算涨停价格
            limit_up_price = prev_close * (1 + limit_ratio)
            
            # 四舍五入到分（保留2位小数）
            limit_up_price = round(limit_up_price, 2)
            
            return limit_up_price
            
        except Exception as e:
            logger.error(f"计算涨停价格失败 {stock_code}: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return None
    
    def _get_limit_ratio(self, stock_code: str, stock_info: Dict[str, Any]) -> float:
        """获取涨跌幅限制比例
        
        Args:
            stock_code: 股票代码
            stock_info: 股票基础信息
            
        Returns:
            涨跌幅限制比例（如0.1表示10%）
        """
        try:
            # ST股票：5%
            if stock_info.get('is_st', False):
                return 0.05
            
            # 创业板（300开头）：20%
            if stock_code.startswith('30'):
                return 0.20
            
            # 科创板（688开头）：20%
            if stock_code.startswith('688'):
                return 0.20
            
            # 北交所（8开头，43开头）：30%
            if stock_code.startswith('8') or stock_code.startswith('43'):
                return 0.30
            
            # 其他A股（主板）：10%
            return 0.10
            
        except Exception as e:
            logger.error(f"获取涨跌幅限制失败 {stock_code}: {e}")
            # 默认返回10%
            return 0.10
    
    def get_name(self) -> str:
        return "is_break_board"
    
    def get_description(self) -> str:
        return "判断是否为破板股"


class MainFundInflowCondition(CustomConditionBase):
    """主力资金净流入"""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__("main_fund_inflow", "主力资金净流入", parameters)
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> int:
        try:
            # 简化实现：基于成交量和价格变化估算资金流向
            # TODO: 需要真实的资金流数据
            if len(stock_data) < 2:
                return 0
            
            # 简单估算：价格上涨且成交量放大
            latest = stock_data.iloc[-1]
            previous = stock_data.iloc[-2]
            
            price_up = latest['close_price'] > previous['close_price']
            volume_up = latest['volume'] > previous['volume']
            
            return 1 if (price_up and volume_up) else 0
            
        except Exception as e:
            logger.error(f"计算主力资金流入失败: {e}")
            return 0
    
    def get_name(self) -> str:
        return "main_fund_inflow"
    
    def get_description(self) -> str:
        return "主力资金净流入"


class LowAboveMACondition(CustomConditionBase):
    """最低价高于MA"""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__("low_above_ma", "最低价高于MA", parameters)
    
    def _parse_parameters(self):
        """解析参数"""
        self.ma_period = self.get_parameter('ma_period', 5)
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> int:
        try:
            ma_period = parameters.get('ma_period', 5) if parameters else 5
            
            if len(stock_data) < ma_period:
                return 0
            
            # 计算5日均线
            ma5 = stock_data['close_price'].rolling(window=ma_period).mean()
            
            # 检查最新一天的最低价是否高于5日均线
            latest_low = stock_data['low_price'].iloc[-1]
            latest_ma5 = ma5.iloc[-1]
            
            return 1 if latest_low > latest_ma5 else 0
            
        except Exception as e:
            logger.error(f"计算最低价高于MA5失败: {e}")
            return 0
    
    def get_name(self) -> str:
        return "low_above_ma"
    
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
            ConsecutiveCloseAboveMACondition(),
            IsKCBStockCondition(),
            IsBSEStockCondition(),
            IsSTStockCondition(),
            ConsecutiveCloseAboveOpenCondition(),
            MAAngleConsecutiveCondition(),
            MAAngleLatestCondition(),
            IsBreakBoardCondition(),
            MainFundInflowCondition(),
            LowAboveMACondition()
        ]
        
        for condition in default_conditions:
            self.register_condition(condition)
    
    def create_condition_with_parameters(self, condition_name: str, parameters: Optional[Dict[str, Any]] = None) -> Optional[CustomConditionBase]:
        """根据条件名称和参数创建条件实例
        
        Args:
            condition_name: 条件名称
            parameters: 参数字典
            
        Returns:
            条件实例
        """
        try:
            # 条件类映射
            condition_classes = {
                'consecutive_close_above_ma': ConsecutiveCloseAboveMACondition,
                'consecutive_close_above_open': ConsecutiveCloseAboveOpenCondition,
                'ma_angle_consecutive': MAAngleConsecutiveCondition,
                'ma_angle_latest': MAAngleLatestCondition,
                'low_above_ma': LowAboveMACondition,
                'is_kcb_stock': IsKCBStockCondition,
                'is_bse_stock': IsBSEStockCondition,
                'is_st_stock': IsSTStockCondition,
                'is_break_board': IsBreakBoardCondition,
                'main_fund_inflow': MainFundInflowCondition
            }
            
            condition_class = condition_classes.get(condition_name)
            if condition_class:
                return condition_class(parameters=parameters)
            else:
                logger.warning(f"未知的条件类型: {condition_name}")
                return None
                
        except Exception as e:
            logger.error(f"创建条件实例失败: {condition_name}, 错误: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return None
    
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
            
            # 类型转换：确保value和indicator_value类型一致
            converted_value = self._convert_value_type(value, indicator_value)
            
            # 评估条件
            if operator == "==":
                return indicator_value == converted_value
            elif operator == "!=":
                return indicator_value != converted_value
            elif operator == ">":
                return indicator_value > converted_value
            elif operator == ">=":
                return indicator_value >= converted_value
            elif operator == "<":
                return indicator_value < converted_value
            elif operator == "<=":
                return indicator_value <= converted_value
            elif operator == "between":
                if isinstance(value, dict) and "min" in value and "max" in value:
                    min_val = self._convert_value_type(value["min"], indicator_value)
                    max_val = self._convert_value_type(value["max"], indicator_value)
                    return min_val <= indicator_value <= max_val
                elif isinstance(value, str):
                    # 处理字符串格式的between值，如 '{"min": -5.0, "max": 6.1}'
                    import json
                    try:
                        value_dict = json.loads(value)
                        if "min" in value_dict and "max" in value_dict:
                            min_val = self._convert_value_type(value_dict["min"], indicator_value)
                            max_val = self._convert_value_type(value_dict["max"], indicator_value)
                            return min_val <= indicator_value <= max_val
                    except json.JSONDecodeError:
                        pass
            elif operator == "in":
                if isinstance(value, list):
                    converted_list = [self._convert_value_type(v, indicator_value) for v in value]
                    return indicator_value in converted_list
            elif operator == "not_in":
                if isinstance(value, list):
                    converted_list = [self._convert_value_type(v, indicator_value) for v in value]
                    return indicator_value not in converted_list
            
            return False
            
        except Exception as e:
            logger.error(f"评估自定义条件失败: {traceback.format_exc()}, 条件: {condition_dict}, indicator_value: {indicator_value}, value: {value}")
            return False
    
    def _convert_value_type(self, value: Any, reference_value: Any) -> Any:
        """根据参考值的类型转换value的类型"""
        try:
            # 如果value已经是正确类型，直接返回
            if type(value) == type(reference_value):
                return value
            
            # 根据reference_value的类型进行转换
            if isinstance(reference_value, bool):
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                return bool(value)
            elif isinstance(reference_value, int):
                if isinstance(value, str):
                    # 处理布尔字符串
                    if value.lower() in ('true', 'false'):
                        return 1 if value.lower() == 'true' else 0
                return int(float(value))  # 先转float再转int，处理"1.0"这种情况
            elif isinstance(reference_value, float):
                return float(value)
            elif isinstance(reference_value, str):
                return str(value)
            else:
                return value
                
        except (ValueError, TypeError) as e:
            logger.warning(f"类型转换失败: {value} -> {type(reference_value)}, 错误: {e}")
            return value


# 全局单例
_custom_condition_manager = None


def get_custom_condition_manager() -> CustomConditionManager:
    """获取自定义条件管理器单例"""
    global _custom_condition_manager
    if _custom_condition_manager is None:
        _custom_condition_manager = CustomConditionManager()
    return _custom_condition_manager