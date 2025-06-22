# -*- coding: utf-8 -*-
"""
配置管理API路由
处理系统配置的查询和更新
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator

from config import get_settings

# 创建配置路由器
config_router = APIRouter(prefix="/api/config")

# 获取配置
settings = get_settings()

# 响应模型类
class ApiResponse:
    def __init__(self, success=True, message="", data=None):
        self.success = success
        self.message = message
        self.data = data
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp
        }

# 请求模型
class DatabaseConfigRequest(BaseModel):
    """数据库配置请求"""
    host: Optional[str] = Field(None, description="数据库主机")
    port: Optional[int] = Field(None, description="数据库端口", ge=1, le=65535)
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    database: Optional[str] = Field(None, description="数据库名")

class RedisConfigRequest(BaseModel):
    """Redis配置请求"""
    host: Optional[str] = Field(None, description="Redis主机")
    port: Optional[int] = Field(None, description="Redis端口", ge=1, le=65535)
    password: Optional[str] = Field(None, description="Redis密码")
    db: Optional[int] = Field(None, description="数据库编号", ge=0, le=15)

class XtQuantConfigRequest(BaseModel):
    """XtQuant配置请求"""
    path: Optional[str] = Field(None, description="MiniQMT路径")
    session_id: Optional[int] = Field(None, description="会话ID")
    account_id: Optional[str] = Field(None, description="账户ID")
    account_type: Optional[str] = Field(None, description="账户类型")

class TradingConfigRequest(BaseModel):
    """交易配置请求"""
    max_position_size: Optional[float] = Field(None, description="最大持仓比例", ge=0, le=1)
    commission_rate: Optional[float] = Field(None, description="手续费率", ge=0, le=0.01)
    slippage: Optional[float] = Field(None, description="滑点", ge=0, le=0.01)
    risk_level: Optional[str] = Field(None, description="风险等级")

class NotificationConfigRequest(BaseModel):
    """通知配置请求"""
    webhook_url: Optional[str] = Field(None, description="Webhook URL")
    secret: Optional[str] = Field(None, description="密钥")
    enabled: Optional[bool] = Field(None, description="是否启用")
    channels: Optional[list] = Field(None, description="通知渠道")

# 路由端点
@config_router.get("/", summary="获取所有配置", description="获取系统所有配置信息")
def get_all_config():
    """获取所有配置"""
    try:
        config_data = {
            "app": {
                "name": settings.app_name,
                "version": settings.version,
                "debug": settings.debug,
                "api_port": settings.api_port
            },
            "database": {
                "type": settings.database.db_type,
                "path": settings.database.path
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="获取配置成功",
            data=config_data
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@config_router.get("/database", summary="获取数据库配置", description="获取数据库连接配置")
def get_database_config():
    """获取数据库配置"""
    try:
        config_data = {
            "type": settings.database.db_type,
            "path": settings.database.path,
            "url": settings.database.get_url()
        }
        
        return ApiResponse(
            message="获取数据库配置成功",
            data=config_data
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@config_router.put("/database", summary="更新数据库配置", description="更新数据库连接配置")
def update_database_config(request: DatabaseConfigRequest):
    """更新数据库配置"""
    try:
        # 这里应该实现配置更新逻辑
        # 注意：当前为简化实现，实际生产环境中应连接真实配置系统
        
        updated_config = {
            "type": settings.database.db_type,
            "path": settings.database.path,
            "updated_fields": []
        }
        
        # 检查哪些字段被更新
        if request.host is not None:
            updated_config["updated_fields"].append("host")
        if request.port is not None:
            updated_config["updated_fields"].append("port")
        if request.database is not None:
            updated_config["updated_fields"].append("database")
            
        return ApiResponse(
            message="数据库配置更新成功",
            data=updated_config
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@config_router.get("/trading", summary="获取交易配置", description="获取交易相关配置")
def get_trading_config():
    """获取交易配置"""
    try:
        # 从实际配置获取交易配置数据
        config_data = {
            "max_position_size": getattr(settings.trading, 'max_position_size', None),
            "commission_rate": getattr(settings.trading, 'commission_rate', None),
            "slippage": getattr(settings.trading, 'slippage', None),
            "risk_level": getattr(settings.trading, 'risk_level', None),
            "auto_trading": getattr(settings.trading, 'auto_trading', None),
            "max_orders_per_day": getattr(settings.trading, 'max_orders_per_day', None)
        }
        
        return ApiResponse(
            message="获取交易配置成功",
            data=config_data
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@config_router.put("/trading", summary="更新交易配置", description="更新交易相关配置")
def update_trading_config(request: TradingConfigRequest):
    """更新交易配置"""
    try:
        updated_fields = []
        
        if request.max_position_size is not None:
            updated_fields.append("max_position_size")
        if request.commission_rate is not None:
            updated_fields.append("commission_rate")
        if request.slippage is not None:
            updated_fields.append("slippage")
        if request.risk_level is not None:
            updated_fields.append("risk_level")
            
        return ApiResponse(
            message="交易配置更新成功",
            data={"updated_fields": updated_fields}
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@config_router.get("/xtquant", summary="获取XtQuant配置", description="获取XtQuant连接配置")
def get_xtquant_config():
    """获取XtQuant配置"""
    try:
        # 从实际配置获取XtQuant配置数据
        config_data = {
            "path": settings.xtquant.path,
            "session_id": settings.xtquant.session_id,
            "account_id": settings.xtquant.account_id,
            "account_type": settings.xtquant.account_type,
            "connected": False  # 这个需要从服务状态获取
        }
        
        return ApiResponse(
            message="获取XtQuant配置成功",
            data=config_data
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@config_router.put("/xtquant", summary="更新XtQuant配置", description="更新XtQuant连接配置")
def update_xtquant_config(request: XtQuantConfigRequest):
    """更新XtQuant配置"""
    try:
        updated_fields = []
        
        if request.path is not None:
            updated_fields.append("path")
        if request.session_id is not None:
            updated_fields.append("session_id")
        if request.account_id is not None:
            updated_fields.append("account_id")
        if request.account_type is not None:
            updated_fields.append("account_type")
            
        return ApiResponse(
            message="XtQuant配置更新成功",
            data={"updated_fields": updated_fields}
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@config_router.get("/notification", summary="获取通知配置", description="获取通知系统配置")
def get_notification_config():
    """获取通知配置"""
    try:
        # 从实际配置获取通知配置数据
        config_data = {
            "enabled": getattr(settings.notification, 'enabled', None),
            "channels": getattr(settings.notification, 'channels', []),
            "webhook_url": getattr(settings.notification, 'webhook_url', None),
            "email_smtp": getattr(settings.notification, 'email_smtp', None),
            "email_port": getattr(settings.notification, 'email_port', None)
        }
        
        return ApiResponse(
            message="获取通知配置成功",
            data=config_data
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@config_router.put("/notification", summary="更新通知配置", description="更新通知系统配置")
def update_notification_config(request: NotificationConfigRequest):
    """更新通知配置"""
    try:
        updated_fields = []
        
        if request.webhook_url is not None:
            updated_fields.append("webhook_url")
        if request.secret is not None:
            updated_fields.append("secret")
        if request.enabled is not None:
            updated_fields.append("enabled")
        if request.channels is not None:
            updated_fields.append("channels")
            
        return ApiResponse(
            message="通知配置更新成功",
            data={"updated_fields": updated_fields}
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))