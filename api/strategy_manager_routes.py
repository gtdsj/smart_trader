# -*- coding: utf-8 -*-
"""
策略管理API路由
提供策略的创建、查询、更新、删除等接口
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field, validator
from loguru import logger

from services.strategy_manager import (
    StrategyManager, StrategyCategory, ConditionType, 
    OperatorType, LogicOperator
)
from services.strategy_executor import StrategyExecutor

# 创建路由器
router = APIRouter(prefix="/api/v1/strategy-manager", tags=["策略管理"])

# 全局服务实例
_strategy_manager: StrategyManager = None
_strategy_executor: StrategyExecutor = None

def set_strategy_manager(manager: StrategyManager):
    """设置策略管理器实例"""
    global _strategy_manager
    _strategy_manager = manager

def get_strategy_manager() -> StrategyManager:
    """获取策略管理器实例"""
    if _strategy_manager is None:
        raise HTTPException(status_code=500, detail="策略管理器未初始化")
    return _strategy_manager

def set_strategy_executor(executor: StrategyExecutor):
    """设置策略执行器实例"""
    global _strategy_executor
    _strategy_executor = executor

def get_strategy_executor() -> StrategyExecutor:
    """获取策略执行器实例"""
    if _strategy_executor is None:
        raise HTTPException(status_code=500, detail="策略执行器未初始化")
    return _strategy_executor


# 请求模型
class StrategyConditionRequest(BaseModel):
    """策略条件请求模型"""
    condition_type: str = Field(..., description="条件类型(technical/fundamental/custom)")
    indicator: str = Field(..., description="指标名称")
    operator: str = Field(..., description="操作符")
    value: Any = Field(..., description="条件值")
    logic_operator: str = Field("AND", description="逻辑操作符(AND/OR)")
    is_active: bool = Field(True, description="是否启用")
    
    @validator('condition_type')
    def validate_condition_type(cls, v):
        valid_types = [ct.value for ct in ConditionType]
        if v not in valid_types:
            raise ValueError(f"无效的条件类型: {v}")
        return v
    
    @validator('operator')
    def validate_operator(cls, v):
        valid_operators = [op.value for op in OperatorType]
        if v not in valid_operators:
            raise ValueError(f"无效的操作符: {v}")
        return v
    
    @validator('logic_operator')
    def validate_logic_operator(cls, v):
        valid_operators = [lo.value for lo in LogicOperator]
        if v not in valid_operators:
            raise ValueError(f"无效的逻辑操作符: {v}")
        return v


class CreateStrategyRequest(BaseModel):
    """创建策略请求模型"""
    name: str = Field(..., description="策略名称", min_length=1, max_length=100)
    description: str = Field("", description="策略描述", max_length=1000)
    strategy_type: str = Field(..., description="策略类型")
    category: str = Field(..., description="策略分类")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="策略参数")
    conditions: List[StrategyConditionRequest] = Field(default_factory=list, description="策略条件")
    priority: int = Field(0, description="优先级", ge=0, le=100)
    created_by: str = Field("system", description="创建者")
    version: str = Field("1.0", description="版本号")
    
    @validator('category')
    def validate_category(cls, v):
        valid_categories = [cat.value for cat in StrategyCategory]
        if v not in valid_categories:
            raise ValueError(f"无效的策略分类: {v}")
        return v


class UpdateStrategyRequest(BaseModel):
    """更新策略请求模型"""
    name: Optional[str] = Field(None, description="策略名称", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="策略描述", max_length=1000)
    strategy_type: Optional[str] = Field(None, description="策略类型")
    category: Optional[str] = Field(None, description="策略分类")
    parameters: Optional[Dict[str, Any]] = Field(None, description="策略参数")
    conditions: Optional[List[StrategyConditionRequest]] = Field(None, description="策略条件")
    priority: Optional[int] = Field(None, description="优先级", ge=0, le=100)
    version: Optional[str] = Field(None, description="版本号")
    
    @validator('category')
    def validate_category(cls, v):
        if v is not None:
            valid_categories = [cat.value for cat in StrategyCategory]
            if v not in valid_categories:
                raise ValueError(f"无效的策略分类: {v}")
        return v


class StrategyQueryRequest(BaseModel):
    """策略查询请求模型"""
    category: Optional[str] = Field(None, description="策略分类")
    active_only: bool = Field(False, description="仅查询激活的策略")
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(20, description="每页数量", ge=1, le=100)


# 响应模型
class StrategyConditionResponse(BaseModel):
    """策略条件响应模型"""
    id: Optional[int] = Field(None, description="条件ID")
    condition_type: str = Field(..., description="条件类型")
    indicator: str = Field(..., description="指标名称")
    operator: str = Field(..., description="操作符")
    value: Any = Field(..., description="条件值")
    logic_operator: str = Field(..., description="逻辑操作符")
    order_index: int = Field(..., description="条件顺序")
    is_active: bool = Field(..., description="是否启用")


class StrategyResponse(BaseModel):
    """策略响应模型"""
    id: int = Field(..., description="策略ID")
    name: str = Field(..., description="策略名称")
    description: str = Field(..., description="策略描述")
    strategy_type: str = Field(..., description="策略类型")
    category: str = Field(..., description="策略分类")
    parameters: Dict[str, Any] = Field(..., description="策略参数")
    conditions: Dict[str, Any] = Field(..., description="策略条件配置")
    is_active: bool = Field(..., description="是否激活")
    priority: int = Field(..., description="优先级")
    created_by: str = Field(..., description="创建者")
    version: str = Field(..., description="版本号")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")
    condition_count: int = Field(..., description="条件数量")


class StrategyDetailResponse(StrategyResponse):
    """策略详情响应模型"""
    condition_details: List[StrategyConditionResponse] = Field(..., description="条件详情")


class IndicatorResponse(BaseModel):
    """指标响应模型"""
    technical: Dict[str, str] = Field(..., description="技术指标")
    fundamental: Dict[str, str] = Field(..., description="基本面指标")


class StrategyTemplateResponse(BaseModel):
    """策略模板响应模型"""
    name: str = Field(..., description="模板名称")
    description: str = Field(..., description="模板描述")
    category: str = Field(..., description="策略分类")
    strategy_type: str = Field(..., description="策略类型")
    template: Dict[str, Any] = Field(..., description="模板配置")


class ExecuteStrategyRequest(BaseModel):
    """执行策略请求模型"""
    strategy_id: int
    stock_codes: Optional[List[str]] = None
    execution_type: str = "scan"


class StrategySignalResponse(BaseModel):
    """策略信号响应模型"""
    id: int
    strategy_id: int
    execution_id: int
    stock_code: str
    signal_type: str
    signal_strength: float
    trigger_price: float
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    reason: str
    confidence: float
    is_processed: bool
    created_at: str


class ExecutionHistoryResponse(BaseModel):
    """执行历史响应模型"""
    id: int
    strategy_id: int
    execution_type: str
    status: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_stocks: Optional[int] = None
    signal_count: Optional[int] = None
    success_rate: Optional[float] = None
    error_message: Optional[str] = None
    created_at: str


class ExecuteStrategyResponse(BaseModel):
    """执行策略响应模型"""
    execution_id: int
    strategy_id: int
    strategy_name: str
    total_stocks: int
    signal_count: int
    signals: List[Dict[str, Any]]
    execution_time: str


class ApiResponse(BaseModel):
    """API响应基类"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Any = Field(None, description="响应数据")


class PaginatedResponse(BaseModel):
    """分页响应模型"""
    items: List[Any] = Field(..., description="数据列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")


# API路由
@router.post("/strategies", response_model=ApiResponse, summary="创建策略")
async def create_strategy(
    request: CreateStrategyRequest,
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """创建新策略"""
    try:
        strategy_data = request.dict()
        result = await manager.create_strategy(strategy_data)
        return result
    except Exception as e:
        logger.error(f"创建策略API错误: {e}")
        raise HTTPException(status_code=500, detail=f"创建策略失败: {str(e)}")


@router.get("/strategies", response_model=ApiResponse, summary="获取策略列表")
async def get_strategies(
    category: Optional[str] = Query(None, description="策略分类"),
    active_only: bool = Query(False, description="仅查询激活的策略"),
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """获取策略列表"""
    try:
        strategies = await manager.get_strategies(category=category, active_only=active_only)
        return {
            "success": True,
            "message": "获取策略列表成功",
            "data": strategies
        }
    except Exception as e:
        logger.error(f"获取策略列表API错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略列表失败: {str(e)}")


@router.get("/strategies/{strategy_id}", response_model=ApiResponse, summary="获取策略详情")
async def get_strategy_detail(
    strategy_id: int = Path(..., description="策略ID"),
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """获取策略详情"""
    try:
        strategy = await manager.get_strategy_detail(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="策略不存在")
        
        return {
            "success": True,
            "message": "获取策略详情成功",
            "data": strategy
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略详情API错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略详情失败: {str(e)}")


@router.put("/strategies/{strategy_id}", response_model=ApiResponse, summary="更新策略")
async def update_strategy(
    strategy_id: int = Path(..., description="策略ID"),
    request: UpdateStrategyRequest = None,
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """更新策略"""
    try:
        update_data = request.dict(exclude_unset=True) if request else {}
        result = await manager.update_strategy(strategy_id, update_data)
        return result
    except Exception as e:
        logger.error(f"更新策略API错误: {e}")
        raise HTTPException(status_code=500, detail=f"更新策略失败: {str(e)}")


@router.delete("/strategies/{strategy_id}", response_model=ApiResponse, summary="删除策略")
async def delete_strategy(
    strategy_id: int = Path(..., description="策略ID"),
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """删除策略"""
    try:
        result = await manager.delete_strategy(strategy_id)
        return result
    except Exception as e:
        logger.error(f"删除策略API错误: {e}")
        raise HTTPException(status_code=500, detail=f"删除策略失败: {str(e)}")


@router.post("/strategies/{strategy_id}/activate", response_model=ApiResponse, summary="激活策略")
async def activate_strategy(
    strategy_id: int = Path(..., description="策略ID"),
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """激活策略"""
    try:
        result = await manager.activate_strategy(strategy_id)
        return result
    except Exception as e:
        logger.error(f"激活策略API错误: {e}")
        raise HTTPException(status_code=500, detail=f"激活策略失败: {str(e)}")


@router.post("/strategies/{strategy_id}/deactivate", response_model=ApiResponse, summary="停用策略")
async def deactivate_strategy(
    strategy_id: int = Path(..., description="策略ID"),
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """停用策略"""
    try:
        result = await manager.deactivate_strategy(strategy_id)
        return result
    except Exception as e:
        logger.error(f"停用策略API错误: {e}")
        raise HTTPException(status_code=500, detail=f"停用策略失败: {str(e)}")


@router.get("/indicators", response_model=ApiResponse, summary="获取可用指标列表")
async def get_available_indicators(
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """获取可用指标列表"""
    try:
        indicators = await manager.get_available_indicators()
        return {
            "success": True,
            "message": "获取指标列表成功",
            "data": indicators
        }
    except Exception as e:
        logger.error(f"获取指标列表API错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取指标列表失败: {str(e)}")


@router.get("/templates", response_model=ApiResponse, summary="获取策略模板")
async def get_strategy_templates(
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """获取策略模板"""
    try:
        templates = await manager.get_strategy_templates()
        return {
            "success": True,
            "message": "获取策略模板成功",
            "data": templates
        }
    except Exception as e:
        logger.error(f"获取策略模板API错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略模板失败: {str(e)}")


@router.get("/categories", response_model=ApiResponse, summary="获取策略分类列表")
async def get_strategy_categories():
    """获取策略分类列表"""
    try:
        categories = [
            {
                "value": cat.value,
                "label": {
                    "stock_selection": "选股策略",
                    "trading": "交易策略",
                    "risk_management": "风险管理策略"
                }[cat.value]
            }
            for cat in StrategyCategory
        ]
        
        return {
            "success": True,
            "message": "获取策略分类成功",
            "data": categories
        }
    except Exception as e:
        logger.error(f"获取策略分类API错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略分类失败: {str(e)}")


@router.get("/operators", response_model=ApiResponse, summary="获取操作符列表")
async def get_operators():
    """获取操作符列表"""
    try:
        operators = [
            {
                "value": op.value,
                "label": {
                    ">": "大于",
                    "<": "小于",
                    ">=": "大于等于",
                    "<=": "小于等于",
                    "==": "等于",
                    "!=": "不等于",
                    "between": "区间",
                    "in": "包含",
                    "not_in": "不包含"
                }[op.value]
            }
            for op in OperatorType
        ]
        
        return {
            "success": True,
            "message": "获取操作符列表成功",
            "data": operators
        }
    except Exception as e:
        logger.error(f"获取操作符列表API错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取操作符列表失败: {str(e)}")


@router.post("/execute", response_model=ApiResponse, summary="执行策略")
async def execute_strategy(request: ExecuteStrategyRequest):
    """执行策略"""
    try:
        executor = get_strategy_executor()
        result = await executor.execute_strategy(
            strategy_id=request.strategy_id,
            stock_codes=request.stock_codes,
            execution_type=request.execution_type
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "data": result["data"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals", response_model=ApiResponse, summary="获取策略信号")
async def get_strategy_signals(
    strategy_id: Optional[int] = Query(None, description="策略ID"),
    execution_id: Optional[int] = Query(None, description="执行ID"),
    stock_code: Optional[str] = Query(None, description="股票代码"),
    signal_type: Optional[str] = Query(None, description="信号类型"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    limit: int = Query(100, description="限制数量")
):
    """获取策略信号"""
    try:
        executor = get_strategy_executor()
        signals = await executor.get_strategy_signals(
            strategy_id=strategy_id,
            execution_id=execution_id,
            stock_code=stock_code,
            signal_type=signal_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return {
            "success": True,
            "message": "获取策略信号成功",
            "data": signals
        }
        
    except Exception as e:
        logger.error(f"获取策略信号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions", response_model=ApiResponse, summary="获取执行历史记录")
async def get_execution_history(
    strategy_id: Optional[int] = Query(None, description="策略ID"),
    execution_type: Optional[str] = Query(None, description="执行类型"),
    status: Optional[str] = Query(None, description="状态"),
    limit: int = Query(20, description="限制数量")
):
    """获取执行历史记录"""
    try:
        executor = get_strategy_executor()
        executions = await executor.get_execution_history(
            strategy_id=strategy_id,
            execution_type=execution_type,
            status=status,
            limit=limit
        )
        
        return {
            "success": True,
            "message": "获取执行历史记录成功",
            "data": executions
        }
        
    except Exception as e:
        logger.error(f"获取执行历史记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))