"""统一数据补全API路由
整合优化补全、增量更新和传统补全功能
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field

from services.optimized_backfill_service import OptimizedBackfillService
from services.data_service import DataService
from api.dependencies import get_data_service, get_optimized_backfill_service
from configs.optimized_backfill_config import OptimizedBackfillConfig
from utils.logger import get_logger
from models.api_response import ApiResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/unified-backfill", tags=["统一数据补全"])

# 全局任务管理
_unified_tasks = {}
_task_counter = 0


class UnifiedBackfillRequest(BaseModel):
    """统一数据补全请求模型"""
    task_name: str = Field(..., description="任务名称")
    mode: str = Field("optimized", description="补全模式：optimized、incremental、traditional")
    market: str = Field("ALL", description="市场代码：SH、SZ或ALL")
    start_date: Optional[str] = Field(None, description="开始日期，格式YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="结束日期，格式YYYY-MM-DD")
    stock_codes: Optional[List[str]] = Field(None, description="指定股票代码列表")
    force_update: bool = Field(False, description="是否强制更新已存在的数据")
    
    # 性能相关参数
    batch_size: int = Field(100, description="批量处理大小", ge=10, le=200)
    enable_parallel: bool = Field(True, description="是否启用并行处理")
    priority: str = Field("normal", description="任务优先级：low、normal、high")
    
    # 传统模式参数
    delay_seconds: float = Field(0.1, description="批次间延迟秒数", ge=0.000001, le=5.0)
    auto_retry: bool = Field(True, description="是否自动重试失败的股票")
    max_retries: int = Field(3, description="最大重试次数", ge=1, le=5)
    
    # 监控参数
    enable_monitoring: bool = Field(True, description="是否启用性能监控")


class QuickBackfillRequest(BaseModel):
    """快速补全请求模型"""
    market: str = Field("ALL", description="市场代码")
    days: int = Field(30, description="补全最近N天数据", ge=1, le=365)
    mode: str = Field("optimized", description="补全模式")
    force_update: bool = Field(False, description="是否强制更新")


@router.get("/modes", response_model=ApiResponse, summary="获取支持的补全模式")
async def get_backfill_modes():
    """获取支持的数据补全模式及其特点"""
    try:
        modes_info = {
            "optimized": {
                "name": "优化补全",
                "description": "高性能批量插入策略，支持并行处理",
                "features": ["智能批量插入", "并行处理", "内存优化", "DuckDB调优"],
                "performance": "60-88%性能提升",
                "recommended_for": ["大规模历史数据补全", "全市场数据初始化"],
                "default_batch_size": 100
            },
            "incremental": {
                "name": "增量更新",
                "description": "轻量级增量数据同步",
                "features": ["快速执行", "简单直接", "低资源消耗"],
                "performance": "20%性能提升",
                "recommended_for": ["日常数据维护", "定时增量同步"],
                "default_batch_size": 50
            },
            "traditional": {
                "name": "传统补全",
                "description": "完整的任务管理和调度功能",
                "features": ["任务管理", "调度功能", "重试机制", "详细日志"],
                "performance": "基准性能",
                "recommended_for": ["复杂补全场景", "需要详细管理的任务"],
                "default_batch_size": 30
            }
        }
        
        return ApiResponse.success_response(
            message="获取补全模式成功",
            data=modes_info
        )
        
    except Exception as e:
        logger.error(f"获取补全模式失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取模式失败: {str(e)}")


@router.post("/quick", response_model=ApiResponse, summary="快速数据补全")
async def quick_backfill(
    request: QuickBackfillRequest,
    background_tasks: BackgroundTasks,
    data_service: DataService = Depends(get_data_service),
    optimized_service: OptimizedBackfillService = Depends(get_optimized_backfill_service)
):
    """快速补全最近N天的数据"""
    global _task_counter
    
    try:
        _task_counter += 1
        task_id = f"quick_{request.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_task_counter}"
        
        # 计算日期范围
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=request.days)).strftime('%Y-%m-%d')
        
        # 创建任务信息
        task_info = {
            "task_id": task_id,
            "task_name": f"快速补全{request.days}天数据",
            "mode": request.mode,
            "market": request.market,
            "start_date": start_date,
            "end_date": end_date,
            "status": "created",
            "progress": 0,
            "start_time": datetime.now().isoformat(),
            "type": "quick"
        }
        
        _unified_tasks[task_id] = task_info
        
        # 根据模式选择服务
        if request.mode == "optimized":
            background_tasks.add_task(
                _execute_optimized_quick_backfill,
                task_id, request, optimized_service
            )
        else:
            background_tasks.add_task(
                _execute_traditional_quick_backfill,
                task_id, request, data_service
            )
        
        logger.info(f"创建快速补全任务：{task_id}")
        
        return ApiResponse.success_response(
            message=f"快速补全任务创建成功，将补全最近{request.days}天数据",
            data={
                "task_id": task_id,
                "mode": request.mode,
                "date_range": f"{start_date} 至 {end_date}",
                "estimated_duration": f"{request.days * 2}分钟" if request.mode == "traditional" else f"{request.days}分钟"
            }
        )
        
    except Exception as e:
        logger.error(f"创建快速补全任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/full-market", response_model=ApiResponse, summary="全市场数据补全")
async def full_market_backfill(
    request: UnifiedBackfillRequest,
    background_tasks: BackgroundTasks,
    data_service: DataService = Depends(get_data_service),
    optimized_service: OptimizedBackfillService = Depends(get_optimized_backfill_service)
):
    """启动全市场数据补全任务"""
    global _task_counter
    
    try:
        # 生成任务ID
        _task_counter += 1
        task_id = f"full_{request.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_task_counter}"
        
        # 验证日期格式
        if request.start_date:
            try:
                datetime.strptime(request.start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="开始日期格式错误")
        
        if request.end_date:
            try:
                datetime.strptime(request.end_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="结束日期格式错误")
        
        # 检查任务重复
        for existing_task in _unified_tasks.values():
            if (existing_task.get("task_name") == request.task_name and 
                existing_task.get("status") in ["created", "running"]):
                raise HTTPException(status_code=400, detail=f"任务'{request.task_name}'已在运行中")
        
        # 创建任务信息
        task_info = {
            "task_id": task_id,
            "task_name": request.task_name,
            "mode": request.mode,
            "market": request.market,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "stock_codes": request.stock_codes,
            "batch_size": request.batch_size,
            "force_update": request.force_update,
            "enable_parallel": request.enable_parallel,
            "priority": request.priority,
            "status": "created",
            "progress": 0,
            "start_time": datetime.now().isoformat(),
            "type": "full_market"
        }
        
        _unified_tasks[task_id] = task_info
        
        # 根据模式选择执行策略
        if request.mode == "optimized":
            background_tasks.add_task(
                _execute_optimized_backfill,
                task_id, request, optimized_service
            )
        elif request.mode == "incremental":
            background_tasks.add_task(
                _execute_incremental_backfill,
                task_id, request, data_service
            )
        else:  # traditional
            background_tasks.add_task(
                _execute_traditional_backfill,
                task_id, request, data_service
            )
        
        logger.info(f"创建{request.mode}模式补全任务：{task_id} - {request.task_name}")
        
        return ApiResponse.success_response(
            message=f"数据补全任务'{request.task_name}'创建成功",
            data={
                "task_id": task_id,
                "mode": request.mode,
                "task_name": request.task_name,
                "status": "created",
                "estimated_duration": _estimate_unified_task_duration(request)
            }
        )
        
    except Exception as e:
        logger.error(f"创建补全任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}", response_model=ApiResponse, summary="获取任务状态")
async def get_task_status(task_id: str):
    """获取指定任务的详细状态"""
    try:
        if task_id in _unified_tasks:
            task_info = _unified_tasks[task_id]
            return ApiResponse.success_response(
                message="获取任务状态成功",
                data=task_info
            )
        else:
            raise HTTPException(status_code=404, detail="任务不存在")
            
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks", response_model=ApiResponse, summary="获取任务列表")
async def get_tasks_list(
    mode: Optional[str] = Query(None, description="按模式筛选"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    limit: int = Query(20, description="返回数量限制", ge=1, le=100)
):
    """获取任务列表"""
    try:
        tasks = list(_unified_tasks.values())
        
        # 按模式筛选
        if mode:
            tasks = [t for t in tasks if t.get("mode") == mode]
        
        # 按状态筛选
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        
        # 按创建时间倒序排列
        tasks.sort(key=lambda x: x.get("start_time", ""), reverse=True)
        
        # 限制返回数量
        tasks = tasks[:limit]
        
        return ApiResponse.success_response(
            message=f"获取任务列表成功，共{len(tasks)}个任务",
            data={
                "tasks": tasks,
                "total_count": len(_unified_tasks),
                "filtered_count": len(tasks)
            }
        )
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/task/{task_id}", response_model=ApiResponse, summary="取消任务")
async def cancel_task(task_id: str):
    """取消指定的任务"""
    try:
        if task_id not in _unified_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        task_info = _unified_tasks[task_id]
        
        if task_info.get("status") in ["completed", "failed", "cancelled"]:
            return ApiResponse.success_response(
                message=f"任务已处于{task_info.get('status')}状态，无需取消",
                data={"task_id": task_id, "status": task_info.get("status")}
            )
        
        # 更新任务状态
        task_info["status"] = "cancelled"
        task_info["end_time"] = datetime.now().isoformat()
        task_info["cancel_reason"] = "用户主动取消"
        
        logger.info(f"任务{task_id}已被取消")
        
        return ApiResponse.success_response(
            message="任务取消成功",
            data={"task_id": task_id, "status": "cancelled"}
        )
        
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 内部执行函数
async def _execute_optimized_backfill(task_id: str, request: UnifiedBackfillRequest, service: OptimizedBackfillService):
    """执行优化补全任务"""
    try:
        task_info = _unified_tasks[task_id]
        task_info["status"] = "running"
        
        # 调用优化服务
        result = await service.full_market_backfill(
            market=request.market,
            start_date=request.start_date,
            end_date=request.end_date,
            force_update=request.force_update
        )
        
        task_info["status"] = "completed"
        task_info["progress"] = 100
        task_info["end_time"] = datetime.now().isoformat()
        task_info["result"] = result
        
        logger.info(f"优化补全任务{task_id}完成")
        
    except Exception as e:
        task_info = _unified_tasks[task_id]
        task_info["status"] = "failed"
        task_info["error"] = str(e)
        task_info["end_time"] = datetime.now().isoformat()
        logger.error(f"优化补全任务{task_id}失败: {e}")


async def _execute_incremental_backfill(task_id: str, request: UnifiedBackfillRequest, service: DataService):
    """执行增量补全任务"""
    try:
        task_info = _unified_tasks[task_id]
        task_info["status"] = "running"
        
        # 获取股票列表
        stocks = await service.get_stock_list(request.market)
        stock_codes = [stock["stock_code"] for stock in stocks]
        
        # 批量更新数据
        result = await service._batch_update_daily_data_optimized(stock_codes, request.batch_size)
        
        task_info["status"] = "completed"
        task_info["progress"] = 100
        task_info["end_time"] = datetime.now().isoformat()
        task_info["result"] = result
        
        logger.info(f"增量补全任务{task_id}完成")
        
    except Exception as e:
        task_info = _unified_tasks[task_id]
        task_info["status"] = "failed"
        task_info["error"] = str(e)
        task_info["end_time"] = datetime.now().isoformat()
        logger.error(f"增量补全任务{task_id}失败: {e}")


async def _execute_traditional_backfill(task_id: str, request: UnifiedBackfillRequest, service: DataService):
    """执行传统补全任务"""
    try:
        task_info = _unified_tasks[task_id]
        task_info["status"] = "running"
        
        # 使用传统方法进行数据补全
        # 这里可以调用原有的传统补全逻辑
        result = await service.batch_update_daily_data(
            stock_codes=request.stock_codes or [],
            batch_size=request.batch_size,
            delay_seconds=request.delay_seconds
        )
        
        task_info["status"] = "completed"
        task_info["progress"] = 100
        task_info["end_time"] = datetime.now().isoformat()
        task_info["result"] = result
        
        logger.info(f"传统补全任务{task_id}完成")
        
    except Exception as e:
        task_info = _unified_tasks[task_id]
        task_info["status"] = "failed"
        task_info["error"] = str(e)
        task_info["end_time"] = datetime.now().isoformat()
        logger.error(f"传统补全任务{task_id}失败: {e}")


async def _execute_optimized_quick_backfill(task_id: str, request: QuickBackfillRequest, service: OptimizedBackfillService):
    """执行优化快速补全"""
    try:
        task_info = _unified_tasks[task_id]
        task_info["status"] = "running"
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=request.days)).strftime('%Y-%m-%d')
        
        result = await service.full_market_backfill(
            market=request.market,
            start_date=start_date,
            end_date=end_date,
            force_update=request.force_update
        )
        
        task_info["status"] = "completed"
        task_info["progress"] = 100
        task_info["end_time"] = datetime.now().isoformat()
        task_info["result"] = result
        
        logger.info(f"优化快速补全任务{task_id}完成")
        
    except Exception as e:
        task_info = _unified_tasks[task_id]
        task_info["status"] = "failed"
        task_info["error"] = str(e)
        task_info["end_time"] = datetime.now().isoformat()
        logger.error(f"优化快速补全任务{task_id}失败: {e}")


async def _execute_traditional_quick_backfill(task_id: str, request: QuickBackfillRequest, service: DataService):
    """执行传统快速补全"""
    try:
        task_info = _unified_tasks[task_id]
        task_info["status"] = "running"
        
        # 获取股票列表
        stocks = await service.get_stock_list(request.market)
        stock_codes = [stock["stock_code"] for stock in stocks]
        
        # 批量更新数据
        result = await service._batch_update_daily_data_optimized(stock_codes, 50)
        
        task_info["status"] = "completed"
        task_info["progress"] = 100
        task_info["end_time"] = datetime.now().isoformat()
        task_info["result"] = result
        
        logger.info(f"传统快速补全任务{task_id}完成")
        
    except Exception as e:
        task_info = _unified_tasks[task_id]
        task_info["status"] = "failed"
        task_info["error"] = str(e)
        task_info["end_time"] = datetime.now().isoformat()
        logger.error(f"传统快速补全任务{task_id}失败: {e}")


def _estimate_unified_task_duration(request: UnifiedBackfillRequest) -> str:
    """估算任务执行时间"""
    base_time = 30  # 基础时间（分钟）
    
    if request.mode == "optimized":
        multiplier = 0.3  # 优化模式快3倍
    elif request.mode == "incremental":
        multiplier = 0.5  # 增量模式快2倍
    else:
        multiplier = 1.0  # 传统模式基准
    
    # 根据批量大小调整
    if request.batch_size > 100:
        multiplier *= 0.8
    elif request.batch_size < 50:
        multiplier *= 1.2
    
    estimated_minutes = int(base_time * multiplier)
    
    if estimated_minutes < 60:
        return f"{estimated_minutes}分钟"
    else:
        hours = estimated_minutes // 60
        minutes = estimated_minutes % 60
        return f"{hours}小时{minutes}分钟"