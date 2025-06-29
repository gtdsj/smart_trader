# -*- coding: utf-8 -*-
"""
系统监控API
提供系统性能监控、资源使用情况等功能
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Dict, Any
import psutil
import os
import logging
import traceback

logger = logging.getLogger(__name__)

from config import get_settings
from core.local_cache import get_cache
from core.duckdb_adapter import get_duckdb

# 创建监控路由器
router = APIRouter(prefix="/monitoring", tags=["系统监控"])

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

@router.get("/", summary="系统监控概览", description="获取系统监控概览信息")
def get_monitoring_overview():
    """获取系统监控概览"""
    try:
        # 获取基本系统信息
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        overview = {
            "system": {
                "cpu_usage": cpu_percent,
                "memory_usage": {
                    "total": memory.total,
                    "used": memory.used,
                    "available": memory.available,
                    "percent": memory.percent
                },
                "disk_usage": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                }
            },
            "process": {
                "pid": os.getpid(),
                "memory_info": dict(psutil.Process().memory_info()._asdict()),
                "cpu_percent": psutil.Process().cpu_percent()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="获取监控概览成功",
            data=overview
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cache", summary="缓存监控", description="获取缓存系统监控信息")
def get_cache_monitoring():
    """获取缓存监控信息"""
    try:
        cache = get_cache()
        
        if cache is None:
            raise HTTPException(status_code=503, detail="缓存服务不可用")
        
        # 获取缓存统计信息
        cache_info = {
            "type": "local_cache",
            "status": "active",
            "stats": {
                "total_keys": len(cache._cache) if hasattr(cache, '_cache') else 0,
                "memory_usage": "N/A",  # 可以实现实际内存使用计算
                "hit_rate": "N/A",  # 可以实现缓存命中率统计
                "miss_rate": "N/A"  # 可以实现缓存未命中率统计
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="获取缓存监控信息成功",
            data=cache_info
        ).to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/database", summary="数据库监控", description="获取数据库监控信息")
def get_database_monitoring():
    """获取数据库监控信息"""
    try:
        db = get_duckdb()
        
        if db is None:
            raise HTTPException(status_code=503, detail="数据库连接不可用")
        
        # 获取数据库信息
        db_info = {
            "type": "DuckDB",
            "status": "connected",
            "path": settings.database.path,
            "stats": {
                "tables": [],  # 可以查询实际表信息
                "size": "N/A",  # 可以获取数据库文件大小
                "connections": 1  # DuckDB是嵌入式数据库
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="获取数据库监控信息成功",
            data=db_info
        ).to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance", summary="性能监控", description="获取系统性能指标")
def get_performance_metrics():
    """获取性能指标"""
    try:
        # 获取详细的性能指标
        process = psutil.Process()
        
        performance = {
            "cpu": {
                "system_usage": psutil.cpu_percent(interval=1),
                "process_usage": process.cpu_percent(),
                "cpu_count": psutil.cpu_count(),
                "cpu_freq": dict(psutil.cpu_freq()._asdict()) if psutil.cpu_freq() else None
            },
            "memory": {
                "system": dict(psutil.virtual_memory()._asdict()),
                "process": dict(process.memory_info()._asdict()),
                "process_percent": process.memory_percent()
            },
            "io": {
                "disk_io": dict(psutil.disk_io_counters()._asdict()) if psutil.disk_io_counters() else None,
                "network_io": dict(psutil.net_io_counters()._asdict()) if psutil.net_io_counters() else None
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="获取性能指标成功",
            data=performance
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cache/clear", summary="清空缓存", description="清空所有缓存数据")
def clear_cache():
    """清空缓存"""
    try:
        cache = get_cache()
        
        if cache is None:
            raise HTTPException(status_code=503, detail="缓存服务不可用")
        
        cache.clear()
        
        return ApiResponse(
            message="缓存清空成功",
            data={"cleared_at": datetime.now().isoformat()}
        ).to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))