# -*- coding: utf-8 -*-
"""
业务API模块
包含交易、数据、策略、回测、通知等业务功能
"""

from fastapi import APIRouter
from .trading import router as trading_router
from .data import router as data_router
from .strategy import router as strategy_router
from .backtest import router as backtest_router
from .notification import router as notification_router

# 创建业务API路由器
router = APIRouter()

# 注册子路由
router.include_router(trading_router)
router.include_router(data_router)
router.include_router(strategy_router)
router.include_router(backtest_router)
router.include_router(notification_router)

# 导出路由器
__all__ = ["business_router"]