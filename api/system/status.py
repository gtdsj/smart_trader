# -*- coding: utf-8 -*-
"""
系统状态API
提供系统运行状态和基本信息
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Dict, Any

from config_simple import get_settings
from core.local_cache import get_cache
from core.duckdb_adapter import get_duckdb

# 创建状态路由器
router = APIRouter(prefix="/status", tags=["系统状态"])

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

@router.get("/", summary="系统状态", description="获取系统整体运行状态")
def get_system_status():
    """获取系统状态"""
    try:
        cache = get_cache()
        db = get_duckdb()
        
        status = {
            "app_name": settings.app_name,
            "version": settings.version,
            "status": "running",
            "cache_status": "active" if cache else "inactive",
            "database_status": "connected" if db else "disconnected",
            "timestamp": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="系统运行正常",
            data=status
        ).to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/info", summary="系统信息", description="获取系统详细信息")
def get_system_info():
    """获取系统信息"""
    try:
        info = {
            "application": {
                "name": settings.app_name,
                "version": settings.version,
                "description": "智能量化交易系统",
                "framework": "FastAPI",
                "architecture": "模块化微服务"
            },
            "api": {
                "version": "v1",
                "base_url": "/api",
                "documentation": {
                    "swagger": "/docs",
                    "redoc": "/redoc"
                }
            },
            "modules": {
                "system": "系统管理模块",
                "business": "业务功能模块",
                "config": "配置管理模块"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="获取系统信息成功",
            data=info
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/version", summary="版本信息", description="获取系统版本信息")
def get_version_info():
    """获取版本信息"""
    try:
        version_info = {
            "version": settings.version,
            "build_date": "2024-01-01",  # 可以从构建时动态生成
            "git_commit": "N/A",  # 可以从Git信息获取
            "environment": "development" if settings.debug else "production"
        }
        
        return ApiResponse(
            message="获取版本信息成功",
            data=version_info
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/uptime", summary="运行时间", description="获取系统运行时间")
def get_uptime():
    """获取系统运行时间"""
    try:
        # 这里可以实现实际的运行时间计算
        uptime_info = {
            "start_time": "N/A",  # 可以记录实际启动时间
            "uptime_seconds": 0,  # 可以计算实际运行秒数
            "uptime_formatted": "N/A",  # 格式化的运行时间
            "current_time": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="获取运行时间成功",
            data=uptime_info
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))