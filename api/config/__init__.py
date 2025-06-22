# -*- coding: utf-8 -*-
"""
配置管理API模块
包含系统配置、数据库配置、交易配置等配置管理功能
"""

from fastapi import APIRouter
from .database import router as database_router
from .trading import router as trading_router
from .notification import router as notification_router
from .xtquant import router as xtquant_router

# 创建配置管理路由器
router = APIRouter()

# 注册子路由
router.include_router(database_router)
router.include_router(trading_router)
router.include_router(notification_router)
router.include_router(xtquant_router)

# 导出路由器
__all__ = ["config_router"]