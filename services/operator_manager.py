# -*- coding: utf-8 -*-
"""
操作符管理服务模块
提供通用操作符和逻辑操作符的统一管理和计算功能
"""

import traceback
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
import pandas as pd
import numpy as np
from loguru import logger


class OperatorType(Enum):
    """操作符类型枚举"""
    # 比较操作符
    GT = ">"  # 大于
    LT = "<"  # 小于
    GTE = ">="  # 大于等于
    LTE = "<="  # 小于等于
    EQ = "=="  # 等于
    NEQ = "!="  # 不等于
    
    # 区间操作符
    BETWEEN = "between"  # 区间（闭区间）
    BETWEEN_OPEN = "between_open"  # 开区间
    BETWEEN_LEFT_OPEN = "between_left_open"  # 左开右闭
    BETWEEN_RIGHT_OPEN = "between_right_open"  # 左闭右开
    
    # 包含操作符
    IN = "in"  # 包含
    NOT_IN = "not_in"  # 不包含
    
    # 字符串操作符
    CONTAINS = "contains"  # 字符串包含
    STARTS_WITH = "starts_with"  # 以...开始
    ENDS_WITH = "ends_with"  # 以...结束
    REGEX = "regex"  # 正则表达式匹配
    
    # 空值操作符
    IS_NULL = "is_null"  # 为空
    IS_NOT_NULL = "is_not_null"  # 不为空
    
    # 数值操作符
    NEAR = "near"  # 接近（在误差范围内）
    PERCENT_CHANGE = "percent_change"  # 百分比变化


class LogicOperator(Enum):
    """逻辑操作符枚举"""
    AND = "AND"  # 与
    OR = "OR"  # 或
    NOT = "NOT"  # 非
    XOR = "XOR"  # 异或


class OperatorManager:
    """操作符管理器"""
    
    def __init__(self):
        # 操作符定义
        self.operators = {
            # 基本比较操作符
            OperatorType.GT.value: {
                "name": "大于",
                "description": "左值大于右值",
                "symbol": ">",
                "value_type": "single",
                "calculator": self._calculate_gt
            },
            OperatorType.LT.value: {
                "name": "小于",
                "description": "左值小于右值",
                "symbol": "<",
                "value_type": "single",
                "calculator": self._calculate_lt
            },
            OperatorType.GTE.value: {
                "name": "大于等于",
                "description": "左值大于或等于右值",
                "symbol": ">=",
                "value_type": "single",
                "calculator": self._calculate_gte
            },
            OperatorType.LTE.value: {
                "name": "小于等于",
                "description": "左值小于或等于右值",
                "symbol": "<=",
                "value_type": "single",
                "calculator": self._calculate_lte
            },
            OperatorType.EQ.value: {
                "name": "等于",
                "description": "左值等于右值",
                "symbol": "==",
                "value_type": "single",
                "calculator": self._calculate_eq
            },
            OperatorType.NEQ.value: {
                "name": "不等于",
                "description": "左值不等于右值",
                "symbol": "!=",
                "value_type": "single",
                "calculator": self._calculate_neq
            },
            
            # 区间操作符
            OperatorType.BETWEEN.value: {
                "name": "区间（闭区间）",
                "description": "值在指定的闭区间内 [min, max]",
                "symbol": "between",
                "value_type": "range",
                "calculator": self._calculate_between
            },
            OperatorType.BETWEEN_OPEN.value: {
                "name": "区间（开区间）",
                "description": "值在指定的开区间内 (min, max)",
                "symbol": "between_open",
                "value_type": "range",
                "calculator": self._calculate_between_open
            },
            OperatorType.BETWEEN_LEFT_OPEN.value: {
                "name": "区间（左开右闭）",
                "description": "值在指定的左开右闭区间内 (min, max]",
                "symbol": "between_left_open",
                "value_type": "range",
                "calculator": self._calculate_between_left_open
            },
            OperatorType.BETWEEN_RIGHT_OPEN.value: {
                "name": "区间（左闭右开）",
                "description": "值在指定的左闭右开区间内 [min, max)",
                "symbol": "between_right_open",
                "value_type": "range",
                "calculator": self._calculate_between_right_open
            },
            
            # 包含操作符
            OperatorType.IN.value: {
                "name": "包含",
                "description": "值在指定的列表中",
                "symbol": "in",
                "value_type": "list",
                "calculator": self._calculate_in
            },
            OperatorType.NOT_IN.value: {
                "name": "不包含",
                "description": "值不在指定的列表中",
                "symbol": "not_in",
                "value_type": "list",
                "calculator": self._calculate_not_in
            },
            
            # 字符串操作符
            OperatorType.CONTAINS.value: {
                "name": "字符串包含",
                "description": "字符串包含指定的子字符串",
                "symbol": "contains",
                "value_type": "single",
                "calculator": self._calculate_contains
            },
            OperatorType.STARTS_WITH.value: {
                "name": "以...开始",
                "description": "字符串以指定的前缀开始",
                "symbol": "starts_with",
                "value_type": "single",
                "calculator": self._calculate_starts_with
            },
            OperatorType.ENDS_WITH.value: {
                "name": "以...结束",
                "description": "字符串以指定的后缀结束",
                "symbol": "ends_with",
                "value_type": "single",
                "calculator": self._calculate_ends_with
            },
            OperatorType.REGEX.value: {
                "name": "正则表达式",
                "description": "字符串匹配指定的正则表达式",
                "symbol": "regex",
                "value_type": "single",
                "calculator": self._calculate_regex
            },
            
            # 空值操作符
            OperatorType.IS_NULL.value: {
                "name": "为空",
                "description": "值为空或NaN",
                "symbol": "is_null",
                "value_type": "none",
                "calculator": self._calculate_is_null
            },
            OperatorType.IS_NOT_NULL.value: {
                "name": "不为空",
                "description": "值不为空且不是NaN",
                "symbol": "is_not_null",
                "value_type": "none",
                "calculator": self._calculate_is_not_null
            },
            
            # 数值操作符
            OperatorType.NEAR.value: {
                "name": "接近",
                "description": "值在指定值的误差范围内",
                "symbol": "near",
                "value_type": "tolerance",
                "calculator": self._calculate_near
            },
            OperatorType.PERCENT_CHANGE.value: {
                "name": "百分比变化",
                "description": "相对于基准值的百分比变化",
                "symbol": "percent_change",
                "value_type": "percent",
                "calculator": self._calculate_percent_change
            }
        }
        
        # 逻辑操作符定义
        self.logic_operators = {
            LogicOperator.AND.value: {
                "name": "与",
                "description": "所有条件都为真",
                "symbol": "AND",
                "calculator": self._calculate_and
            },
            LogicOperator.OR.value: {
                "name": "或",
                "description": "至少一个条件为真",
                "symbol": "OR",
                "calculator": self._calculate_or
            },
            LogicOperator.NOT.value: {
                "name": "非",
                "description": "条件取反",
                "symbol": "NOT",
                "calculator": self._calculate_not
            },
            LogicOperator.XOR.value: {
                "name": "异或",
                "description": "有且仅有一个条件为真",
                "symbol": "XOR",
                "calculator": self._calculate_xor
            }
        }
    
    def get_all_operators(self) -> Dict[str, Any]:
        """获取所有操作符"""
        return {
            "comparison": {k: {"name": v["name"], "description": v["description"], 
                              "symbol": v["symbol"], "value_type": v["value_type"]} 
                          for k, v in self.operators.items()},
            "logic": {k: {"name": v["name"], "description": v["description"], 
                         "symbol": v["symbol"]} 
                     for k, v in self.logic_operators.items()}
        }
    
    def get_operators_by_value_type(self, value_type: str) -> Dict[str, Any]:
        """根据值类型获取操作符"""
        result = {}
        for key, operator in self.operators.items():
            if operator["value_type"] == value_type:
                result[key] = operator
        return result
    
    def validate_operator_value(self, operator: str, value: Any) -> Dict[str, Any]:
        """验证操作符的值"""
        try:
            if operator not in self.operators:
                return {"valid": False, "message": f"未知的操作符: {operator}"}
            
            operator_info = self.operators[operator]
            value_type = operator_info["value_type"]
            
            if value_type == "none":
                # 不需要值
                return {"valid": True, "value": None}
            
            elif value_type == "single":
                # 单个值
                if value is None:
                    return {"valid": False, "message": "操作符需要一个值"}
                return {"valid": True, "value": value}
            
            elif value_type == "range":
                # 区间值，需要min和max
                if not isinstance(value, dict) or "min" not in value or "max" not in value:
                    return {"valid": False, "message": "区间操作符需要包含min和max的字典"}
                
                if value["min"] >= value["max"]:
                    return {"valid": False, "message": "区间的最小值必须小于最大值"}
                
                return {"valid": True, "value": value}
            
            elif value_type == "list":
                # 列表值
                if not isinstance(value, list) or len(value) == 0:
                    return {"valid": False, "message": "包含操作符需要非空列表"}
                return {"valid": True, "value": value}
            
            elif value_type == "tolerance":
                # 容差值，需要value和tolerance
                if not isinstance(value, dict) or "value" not in value or "tolerance" not in value:
                    return {"valid": False, "message": "接近操作符需要包含value和tolerance的字典"}
                
                if value["tolerance"] < 0:
                    return {"valid": False, "message": "容差值不能为负数"}
                
                return {"valid": True, "value": value}
            
            elif value_type == "percent":
                # 百分比值，需要base_value和percent
                if not isinstance(value, dict) or "base_value" not in value or "percent" not in value:
                    return {"valid": False, "message": "百分比变化操作符需要包含base_value和percent的字典"}
                
                return {"valid": True, "value": value}
            
            else:
                return {"valid": False, "message": f"未知的值类型: {value_type}"}
            
        except Exception as e:
            return {"valid": False, "message": f"验证操作符值失败: {str(e)}"}
    
    def evaluate_condition(self, left_value: Any, operator: str, right_value: Any) -> bool:
        """评估条件"""
        try:
            if operator not in self.operators:
                logger.error(f"未知的操作符: {operator}")
                return False
            
            calculator = self.operators[operator]["calculator"]
            return calculator(left_value, right_value)
            
        except Exception as e:
            logger.error(f"评估条件失败: {e}, {traceback.format_exc()}")
            return False
    
    def evaluate_logic_condition(self, conditions: List[bool], logic_operator: str) -> bool:
        """评估逻辑条件"""
        try:
            if logic_operator not in self.logic_operators:
                logger.error(f"未知的逻辑操作符: {logic_operator}")
                return False
            
            calculator = self.logic_operators[logic_operator]["calculator"]
            return calculator(conditions)
            
        except Exception as e:
            logger.error(f"评估逻辑条件失败: {e}, {traceback.format_exc()}")
            return False
    
    # 比较操作符计算函数
    def _calculate_gt(self, left: Any, right: Any) -> bool:
        """大于"""
        try:
            return float(left) > float(right)
        except (ValueError, TypeError):
            return False
    
    def _calculate_lt(self, left: Any, right: Any) -> bool:
        """小于"""
        try:
            return float(left) < float(right)
        except (ValueError, TypeError):
            return False
    
    def _calculate_gte(self, left: Any, right: Any) -> bool:
        """大于等于"""
        try:
            return float(left) >= float(right)
        except (ValueError, TypeError):
            return False
    
    def _calculate_lte(self, left: Any, right: Any) -> bool:
        """小于等于"""
        try:
            return float(left) <= float(right)
        except (ValueError, TypeError):
            return False
    
    def _calculate_eq(self, left: Any, right: Any) -> bool:
        """等于"""
        try:
            # 尝试数值比较
            return float(left) == float(right)
        except (ValueError, TypeError):
            # 回退到字符串比较
            return str(left) == str(right)
    
    def _calculate_neq(self, left: Any, right: Any) -> bool:
        """不等于"""
        return not self._calculate_eq(left, right)
    
    # 区间操作符计算函数
    def _calculate_between(self, left: Any, right: Dict[str, Any]) -> bool:
        """闭区间 [min, max]"""
        try:
            value = float(left)
            min_val = float(right["min"])
            max_val = float(right["max"])
            return min_val <= value <= max_val
        except (ValueError, TypeError, KeyError):
            return False
    
    def _calculate_between_open(self, left: Any, right: Dict[str, Any]) -> bool:
        """开区间 (min, max)"""
        try:
            value = float(left)
            min_val = float(right["min"])
            max_val = float(right["max"])
            return min_val < value < max_val
        except (ValueError, TypeError, KeyError):
            return False
    
    def _calculate_between_left_open(self, left: Any, right: Dict[str, Any]) -> bool:
        """左开右闭 (min, max]"""
        try:
            value = float(left)
            min_val = float(right["min"])
            max_val = float(right["max"])
            return min_val < value <= max_val
        except (ValueError, TypeError, KeyError):
            return False
    
    def _calculate_between_right_open(self, left: Any, right: Dict[str, Any]) -> bool:
        """左闭右开 [min, max)"""
        try:
            value = float(left)
            min_val = float(right["min"])
            max_val = float(right["max"])
            return min_val <= value < max_val
        except (ValueError, TypeError, KeyError):
            return False
    
    # 包含操作符计算函数
    def _calculate_in(self, left: Any, right: List[Any]) -> bool:
        """包含"""
        try:
            return left in right
        except TypeError:
            return False
    
    def _calculate_not_in(self, left: Any, right: List[Any]) -> bool:
        """不包含"""
        return not self._calculate_in(left, right)
    
    # 字符串操作符计算函数
    def _calculate_contains(self, left: Any, right: Any) -> bool:
        """字符串包含"""
        try:
            return str(right) in str(left)
        except TypeError:
            return False
    
    def _calculate_starts_with(self, left: Any, right: Any) -> bool:
        """以...开始"""
        try:
            return str(left).startswith(str(right))
        except (TypeError, AttributeError):
            return False
    
    def _calculate_ends_with(self, left: Any, right: Any) -> bool:
        """以...结束"""
        try:
            return str(left).endswith(str(right))
        except (TypeError, AttributeError):
            return False
    
    def _calculate_regex(self, left: Any, right: Any) -> bool:
        """正则表达式匹配"""
        try:
            import re
            return bool(re.search(str(right), str(left)))
        except (TypeError, re.error):
            return False
    
    # 空值操作符计算函数
    def _calculate_is_null(self, left: Any, right: Any) -> bool:
        """为空"""
        return left is None or (isinstance(left, float) and np.isnan(left))
    
    def _calculate_is_not_null(self, left: Any, right: Any) -> bool:
        """不为空"""
        return not self._calculate_is_null(left, right)
    
    # 数值操作符计算函数
    def _calculate_near(self, left: Any, right: Dict[str, Any]) -> bool:
        """接近"""
        try:
            value = float(left)
            target = float(right["value"])
            tolerance = float(right["tolerance"])
            return abs(value - target) <= tolerance
        except (ValueError, TypeError, KeyError):
            return False
    
    def _calculate_percent_change(self, left: Any, right: Dict[str, Any]) -> bool:
        """百分比变化"""
        try:
            current_value = float(left)
            base_value = float(right["base_value"])
            expected_percent = float(right["percent"])
            
            if base_value == 0:
                return False
            
            actual_percent = ((current_value - base_value) / base_value) * 100
            return abs(actual_percent - expected_percent) < 0.01  # 0.01%的误差
        except (ValueError, TypeError, KeyError, ZeroDivisionError):
            return False
    
    # 逻辑操作符计算函数
    def _calculate_and(self, conditions: List[bool]) -> bool:
        """与操作"""
        return all(conditions)
    
    def _calculate_or(self, conditions: List[bool]) -> bool:
        """或操作"""
        return any(conditions)
    
    def _calculate_not(self, conditions: List[bool]) -> bool:
        """非操作"""
        if len(conditions) != 1:
            return False
        return not conditions[0]
    
    def _calculate_xor(self, conditions: List[bool]) -> bool:
        """异或操作"""
        true_count = sum(conditions)
        return true_count == 1
    
    def get_operator_description(self, operator: str, value: Any) -> str:
        """获取操作符的描述"""
        try:
            if operator not in self.operators:
                return f"未知操作符: {operator}"
            
            operator_info = self.operators[operator]
            name = operator_info["name"]
            
            if operator_info["value_type"] == "none":
                return name
            elif operator_info["value_type"] == "single":
                return f"{name} {value}"
            elif operator_info["value_type"] == "range":
                if isinstance(value, dict) and "min" in value and "max" in value:
                    return f"{name} [{value['min']}, {value['max']}]"
                return f"{name} {value}"
            elif operator_info["value_type"] == "list":
                if isinstance(value, list):
                    return f"{name} {value}"
                return f"{name} {value}"
            elif operator_info["value_type"] == "tolerance":
                if isinstance(value, dict) and "value" in value and "tolerance" in value:
                    return f"{name} {value['value']} ±{value['tolerance']}"
                return f"{name} {value}"
            elif operator_info["value_type"] == "percent":
                if isinstance(value, dict) and "base_value" in value and "percent" in value:
                    return f"{name} {value['percent']}% (基准: {value['base_value']})"
                return f"{name} {value}"
            else:
                return f"{name} {value}"
                
        except Exception as e:
            logger.error(f"获取操作符描述失败: {e}")
            return f"{operator} {value}"