# -*- coding: utf-8 -*-
"""
策略管理服务模块
提供策略的创建、更新、删除、查询和执行功能
"""

import threading
import traceback
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import pandas as pd
import numpy as np
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, and_, desc, func
from sqlalchemy.orm import selectinload

from config import get_settings
from core.database import (
    get_db, Strategy, StrategyCondition, StrategyExecution, 
    StrategySignal, StockData
)
from core.cache_adapter import get_cache_client
from services.data_service import DataService
from services.indicator_manager import IndicatorManager
from services.operator_manager import OperatorManager
from services.strategy_expression_parser import StrategyExpressionParser


class StrategyCategory(Enum):
    """策略分类枚举"""
    STOCK_SELECTION = "stock_selection"  # 选股策略
    TRADING = "trading"  # 交易策略
    RISK_MANAGEMENT = "risk_management"  # 风险管理策略


class ConditionType(Enum):
    """条件类型枚举"""
    TECHNICAL = "technical"  # 技术指标
    FUNDAMENTAL = "fundamental"  # 基本面指标
    CUSTOM = "custom"  # 自定义条件


class OperatorType(Enum):
    """操作符类型枚举"""
    GT = ">"  # 大于
    LT = "<"  # 小于
    GTE = ">="  # 大于等于
    LTE = "<="  # 小于等于
    EQ = "=="  # 等于
    NEQ = "!="  # 不等于
    BETWEEN = "between"  # 区间
    IN = "in"  # 包含
    NOT_IN = "not_in"  # 不包含


class LogicOperator(Enum):
    """逻辑操作符枚举"""
    AND = "AND"
    OR = "OR"


class ExecutionStatus(Enum):
    """执行状态枚举"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SignalType(Enum):
    """信号类型枚举"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class StrategyManager:
    """策略管理器"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.settings = get_settings()
        self.cache_client = get_cache_client()
        self.data_service = None  # 延迟初始化
        
        # 初始化指标管理器、操作符管理器和表达式解析器
        self.indicator_manager = IndicatorManager()
        self.operator_manager = OperatorManager()
        self.expression_parser = StrategyExpressionParser()
    
    def set_data_service(self, data_service: DataService):
        """设置数据服务"""
        self.data_service = data_service
    
    def create_strategy(self, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建策略"""
        try:
            db_gen = get_db()
            db = next(db_gen)
            try:
                # 验证策略数据
                validation_result = self._validate_strategy_data(strategy_data)
                if not validation_result["valid"]:
                    return {
                        "success": False,
                        "message": f"策略数据验证失败: {validation_result['message']}",
                        "data": None
                    }
                
                # 创建策略记录
                parameters = strategy_data.get("parameters", {})
                if isinstance(parameters, dict):
                    parameters = json.dumps(parameters, ensure_ascii=False)
                
                # 注意：conditions字段在Strategy表中只是用于存储简单的条件描述
                # 实际的条件数据存储在strategy_conditions表中
                strategy_record = {
                    "name": strategy_data["name"],
                    "description": strategy_data.get("description", ""),
                    "strategy_type": strategy_data["strategy_type"],
                    "category": strategy_data["category"],
                    "parameters": parameters,
                    "conditions": "",  # 留空，实际条件存储在strategy_conditions表中
                    "priority": strategy_data.get("priority", 0),
                    "created_by": strategy_data.get("created_by", "system"),
                    "version": strategy_data.get("version", "1.0"),
                    "is_active": False
                }
                
                stmt = insert(Strategy).values(**strategy_record)
                result = db.execute(stmt)
                strategy_id = result.inserted_primary_key[0]
                
                # 创建策略条件
                conditions = strategy_data.get("conditions", [])
                if conditions:
                    self._create_strategy_conditions(db, strategy_id, conditions)
                
                db.commit()
                
                logger.info(f"创建策略成功: {strategy_data['name']} (ID: {strategy_id})")
                return {
                    "success": True,
                    "message": "策略创建成功",
                    "data": {"strategy_id": strategy_id}
                }
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"创建策略失败: {e}, {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"创建策略失败: {str(e)}",
                "data": None
            }
    
    def _create_strategy_conditions(self, db, strategy_id: int, 
                                        conditions: List[Dict[str, Any]]):
        """创建策略条件"""
        for i, condition in enumerate(conditions):
            # 将value序列化为JSON字符串存储到数据库
            value = condition["value"]
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            condition_record = {
                "strategy_id": strategy_id,
                "condition_type": condition["condition_type"],
                "indicator": condition["indicator"],
                "operator": condition["operator"],
                "value": value,
                "logic_operator": condition.get("logic_operator", "AND"),
                "order_index": i,
                "is_active": condition.get("is_active", True),
                "parameters": condition.get("parameters", "")
            }
            
            stmt = insert(StrategyCondition).values(**condition_record)
            db.execute(stmt)
    
    def _validate_strategy_data(self, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证策略数据"""
        try:
            # 必填字段检查
            required_fields = ["name", "strategy_type", "category"]
            for field in required_fields:
                if field not in strategy_data or not strategy_data[field]:
                    return {
                        "valid": False,
                        "message": f"缺少必填字段: {field}"
                    }
            
            # 策略分类验证
            valid_categories = [cat.value for cat in StrategyCategory]
            if strategy_data["category"] not in valid_categories:
                return {
                    "valid": False,
                    "message": f"无效的策略分类: {strategy_data['category']}"
                }
            
            # 条件验证
            conditions = strategy_data.get("conditions", [])
            if conditions:
                for condition in conditions:
                    validation_result = self._validate_condition(condition)
                    if not validation_result["valid"]:
                        return validation_result
            
            return {"valid": True, "message": "验证通过"}
            
        except Exception as e:
            return {
                "valid": False,
                "message": f"验证过程出错: {str(e)}"
            }
    
    def _validate_condition(self, condition: Dict[str, Any]) -> Dict[str, Any]:
        """验证单个条件"""
        try:
            # 必填字段检查
            required_fields = ["condition_type", "indicator", "operator", "value"]
            for field in required_fields:
                if field not in condition:
                    return {
                        "valid": False,
                        "message": f"条件缺少必填字段: {field}"
                    }
            
            # 条件类型验证
            valid_types = [ct.value for ct in ConditionType]
            if condition["condition_type"] not in valid_types:
                return {
                    "valid": False,
                    "message": f"无效的条件类型: {condition['condition_type']}"
                }
            
            # 操作符验证
            valid_operators = [op.value for op in OperatorType]
            if condition["operator"] not in valid_operators:
                return {
                    "valid": False,
                    "message": f"无效的操作符: {condition['operator']}"
                }
            
            # 指标验证
            condition_type = condition["condition_type"]
            indicator = condition["indicator"]
            
            if condition_type in ["technical", "fundamental"]:
                # 检查指标是否存在
                indicator_info = self.indicator_manager.get_indicator_info(indicator)
                if not indicator_info:
                    return {
                        "valid": False,
                        "message": f"未知的指标: {indicator}"
                    }
                
                # 验证指标参数
                parameters = condition.get("parameters", {})
                param_validation = self.indicator_manager.validate_indicator_parameters(indicator, parameters)
                if not param_validation["valid"]:
                    return param_validation
            
            # 验证操作符的值
            value = condition.get("value")
            operator = condition["operator"]
            
            # 添加调试信息
            logger.info(f"验证条件: {condition.get('indicator')} {operator} {value} (类型: {type(value)})")
            
            operator_validation = self.operator_manager.validate_operator_value(operator, value)
            if not operator_validation["valid"]:
                logger.error(f"操作符验证失败: {operator_validation}")
                return operator_validation
            
            return {"valid": True, "message": "条件验证通过"}
            
        except Exception as e:
            return {
                "valid": False,
                "message": f"条件验证出错: {str(e)}"
            }
    
    async def get_strategies(self, category: Optional[str] = None, 
                           active_only: bool = False) -> List[Dict[str, Any]]:
        """获取策略列表"""
        try:
            db_gen = get_db()
            db = next(db_gen)
            try:
                query = select(Strategy).options(
                    selectinload(Strategy.strategy_conditions)
                ).order_by(desc(Strategy.created_at))
                
                if category:
                    query = query.where(Strategy.category == category)
                
                if active_only:
                    query = query.where(Strategy.is_active == True)
                
                result = db.execute(query)
                strategies = result.scalars().all()
                
                strategy_list = []
                for strategy in strategies:
                    strategy_dict = {
                        "id": strategy.id,
                        "name": strategy.name,
                        "description": strategy.description,
                        "strategy_type": strategy.strategy_type,
                        "category": strategy.category,
                        "parameters": strategy.parameters,
                        "conditions": strategy.conditions,
                        "is_active": strategy.is_active,
                        "priority": strategy.priority,
                        "created_by": strategy.created_by,
                        "version": strategy.version,
                        "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
                        "condition_count": len(strategy.strategy_conditions)
                    }
                    strategy_list.append(strategy_dict)
                
                return strategy_list
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取策略列表失败: {e}, {traceback.format_exc()}")
            return []
    
    async def get_strategy_detail(self, strategy_id: int) -> Optional[Dict[str, Any]]:
        """获取策略详情"""
        try:
            db_gen = get_db()
            db = next(db_gen)
            try:
                query = select(Strategy).options(
                    selectinload(Strategy.strategy_conditions.and_(StrategyCondition.is_active == True))
                ).where( Strategy.id == strategy_id)
                
                result = db.execute(query)
                strategy = result.scalar_one_or_none()
                
                if not strategy:
                    return None
                
                # 获取条件详情
                conditions = []
                for condition in strategy.strategy_conditions:
                    try:
                        val = json.loads(condition.value)
                    except json.JSONDecodeError:
                        val = condition.value
                    conditions.append({
                        "id": condition.id,
                        "condition_type": condition.condition_type,
                        "indicator": condition.indicator,
                        "operator": condition.operator,
                        "value": val,
                        "logic_operator": condition.logic_operator,
                        "order_index": condition.order_index,
                        "is_active": condition.is_active,
                        "parameters": json.loads(condition.parameters) if condition.parameters else {}
                    })
                
                return {
                    "id": strategy.id,
                    "name": strategy.name,
                    "description": strategy.description,
                    "strategy_type": strategy.strategy_type,
                    "category": strategy.category,
                    "parameters": strategy.parameters,
                    "conditions": strategy.conditions,
                    "is_active": strategy.is_active,
                    "priority": strategy.priority,
                    "created_by": strategy.created_by,
                    "version": strategy.version,
                    "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
                    "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None,
                    "condition_details": conditions
                }
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取策略详情失败: {e}, {traceback.format_exc()}")
            return None
    
    async def update_strategy(self, strategy_id: int, 
                            update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新策略"""
        try:
            db_gen = get_db()
            db = next(db_gen)
            try:
                # 验证策略是否存在
                strategy = await self.get_strategy_detail(strategy_id)
                if not strategy:
                    return {
                        "success": False,
                        "message": "策略不存在",
                        "data": None
                    }
                
                # 更新策略基本信息
                update_fields = {}
                allowed_fields = [
                    "name", "description", "strategy_type", "category",
                    "parameters", "conditions", "priority", "version"
                ]
                
                for field in allowed_fields:
                    if field in update_data:
                        update_fields[field] = update_data[field]
                
                if update_fields:
                    update_fields["updated_at"] = datetime.now()
                    
                    stmt = update(Strategy).where(
                        Strategy.id == strategy_id
                    ).values(**update_fields)
                    
                    db.execute(stmt)
                
                # 更新条件
                if "conditions" in update_data:
                    # 删除旧条件
                    db.execute(
                        delete(StrategyCondition).where(
                            StrategyCondition.strategy_id == strategy_id
                        )
                    )
                    
                    # 创建新条件
                    conditions = update_data["conditions"]
                    if conditions:
                        await self._create_strategy_conditions(db, strategy_id, conditions)
                
                db.commit()
                
                logger.info(f"更新策略成功: {strategy_id}")
                return {
                    "success": True,
                    "message": "策略更新成功",
                    "data": {"strategy_id": strategy_id}
                }
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"更新策略失败: {e}, {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"更新策略失败: {str(e)}",
                "data": None
            }
    
    async def delete_strategy(self, strategy_id: int) -> Dict[str, Any]:
        """删除策略"""
        try:
            db_gen = get_db()
            db = next(db_gen)
            try:
                # 验证策略是否存在
                strategy = await self.get_strategy_detail(strategy_id)
                if not strategy:
                    return {
                        "success": False,
                        "message": "策略不存在",
                        "data": None
                    }
                
                # 检查策略是否正在使用
                if strategy["is_active"]:
                    return {
                        "success": False,
                        "message": "无法删除激活状态的策略，请先停用",
                        "data": None
                    }
                
                # 删除相关数据
                db.execute(
                    delete(StrategyCondition).where(
                        StrategyCondition.strategy_id == strategy_id
                    )
                )
                
                db.execute(
                    delete(StrategySignal).where(
                        StrategySignal.strategy_id == strategy_id
                    )
                )
                
                db.execute(
                    delete(StrategyExecution).where(
                        StrategyExecution.strategy_id == strategy_id
                    )
                )
                
                db.execute(
                    delete(Strategy).where(Strategy.id == strategy_id)
                )
                
                db.commit()
                
                logger.info(f"删除策略成功: {strategy_id}")
                return {
                    "success": True,
                    "message": "策略删除成功",
                    "data": None
                }
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"删除策略失败: {e}, {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"删除策略失败: {str(e)}",
                "data": None
            }
    
    async def activate_strategy(self, strategy_id: int) -> Dict[str, Any]:
        """激活策略"""
        try:
            db_gen = get_db()
            db = next(db_gen)
            try:
                stmt = update(Strategy).where(
                    Strategy.id == strategy_id
                ).values(
                    is_active=True,
                    updated_at=datetime.now()
                )
                
                result = db.execute(stmt)
                if result.rowcount == 0:
                    return {
                        "success": False,
                        "message": "策略不存在",
                        "data": None
                    }
                
                db.commit()
                
                logger.info(f"激活策略: {strategy_id}")
                return {
                    "success": True,
                    "message": "策略激活成功",
                    "data": None
                }
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"激活策略失败: {e}, {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"激活策略失败: {str(e)}",
                "data": None
            }
    
    async def deactivate_strategy(self, strategy_id: int) -> Dict[str, Any]:
        """停用策略"""
        try:
            db_gen = get_db()
            db = next(db_gen)
            try:
                stmt = update(Strategy).where(
                    Strategy.id == strategy_id
                ).values(
                    is_active=False,
                    updated_at=datetime.now()
                )
                
                result = db.execute(stmt)
                if result.rowcount == 0:
                    return {
                        "success": False,
                        "message": "策略不存在",
                        "data": None
                    }
                
                db.commit()
                
                logger.info(f"停用策略: {strategy_id}")
                return {
                    "success": True,
                    "message": "策略停用成功",
                    "data": None
                }
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"停用策略失败: {e}, {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"停用策略失败: {str(e)}",
                "data": None
            }
    
    async def get_available_indicators(self) -> Dict[str, Any]:
        """获取可用指标列表"""
        return self.indicator_manager.get_all_indicators()
    
    async def get_available_operators(self) -> Dict[str, Any]:
        """获取可用操作符列表"""
        return self.operator_manager.get_all_operators()
    
    async def parse_strategy_expression(self, expression: str) -> Dict[str, Any]:
        """解析策略表达式"""
        try:
            parsed_expression = self.expression_parser.parse_expression_string(expression)
            validation_result = self.expression_parser.validate_expression(parsed_expression)
            description = self.expression_parser.get_expression_description(parsed_expression)
            
            return {
                "success": True,
                "expression": parsed_expression,
                "validation": validation_result,
                "description": description,
                "message": "表达式解析成功"
            }
        except Exception as e:
            logger.error(f"解析策略表达式失败: {e}")
            return {
                "success": False,
                "expression": None,
                "validation": {"valid": False, "message": str(e)},
                "description": "",
                "message": f"表达式解析失败: {str(e)}"
            }
    
    async def evaluate_strategy_expression(self, expression: str, stock_data: pd.DataFrame, symbol: str = None) -> Dict[str, Any]:
        """评估策略表达式"""
        try:
            # 解析表达式
            parsed_expression = self.expression_parser.parse_expression_string(expression)
            
            # 评估表达式
            evaluation_result = self.expression_parser.evaluate_expression(parsed_expression, stock_data, symbol)
            
            return evaluation_result
        except Exception as e:
            logger.error(f"评估策略表达式失败: {e}")
            return {
                "success": False,
                "result": False,
                "indicators": {},
                "message": f"表达式评估失败: {str(e)}"
            }
    
    async def get_strategy_templates(self) -> List[Dict[str, Any]]:
        """获取策略模板"""
        templates = [
            {
                "name": "趋势选股策略",
                "description": "基于技术指标的趋势选股策略",
                "category": "stock_selection",
                "strategy_type": "technical",
                "template": {
                    "conditions": [
                        {
                            "condition_type": "technical",
                            "indicator": "ma",
                            "operator": ">",
                            "value": {"period": 20, "threshold": 0},
                            "logic_operator": "AND"
                        },
                        {
                            "condition_type": "technical",
                            "indicator": "rsi",
                            "operator": "between",
                            "value": {"min": 30, "max": 70},
                            "logic_operator": "AND"
                        }
                    ],
                    "parameters": {
                        "scan_period": "daily",
                        "min_volume": 1000000,
                        "max_results": 50
                    }
                }
            },
            {
                "name": "价值选股策略",
                "description": "基于基本面指标的价值选股策略",
                "category": "stock_selection",
                "strategy_type": "fundamental",
                "template": {
                    "conditions": [
                        {
                            "condition_type": "fundamental",
                            "indicator": "pe_ratio",
                            "operator": "<",
                            "value": 20,
                            "logic_operator": "AND"
                        },
                        {
                            "condition_type": "fundamental",
                            "indicator": "pb_ratio",
                            "operator": "<",
                            "value": 2,
                            "logic_operator": "AND"
                        }
                    ],
                    "parameters": {
                        "scan_period": "weekly",
                        "min_market_cap": 5000000000,
                        "max_results": 30
                    }
                }
            }
        ]
        
        return templates