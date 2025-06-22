# -*- coding: utf-8 -*-
"""
通知服务API路由
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, validator
from loguru import logger

from services.notification_service import NotificationService, NotificationLevel

# 创建路由器
router = APIRouter(prefix="/api/v1/notification", tags=["通知服务"])

# 全局通知服务实例
notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """获取通知服务实例"""
    global notification_service
    if notification_service is None:
        raise HTTPException(status_code=500, detail="通知服务未初始化")
    return notification_service


def set_notification_service(service: NotificationService):
    """设置通知服务实例"""
    global notification_service
    notification_service = service


# 请求模型
class SendNotificationRequest(BaseModel):
    """发送通知请求"""
    title: str = Field(..., description="通知标题")
    content: str = Field(..., description="通知内容")
    level: str = Field("info", description="通知级别")
    notification_type: str = Field("custom", description="通知类型")
    data: Optional[Dict[str, Any]] = Field(None, description="附加数据")
    
    @validator('level')
    def validate_level(cls, v):
        try:
            NotificationLevel(v)
            return v
        except ValueError:
            raise ValueError('无效的通知级别')


class SendTradeSignalRequest(BaseModel):
    """发送交易信号通知请求"""
    stock_code: str = Field(..., description="股票代码")
    signal: str = Field(..., description="信号类型")
    strategy: str = Field(..., description="策略名称")
    price: float = Field(..., description="价格")
    reason: str = Field(..., description="信号原因")
    strength: float = Field(..., description="信号强度", ge=0, le=1)


class SendOrderNotificationRequest(BaseModel):
    """发送订单通知请求"""
    order_id: str = Field(..., description="订单ID")
    stock_code: str = Field(..., description="股票代码")
    action: str = Field(..., description="交易动作")
    quantity: int = Field(..., description="数量")
    price: float = Field(..., description="价格")
    status: str = Field(..., description="订单状态")
    message: Optional[str] = Field(None, description="附加消息")


class SendSystemAlertRequest(BaseModel):
    """发送系统告警请求"""
    alert_type: str = Field(..., description="告警类型")
    message: str = Field(..., description="告警消息")
    severity: str = Field("warning", description="严重程度")
    component: Optional[str] = Field(None, description="组件名称")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")


class NotificationConfigRequest(BaseModel):
    """通知配置请求"""
    webhook_url: Optional[str] = Field(None, description="钉钉Webhook URL")
    secret: Optional[str] = Field(None, description="钉钉密钥")
    enabled: Optional[bool] = Field(None, description="是否启用")
    min_level: Optional[str] = Field(None, description="最小通知级别")
    
    @validator('min_level')
    def validate_min_level(cls, v):
        if v is not None:
            try:
                NotificationLevel(v)
                return v
            except ValueError:
                raise ValueError('无效的通知级别')
        return v


# 响应模型
class NotificationInfo(BaseModel):
    """通知信息"""
    id: int = Field(..., description="通知ID")
    title: str = Field(..., description="通知标题")
    content: str = Field(..., description="通知内容")
    level: str = Field(..., description="通知级别")
    notification_type: str = Field(..., description="通知类型")
    status: str = Field(..., description="发送状态")
    created_at: str = Field(..., description="创建时间")
    sent_at: Optional[str] = Field(None, description="发送时间")
    error_message: Optional[str] = Field(None, description="错误消息")
    data: Optional[Dict[str, Any]] = Field(None, description="附加数据")


class NotificationStats(BaseModel):
    """通知统计"""
    total_sent: int = Field(..., description="总发送数")
    success_count: int = Field(..., description="成功数")
    failed_count: int = Field(..., description="失败数")
    pending_count: int = Field(..., description="待发送数")
    success_rate: float = Field(..., description="成功率")
    last_24h_count: int = Field(..., description="24小时内发送数")
    by_level: Dict[str, int] = Field(..., description="按级别统计")
    by_type: Dict[str, int] = Field(..., description="按类型统计")


class NotificationConfig(BaseModel):
    """通知配置"""
    webhook_url: str = Field(..., description="钉钉Webhook URL")
    secret: str = Field(..., description="钉钉密钥")
    enabled: bool = Field(..., description="是否启用")
    min_level: str = Field(..., description="最小通知级别")
    rate_limit: int = Field(..., description="速率限制（每分钟）")
    retry_count: int = Field(..., description="重试次数")
    timeout: int = Field(..., description="超时时间（秒）")


class ApiResponse(BaseModel):
    """API响应基类"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Any = Field(None, description="响应数据")


# API路由
@router.get("/config", response_model=ApiResponse, summary="获取通知配置")
async def get_notification_config(
    service: NotificationService = Depends(get_notification_service)
):
    """获取通知配置"""
    try:
        config = {
            "webhook_url": service.dingtalk_bot.webhook_url if service.dingtalk_bot else "",
            "secret": "***" if service.dingtalk_bot and service.dingtalk_bot.secret else "",
            "enabled": service.enabled,
            "min_level": "info",  # 默认最小级别
            "rate_limit": 60,  # 每分钟60条
            "retry_count": 3,
            "timeout": 10
        }
        
        return ApiResponse(
            success=True,
            message="获取通知配置成功",
            data=config
        )
    except Exception as e:
        logger.error(f"获取通知配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config", response_model=ApiResponse, summary="更新通知配置")
async def update_notification_config(
    request: NotificationConfigRequest,
    service: NotificationService = Depends(get_notification_service)
):
    """更新通知配置"""
    try:
        # 更新钉钉配置
        if request.webhook_url or request.secret:
            if service.dingtalk_bot:
                if request.webhook_url:
                    service.dingtalk_bot.webhook_url = request.webhook_url
                if request.secret:
                    service.dingtalk_bot.secret = request.secret
        
        # 更新服务状态
        if request.enabled is not None:
            service.enabled = request.enabled
        
        return ApiResponse(
            success=True,
            message="更新通知配置成功",
            data=None
        )
    except Exception as e:
        logger.error(f"更新通知配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test", response_model=ApiResponse, summary="测试通知")
async def test_notification(
    service: NotificationService = Depends(get_notification_service)
):
    """测试通知发送"""
    try:
        success = await service.send_custom_notification(
            title="测试通知",
            content="这是一条测试通知，用于验证通知服务是否正常工作。",
            level=NotificationLevel.INFO
        )
        
        if success:
            return ApiResponse(
                success=True,
                message="测试通知发送成功",
                data=None
            )
        else:
            return ApiResponse(
                success=False,
                message="测试通知发送失败",
                data=None
            )
    except Exception as e:
        logger.error(f"测试通知失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send", response_model=ApiResponse, summary="发送自定义通知")
async def send_notification(
    request: SendNotificationRequest,
    service: NotificationService = Depends(get_notification_service)
):
    """发送自定义通知"""
    try:
        success = await service.send_custom_notification(
            title=request.title,
            content=request.content,
            level=NotificationLevel(request.level),
            data=request.data
        )
        
        if success:
            return ApiResponse(
                success=True,
                message="通知发送成功",
                data=None
            )
        else:
            return ApiResponse(
                success=False,
                message="通知发送失败",
                data=None
            )
    except Exception as e:
        logger.error(f"发送通知失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trade-signal", response_model=ApiResponse, summary="发送交易信号通知")
async def send_trade_signal_notification(
    request: SendTradeSignalRequest,
    service: NotificationService = Depends(get_notification_service)
):
    """发送交易信号通知"""
    try:
        success = await service.send_trade_signal_notification(
            stock_code=request.stock_code,
            signal=request.signal,
            strategy=request.strategy,
            price=request.price,
            reason=request.reason,
            strength=request.strength
        )
        
        if success:
            return ApiResponse(
                success=True,
                message="交易信号通知发送成功",
                data=None
            )
        else:
            return ApiResponse(
                success=False,
                message="交易信号通知发送失败",
                data=None
            )
    except Exception as e:
        logger.error(f"发送交易信号通知失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/order", response_model=ApiResponse, summary="发送订单通知")
async def send_order_notification(
    request: SendOrderNotificationRequest,
    service: NotificationService = Depends(get_notification_service)
):
    """发送订单通知"""
    try:
        success = await service.send_order_notification(
            order_id=request.order_id,
            stock_code=request.stock_code,
            action=request.action,
            quantity=request.quantity,
            price=request.price,
            status=request.status,
            message=request.message
        )
        
        if success:
            return ApiResponse(
                success=True,
                message="订单通知发送成功",
                data=None
            )
        else:
            return ApiResponse(
                success=False,
                message="订单通知发送失败",
                data=None
            )
    except Exception as e:
        logger.error(f"发送订单通知失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system-alert", response_model=ApiResponse, summary="发送系统告警")
async def send_system_alert(
    request: SendSystemAlertRequest,
    service: NotificationService = Depends(get_notification_service)
):
    """发送系统告警"""
    try:
        # 根据严重程度确定通知级别
        level_mapping = {
            "info": NotificationLevel.INFO,
            "warning": NotificationLevel.WARNING,
            "error": NotificationLevel.ERROR,
            "critical": NotificationLevel.ERROR
        }
        level = level_mapping.get(request.severity, NotificationLevel.WARNING)
        
        success = await service.send_system_alert(
            alert_type=request.alert_type,
            message=request.message,
            level=level,
            component=request.component,
            details=request.details
        )
        
        if success:
            return ApiResponse(
                success=True,
                message="系统告警发送成功",
                data=None
            )
        else:
            return ApiResponse(
                success=False,
                message="系统告警发送失败",
                data=None
            )
    except Exception as e:
        logger.error(f"发送系统告警失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=ApiResponse, summary="获取通知历史")
async def get_notification_history(
    level: Optional[str] = Query(None, description="通知级别过滤"),
    notification_type: Optional[str] = Query(None, description="通知类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=200),
    offset: int = Query(0, description="偏移量", ge=0),
    service: NotificationService = Depends(get_notification_service)
):
    """获取通知历史"""
    try:
        # 验证参数
        if level:
            try:
                NotificationLevel(level)
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的通知级别")
        
        if start_date:
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="开始日期格式必须为 YYYY-MM-DD")
        
        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="结束日期格式必须为 YYYY-MM-DD")
        
        # 获取通知历史
        history = await service.get_notification_history(
            level=level,
            notification_type=notification_type,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        return ApiResponse(
            success=True,
            message="获取通知历史成功",
            data=history
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取通知历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=ApiResponse, summary="获取通知统计")
async def get_notification_statistics(
    days: int = Query(7, description="统计天数", ge=1, le=365),
    service: NotificationService = Depends(get_notification_service)
):
    """获取通知统计信息"""
    try:
        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 获取统计数据（简化处理，实际应该从数据库查询）
        stats = {
            "total_sent": 0,
            "success_count": 0,
            "failed_count": 0,
            "pending_count": 0,
            "success_rate": 0.0,
            "last_24h_count": 0,
            "by_level": {
                "info": 0,
                "warning": 0,
                "error": 0
            },
            "by_type": {
                "trade_signal": 0,
                "order_fill": 0,
                "system_alert": 0,
                "custom": 0
            },
            "period_days": days,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d')
        }
        
        return ApiResponse(
            success=True,
            message="获取通知统计成功",
            data=stats
        )
    except Exception as e:
        logger.error(f"获取通知统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/levels", response_model=ApiResponse, summary="获取通知级别列表")
async def get_notification_levels():
    """获取通知级别列表"""
    try:
        levels = [
            {
                "value": level.value,
                "label": {
                    "info": "信息",
                    "warning": "警告",
                    "error": "错误"
                }.get(level.value, level.value)
            }
            for level in NotificationLevel
        ]
        
        return ApiResponse(
            success=True,
            message="获取通知级别成功",
            data=levels
        )
    except Exception as e:
        logger.error(f"获取通知级别失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types", response_model=ApiResponse, summary="获取通知类型列表")
async def get_notification_types():
    """获取通知类型列表"""
    try:
        types = [
            {"value": "trade_signal", "label": "交易信号"},
            {"value": "order_fill", "label": "订单成交"},
            {"value": "order_error", "label": "订单错误"},
            {"value": "system_alert", "label": "系统告警"},
            {"value": "backtest_complete", "label": "回测完成"},
            {"value": "strategy_signal", "label": "策略信号"},
            {"value": "custom", "label": "自定义"}
        ]
        
        return ApiResponse(
            success=True,
            message="获取通知类型成功",
            data=types
        )
    except Exception as e:
        logger.error(f"获取通知类型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear-history", response_model=ApiResponse, summary="清理通知历史")
async def clear_notification_history(
    days: int = Query(30, description="保留天数", ge=1, le=365),
    service: NotificationService = Depends(get_notification_service)
):
    """清理指定天数之前的通知历史"""
    try:
        # 计算清理日期
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 执行清理（这里需要实现数据库清理逻辑）
        # deleted_count = await service.clear_old_notifications(cutoff_date)
        deleted_count = 0  # 占位符
        
        return ApiResponse(
            success=True,
            message=f"清理通知历史成功，删除了{deleted_count}条记录",
            data={"deleted_count": deleted_count, "cutoff_date": cutoff_date.strftime('%Y-%m-%d')}
        )
    except Exception as e:
        logger.error(f"清理通知历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))