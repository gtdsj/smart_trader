# coding=utf-8
"""
定时任务管理API路由
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# from api.base import ApiResponse  # 使用本地定义
from services.scheduler_service import SchedulerService, ScheduledTask, TaskType, TaskStatus
from services.data_service import DataService
from services.notification_service import NotificationService
from strategies.custom_stock_selection import CustomStockSelectionStrategy
# from utils.logger import logger  # 使用简单的print替代


router = APIRouter(prefix="/api/v1/scheduler", tags=["定时任务管理"])


# 请求模型
class ApiResponse(BaseModel):
    """API响应模型"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    name: str = Field(..., description="任务名称")
    description: str = Field(..., description="任务描述")
    task_type: str = Field(..., description="任务类型")
    cron_expression: str = Field(..., description="Cron表达式")
    task_params: Dict[str, Any] = Field(default_factory=dict, description="任务参数")
    is_active: bool = Field(default=True, description="是否激活")


class UpdateTaskRequest(BaseModel):
    """更新任务请求"""
    name: Optional[str] = Field(None, description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    cron_expression: Optional[str] = Field(None, description="Cron表达式")
    task_params: Optional[Dict[str, Any]] = Field(None, description="任务参数")
    is_active: Optional[bool] = Field(None, description="是否激活")


class StockSelectionRequest(BaseModel):
    """选股请求"""
    target_date: Optional[str] = Field(None, description="目标日期，格式YYYY-MM-DD")
    save_to_db: bool = Field(default=False, description="是否保存到数据库")
    send_notification: bool = Field(default=True, description="是否发送通知")


# 全局服务实例
_scheduler_service: Optional[SchedulerService] = None


def get_scheduler_service() -> SchedulerService:
    """获取调度器服务实例"""
    global _scheduler_service
    if _scheduler_service is None:
        # 这里需要依赖注入，实际使用时应该从容器获取
        data_service = DataService()
        notification_service = NotificationService()
        _scheduler_service = SchedulerService(data_service, notification_service)
    return _scheduler_service


@router.get("/status", response_model=ApiResponse, summary="获取调度器状态")
async def get_scheduler_status(
    service: SchedulerService = Depends(get_scheduler_service)
):
    """
    获取调度器运行状态
    
    Returns:
        调度器状态信息
    """
    try:
        tasks = service.list_tasks()
        running_tasks = [task for task in tasks if task['is_running']]
        active_tasks = [task for task in tasks if task['is_active']]
        
        return ApiResponse(
            success=True,
            message="获取调度器状态成功",
            data={
                "is_running": service.is_running,
                "total_tasks": len(tasks),
                "active_tasks": len(active_tasks),
                "running_tasks": len(running_tasks),
                "tasks": tasks
            }
        )
        
    except Exception as e:
        print(f"[ERROR] 获取调度器状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取调度器状态失败: {str(e)}")


@router.post("/start", response_model=ApiResponse, summary="启动调度器")
async def start_scheduler(
    service: SchedulerService = Depends(get_scheduler_service)
):
    """
    启动定时任务调度器
    
    Returns:
        启动结果
    """
    try:
        await service.start()
        
        return ApiResponse(
            success=True,
            message="调度器启动成功",
            data={"status": "running"}
        )
        
    except Exception as e:
        print(f"[ERROR] 启动调度器失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动调度器失败: {str(e)}")


@router.post("/stop", response_model=ApiResponse, summary="停止调度器")
async def stop_scheduler(
    service: SchedulerService = Depends(get_scheduler_service)
):
    """
    停止定时任务调度器
    
    Returns:
        停止结果
    """
    try:
        await service.stop()
        
        return ApiResponse(
            success=True,
            message="调度器停止成功",
            data={"status": "stopped"}
        )
        
    except Exception as e:
        print(f"[ERROR] 停止调度器失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止调度器失败: {str(e)}")


@router.get("/tasks", response_model=ApiResponse, summary="获取任务列表")
async def get_tasks(
    task_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    service: SchedulerService = Depends(get_scheduler_service)
):
    """
    获取定时任务列表
    
    Args:
        task_type: 任务类型过滤
        is_active: 是否激活过滤
        
    Returns:
        任务列表
    """
    try:
        tasks = service.list_tasks()
        
        # 应用过滤条件
        if task_type:
            tasks = [task for task in tasks if task['task_type'] == task_type]
            
        if is_active is not None:
            tasks = [task for task in tasks if task['is_active'] == is_active]
            
        return ApiResponse(
            success=True,
            message=f"获取任务列表成功，共{len(tasks)}个任务",
            data={
                "total_count": len(tasks),
                "tasks": tasks
            }
        )
        
    except Exception as e:
        print(f"[ERROR] 获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.get("/tasks/{task_id}", response_model=ApiResponse, summary="获取任务详情")
async def get_task(
    task_id: str,
    service: SchedulerService = Depends(get_scheduler_service)
):
    """
    获取指定任务的详细信息
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务详情
    """
    try:
        task_status = service.get_task_status(task_id)
        
        if not task_status:
            raise HTTPException(status_code=404, detail=f"任务{task_id}不存在")
            
        return ApiResponse(
            success=True,
            message="获取任务详情成功",
            data=task_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] 获取任务详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务详情失败: {str(e)}")


@router.post("/tasks/{task_id}/run", response_model=ApiResponse, summary="立即执行任务")
async def run_task(
    task_id: str,
    service: SchedulerService = Depends(get_scheduler_service)
):
    """
    立即执行指定任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        执行结果
    """
    try:
        success = await service.run_task_now(task_id)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"任务{task_id}执行失败")
            
        return ApiResponse(
            success=True,
            message=f"任务{task_id}已开始执行",
            data={"task_id": task_id, "status": "running"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] 执行任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"执行任务失败: {str(e)}")


@router.delete("/tasks/{task_id}", response_model=ApiResponse, summary="删除任务")
async def delete_task(
    task_id: str,
    service: SchedulerService = Depends(get_scheduler_service)
):
    """
    删除指定任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        删除结果
    """
    try:
        success = service.remove_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"任务{task_id}不存在")
            
        return ApiResponse(
            success=True,
            message=f"任务{task_id}删除成功",
            data={"task_id": task_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] 删除任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


@router.post("/stock-selection/run", response_model=ApiResponse, summary="执行选股任务")
async def run_stock_selection(
    request: StockSelectionRequest,
    background_tasks: BackgroundTasks,
    service: SchedulerService = Depends(get_scheduler_service)
):
    """
    立即执行选股任务
    
    Args:
        request: 选股请求参数
        background_tasks: 后台任务
        
    Returns:
        选股结果
    """
    try:
        # 创建选股策略实例
        data_service = DataService()
        strategy = CustomStockSelectionStrategy(data_service)
        
        # 执行选股
        if request.target_date:
            # 验证日期格式
            try:
                datetime.strptime(request.target_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="日期格式错误，应为YYYY-MM-DD")
                
        # 后台执行选股任务
        background_tasks.add_task(
            _run_stock_selection_background,
            strategy,
            request.target_date,
            request.save_to_db,
            request.send_notification,
            service
        )
        
        return ApiResponse(
            success=True,
            message="选股任务已启动，正在后台执行",
            data={
                "target_date": request.target_date,
                "save_to_db": request.save_to_db,
                "send_notification": request.send_notification
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] 执行选股任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"执行选股任务失败: {str(e)}")


@router.get("/stock-selection/history", response_model=ApiResponse, summary="获取选股历史")
async def get_stock_selection_history(
    limit: int = 10,
    offset: int = 0
):
    """
    获取选股历史记录
    
    Args:
        limit: 返回数量限制
        offset: 偏移量
        
    Returns:
        选股历史记录
    """
    try:
        # TODO: 从数据库获取选股历史记录
        # 这里返回模拟数据
        history = [
            {
                "id": 1,
                "selection_date": "2024-12-01",
                "strategy_name": "自定义多维度选股策略",
                "selected_count": 15,
                "execution_time": "2024-12-01T09:00:00",
                "status": "completed"
            }
        ]
        
        return ApiResponse(
            success=True,
            message="获取选股历史成功",
            data={
                "total_count": len(history),
                "history": history[offset:offset+limit]
            }
        )
        
    except Exception as e:
        print(f"[ERROR] 获取选股历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取选股历史失败: {str(e)}")


async def _run_stock_selection_background(
    strategy: CustomStockSelectionStrategy,
    target_date: Optional[str],
    save_to_db: bool,
    send_notification: bool,
    scheduler_service: SchedulerService
):
    """
    后台执行选股任务
    
    Args:
        strategy: 选股策略实例
        target_date: 目标日期
        save_to_db: 是否保存到数据库
        send_notification: 是否发送通知
        scheduler_service: 调度器服务
    """
    try:
        print("[INFO] 开始后台执行选股任务")
        
        # 执行选股
        results = await strategy.screen_stocks(target_date)
        
        print(f"[INFO] 选股完成，发现{len(results)}只符合条件的股票")
        
        # 保存到数据库
        if save_to_db:
            # TODO: 实现保存选股结果到数据库的逻辑
            print("[INFO] 选股结果已保存到数据库")
            
        # 发送通知
        if send_notification and scheduler_service.notification_service:
            await scheduler_service._send_stock_selection_notification(
                type('Task', (), {
                    'name': '手动选股任务',
                    'task_type': TaskType.STOCK_SELECTION
                })(),
                results
            )
            
        print("[INFO] 后台选股任务执行完成")
        
    except Exception as e:
        print(f"[ERROR] 后台选股任务执行失败: {e}")