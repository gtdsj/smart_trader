#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Trader FastAPI应用
基于FastAPI框架的量化交易系统API服务
简化版本，不依赖pydantic高级特性
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Optional, Dict, Any
import uvicorn

# 导入配置和核心模块
from config_simple import get_settings
from core.local_cache import get_cache, init_cache
from core.duckdb_adapter import get_duckdb, init_duckdb

# 简单的日志函数
def log_info(msg):
    print("[INFO] {}".format(msg))

def log_error(msg):
    print("[ERROR] {}".format(msg))

def log_warning(msg):
    print("[WARNING] {}".format(msg))

# 获取配置
settings = get_settings()

# 创建FastAPI应用
app = FastAPI(
    title="Smart Trader API",
    description="智能量化交易系统API",
    version=settings.version
)

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

@app.get("/")
def root():
    """根路径"""
    return ApiResponse(
        message="欢迎使用 {} v{}".format(settings.app_name, settings.version),
        data={
            "app_name": settings.app_name,
            "version": settings.version,
            "docs": "/docs",
            "redoc": "/redoc"
        }
    ).to_dict()

@app.get("/api/status")
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
        
        return ApiResponse(
            message="系统运行正常",
            data=status
        ).to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/account")
def get_account():
    """获取账户信息"""
    try:
        # 先从缓存获取
        cache = get_cache()
        cache_key = "account_info"
        cached_data = cache.get_json(cache_key)
        
        if cached_data:
            cached_data["source"] = "cache"
            return ApiResponse(
                message="获取账户信息成功",
                data=cached_data
            ).to_dict()
        
        # 从数据库或XtQuant获取（这里先返回模拟数据）
        account_info = {
            "account_id": "demo_account",
            "cash": 100000.0,
            "market_value": 52500.0,
            "total_asset": 152500.0,
            "available_cash": 95000.0,
            "frozen_cash": 5000.0,
            "profit_loss": 1300.0,
            "profit_loss_ratio": 0.86,
            "status": "connected",
            "source": "database",
            "timestamp": datetime.now().isoformat()
        }
        
        # 缓存数据（1分钟过期）
        cache.set_json(cache_key, account_info, expire=60)
        
        return ApiResponse(
            message="获取账户信息成功",
            data=account_info
        ).to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock/{stock_code}")
def get_stock_data(stock_code: str):
    """获取股票数据"""
    try:
        # 先从缓存获取
        cache = get_cache()
        cache_key = "stock_data:{}".format(stock_code)
        cached_data = cache.get_json(cache_key)
        
        if cached_data:
            return ApiResponse(
                message="获取股票数据成功",
                data=cached_data
            ).to_dict()
        
        # 从数据库查询（这里先返回模拟数据）
        stock_data = {
            "stock_code": stock_code,
            "name": "股票{}".format(stock_code),
            "price": 10.50,
            "change": 0.25,
            "change_percent": 2.44,
            "volume": 1000000,
            "turnover": 10500000.0,
            "high": 10.80,
            "low": 10.20,
            "open": 10.25,
            "prev_close": 10.25,
            "timestamp": datetime.now().isoformat(),
            "source": "database"
        }
        
        # 缓存数据（5分钟过期）
        cache.set_json(cache_key, stock_data, expire=300)
        
        return ApiResponse(
            message="获取股票数据成功",
            data=stock_data
        ).to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/positions")
def get_positions():
    """获取当前持仓"""
    try:
        # 先从缓存获取
        cache = get_cache()
        cache_key = "positions"
        cached_data = cache.get_json(cache_key)
        
        if cached_data:
            cached_data["source"] = "cache"
            return ApiResponse(
                message="获取持仓信息成功",
                data=cached_data
            ).to_dict()
        
        # 从数据库或XtQuant获取（这里先返回模拟数据）
        positions = {
            "total_positions": 3,
            "total_market_value": 52500.0,
            "total_cost": 51200.0,
            "total_profit_loss": 1300.0,
            "total_profit_loss_ratio": 2.54,
            "positions": [
                {
                    "stock_code": "600000.SH",
                    "stock_name": "浦发银行",
                    "quantity": 1000,
                    "available_quantity": 1000,
                    "avg_cost": 10.50,
                    "current_price": 10.75,
                    "market_value": 10750.0,
                    "cost_value": 10500.0,
                    "profit_loss": 250.0,
                    "profit_loss_ratio": 2.38,
                    "position_ratio": 20.48
                },
                {
                    "stock_code": "000001.SZ",
                    "stock_name": "平安银行",
                    "quantity": 2000,
                    "available_quantity": 2000,
                    "avg_cost": 12.30,
                    "current_price": 12.60,
                    "market_value": 25200.0,
                    "cost_value": 24600.0,
                    "profit_loss": 600.0,
                    "profit_loss_ratio": 2.44,
                    "position_ratio": 48.00
                },
                {
                    "stock_code": "002415.SZ",
                    "stock_name": "海康威视",
                    "quantity": 500,
                    "available_quantity": 500,
                    "avg_cost": 32.20,
                    "current_price": 33.10,
                    "market_value": 16550.0,
                    "cost_value": 16100.0,
                    "profit_loss": 450.0,
                    "profit_loss_ratio": 2.80,
                    "position_ratio": 31.52
                }
            ],
            "source": "database",
            "timestamp": datetime.now().isoformat()
        }
        
        # 缓存数据（30秒过期）
        cache.set_json(cache_key, positions, expire=30)
        
        return ApiResponse(
            message="获取持仓信息成功",
            data=positions
        ).to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/positions/{stock_code}")
def get_position(stock_code: str):
    """获取指定股票的持仓"""
    try:
        # 先从缓存获取
        cache = get_cache()
        cache_key = "position:{}".format(stock_code)
        cached_data = cache.get_json(cache_key)
        
        if cached_data:
            cached_data["source"] = "cache"
            return ApiResponse(
                message="获取持仓信息成功",
                data=cached_data
            ).to_dict()
        
        # 模拟数据 - 根据股票代码返回对应持仓
        positions_data = {
            "600000.SH": {
                "stock_code": "600000.SH",
                "stock_name": "浦发银行",
                "quantity": 1000,
                "available_quantity": 1000,
                "avg_cost": 10.50,
                "current_price": 10.75,
                "market_value": 10750.0,
                "cost_value": 10500.0,
                "profit_loss": 250.0,
                "profit_loss_ratio": 2.38,
                "position_ratio": 20.48
            },
            "000001.SZ": {
                "stock_code": "000001.SZ",
                "stock_name": "平安银行",
                "quantity": 2000,
                "available_quantity": 2000,
                "avg_cost": 12.30,
                "current_price": 12.60,
                "market_value": 25200.0,
                "cost_value": 24600.0,
                "profit_loss": 600.0,
                "profit_loss_ratio": 2.44,
                "position_ratio": 48.00
            },
            "002415.SZ": {
                "stock_code": "002415.SZ",
                "stock_name": "海康威视",
                "quantity": 500,
                "available_quantity": 500,
                "avg_cost": 32.20,
                "current_price": 33.10,
                "market_value": 16550.0,
                "cost_value": 16100.0,
                "profit_loss": 450.0,
                "profit_loss_ratio": 2.80,
                "position_ratio": 31.52
            }
        }
        
        position = positions_data.get(stock_code)
        if position:
            position["source"] = "database"
            position["timestamp"] = datetime.now().isoformat()
            
            # 缓存数据（30秒过期）
            cache.set_json(cache_key, position, expire=30)
            
            return ApiResponse(
                message="获取持仓信息成功",
                data=position
            ).to_dict()
        else:
            return ApiResponse(
                success=False,
                message="未找到股票 {} 的持仓".format(stock_code),
                data={
                    "stock_code": stock_code,
                    "quantity": 0,
                    "timestamp": datetime.now().isoformat()
                }
            ).to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config")
def get_config():
    """获取系统配置"""
    config = {
        "app_name": settings.app_name,
        "version": settings.version,
        "debug": settings.debug,
        "api_port": settings.api_port,
        "database": {
            "type": settings.database.type,
            "path": settings.database.path,
            "memory": settings.database.memory
        },
        "trading": {
            "max_position_ratio": settings.trading.max_position_ratio,
            "stop_loss_ratio": settings.trading.stop_loss_ratio,
            "take_profit_ratio": settings.trading.take_profit_ratio
        }
    }
    return ApiResponse(
        message="获取配置信息成功",
        data=config
    ).to_dict()

@app.get("/api/cache/info")
def get_cache_info():
    """获取缓存信息"""
    try:
        cache = get_cache()
        cache_info = cache.info()
        cache_info['status'] = 'active'
        return ApiResponse(
            message="获取缓存信息成功",
            data=cache_info
        ).to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cache/clear")
def clear_cache():
    """清空缓存"""
    try:
        cache = get_cache()
        cache.clear()
        return ApiResponse(
            message="缓存已清空",
            data={"status": "success"}
        ).to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/database/info")
def get_database_info():
    """获取数据库信息"""
    try:
        db = get_duckdb()
        # 获取数据库基本信息
        info = {
            "type": "DuckDB",
            "path": settings.database.path if not settings.database.memory else ":memory:",
            "memory": settings.database.memory,
            "status": "connected"
        }
        return ApiResponse(
            message="获取数据库信息成功",
            data=info
        ).to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 启动事件
@app.on_event("startup")
def startup_event():
    """应用启动时初始化服务"""
    try:
        log_info("Smart Trader FastAPI服务启动中...")
        log_info("应用名称: {}".format(settings.app_name))
        log_info("版本: {}".format(settings.version))
        
        log_info("初始化本地缓存...")
        init_cache()
        
        log_info("初始化DuckDB数据库...")
        init_duckdb()
        
        log_info("所有服务初始化完成")
    except Exception as e:
        log_error("服务初始化失败: {}".format(e))
        raise

# 关闭事件
@app.on_event("shutdown")
def shutdown_event():
    """应用关闭时清理资源"""
    log_info("Smart Trader FastAPI服务正在关闭...")

if __name__ == '__main__':
    print("Smart Trader FastAPI服务启动中...")
    print("应用名称: {}".format(settings.app_name))
    print("版本: {}".format(settings.version))
    print("访问地址: http://localhost:{}".format(settings.api_port))
    print("API文档: http://localhost:{}/docs".format(settings.api_port))
    print("ReDoc文档: http://localhost:{}/redoc".format(settings.api_port))
    print("API端点:")
    print("  - 系统状态: http://localhost:{}/api/status".format(settings.api_port))
    print("  - 配置信息: http://localhost:{}/api/config".format(settings.api_port))
    print("  - 缓存信息: http://localhost:{}/api/cache/info".format(settings.api_port))
    print("  - 数据库信息: http://localhost:{}/api/database/info".format(settings.api_port))
    print("  - 股票数据: http://localhost:{}/api/stock/<股票代码>".format(settings.api_port))
    print("  - 账户信息: http://localhost:{}/api/account".format(settings.api_port))
    print("  - 所有持仓: http://localhost:{}/api/positions".format(settings.api_port))
    print("  - 单个持仓: http://localhost:{}/api/positions/<股票代码>".format(settings.api_port))
    
    uvicorn.run(
        "main_fastapi:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=settings.debug,
        log_level="info"
    )