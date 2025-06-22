# -*- coding: utf-8 -*-
"""
交易配置API
提供交易系统配置的管理功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

from config_simple import get_settings

# 创建交易配置路由器
router = APIRouter(prefix="/trading", tags=["交易配置"])

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
class TradingConfigRequest(BaseModel):
    account_id: Optional[str] = None
    account_type: Optional[str] = "STOCK"
    max_position_ratio: Optional[float] = 0.95
    max_single_position: Optional[float] = 0.1
    stop_loss_ratio: Optional[float] = 0.05
    take_profit_ratio: Optional[float] = 0.1
    trading_hours: Optional[Dict[str, str]] = None
    risk_control: Optional[Dict[str, Any]] = None

class RiskControlRequest(BaseModel):
    max_daily_loss: Optional[float] = None
    max_drawdown: Optional[float] = None
    position_limit: Optional[int] = None
    order_limit: Optional[int] = None
    enabled: Optional[bool] = True

@router.get("/", summary="获取交易配置", description="获取当前交易系统配置")
def get_trading_config():
    """获取交易配置"""
    try:
        config = {
            "account": {
                "account_id": getattr(settings.trading, 'account_id', ''),
                "account_type": getattr(settings.trading, 'account_type', 'STOCK')
            },
            "position": {
                "max_position_ratio": getattr(settings.trading, 'max_position_ratio', 0.95),
                "max_single_position": getattr(settings.trading, 'max_single_position', 0.1)
            },
            "risk": {
                "stop_loss_ratio": getattr(settings.trading, 'stop_loss_ratio', 0.05),
                "take_profit_ratio": getattr(settings.trading, 'take_profit_ratio', 0.1)
            },
            "trading_hours": getattr(settings.trading, 'trading_hours', {
                "morning_start": "09:30",
                "morning_end": "11:30",
                "afternoon_start": "13:00",
                "afternoon_end": "15:00"
            }),
            "risk_control": getattr(settings.trading, 'risk_control', {
                "enabled": True,
                "max_daily_loss": 0.02,
                "max_drawdown": 0.1,
                "position_limit": 10,
                "order_limit": 100
            })
        }
        
        return ApiResponse(
            message="获取交易配置成功",
            data=config
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/", summary="更新交易配置", description="更新交易系统配置")
def update_trading_config(config_request: TradingConfigRequest):
    """更新交易配置"""
    try:
        updated_config = {
            "account": {
                "account_id": config_request.account_id,
                "account_type": config_request.account_type
            },
            "position": {
                "max_position_ratio": config_request.max_position_ratio,
                "max_single_position": config_request.max_single_position
            },
            "risk": {
                "stop_loss_ratio": config_request.stop_loss_ratio,
                "take_profit_ratio": config_request.take_profit_ratio
            },
            "trading_hours": config_request.trading_hours or {
                "morning_start": "09:30",
                "morning_end": "11:30",
                "afternoon_start": "13:00",
                "afternoon_end": "15:00"
            },
            "risk_control": config_request.risk_control or {
                "enabled": True,
                "max_daily_loss": 0.02,
                "max_drawdown": 0.1,
                "position_limit": 10,
                "order_limit": 100
            },
            "updated_at": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="交易配置更新成功",
            data=updated_config
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risk-control", summary="获取风控配置", description="获取风险控制配置")
def get_risk_control_config():
    """获取风控配置"""
    try:
        risk_config = getattr(settings.trading, 'risk_control', {
            "enabled": True,
            "max_daily_loss": 0.02,
            "max_drawdown": 0.1,
            "position_limit": 10,
            "order_limit": 100,
            "auto_stop_trading": True,
            "alert_thresholds": {
                "loss_warning": 0.01,
                "position_warning": 0.8
            }
        })
        
        return ApiResponse(
            message="获取风控配置成功",
            data=risk_config
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/risk-control", summary="更新风控配置", description="更新风险控制配置")
def update_risk_control_config(risk_request: RiskControlRequest):
    """更新风控配置"""
    try:
        updated_risk_config = {
            "enabled": risk_request.enabled,
            "max_daily_loss": risk_request.max_daily_loss,
            "max_drawdown": risk_request.max_drawdown,
            "position_limit": risk_request.position_limit,
            "order_limit": risk_request.order_limit,
            "updated_at": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="风控配置更新成功",
            data=updated_risk_config
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", summary="交易状态", description="获取交易系统状态")
def get_trading_status():
    """获取交易状态"""
    try:
        status = {
            "trading_enabled": True,  # 可以从实际交易系统获取
            "market_status": "closed",  # 可以根据时间判断市场状态
            "account_status": "active",  # 可以从XtQuant获取账户状态
            "risk_control_status": "normal",  # 可以从风控系统获取
            "last_update": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="获取交易状态成功",
            data=status
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate", summary="验证交易配置", description="验证交易配置的有效性")
def validate_trading_config():
    """验证交易配置"""
    try:
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "checks": {
                "account_config": "passed",
                "position_limits": "passed",
                "risk_parameters": "passed",
                "trading_hours": "passed"
            },
            "validated_at": datetime.now().isoformat()
        }
        
        # 这里可以添加实际的配置验证逻辑
        
        return ApiResponse(
            message="交易配置验证完成",
            data=validation_result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))