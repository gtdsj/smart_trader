# -*- coding: utf-8 -*-
"""
系统级API路由
处理系统状态、健康检查、基础信息等
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Dict, Any

from config import get_settings
from core.local_cache import get_cache
from core.duckdb_adapter import get_duckdb
from models.api_response import ApiResponse

# 创建系统路由器
system_router = APIRouter(prefix="/api")

# 获取配置
settings = get_settings()

@system_router.get("/", summary="根路径", description="API服务根路径，返回基本信息")
def root():
    """根路径"""
    return ApiResponse.success_response(
        message="欢迎使用 {} v{}".format(settings.app_name, settings.version),
        data={
            "app_name": settings.app_name,
            "version": settings.version,
            "docs": "/docs",
            "redoc": "/redoc",
            "api_prefix": "/api"
        }
    ).model_dump()

@system_router.get("/status", summary="系统状态", description="获取系统运行状态")
def get_status():
    """获取系统状态"""
    try:
        cache = get_cache()
        db = get_duckdb()
        
        status = {
            "app_name": settings.app_name,
            "version": settings.version,
            "status": "running",
            "cache_status": "active",
            "database_status": "connected",
            "timestamp": datetime.now().isoformat()
        }
        
        return ApiResponse.success_response(
            message="系统运行正常",
            data=status
        ).model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@system_router.get("/health", summary="健康检查", description="系统健康检查接口")
def health_check():
    """健康检查"""
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
            
        return ApiResponse.success_response(
            message="系统健康",
            data=health_data
        ).model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })

@system_router.get("/info", summary="系统信息", description="获取系统详细信息")
def get_info():
    """获取系统信息"""
    try:
        info = {
            "application": {
                "name": settings.app_name,
                "version": settings.version,
                "description": "智能量化交易系统",
                "framework": "FastAPI"
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
                "trading": "交易模块",
                "data": "数据模块", 
                "strategy": "策略模块",
                "backtest": "回测模块",
                "notification": "通知模块",
                "config": "配置模块"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return ApiResponse.success_response(
            message="获取系统信息成功",
            data=info
        ).model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@system_router.get("/cache/info", summary="缓存信息", description="获取缓存系统信息")
def get_cache_info():
    """获取缓存信息"""
    try:
        cache = get_cache()
        
        # 获取缓存统计信息
        info = {
            "type": "local_cache",
            "status": "active",
            "stats": {
                "total_keys": len(cache._cache) if hasattr(cache, '_cache') else 0,
                "memory_usage": "N/A"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return ApiResponse.success_response(
            message="获取缓存信息成功",
            data=info
        ).model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@system_router.delete("/cache/clear", summary="清空缓存", description="清空所有缓存数据")
def clear_cache():
    """清空缓存"""
    try:
        cache = get_cache()
        cache.clear()
        
        return ApiResponse.success_response(
            message="缓存清空成功"
        ).model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@system_router.get("/database/info", summary="数据库信息", description="获取数据库连接信息")
def get_database_info():
    """获取数据库信息"""
    try:
        db = get_duckdb()
        
        # 获取数据库信息
        info = {
            "type": "DuckDB",
            "status": "connected",
            "path": settings.database.path,
            "tables": [],  # 可以查询实际表信息
            "timestamp": datetime.now().isoformat()
        }
        
        return ApiResponse.success_response(
            message="获取数据库信息成功",
            data=info
        ).model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))