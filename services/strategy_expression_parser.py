# -*- coding: utf-8 -*-
"""
策略表达式解析器
支持复杂的策略表达式解析和执行，包括多个条件的逻辑组合
"""

import traceback
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import json
import re
from dataclasses import dataclass
from loguru import logger
import pandas as pd

from services.indicator_manager import IndicatorManager
from services.operator_manager import OperatorManager, LogicOperator


class ExpressionType(Enum):
    """表达式类型"""
    CONDITION = "condition"  # 单个条件
    LOGIC = "logic"  # 逻辑表达式
    GROUP = "group"  # 分组表达式


@dataclass
class ConditionExpression:
    """条件表达式"""
    indicator: str  # 指标名称
    operator: str  # 操作符
    value: Any  # 比较值
    condition_type: str = "technical"  # 条件类型：technical, fundamental, custom
    parameters: Dict[str, Any] = None  # 指标参数


@dataclass
class LogicExpression:
    """逻辑表达式"""
    operator: str  # 逻辑操作符：AND, OR, NOT, XOR
    operands: List[Union['LogicExpression', ConditionExpression, 'GroupExpression']]  # 操作数


@dataclass
class GroupExpression:
    """分组表达式"""
    expression: Union[LogicExpression, ConditionExpression]  # 分组内的表达式


class StrategyExpressionParser:
    """策略表达式解析器"""
    
    def __init__(self):
        self.indicator_manager = IndicatorManager()
        self.operator_manager = OperatorManager()
        
        # 逻辑操作符优先级（数字越大优先级越高）
        self.logic_precedence = {
            'OR': 1,
            'XOR': 1,
            'AND': 2,
            'NOT': 3
        }
    
    def parse_expression_string(self, expression_str: str) -> Union[LogicExpression, ConditionExpression, GroupExpression]:
        """解析表达式字符串
        
        支持的表达式格式：
        1. 单个条件：MA(5) > 10
        2. 逻辑组合：MA(5) > 10 AND RSI < 30
        3. 分组：(MA(5) > 10 AND RSI < 30) OR (MACD > 0)
        4. 复杂嵌套：((MA(5) > 10 AND RSI < 30) OR MACD > 0) AND Volume > 1000000
        """
        try:
            # 预处理表达式字符串
            expression_str = self._preprocess_expression(expression_str)
            
            # 词法分析
            tokens = self._tokenize(expression_str)
            
            # 语法分析
            expression = self._parse_tokens(tokens)
            
            return expression
            
        except Exception as e:
            logger.error(f"解析表达式失败: {e}, {traceback.format_exc()}")
            raise ValueError(f"表达式解析失败: {str(e)}")
    
    def parse_expression_dict(self, expression_dict: Dict[str, Any]) -> Union[LogicExpression, ConditionExpression]:
        """解析表达式字典
        
        支持的字典格式：
        {
            "type": "logic",
            "operator": "AND",
            "operands": [
                {
                    "type": "condition",
                    "indicator": "MA",
                    "operator": ">",
                    "value": 10,
                    "parameters": {"period": 5}
                },
                {
                    "type": "condition",
                    "indicator": "RSI",
                    "operator": "<",
                    "value": 30
                }
            ]
        }
        """
        try:
            return self._parse_expression_dict_recursive(expression_dict)
            
        except Exception as e:
            logger.error(f"解析表达式字典失败: {e}, {traceback.format_exc()}")
            raise ValueError(f"表达式字典解析失败: {str(e)}")
    
    def evaluate_expression(self, expression: Union[LogicExpression, ConditionExpression, GroupExpression], 
                          stock_data: pd.DataFrame, symbol: str = None) -> Dict[str, Any]:
        """评估表达式"""
        try:
            # 计算所需的指标
            indicators = self._calculate_required_indicators(expression, stock_data)
            
            # 评估表达式
            result = self._evaluate_expression_recursive(expression, stock_data, indicators, symbol)
            
            return {
                "success": True,
                "result": result,
                "indicators": indicators,
                "message": "表达式评估成功"
            }
            
        except Exception as e:
            logger.error(f"评估表达式失败: {e}, {traceback.format_exc()}")
            return {
                "success": False,
                "result": False,
                "indicators": {},
                "message": f"表达式评估失败: {str(e)}"
            }
    
    def validate_expression(self, expression: Union[LogicExpression, ConditionExpression, GroupExpression]) -> Dict[str, Any]:
        """验证表达式"""
        try:
            validation_result = self._validate_expression_recursive(expression)
            
            return {
                "valid": validation_result["valid"],
                "message": validation_result["message"],
                "errors": validation_result.get("errors", [])
            }
            
        except Exception as e:
            logger.error(f"验证表达式失败: {e}, {traceback.format_exc()}")
            return {
                "valid": False,
                "message": f"表达式验证失败: {str(e)}",
                "errors": [str(e)]
            }
    
    def get_expression_description(self, expression: Union[LogicExpression, ConditionExpression, GroupExpression]) -> str:
        """获取表达式的描述"""
        try:
            return self._get_expression_description_recursive(expression)
            
        except Exception as e:
            logger.error(f"获取表达式描述失败: {e}")
            return "表达式描述获取失败"
    
    def _preprocess_expression(self, expression_str: str) -> str:
        """预处理表达式字符串"""
        # 移除多余的空格
        expression_str = re.sub(r'\s+', ' ', expression_str.strip())
        
        # 标准化逻辑操作符
        expression_str = re.sub(r'\b(and|And)\b', 'AND', expression_str)
        expression_str = re.sub(r'\b(or|Or)\b', 'OR', expression_str)
        expression_str = re.sub(r'\b(not|Not)\b', 'NOT', expression_str)
        expression_str = re.sub(r'\b(xor|Xor)\b', 'XOR', expression_str)
        
        return expression_str
    
    def _tokenize(self, expression_str: str) -> List[str]:
        """词法分析"""
        # 定义token模式
        patterns = [
            r'\(',  # 左括号
            r'\)',  # 右括号
            r'\b(AND|OR|NOT|XOR)\b',  # 逻辑操作符
            r'\b\w+\([^)]*\)',  # 函数调用（如MA(5)）
            r'\b\w+',  # 标识符
            r'[><=!]+',  # 比较操作符
            r'\d+\.\d+',  # 浮点数
            r'\d+',  # 整数
            r'"[^"]*"',  # 字符串
            r"'[^']*'",  # 字符串
            r'\[.*?\]',  # 列表
            r'\{.*?\}',  # 字典
        ]
        
        pattern = '|'.join(f'({p})' for p in patterns)
        tokens = []
        
        for match in re.finditer(pattern, expression_str):
            token = match.group().strip()
            if token:  # 忽略空token
                tokens.append(token)
        
        return tokens
    
    def _parse_tokens(self, tokens: List[str]) -> Union[LogicExpression, ConditionExpression, GroupExpression]:
        """语法分析"""
        if not tokens:
            raise ValueError("空的token列表")
        
        # 使用递归下降解析器
        self.tokens = tokens
        self.position = 0
        
        expression = self._parse_or_expression()
        
        if self.position < len(self.tokens):
            raise ValueError(f"表达式解析不完整，剩余token: {self.tokens[self.position:]}")
        
        return expression
    
    def _parse_or_expression(self):
        """解析OR表达式（最低优先级）"""
        left = self._parse_xor_expression()
        
        while self.position < len(self.tokens) and self.tokens[self.position] == 'OR':
            self.position += 1  # 跳过OR
            right = self._parse_xor_expression()
            left = LogicExpression(operator='OR', operands=[left, right])
        
        return left
    
    def _parse_xor_expression(self):
        """解析XOR表达式"""
        left = self._parse_and_expression()
        
        while self.position < len(self.tokens) and self.tokens[self.position] == 'XOR':
            self.position += 1  # 跳过XOR
            right = self._parse_and_expression()
            left = LogicExpression(operator='XOR', operands=[left, right])
        
        return left
    
    def _parse_and_expression(self):
        """解析AND表达式"""
        left = self._parse_not_expression()
        
        while self.position < len(self.tokens) and self.tokens[self.position] == 'AND':
            self.position += 1  # 跳过AND
            right = self._parse_not_expression()
            left = LogicExpression(operator='AND', operands=[left, right])
        
        return left
    
    def _parse_not_expression(self):
        """解析NOT表达式（最高优先级）"""
        if self.position < len(self.tokens) and self.tokens[self.position] == 'NOT':
            self.position += 1  # 跳过NOT
            operand = self._parse_primary_expression()
            return LogicExpression(operator='NOT', operands=[operand])
        
        return self._parse_primary_expression()
    
    def _parse_primary_expression(self):
        """解析基本表达式"""
        if self.position >= len(self.tokens):
            raise ValueError("意外的表达式结束")
        
        token = self.tokens[self.position]
        
        # 处理括号分组
        if token == '(':
            self.position += 1  # 跳过(
            expression = self._parse_or_expression()
            
            if self.position >= len(self.tokens) or self.tokens[self.position] != ')':
                raise ValueError("缺少右括号")
            
            self.position += 1  # 跳过)
            return GroupExpression(expression=expression)
        
        # 处理条件表达式
        return self._parse_condition_expression()
    
    def _parse_condition_expression(self):
        """解析条件表达式"""
        if self.position + 2 >= len(self.tokens):
            raise ValueError("条件表达式不完整")
        
        # 解析指标
        indicator_token = self.tokens[self.position]
        self.position += 1
        
        # 解析指标名称和参数
        indicator, parameters = self._parse_indicator(indicator_token)
        
        # 解析操作符
        operator = self.tokens[self.position]
        self.position += 1
        
        # 解析值
        value = self._parse_value(self.tokens[self.position])
        self.position += 1
        
        return ConditionExpression(
            indicator=indicator,
            operator=operator,
            value=value,
            parameters=parameters
        )
    
    def _parse_indicator(self, indicator_token: str) -> tuple:
        """解析指标名称和参数"""
        # 检查是否有参数（如MA(5)）
        if '(' in indicator_token and indicator_token.endswith(')'):
            indicator = indicator_token[:indicator_token.index('(')]
            params_str = indicator_token[indicator_token.index('(') + 1:-1]
            
            # 解析参数
            parameters = {}
            if params_str.strip():
                # 简单参数解析（支持数字参数）
                try:
                    if ',' in params_str:
                        # 多个参数
                        param_values = [float(p.strip()) for p in params_str.split(',')]
                        if indicator.upper() in ['MA', 'EMA']:
                            parameters['period'] = int(param_values[0])
                        elif indicator.upper() == 'MACD':
                            parameters['fast_period'] = int(param_values[0]) if len(param_values) > 0 else 12
                            parameters['slow_period'] = int(param_values[1]) if len(param_values) > 1 else 26
                            parameters['signal_period'] = int(param_values[2]) if len(param_values) > 2 else 9
                        elif indicator.upper() == 'RSI':
                            parameters['period'] = int(param_values[0])
                    else:
                        # 单个参数
                        param_value = float(params_str)
                        if indicator.upper() in ['MA', 'EMA', 'RSI']:
                            parameters['period'] = int(param_value)
                        else:
                            parameters['value'] = param_value
                except ValueError:
                    # 如果解析失败，将参数作为字符串处理
                    parameters['raw'] = params_str
            
            return indicator, parameters
        else:
            return indicator_token, {}
    
    def _parse_value(self, value_token: str) -> Any:
        """解析值"""
        # 尝试解析为数字
        try:
            if '.' in value_token:
                return float(value_token)
            else:
                return int(value_token)
        except ValueError:
            pass
        
        # 尝试解析为字符串
        if (value_token.startswith('"') and value_token.endswith('"')) or \
           (value_token.startswith("'") and value_token.endswith("'")):
            return value_token[1:-1]
        
        # 尝试解析为列表
        if value_token.startswith('[') and value_token.endswith(']'):
            try:
                return json.loads(value_token)
            except json.JSONDecodeError:
                pass
        
        # 尝试解析为字典
        if value_token.startswith('{') and value_token.endswith('}'):
            try:
                return json.loads(value_token)
            except json.JSONDecodeError:
                pass
        
        # 默认返回字符串
        return value_token
    
    def _parse_expression_dict_recursive(self, expr_dict: Dict[str, Any]) -> Union[LogicExpression, ConditionExpression]:
        """递归解析表达式字典"""
        expr_type = expr_dict.get("type")
        
        if expr_type == "condition":
            return ConditionExpression(
                indicator=expr_dict["indicator"],
                operator=expr_dict["operator"],
                value=expr_dict["value"],
                condition_type=expr_dict.get("condition_type", "technical"),
                parameters=expr_dict.get("parameters", {})
            )
        
        elif expr_type == "logic":
            operands = []
            for operand_dict in expr_dict["operands"]:
                operand = self._parse_expression_dict_recursive(operand_dict)
                operands.append(operand)
            
            return LogicExpression(
                operator=expr_dict["operator"],
                operands=operands
            )
        
        else:
            raise ValueError(f"未知的表达式类型: {expr_type}")
    
    def _calculate_required_indicators(self, expression: Union[LogicExpression, ConditionExpression, GroupExpression], 
                                     stock_data: pd.DataFrame) -> Dict[str, Any]:
        """计算表达式所需的所有指标"""
        indicators = {}
        required_indicators = self._collect_required_indicators(expression)
        
        for indicator_info in required_indicators:
            indicator = indicator_info["indicator"]
            parameters = indicator_info["parameters"]
            
            try:
                result = self.indicator_manager.calculate_indicator(indicator, stock_data, parameters)
                if result["success"]:
                    indicators[f"{indicator}_{hash(str(parameters))}"] = result["value"]
                    # 也保存不带参数hash的版本，用于简单引用
                    if not parameters:
                        indicators[indicator] = result["value"]
                else:
                    logger.warning(f"计算指标 {indicator} 失败: {result['message']}")
            except Exception as e:
                logger.error(f"计算指标 {indicator} 异常: {e}")
        
        return indicators
    
    def _collect_required_indicators(self, expression: Union[LogicExpression, ConditionExpression, GroupExpression]) -> List[Dict[str, Any]]:
        """收集表达式所需的所有指标"""
        indicators = []
        
        if isinstance(expression, ConditionExpression):
            indicators.append({
                "indicator": expression.indicator,
                "parameters": expression.parameters or {}
            })
        
        elif isinstance(expression, LogicExpression):
            for operand in expression.operands:
                indicators.extend(self._collect_required_indicators(operand))
        
        elif isinstance(expression, GroupExpression):
            indicators.extend(self._collect_required_indicators(expression.expression))
        
        return indicators
    
    def _evaluate_expression_recursive(self, expression: Union[LogicExpression, ConditionExpression, GroupExpression], 
                                     stock_data: pd.DataFrame, indicators: Dict[str, Any], symbol: str = None) -> bool:
        """递归评估表达式"""
        if isinstance(expression, ConditionExpression):
            return self._evaluate_condition(expression, stock_data, indicators, symbol)
        
        elif isinstance(expression, LogicExpression):
            operand_results = []
            for operand in expression.operands:
                result = self._evaluate_expression_recursive(operand, stock_data, indicators, symbol)
                operand_results.append(result)
            
            return self.operator_manager.evaluate_logic_condition(operand_results, expression.operator)
        
        elif isinstance(expression, GroupExpression):
            return self._evaluate_expression_recursive(expression.expression, stock_data, indicators, symbol)
        
        else:
            raise ValueError(f"未知的表达式类型: {type(expression)}")
    
    def _evaluate_condition(self, condition: ConditionExpression, stock_data: pd.DataFrame, 
                          indicators: Dict[str, Any], symbol: str = None) -> bool:
        """评估单个条件"""
        try:
            # 获取指标值
            indicator_key = f"{condition.indicator}_{hash(str(condition.parameters))}"
            if indicator_key in indicators:
                indicator_value = indicators[indicator_key]
            elif condition.indicator in indicators:
                indicator_value = indicators[condition.indicator]
            else:
                logger.warning(f"指标 {condition.indicator} 未找到")
                return False
            
            # 如果指标值是Series，取最后一个值
            if hasattr(indicator_value, 'iloc'):
                indicator_value = indicator_value.iloc[-1]
            
            # 评估条件
            return self.operator_manager.evaluate_condition(indicator_value, condition.operator, condition.value)
            
        except Exception as e:
            logger.error(f"评估条件失败: {e}")
            return False
    
    def _validate_expression_recursive(self, expression: Union[LogicExpression, ConditionExpression, GroupExpression]) -> Dict[str, Any]:
        """递归验证表达式"""
        errors = []
        
        if isinstance(expression, ConditionExpression):
            # 验证指标
            indicator_validation = self.indicator_manager.validate_indicator(expression.indicator, expression.condition_type)
            if not indicator_validation["valid"]:
                errors.append(f"指标验证失败: {indicator_validation['message']}")
            
            # 验证操作符
            operator_validation = self.operator_manager.validate_operator_value(expression.operator, expression.value)
            if not operator_validation["valid"]:
                errors.append(f"操作符验证失败: {operator_validation['message']}")
        
        elif isinstance(expression, LogicExpression):
            # 验证逻辑操作符
            if expression.operator not in [e.value for e in LogicOperator]:
                errors.append(f"未知的逻辑操作符: {expression.operator}")
            
            # 验证操作数
            if not expression.operands:
                errors.append("逻辑表达式缺少操作数")
            
            for operand in expression.operands:
                operand_validation = self._validate_expression_recursive(operand)
                if not operand_validation["valid"]:
                    errors.extend(operand_validation["errors"])
        
        elif isinstance(expression, GroupExpression):
            group_validation = self._validate_expression_recursive(expression.expression)
            if not group_validation["valid"]:
                errors.extend(group_validation["errors"])
        
        return {
            "valid": len(errors) == 0,
            "message": "表达式验证通过" if len(errors) == 0 else f"表达式验证失败: {'; '.join(errors)}",
            "errors": errors
        }
    
    def _get_expression_description_recursive(self, expression: Union[LogicExpression, ConditionExpression, GroupExpression]) -> str:
        """递归获取表达式描述"""
        if isinstance(expression, ConditionExpression):
            indicator_desc = expression.indicator
            if expression.parameters:
                params_str = ', '.join([f"{k}={v}" for k, v in expression.parameters.items()])
                indicator_desc += f"({params_str})"
            
            operator_desc = self.operator_manager.get_operator_description(expression.operator, expression.value)
            return f"{indicator_desc} {operator_desc}"
        
        elif isinstance(expression, LogicExpression):
            operand_descriptions = []
            for operand in expression.operands:
                desc = self._get_expression_description_recursive(operand)
                operand_descriptions.append(desc)
            
            if expression.operator == "NOT":
                return f"NOT ({operand_descriptions[0]})"
            else:
                return f" {expression.operator} ".join(operand_descriptions)
        
        elif isinstance(expression, GroupExpression):
            inner_desc = self._get_expression_description_recursive(expression.expression)
            return f"({inner_desc})"
        
        else:
            return "未知表达式"