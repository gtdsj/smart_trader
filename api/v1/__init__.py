# -*- coding: utf-8 -*-
"""
API v1版本路由模块 (已废弃)
此文件保留用于向后兼容，新的业务API已迁移到 api.business 模块
"""

from fastapi import APIRouter

# 创建空的v1版本路由器用于向后兼容
api_router = APIRouter()

# 注意：此模块已废弃，新的业务API请使用 api.business 模块

# API模块信息
API_MODULES = {
    "trading": {
        "name": "交易服务",
        "description": "提供股票交易、订单管理、持仓查询等功能",
        "prefix": "/api/v1/trading",
        "version": "1.0.0"
    },
    "data": {
        "name": "数据服务",
        "description": "提供股票数据、实时行情、历史数据等功能",
        "prefix": "/api/v1/data",
        "version": "1.0.0"
    },
    "strategy": {
        "name": "策略服务",
        "description": "提供策略管理、信号生成、策略回测等功能",
        "prefix": "/api/v1/strategy",
        "version": "1.0.0"
    },
    "backtest": {
        "name": "回测服务",
        "description": "提供策略回测、性能分析、报告生成等功能",
        "prefix": "/api/v1/backtest",
        "version": "1.0.0"
    },
    "notification": {
        "name": "通知服务",
        "description": "提供消息推送、通知管理、告警设置等功能",
        "prefix": "/api/v1/notification",
        "version": "1.0.0"
    }
}

def get_api_modules():
    """获取API模块信息"""
    return API_MODULES