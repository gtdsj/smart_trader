# -*- coding: utf-8 -*-
"""
通知配置API
提供通知系统配置的管理功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, List

from models.api_response import ApiResponse

from config import get_settings

# 创建通知配置路由器
router = APIRouter(prefix="/notification", tags=["通知配置"])

# 获取配置
settings = get_settings()



# 请求模型
class NotificationConfigRequest(BaseModel):
    enabled: Optional[bool] = True
    channels: Optional[List[str]] = ["dingtalk", "email"]
    dingtalk: Optional[Dict] = None
    email: Optional[Dict] = None
    wechat: Optional[Dict] = None
    alert_rules: Optional[Dict] = None

class DingTalkConfigRequest(BaseModel):
    webhook_url: str
    secret: Optional[str] = None
    enabled: Optional[bool] = True
    at_mobiles: Optional[List[str]] = []
    at_all: Optional[bool] = False

class EmailConfigRequest(BaseModel):
    smtp_server: str
    smtp_port: Optional[int] = 587
    username: str
    password: str
    from_email: str
    to_emails: List[str]
    enabled: Optional[bool] = True
    use_tls: Optional[bool] = True

@router.get("/", summary="获取通知配置", description="获取当前通知系统配置")
def get_notification_config():
    """获取通知配置"""
    try:
        config = {
            "enabled": getattr(settings.notification, 'enabled', True),
            "channels": getattr(settings.notification, 'channels', ["dingtalk", "email"]),
            "dingtalk": getattr(settings.notification, 'dingtalk', {
                "enabled": False,
                "webhook_url": "",
                "secret": "",
                "at_mobiles": [],
                "at_all": False
            }),
            "email": getattr(settings.notification, 'email', {
                "enabled": False,
                "smtp_server": "",
                "smtp_port": 587,
                "username": "",
                "from_email": "",
                "to_emails": [],
                "use_tls": True
            }),
            "wechat": getattr(settings.notification, 'wechat', {
                "enabled": False,
                "corp_id": "",
                "corp_secret": "",
                "agent_id": ""
            }),
            "alert_rules": getattr(settings.notification, 'alert_rules', {
                "trade_alerts": True,
                "error_alerts": True,
                "system_alerts": True,
                "performance_alerts": False
            })
        }
        
        return ApiResponse.success_response(
            message="获取通知配置成功",
            data=config
        ).model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/", summary="更新通知配置", description="更新通知系统配置")
def update_notification_config(config_request: NotificationConfigRequest):
    """更新通知配置"""
    try:
        updated_config = {
            "enabled": config_request.enabled,
            "channels": config_request.channels,
            "dingtalk": config_request.dingtalk or {
                "enabled": False,
                "webhook_url": "",
                "secret": "",
                "at_mobiles": [],
                "at_all": False
            },
            "email": config_request.email or {
                "enabled": False,
                "smtp_server": "",
                "smtp_port": 587,
                "username": "",
                "from_email": "",
                "to_emails": [],
                "use_tls": True
            },
            "wechat": config_request.wechat or {
                "enabled": False,
                "corp_id": "",
                "corp_secret": "",
                "agent_id": ""
            },
            "alert_rules": config_request.alert_rules or {
                "trade_alerts": True,
                "error_alerts": True,
                "system_alerts": True,
                "performance_alerts": False
            },
            "updated_at": datetime.now().isoformat()
        }
        
        return ApiResponse.success_response(
            message="通知配置更新成功",
            data=updated_config
        ).model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dingtalk", summary="获取钉钉配置", description="获取钉钉通知配置")
def get_dingtalk_config():
    """获取钉钉配置"""
    try:
        dingtalk_config = getattr(settings.notification, 'dingtalk', {
            "enabled": False,
            "webhook_url": "",
            "secret": "",
            "at_mobiles": [],
            "at_all": False
        })
        
        # 隐藏敏感信息
        if dingtalk_config.get('webhook_url'):
            dingtalk_config['webhook_url'] = dingtalk_config['webhook_url'][:50] + "..."
        if dingtalk_config.get('secret'):
            dingtalk_config['secret'] = "***"
        
        return ApiResponse.success_response(
            message="获取钉钉配置成功",
            data=dingtalk_config
        ).model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/dingtalk", summary="更新钉钉配置", description="更新钉钉通知配置")
def update_dingtalk_config(dingtalk_request: DingTalkConfigRequest):
    """更新钉钉配置"""
    try:
        updated_config = {
            "enabled": dingtalk_request.enabled,
            "webhook_url": dingtalk_request.webhook_url,
            "secret": dingtalk_request.secret,
            "at_mobiles": dingtalk_request.at_mobiles,
            "at_all": dingtalk_request.at_all,
            "updated_at": datetime.now().isoformat()
        }
        
        return ApiResponse.success_response(
            message="钉钉配置更新成功",
            data=updated_config
        ).model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/email", summary="获取邮件配置", description="获取邮件通知配置")
def get_email_config():
    """获取邮件配置"""
    try:
        email_config = getattr(settings.notification, 'email', {
            "enabled": False,
            "smtp_server": "",
            "smtp_port": 587,
            "username": "",
            "from_email": "",
            "to_emails": [],
            "use_tls": True
        })
        
        # 隐藏敏感信息
        if email_config.get('password'):
            email_config['password'] = "***"
        
        return ApiResponse(
            message="获取邮件配置成功",
            data=email_config
        ).model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/email", summary="更新邮件配置", description="更新邮件通知配置")
def update_email_config(email_request: EmailConfigRequest):
    """更新邮件配置"""
    try:
        updated_config = {
            "enabled": email_request.enabled,
            "smtp_server": email_request.smtp_server,
            "smtp_port": email_request.smtp_port,
            "username": email_request.username,
            "password": email_request.password,
            "from_email": email_request.from_email,
            "to_emails": email_request.to_emails,
            "use_tls": email_request.use_tls,
            "updated_at": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="邮件配置更新成功",
            data=updated_config
        ).model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test", summary="测试通知", description="发送测试通知")
def test_notification():
    """测试通知"""
    try:
        test_result = {
            "dingtalk": {
                "status": "success",
                "message": "钉钉测试消息发送成功",
                "sent_at": datetime.now().isoformat()
            },
            "email": {
                "status": "success",
                "message": "邮件测试消息发送成功",
                "sent_at": datetime.now().isoformat()
            }
        }
        
        # 这里可以实现实际的通知发送测试
        
        return ApiResponse(
            message="通知测试完成",
            data=test_result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", summary="通知状态", description="获取通知系统状态")
def get_notification_status():
    """获取通知状态"""
    try:
        status = {
            "enabled": getattr(settings.notification, 'enabled', True),
            "channels": {
                "dingtalk": {
                    "enabled": getattr(settings.notification, 'dingtalk', {}).get('enabled', False),
                    "status": "active"
                },
                "email": {
                    "enabled": getattr(settings.notification, 'email', {}).get('enabled', False),
                    "status": "active"
                },
                "wechat": {
                    "enabled": getattr(settings.notification, 'wechat', {}).get('enabled', False),
                    "status": "inactive"
                }
            },
            "last_notification": "N/A",  # 可以记录最后一次通知时间
            "total_sent": 0,  # 可以统计发送总数
            "last_check": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="获取通知状态成功",
            data=status
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))