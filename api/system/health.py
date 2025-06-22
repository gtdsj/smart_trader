# -*- coding: utf-8 -*-
"""
系统健康检查API
提供系统健康状态监控和检查功能
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Dict, Any

from config_simple import get_settings
from core.local_cache import get_cache
from core.duckdb_adapter import get_duckdb

# 创建健康检查路由器
router = APIRouter(prefix="/health", tags=["系统健康"])

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

@router.get("/", summary="健康检查", description="系统整体健康检查")
def health_check():
    """系统健康检查"""
    try:
        # 检查缓存
        cache = get_cache()
        cache_healthy = cache is not None
        
        # 检查数据库
        db = get_duckdb()
        db_healthy = db is not None
        
        # 整体健康状态
        overall_healthy = cache_healthy and db_healthy
        
        health_data = {
            "status": "healthy" if overall_healthy else "unhealthy",
            "components": {
                "cache": "up" if cache_healthy else "down",
                "database": "up" if db_healthy else "down"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        status_code = 200 if overall_healthy else 503
        
        if not overall_healthy:
            raise HTTPException(status_code=status_code, detail=health_data)
            
        return ApiResponse(
            message="系统健康",
            data=health_data
        ).to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })

@router.get("/cache", summary="缓存健康检查", description="检查缓存系统状态")
def cache_health():
    """缓存健康检查"""
    try:
        cache = get_cache()
        
        if cache is None:
            raise HTTPException(status_code=503, detail={
                "status": "unhealthy",
                "component": "cache",
                "error": "缓存服务不可用"
            })
        
        health_data = {
            "status": "healthy",
            "component": "cache",
            "details": {
                "type": "local_cache",
                "total_keys": len(cache._cache) if hasattr(cache, '_cache') else 0
            }
        }
        
        return ApiResponse(
            message="缓存系统健康",
            data=health_data
        ).to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/database", summary="数据库健康检查", description="检查数据库连接状态")
def database_health():
    """数据库健康检查"""
    try:
        db = get_duckdb()
        
        if db is None:
            raise HTTPException(status_code=503, detail={
                "status": "unhealthy",
                "component": "database",
                "error": "数据库连接不可用"
            })
        
        health_data = {
            "status": "healthy",
            "component": "database",
            "details": {
                "type": "DuckDB",
                "path": settings.database.path
            }
        }
        
        return ApiResponse(
            message="数据库连接健康",
            data=health_data
        ).to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/readiness", summary="就绪检查", description="检查系统是否准备好接收请求")
def readiness_check():
    """就绪检查"""
    try:
        # 检查所有必要组件
        cache = get_cache()
        db = get_duckdb()
        
        ready = cache is not None and db is not None
        
        readiness_data = {
            "ready": ready,
            "components": {
                "cache": cache is not None,
                "database": db is not None
            }
        }
        
        if not ready:
            raise HTTPException(status_code=503, detail=readiness_data)
            
        return ApiResponse(
            message="系统已就绪",
            data=readiness_data
        ).to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/liveness", summary="存活检查", description="检查系统是否存活")
def liveness_check():
    """存活检查"""
    try:
        # 简单的存活检查
        liveness_data = {
            "alive": True,
            "uptime": "N/A",  # 可以添加实际的运行时间计算
            "timestamp": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="系统存活",
            data=liveness_data
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))