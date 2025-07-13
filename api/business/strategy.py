# -*- coding: utf-8 -*-
"""
策略业务API
提供量化策略管理和执行功能
"""
import traceback
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any

from config import get_settings
from utils.log_config import get_logger
from services.strategy_service import StrategyService, StrategyType, SignalType
from api.dependencies import get_strategy_service

# 获取logger实例
logger = get_logger(__name__)

# 创建策略业务路由器
router = APIRouter(prefix="/strategy", tags=["策略业务"])

# 获取配置
settings = get_settings()

# 响应模型类
class ApiResponse(BaseModel):
    """API响应基类"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Any = Field(None, description="响应数据")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="时间戳")

class StrategyInfo(BaseModel):
    """策略信息"""
    id: int = Field(..., description="策略ID")
    name: str = Field(..., description="策略名称")
    description: str = Field(..., description="策略描述")
    strategy_type: str = Field(..., description="策略类型")
    parameters: Dict[str, Any] = Field(..., description="策略参数")
    is_active: bool = Field(..., description="是否激活")
    created_at: Optional[str] = Field(None, description="创建时间")

class SignalInfo(BaseModel):
    """信号信息"""
    stock_code: str = Field(..., description="股票代码")
    signal: str = Field(..., description="信号类型")
    strategy: str = Field(..., description="策略名称")
    reason: str = Field(..., description="信号原因")
    strength: float = Field(..., description="信号强度")
    price: float = Field(..., description="价格")
    timestamp: str = Field(..., description="时间戳")

# 请求模型
class CreateStrategyRequest(BaseModel):
    """创建策略请求"""
    name: str = Field(..., description="策略名称")
    description: str = Field(..., description="策略描述")
    strategy_type: str = Field(..., description="策略类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="策略参数")

class RunStrategyRequest(BaseModel):
    """运行策略请求"""
    strategy_name: str = Field(..., description="策略名称")
    stock_codes: Optional[List[str]] = Field(None, description="股票代码列表")

class StrategyParametersRequest(BaseModel):
    """策略参数请求"""
    parameters: Dict[str, Any] = Field(..., description="策略参数")

# 保留原有的请求模型以保持向后兼容
class StrategyCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    strategy_type: str  # trend, mean_reversion, arbitrage, grid, etc.
    parameters: Dict[str, Any]
    stock_pool: List[str]
    risk_control: Optional[Dict[str, Any]] = None
    schedule: Optional[Dict[str, Any]] = None

class StrategyUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    stock_pool: Optional[List[str]] = None
    risk_control: Optional[Dict[str, Any]] = None
    schedule: Optional[Dict[str, Any]] = None
    status: Optional[str] = None  # active, inactive, paused

class StrategyExecuteRequest(BaseModel):
    strategy_id: str
    execution_mode: Optional[str] = "auto"  # auto, manual, simulation
    force_execute: Optional[bool] = False

@router.get("/", response_model=ApiResponse, summary="策略概览", description="获取策略系统概览信息")
async def get_strategy_overview(service: StrategyService = Depends(get_strategy_service)):
    """获取策略概览"""
    try:
        # 获取真实的策略统计信息
        all_strategies = await service.get_strategies()
        active_strategies = await service.get_strategies(active_only=True)
        
        overview = {
            "strategy_engine": {
                "status": "running",
                "version": "1.0.0",
                "last_update": datetime.now().isoformat()
            },
            "statistics": {
                "total_strategies": len(all_strategies),
                "active_strategies": len(active_strategies),
                "inactive_strategies": len(all_strategies) - len(active_strategies),
                "available_strategy_types": len(service.strategies)
            },
            "available_strategies": list(service.strategies.keys()),
            "strategy_types": [strategy_type.value for strategy_type in StrategyType]
        }
        
        return ApiResponse(
            success=True,
            message="获取策略概览成功",
            data=overview
        )
        
    except Exception as e:
        logger.error(f"获取策略概览失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list", response_model=ApiResponse, summary="策略列表", description="获取策略列表")
async def get_strategy_list(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    active_only: bool = Query(False, description="仅显示激活的策略"),
    service: StrategyService = Depends(get_strategy_service)
):
    """获取策略列表"""
    try:
        # 获取真实的策略数据
        strategies = await service.get_strategies(active_only=active_only)
        
        # StrategyService已经返回字典格式，直接使用
        strategy_list = strategies
        
        # 分页
        total = len(strategy_list)
        start = (page - 1) * size
        end = start + size
        page_strategies = strategy_list[start:end]
        
        result = {
            "strategies": page_strategies,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size
            }
        }
        
        return ApiResponse(
            success=True,
            message="获取策略列表成功",
            data=result
        )
        
    except Exception as e:
        logger.error(f"获取策略列表失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create", response_model=ApiResponse, summary="创建策略", description="创建新的量化策略")
async def create_strategy(
    request: CreateStrategyRequest,
    service: StrategyService = Depends(get_strategy_service)
):
    """创建策略"""
    try:
        # 使用真实的策略服务创建策略
        result = await service.create_strategy(
            name=request.name,
            description=request.description,
            strategy_type=request.strategy_type,
            parameters=request.parameters
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="策略创建失败")
        
        # 创建成功后获取策略信息
        strategies = await service.get_strategies()
        strategy_info = strategies[-1] if strategies else None  # 获取最新创建的策略
        
        if not strategy_info:
            raise HTTPException(status_code=500, detail="无法获取创建的策略信息")
        
        return ApiResponse(
            success=True,
            message="策略创建成功",
            data=strategy_info
        )
        
    except Exception as e:
        logger.error(f"创建策略失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/types", response_model=ApiResponse, summary="策略类型", description="获取所有可用的策略类型")
async def get_strategy_types(service: StrategyService = Depends(get_strategy_service)):
    """获取策略类型"""
    try:
        strategy_types = [{
            "type": strategy_type.value,
            "name": strategy_type.value,
            "description": f"{strategy_type.value}策略"
        } for strategy_type in StrategyType]
        
        return ApiResponse(
            success=True,
            message="获取策略类型成功",
            data=strategy_types
        )
    except Exception as e:
        logger.error(f"获取策略类型失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available", response_model=ApiResponse, summary="可用策略", description="获取所有可用的策略实现")
async def get_available_strategies(service: StrategyService = Depends(get_strategy_service)):
    """获取可用策略"""
    try:
        available_strategies = [{
            "name": name,
            "description": f"{name}策略实现"
        } for name in service.strategies.keys()]
        
        return ApiResponse(
            success=True,
            message="获取可用策略成功",
            data=available_strategies
        )
    except Exception as e:
        logger.error(f"获取可用策略失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{strategy_id}", response_model=ApiResponse, summary="策略详情", description="获取指定策略的详细信息")
async def get_strategy_detail(
    strategy_id: int,
    service: StrategyService = Depends(get_strategy_service)
):
    """获取策略详情"""
    try:
        # 获取真实的策略详情
        strategies = await service.get_strategies()
        strategy = next((s for s in strategies if s["id"] == strategy_id), None)
        
        if not strategy:
            raise HTTPException(status_code=404, detail="策略不存在")
        
        # StrategyService已经返回字典格式，直接使用
        strategy_detail = strategy
        
        return ApiResponse(
            success=True,
            message="获取策略详情成功",
            data=strategy_detail
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略详情失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{strategy_id}/activate", response_model=ApiResponse, summary="激活策略", description="激活指定策略")
async def activate_strategy(
    strategy_id: int,
    service: StrategyService = Depends(get_strategy_service)
):
    """激活策略"""
    try:
        await service.activate_strategy(strategy_id)
        return ApiResponse(
            success=True,
            message="策略激活成功",
            data={"strategy_id": strategy_id, "is_active": True}
        )
    except Exception as e:
        logger.error(f"激活策略失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{strategy_id}/deactivate", response_model=ApiResponse, summary="停用策略", description="停用指定策略")
async def deactivate_strategy(
    strategy_id: int,
    service: StrategyService = Depends(get_strategy_service)
):
    """停用策略"""
    try:
        await service.deactivate_strategy(strategy_id)
        return ApiResponse(
            success=True,
            message="策略停用成功",
            data={"strategy_id": strategy_id, "is_active": False}
        )
    except Exception as e:
        logger.error(f"停用策略失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scan", response_model=ApiResponse, summary="运行策略扫描", description="运行策略扫描以生成交易信号")
async def run_strategy_scan(
    request: RunStrategyRequest,
    background_tasks: BackgroundTasks,
    service: StrategyService = Depends(get_strategy_service)
):
    """运行策略扫描"""
    try:
        # 在后台运行策略扫描
        background_tasks.add_task(
            service.run_strategy_scan,
            request.strategy_name,
            request.stock_codes
        )
        
        return ApiResponse(
            success=True,
            message="策略扫描已启动",
            data={"strategy_name": request.strategy_name, "status": "running"}
        )
    except Exception as e:
        logger.error(f"运行策略扫描失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run-all", response_model=ApiResponse, summary="运行所有激活策略", description="运行所有激活的策略")
async def run_all_active_strategies(
    background_tasks: BackgroundTasks,
    service: StrategyService = Depends(get_strategy_service)
):
    """运行所有激活策略"""
    try:
        # 在后台运行所有激活策略
        background_tasks.add_task(service.run_all_active_strategies)
        
        return ApiResponse(
            success=True,
            message="所有激活策略已启动",
            data={"status": "running"}
        )
    except Exception as e:
        logger.error(f"运行所有激活策略失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signals/latest", response_model=ApiResponse, summary="获取最新信号", description="获取最新的交易信号")
async def get_latest_signals(
    limit: int = Query(10, ge=1, le=100, description="返回信号数量"),
    signal_type: Optional[str] = Query(None, description="信号类型过滤"),
    service: StrategyService = Depends(get_strategy_service)
):
    """获取最新信号"""
    try:
        # 这里应该从数据库获取最新信号
        # 暂时返回模拟数据
        signals = [
            {
                "stock_code": "000001.SZ",
                "signal": "BUY",
                "strategy": "ma_cross",
                "reason": "均线金叉",
                "strength": 0.85,
                "price": 12.45,
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        return ApiResponse(
            success=True,
            message="获取最新信号成功",
            data=signals[:limit]
        )
    except Exception as e:
        logger.error(f"获取最新信号失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{strategy_id}/signals", response_model=ApiResponse, summary="获取策略信号", description="获取指定策略的交易信号")
async def get_strategy_signals(
    strategy_id: int,
    limit: int = Query(10, ge=1, le=100, description="返回信号数量"),
    service: StrategyService = Depends(get_strategy_service)
):
    """获取策略信号"""
    try:
        # 这里应该从数据库获取策略信号
        # 暂时返回模拟数据
        signals = [
            {
                "stock_code": "000001.SZ",
                "signal": "BUY",
                "reason": "策略信号",
                "strength": 0.75,
                "price": 12.45,
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        return ApiResponse(
            success=True,
            message="获取策略信号成功",
            data=signals[:limit]
        )
    except Exception as e:
        logger.error(f"获取策略信号失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# 旧的接口已被移除，使用新的真实策略服务接口