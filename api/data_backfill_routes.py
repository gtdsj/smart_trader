# coding=utf-8
"""
数据补全专用API路由
专门用于A股全市场历史数据的补全和管理
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import json
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from loguru import logger

from services.data_service import DataService
from api.data_routes import get_data_service, ApiResponse

# 创建专用路由器
router = APIRouter(prefix="/api/v1/data-backfill", tags=["数据补全管理"])


# 请求模型
class BackfillTaskRequest(BaseModel):
    """数据补全任务请求"""
    task_name: str = Field(..., description="任务名称")
    market: str = Field("ALL", description="市场代码：SH、SZ或ALL")
    start_date: Optional[str] = Field(None, description="开始日期，格式YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="结束日期，格式YYYY-MM-DD")
    stock_codes: Optional[List[str]] = Field(None, description="指定股票代码列表，为空则处理全市场")
    batch_size: int = Field(30, description="批量处理大小", ge=1, le=100)
    delay_seconds: float = Field(0.2, description="批次间延迟秒数", ge=0.1, le=5.0)
    force_update: bool = Field(False, description="是否强制更新已存在的数据")
    priority: str = Field("normal", description="任务优先级：low、normal、high")
    auto_retry: bool = Field(True, description="是否自动重试失败的股票")
    max_retries: int = Field(3, description="最大重试次数", ge=1, le=5)


class BackfillScheduleRequest(BaseModel):
    """定时补全任务请求"""
    schedule_name: str = Field(..., description="定时任务名称")
    cron_expression: str = Field(..., description="Cron表达式")
    task_config: BackfillTaskRequest = Field(..., description="任务配置")
    enabled: bool = Field(True, description="是否启用")


# 全局任务状态存储（实际应用中应使用Redis或数据库）
_running_tasks = {}
_task_history = []
_scheduled_tasks = {}


@router.get("/status", response_model=ApiResponse, summary="获取数据补全服务状态")
async def get_backfill_status(service: DataService = Depends(get_data_service)):
    """获取数据补全服务的整体状态"""
    try:
        # 获取数据完整度分析
        completeness_analysis = await service.analyze_data_completeness()
        
        # 获取运行中的任务
        running_tasks_info = [
            {
                "task_id": task_id,
                "task_name": task_info.get("task_name", "未知任务"),
                "progress": task_info.get("progress", 0),
                "start_time": task_info.get("start_time"),
                "status": task_info.get("status", "running")
            }
            for task_id, task_info in _running_tasks.items()
        ]
        
        # 获取最近的任务历史
        recent_history = _task_history[-10:] if _task_history else []
        
        status_info = {
            "service_status": "running" if service.is_running else "stopped",
            "data_completeness": completeness_analysis.get("overall_completeness", 0),
            "incomplete_stocks_count": completeness_analysis.get("incomplete_stocks_count", 0),
            "running_tasks_count": len(_running_tasks),
            "scheduled_tasks_count": len(_scheduled_tasks),
            "running_tasks": running_tasks_info,
            "recent_task_history": recent_history,
            "last_analysis_time": completeness_analysis.get("analysis_time"),
            "system_recommendations": _generate_recommendations(completeness_analysis)
        }
        
        return ApiResponse(
            success=True,
            message="获取数据补全服务状态成功",
            data=status_info
        )
        
    except Exception as e:
        logger.error(f"获取数据补全服务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze", response_model=ApiResponse, summary="分析数据完整度")
async def analyze_data_completeness(
    market: Optional[str] = Query("ALL", description="市场代码"),
    detailed: bool = Query(False, description="是否返回详细分析"),
    service: DataService = Depends(get_data_service)
):
    """深度分析数据完整度，生成补全建议"""
    try:
        logger.info(f"开始分析{market}市场数据完整度")
        
        # 执行完整度分析
        analysis_result = await service.analyze_data_completeness()
        
        if not analysis_result:
            return ApiResponse(
                success=False,
                message="数据完整度分析失败",
                data=None
            )
        
        # 生成补全建议
        recommendations = _generate_detailed_recommendations(analysis_result)
        
        # 构建响应数据
        response_data = {
            "analysis_summary": {
                "overall_completeness": analysis_result.get("overall_completeness", 0),
                "total_stocks": analysis_result.get("total_stocks", 0),
                "incomplete_stocks_count": analysis_result.get("incomplete_stocks_count", 0),
                "missing_records": analysis_result.get("missing_records", 0),
                "analysis_time": analysis_result.get("analysis_time")
            },
            "completeness_distribution": analysis_result.get("completeness_distribution", {}),
            "recommendations": recommendations
        }
        
        # 如果需要详细信息，包含具体的股票分析
        if detailed:
            response_data["detailed_analysis"] = {
                "incomplete_stocks": analysis_result.get("incomplete_stocks", [])[:50],  # 限制返回数量
                "priority_stocks": _get_priority_stocks(analysis_result.get("incomplete_stocks", [])),
                "estimated_time": _estimate_backfill_time(analysis_result.get("incomplete_stocks", []))
            }
        
        return ApiResponse(
            success=True,
            message=f"数据完整度分析完成，总体完整度：{analysis_result.get('overall_completeness', 0):.1f}%",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"分析数据完整度失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/task/create", response_model=ApiResponse, summary="创建数据补全任务")
async def create_backfill_task(
    request: BackfillTaskRequest,
    background_tasks: BackgroundTasks,
    service: DataService = Depends(get_data_service)
):
    """创建并启动数据补全任务"""
    try:
        # 生成任务ID
        task_id = f"backfill_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(_running_tasks)}"
        
        # 验证参数
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
        
        # 检查是否有同名任务正在运行
        for existing_task in _running_tasks.values():
            if existing_task.get("task_name") == request.task_name:
                raise HTTPException(status_code=400, detail=f"任务'{request.task_name}'已在运行中")
        
        # 创建任务信息
        task_info = {
            "task_id": task_id,
            "task_name": request.task_name,
            "market": request.market,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "stock_codes": request.stock_codes,
            "batch_size": request.batch_size,
            "delay_seconds": request.delay_seconds,
            "force_update": request.force_update,
            "priority": request.priority,
            "auto_retry": request.auto_retry,
            "max_retries": request.max_retries,
            "status": "created",
            "progress": 0,
            "start_time": datetime.now().isoformat(),
            "created_by": "api"
        }
        
        # 添加到运行任务列表
        _running_tasks[task_id] = task_info
        
        # 在后台启动任务
        background_tasks.add_task(
            _execute_backfill_task,
            task_id,
            request,
            service
        )
        
        logger.info(f"创建数据补全任务：{task_id} - {request.task_name}")
        
        return ApiResponse(
            success=True,
            message=f"数据补全任务'{request.task_name}'创建成功",
            data={
                "task_id": task_id,
                "task_name": request.task_name,
                "status": "created",
                "estimated_duration": _estimate_task_duration(request)
            }
        )
        
    except Exception as e:
        logger.error(f"创建数据补全任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}", response_model=ApiResponse, summary="获取任务状态")
async def get_task_status(task_id: str):
    """获取指定任务的详细状态"""
    try:
        # 先检查运行中的任务
        if task_id in _running_tasks:
            task_info = _running_tasks[task_id]
            return ApiResponse(
                success=True,
                message="获取任务状态成功",
                data=task_info
            )
        
        # 检查历史任务
        for task in _task_history:
            if task.get("task_id") == task_id:
                return ApiResponse(
                    success=True,
                    message="获取任务状态成功",
                    data=task
                )
        
        raise HTTPException(status_code=404, detail=f"未找到任务：{task_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/task/{task_id}/cancel", response_model=ApiResponse, summary="取消任务")
async def cancel_task(task_id: str):
    """取消正在运行的任务"""
    try:
        if task_id not in _running_tasks:
            raise HTTPException(status_code=404, detail=f"未找到运行中的任务：{task_id}")
        
        task_info = _running_tasks[task_id]
        task_info["status"] = "cancelled"
        task_info["end_time"] = datetime.now().isoformat()
        task_info["cancel_reason"] = "用户取消"
        
        # 移动到历史记录
        _task_history.append(task_info)
        del _running_tasks[task_id]
        
        logger.info(f"任务已取消：{task_id}")
        
        return ApiResponse(
            success=True,
            message=f"任务'{task_info.get('task_name', task_id)}'已取消",
            data={"task_id": task_id, "status": "cancelled"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks", response_model=ApiResponse, summary="获取任务列表")
async def get_tasks(
    status: Optional[str] = Query(None, description="任务状态过滤"),
    limit: int = Query(20, description="返回数量限制", ge=1, le=100)
):
    """获取任务列表"""
    try:
        all_tasks = []
        
        # 添加运行中的任务
        for task_info in _running_tasks.values():
            if not status or task_info.get("status") == status:
                all_tasks.append(task_info)
        
        # 添加历史任务
        for task_info in _task_history:
            if not status or task_info.get("status") == status:
                all_tasks.append(task_info)
        
        # 按开始时间排序（最新的在前）
        all_tasks.sort(key=lambda x: x.get("start_time", ""), reverse=True)
        
        # 限制返回数量
        limited_tasks = all_tasks[:limit]
        
        return ApiResponse(
            success=True,
            message=f"获取任务列表成功，共{len(limited_tasks)}个任务",
            data={
                "total_count": len(all_tasks),
                "returned_count": len(limited_tasks),
                "tasks": limited_tasks
            }
        )
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tasks/cleanup", response_model=ApiResponse, summary="清理任务历史")
async def cleanup_task_history(
    keep_days: int = Query(7, description="保留天数", ge=1, le=30)
):
    """清理指定天数之前的任务历史记录"""
    try:
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        cutoff_str = cutoff_date.isoformat()
        
        original_count = len(_task_history)
        
        # 过滤保留最近的任务
        _task_history[:] = [
            task for task in _task_history
            if task.get("start_time", "") > cutoff_str
        ]
        
        cleaned_count = original_count - len(_task_history)
        
        logger.info(f"清理任务历史：删除{cleaned_count}个任务记录")
        
        return ApiResponse(
            success=True,
            message=f"清理完成，删除{cleaned_count}个任务记录，保留{len(_task_history)}个",
            data={
                "cleaned_count": cleaned_count,
                "remaining_count": len(_task_history),
                "cutoff_date": cutoff_str
            }
        )
        
    except Exception as e:
        logger.error(f"清理任务历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 辅助函数
async def _execute_backfill_task(
    task_id: str,
    request: BackfillTaskRequest,
    service: DataService
):
    """执行数据补全任务"""
    task_info = _running_tasks.get(task_id)
    if not task_info:
        return
    
    try:
        task_info["status"] = "running"
        task_info["progress"] = 0
        
        logger.info(f"开始执行数据补全任务：{task_id}")
        
        # 获取股票列表
        if request.stock_codes:
            stock_codes = request.stock_codes
        else:
            all_stocks = await service.get_stock_list(request.market)
            stock_codes = [stock["stock_code"] for stock in all_stocks]
        
        total_stocks = len(stock_codes)
        task_info["total_stocks"] = total_stocks
        
        # 分批处理
        success_count = 0
        failed_count = 0
        
        for i in range(0, total_stocks, request.batch_size):
            # 检查任务是否被取消
            if task_info.get("status") == "cancelled":
                break
            
            batch_stocks = stock_codes[i:i + request.batch_size]
            
            # 更新进度
            progress = int((i / total_stocks) * 100)
            task_info["progress"] = progress
            task_info["current_batch"] = f"{i // request.batch_size + 1}/{(total_stocks + request.batch_size - 1) // request.batch_size}"
            
            # 处理当前批次
            batch_result = await service.batch_update_daily_data(batch_stocks)
            success_count += batch_result.get("success_count", 0)
            failed_count += batch_result.get("failed_count", 0)
            
            # 批次间延迟
            if i + request.batch_size < total_stocks:
                await asyncio.sleep(request.delay_seconds)
        
        # 任务完成
        task_info["status"] = "completed"
        task_info["progress"] = 100
        task_info["end_time"] = datetime.now().isoformat()
        task_info["success_count"] = success_count
        task_info["failed_count"] = failed_count
        task_info["success_rate"] = round(success_count / total_stocks * 100, 2) if total_stocks > 0 else 0
        
        logger.info(f"数据补全任务完成：{task_id}，成功{success_count}只，失败{failed_count}只")
        
    except Exception as e:
        task_info["status"] = "failed"
        task_info["error"] = str(e)
        task_info["end_time"] = datetime.now().isoformat()
        logger.error(f"数据补全任务失败：{task_id}，错误：{e}")
    
    finally:
        # 移动到历史记录
        if task_id in _running_tasks:
            _task_history.append(_running_tasks[task_id])
            del _running_tasks[task_id]


def _generate_recommendations(analysis: Dict[str, Any]) -> List[str]:
    """生成数据补全建议"""
    recommendations = []
    
    completeness = analysis.get("overall_completeness", 0)
    incomplete_count = analysis.get("incomplete_stocks_count", 0)
    
    if completeness < 50:
        recommendations.append("🔴 数据完整度严重不足，建议立即执行全市场数据补全")
    elif completeness < 80:
        recommendations.append("🟡 数据完整度偏低，建议执行增量数据补全")
    elif completeness < 95:
        recommendations.append("🟢 数据完整度良好，建议定期维护更新")
    else:
        recommendations.append("✅ 数据完整度优秀，保持当前更新频率")
    
    if incomplete_count > 100:
        recommendations.append(f"📊 有{incomplete_count}只股票需要补全，建议分批处理")
    
    return recommendations


def _generate_detailed_recommendations(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """生成详细的补全建议"""
    incomplete_stocks = analysis.get("incomplete_stocks", [])
    
    # 按优先级分类
    high_priority = [s for s in incomplete_stocks if s.get("completeness", 0) < 50]
    medium_priority = [s for s in incomplete_stocks if 50 <= s.get("completeness", 0) < 80]
    low_priority = [s for s in incomplete_stocks if s.get("completeness", 0) >= 80]
    
    return {
        "priority_classification": {
            "high_priority_count": len(high_priority),
            "medium_priority_count": len(medium_priority),
            "low_priority_count": len(low_priority)
        },
        "suggested_actions": [
            f"优先处理{len(high_priority)}只完整度<50%的股票",
            f"其次处理{len(medium_priority)}只完整度50-80%的股票",
            f"最后处理{len(low_priority)}只完整度>80%的股票"
        ],
        "estimated_workload": {
            "total_missing_records": analysis.get("missing_records", 0),
            "estimated_time_hours": _estimate_backfill_time(incomplete_stocks)
        }
    }


def _get_priority_stocks(incomplete_stocks: List[Dict]) -> List[Dict]:
    """获取优先级最高的股票"""
    # 按完整度和落后天数排序
    sorted_stocks = sorted(
        incomplete_stocks,
        key=lambda x: (x.get("completeness", 0), -x.get("days_behind", 0))
    )
    return sorted_stocks[:20]  # 返回前20只


def _estimate_backfill_time(incomplete_stocks: List[Dict]) -> float:
    """估算补全时间（小时）"""
    total_missing = sum(stock.get("missing_days", 0) for stock in incomplete_stocks)
    # 假设每秒处理10条记录
    estimated_seconds = total_missing / 10
    return round(estimated_seconds / 3600, 2)


def _estimate_task_duration(request: BackfillTaskRequest) -> str:
    """估算任务持续时间"""
    if request.stock_codes:
        stock_count = len(request.stock_codes)
    else:
        stock_count = 5000  # 估算全市场股票数量
    
    # 估算处理时间
    batch_count = (stock_count + request.batch_size - 1) // request.batch_size
    estimated_minutes = batch_count * (request.delay_seconds + 2) / 60  # 每批次约2秒处理时间
    
    if estimated_minutes < 60:
        return f"约{int(estimated_minutes)}分钟"
    else:
        return f"约{estimated_minutes/60:.1f}小时"