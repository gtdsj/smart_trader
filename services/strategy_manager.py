# -*- coding: utf-8 -*-
"""
策略管理服务模块
提供策略的创建、更新、删除、查询和执行功能
"""
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
    
    def __init__(self):
        self.settings = get_settings()
        self.cache_client = get_cache_client()
        self.data_service = None  # 延迟初始化
        
        # 内置技术指标列表
        self.technical_indicators = {
            "ma": "移动平均线",
            "ema": "指数移动平均线",
            "rsi": "相对强弱指数",
            "macd": "MACD指标",
            "kdj": "KDJ指标",
            "bollinger": "布林带",
            "volume": "成交量",
            "turnover_rate": "换手率",
            "price_change": "价格变化",
            "price_change_pct": "价格变化百分比"
        }
        
        # 基本面指标列表
        self.fundamental_indicators = {
            "pe_ratio": "市盈率",
            "pb_ratio": "市净率",
            "market_cap": "市值",
            "revenue_growth": "营收增长率",
            "profit_growth": "利润增长率",
            "roe": "净资产收益率",
            "debt_ratio": "负债率"
        }
    
    def set_data_service(self, data_service: DataService):
        """设置数据服务"""
        self.data_service = data_service
    
    async def create_strategy(self, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建策略"""
        try:
            async for db in get_db():
                # 验证策略数据
                validation_result = await self._validate_strategy_data(strategy_data)
                if not validation_result["valid"]:
                    return {
                        "success": False,
                        "message": f"策略数据验证失败: {validation_result['message']}",
                        "data": None
                    }
                
                # 创建策略记录
                strategy_record = {
                    "name": strategy_data["name"],
                    "description": strategy_data.get("description", ""),
                    "strategy_type": strategy_data["strategy_type"],
                    "category": strategy_data["category"],
                    "parameters": strategy_data.get("parameters", {}),
                    "conditions": strategy_data.get("conditions", {}),
                    "priority": strategy_data.get("priority", 0),
                    "created_by": strategy_data.get("created_by", "system"),
                    "version": strategy_data.get("version", "1.0"),
                    "is_active": False
                }
                
                stmt = insert(Strategy).values(**strategy_record)
                result = await db.execute(stmt)
                strategy_id = result.inserted_primary_key[0]
                
                # 创建策略条件
                conditions = strategy_data.get("conditions", [])
                if conditions:
                    await self._create_strategy_conditions(db, strategy_id, conditions)
                
                await db.commit()
                
                logger.info(f"创建策略成功: {strategy_data['name']} (ID: {strategy_id})")
                return {
                    "success": True,
                    "message": "策略创建成功",
                    "data": {"strategy_id": strategy_id}
                }
                
        except Exception as e:
            logger.error(f"创建策略失败: {e}, {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"创建策略失败: {str(e)}",
                "data": None
            }
    
    async def _create_strategy_conditions(self, db: AsyncSession, strategy_id: int, 
                                        conditions: List[Dict[str, Any]]):
        """创建策略条件"""
        for i, condition in enumerate(conditions):
            condition_record = {
                "strategy_id": strategy_id,
                "condition_type": condition["condition_type"],
                "indicator": condition["indicator"],
                "operator": condition["operator"],
                "value": condition["value"],
                "logic_operator": condition.get("logic_operator", "AND"),
                "order_index": i,
                "is_active": condition.get("is_active", True)
            }
            
            stmt = insert(StrategyCondition).values(**condition_record)
            await db.execute(stmt)
    
    async def _validate_strategy_data(self, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
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
                    validation_result = await self._validate_condition(condition)
                    if not validation_result["valid"]:
                        return validation_result
            
            return {"valid": True, "message": "验证通过"}
            
        except Exception as e:
            return {
                "valid": False,
                "message": f"验证过程出错: {str(e)}"
            }
    
    async def _validate_condition(self, condition: Dict[str, Any]) -> Dict[str, Any]:
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
            
            if condition_type == "technical":
                if indicator not in self.technical_indicators:
                    return {
                        "valid": False,
                        "message": f"未知的技术指标: {indicator}"
                    }
            elif condition_type == "fundamental":
                if indicator not in self.fundamental_indicators:
                    return {
                        "valid": False,
                        "message": f"未知的基本面指标: {indicator}"
                    }
            
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
            async for db in get_db():
                query = select(Strategy).options(
                    selectinload(Strategy.strategy_conditions)
                ).order_by(desc(Strategy.created_at))
                
                if category:
                    query = query.where(Strategy.category == category)
                
                if active_only:
                    query = query.where(Strategy.is_active == True)
                
                result = await db.execute(query)
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
                
        except Exception as e:
            logger.error(f"获取策略列表失败: {e}, {traceback.format_exc()}")
            return []
    
    async def get_strategy_detail(self, strategy_id: int) -> Optional[Dict[str, Any]]:
        """获取策略详情"""
        try:
            async for db in get_db():
                query = select(Strategy).options(
                    selectinload(Strategy.strategy_conditions)
                ).where(Strategy.id == strategy_id)
                
                result = await db.execute(query)
                strategy = result.scalar_one_or_none()
                
                if not strategy:
                    return None
                
                # 获取条件详情
                conditions = []
                for condition in strategy.strategy_conditions:
                    conditions.append({
                        "id": condition.id,
                        "condition_type": condition.condition_type,
                        "indicator": condition.indicator,
                        "operator": condition.operator,
                        "value": condition.value,
                        "logic_operator": condition.logic_operator,
                        "order_index": condition.order_index,
                        "is_active": condition.is_active
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
                
        except Exception as e:
            logger.error(f"获取策略详情失败: {e}, {traceback.format_exc()}")
            return None
    
    async def update_strategy(self, strategy_id: int, 
                            update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新策略"""
        try:
            async for db in get_db():
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
                    
                    await db.execute(stmt)
                
                # 更新条件
                if "conditions" in update_data:
                    # 删除旧条件
                    await db.execute(
                        delete(StrategyCondition).where(
                            StrategyCondition.strategy_id == strategy_id
                        )
                    )
                    
                    # 创建新条件
                    conditions = update_data["conditions"]
                    if conditions:
                        await self._create_strategy_conditions(db, strategy_id, conditions)
                
                await db.commit()
                
                logger.info(f"更新策略成功: {strategy_id}")
                return {
                    "success": True,
                    "message": "策略更新成功",
                    "data": {"strategy_id": strategy_id}
                }
                
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
            async for db in get_db():
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
                await db.execute(
                    delete(StrategyCondition).where(
                        StrategyCondition.strategy_id == strategy_id
                    )
                )
                
                await db.execute(
                    delete(StrategySignal).where(
                        StrategySignal.strategy_id == strategy_id
                    )
                )
                
                await db.execute(
                    delete(StrategyExecution).where(
                        StrategyExecution.strategy_id == strategy_id
                    )
                )
                
                await db.execute(
                    delete(Strategy).where(Strategy.id == strategy_id)
                )
                
                await db.commit()
                
                logger.info(f"删除策略成功: {strategy_id}")
                return {
                    "success": True,
                    "message": "策略删除成功",
                    "data": None
                }
                
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
            async for db in get_db():
                stmt = update(Strategy).where(
                    Strategy.id == strategy_id
                ).values(
                    is_active=True,
                    updated_at=datetime.now()
                )
                
                result = await db.execute(stmt)
                if result.rowcount == 0:
                    return {
                        "success": False,
                        "message": "策略不存在",
                        "data": None
                    }
                
                await db.commit()
                
                logger.info(f"激活策略: {strategy_id}")
                return {
                    "success": True,
                    "message": "策略激活成功",
                    "data": None
                }
                
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
            async for db in get_db():
                stmt = update(Strategy).where(
                    Strategy.id == strategy_id
                ).values(
                    is_active=False,
                    updated_at=datetime.now()
                )
                
                result = await db.execute(stmt)
                if result.rowcount == 0:
                    return {
                        "success": False,
                        "message": "策略不存在",
                        "data": None
                    }
                
                await db.commit()
                
                logger.info(f"停用策略: {strategy_id}")
                return {
                    "success": True,
                    "message": "策略停用成功",
                    "data": None
                }
                
        except Exception as e:
            logger.error(f"停用策略失败: {e}, {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"停用策略失败: {str(e)}",
                "data": None
            }
    
    async def get_available_indicators(self) -> Dict[str, Any]:
        """获取可用指标列表"""
        return {
            "technical": self.technical_indicators,
            "fundamental": self.fundamental_indicators
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