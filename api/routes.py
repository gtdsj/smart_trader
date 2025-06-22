# -*- coding: utf-8 -*-
"""
主路由模块
整合所有API路由
"""

from fastapi import APIRouter
from .system import router as system_router
from .config import router as config_router
from .business import router as business_router

# 创建主路由器
router = APIRouter()

# 注册系统级API路由 (/api/)
router.include_router(system_router, prefix="", tags=["系统API"])

# 注册配置管理API路由 (/api/config)
router.include_router(config_router, prefix="/config", tags=["配置管理"])

# 注册业务API路由 (/api/v1)
router.include_router(business_router, prefix="/v1", tags=["业务API v1"])

# 路由信息
ROUTE_INFO = {
    "system": {
        "prefix": "/api",
        "description": "系统级API，包括状态检查、健康检查等",
        "endpoints": [
            "/status",
            "/health",
            "/info"
        ]
    },
    "config": {
        "prefix": "/api/config",
        "description": "配置管理API",
        "endpoints": [
            "/database",
            "/trading",
            "/notification",
            "/xtquant"
        ]
    },
    "v1": {
        "prefix": "/api/v1",
        "description": "版本1业务API",
        "modules": {
            "trading": {
                "prefix": "/trading",
                "description": "交易相关API",
                "endpoints": [
                    "/orders",
                    "/positions",
                    "/account",
                    "/balance"
                ]
            },
            "data": {
                "prefix": "/data",
                "description": "数据相关API",
                "endpoints": [
                    "/stocks",
                    "/realtime",
                    "/historical",
                    "/market"
                ]
            },
            "strategy": {
                "prefix": "/strategy",
                "description": "策略相关API",
                "endpoints": [
                    "/list",
                    "/create",
                    "/run",
                    "/signals"
                ]
            },
            "backtest": {
                "prefix": "/backtest",
                "description": "回测相关API",
                "endpoints": [
                    "/create",
                    "/run",
                    "/results",
                    "/reports"
                ]
            },
            "notification": {
                "prefix": "/notification",
                "description": "通知相关API",
                "endpoints": [
                    "/send",
                    "/history",
                    "/settings"
                ]
            }
        }
    }
}

def get_route_info():
    """获取路由信息"""
    return ROUTE_INFO