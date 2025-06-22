# -*- coding: utf-8 -*-
"""
系统级API模块
包含健康检查、状态监控等系统级功能
"""

from fastapi import APIRouter
from .health import router as health_router
from .status import router as status_router
from .monitoring import router as monitoring_router

# 创建系统级路由器
router = APIRouter()

# 注册子路由
router.include_router(health_router)
router.include_router(status_router)
router.include_router(monitoring_router)
__all__ = ["system_router"]