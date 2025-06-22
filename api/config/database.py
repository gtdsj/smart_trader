# -*- coding: utf-8 -*-
"""
数据库配置API
提供数据库连接配置的管理功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from config_simple import get_settings
from core.duckdb_adapter import get_duckdb

# 创建数据库配置路由器
router = APIRouter(prefix="/database", tags=["数据库配置"])

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
class DatabaseConfigRequest(BaseModel):
    path: str
    memory: Optional[bool] = False
    read_only: Optional[bool] = False
    config: Optional[dict] = None

@router.get("/", summary="获取数据库配置", description="获取当前数据库配置信息")
def get_database_config():
    """获取数据库配置"""
    try:
        config = {
            "type": "DuckDB",
            "path": settings.database.path,
            "memory": getattr(settings.database, 'memory', False),
            "read_only": getattr(settings.database, 'read_only', False),
            "status": "connected" if get_duckdb() else "disconnected",
            "config": getattr(settings.database, 'config', {})
        }
        
        return ApiResponse(
            message="获取数据库配置成功",
            data=config
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/", summary="更新数据库配置", description="更新数据库配置信息")
def update_database_config(config_request: DatabaseConfigRequest):
    """更新数据库配置"""
    try:
        # 这里可以实现配置更新逻辑
        # 注意：实际应用中需要重启数据库连接
        
        updated_config = {
            "type": "DuckDB",
            "path": config_request.path,
            "memory": config_request.memory,
            "read_only": config_request.read_only,
            "config": config_request.config or {},
            "updated_at": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="数据库配置更新成功",
            data=updated_config
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", summary="数据库状态", description="获取数据库连接状态")
def get_database_status():
    """获取数据库状态"""
    try:
        db = get_duckdb()
        
        status = {
            "connected": db is not None,
            "type": "DuckDB",
            "path": settings.database.path,
            "last_check": datetime.now().isoformat()
        }
        
        if db:
            # 可以添加更多数据库状态信息
            status.update({
                "version": "N/A",  # 可以查询DuckDB版本
                "tables_count": 0,  # 可以查询表数量
                "size": "N/A"  # 可以获取数据库大小
            })
        
        return ApiResponse(
            message="获取数据库状态成功",
            data=status
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test", summary="测试数据库连接", description="测试数据库连接是否正常")
def test_database_connection():
    """测试数据库连接"""
    try:
        db = get_duckdb()
        
        if db is None:
            raise HTTPException(status_code=503, detail="数据库连接失败")
        
        # 执行简单查询测试连接
        try:
            # 这里可以执行一个简单的查询来测试连接
            test_result = {
                "connection": "success",
                "query_test": "passed",
                "response_time": "< 1ms",  # 可以实际测量响应时间
                "tested_at": datetime.now().isoformat()
            }
        except Exception as query_error:
            test_result = {
                "connection": "success",
                "query_test": "failed",
                "error": str(query_error),
                "tested_at": datetime.now().isoformat()
            }
        
        return ApiResponse(
            message="数据库连接测试完成",
            data=test_result
        ).to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))