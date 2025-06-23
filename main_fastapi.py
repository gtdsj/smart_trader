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
from config import get_settings
from core.local_cache import get_cache, init_cache
from core.duckdb_adapter import get_duckdb, init_duckdb

# 导入业务API路由
from api.business.data import router as data_router
from api.business.trading import router as trading_router
from api.business.strategy import router as strategy_router
from api.business.notification import router as notification_router

# 导入独立的数据路由
from api.data_routes import router as data_routes_router

# 全局XtQuant服务实例
xtquant_service_instance = None

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

# 注册业务API路由
app.include_router(data_router, prefix="/api")
app.include_router(trading_router, prefix="/api")
app.include_router(strategy_router, prefix="/api")
app.include_router(notification_router, prefix="/api")

# 注册独立的数据路由（已包含/api/v1/data前缀）
app.include_router(data_routes_router)

# 注册v1版本路由（向后兼容）
app.include_router(data_router, prefix="/api/v1")
app.include_router(trading_router, prefix="/api/v1")
app.include_router(strategy_router, prefix="/api/v1")
app.include_router(notification_router, prefix="/api/v1")

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
async def get_account():
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
        
        # 从XtQuant获取真实账户资产
        try:
            global xtquant_service_instance
            if xtquant_service_instance is None:
                from services.xtquant_service import XtQuantService
                xtquant_service_instance = XtQuantService()
            
            # 获取账户资产信息
            account_data = await xtquant_service_instance.get_account_asset()
            
            if account_data:
                account_info = {
                    "account_id": get_settings().xtquant.account_id,
                    "cash": asset_data.get("cash", 0.0),
                    "market_value": asset_data.get("market_value", 0.0),
                    "total_asset": asset_data.get("total_asset", 0.0),
                    "available_cash": asset_data.get("available_cash", 0.0),
                    "frozen_cash": asset_data.get("frozen_cash", 0.0),
                    "profit_loss": asset_data.get("profit_loss", 0.0),
                    "profit_loss_ratio": asset_data.get("profit_loss_ratio", 0.0),
                    "status": "connected" if xtquant_service.is_trading_connected else "disconnected",
                    "source": "xtquant",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # 如果无法获取真实数据，返回基础信息
                account_info = {
                    "account_id": get_settings().xtquant.account_id,
                    "cash": 0.0,
                    "market_value": 0.0,
                    "total_asset": 0.0,
                    "available_cash": 0.0,
                    "frozen_cash": 0.0,
                    "profit_loss": 0.0,
                    "profit_loss_ratio": 0.0,
                    "status": "disconnected",
                    "source": "xtquant",
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            # 返回错误状态的账户信息
            account_info = {
                "account_id": get_settings().xtquant.account_id,
                "cash": 0.0,
                "market_value": 0.0,
                "total_asset": 0.0,
                "available_cash": 0.0,
                "frozen_cash": 0.0,
                "profit_loss": 0.0,
                "profit_loss_ratio": 0.0,
                "status": "error",
                "source": "xtquant",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
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
async def get_stock_data(stock_code: str):
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
        
        # 从XtQuant获取真实股票数据
        try:
            global xtquant_service_instance
            if xtquant_service_instance is None:
                from services.xtquant_service import XtQuantService
                xtquant_service_instance = XtQuantService()
            
            # 获取实时行情数据
            realtime_data = await xtquant_service_instance.get_realtime_data([stock_code])
            
            if stock_code in realtime_data:
                data = realtime_data[stock_code]
                stock_data = {
                    "stock_code": stock_code,
                    "name": data.get("name", f"股票{stock_code}"),
                    "price": data.get("last_price", 0.0),
                    "change": data.get("change", 0.0),
                    "change_percent": data.get("change_ratio", 0.0) * 100,
                    "volume": data.get("volume", 0),
                    "turnover": data.get("amount", 0.0),
                    "high": data.get("high", 0.0),
                    "low": data.get("low", 0.0),
                    "open": data.get("open", 0.0),
                    "prev_close": data.get("pre_close", 0.0),
                    "bid1": data.get("bid1", 0.0),
                    "ask1": data.get("ask1", 0.0),
                    "bid1_volume": data.get("bid1_volume", 0),
                    "ask1_volume": data.get("ask1_volume", 0),
                    "timestamp": data.get("timestamp", datetime.now().isoformat()),
                    "source": "xtquant"
                }
            else:
                # 如果无法获取实时数据，返回基础信息
                stock_data = {
                    "stock_code": stock_code,
                    "name": f"股票{stock_code}",
                    "price": 0.0,
                    "change": 0.0,
                    "change_percent": 0.0,
                    "volume": 0,
                    "turnover": 0.0,
                    "high": 0.0,
                    "low": 0.0,
                    "open": 0.0,
                    "prev_close": 0.0,
                    "timestamp": datetime.now().isoformat(),
                    "source": "xtquant",
                    "status": "no_data"
                }
        except Exception as e:
            logger.error(f"获取股票{stock_code}数据失败: {e}")
            # 返回错误状态的股票信息
            stock_data = {
                "stock_code": stock_code,
                "name": f"股票{stock_code}",
                "price": 0.0,
                "change": 0.0,
                "change_percent": 0.0,
                "volume": 0,
                "turnover": 0.0,
                "high": 0.0,
                "low": 0.0,
                "open": 0.0,
                "prev_close": 0.0,
                "timestamp": datetime.now().isoformat(),
                "source": "xtquant",
                "status": "error",
                "error": str(e)
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
async def get_positions():
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
        
        # 从XtQuant获取真实持仓数据
        try:
            global xtquant_service_instance
            if xtquant_service_instance is None:
                from services.xtquant_service import XtQuantService
                xtquant_service_instance = XtQuantService()
            
            # 获取持仓列表
            position_list = await xtquant_service_instance.get_positions()
            
            if position_list:
                # 计算汇总数据
                total_market_value = sum(pos.get("market_value", 0) for pos in position_list)
                total_cost_value = sum(pos.get("cost_value", 0) for pos in position_list)
                total_profit_loss = total_market_value - total_cost_value
                total_profit_loss_ratio = (total_profit_loss / total_cost_value * 100) if total_cost_value > 0 else 0
                
                positions = {
                    "total_positions": len(position_list),
                    "total_market_value": total_market_value,
                    "total_cost": total_cost_value,
                    "total_profit_loss": total_profit_loss,
                    "total_profit_loss_ratio": total_profit_loss_ratio,
                    "positions": position_list,
                    "source": "xtquant",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # 如果没有持仓数据
                positions = {
                    "total_positions": 0,
                    "total_market_value": 0.0,
                    "total_cost": 0.0,
                    "total_profit_loss": 0.0,
                    "total_profit_loss_ratio": 0.0,
                    "positions": [],
                    "source": "xtquant",
                    "timestamp": datetime.now().isoformat(),
                    "status": "no_positions"
                }
        except Exception as e:
            logger.error(f"获取持仓信息失败: {e}")
            # 返回错误状态的持仓信息
            positions = {
                "total_positions": 0,
                "total_market_value": 0.0,
                "total_cost": 0.0,
                "total_profit_loss": 0.0,
                "total_profit_loss_ratio": 0.0,
                "positions": [],
                "source": "xtquant",
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }
        
        # 为了保持兼容性，保留原有的positions结构示例（注释掉）
        # positions = {
        #     "total_positions": 3,
        #     "total_market_value": 52500.0,
        #     "total_cost": 51200.0,
        #     "total_profit_loss": 1300.0,
        #     "total_profit_loss_ratio": 2.54,
        #     "positions": [
        #         {
        #             "stock_code": "600000.SH",
        #             "stock_name": "浦发银行",
        #             "quantity": 1000,
        #             "available_quantity": 1000,
        #             "avg_cost": 10.50,
        #             "current_price": 10.75,
        #             "market_value": 10750.0,
        #             "cost_value": 10500.0,
        #             "profit_loss": 250.0,
        #             "profit_loss_ratio": 2.38,
        #             "position_ratio": 20.48
        #         },
        #         {
        #             "stock_code": "000001.SZ",
        #             "stock_name": "平安银行",
        #             "quantity": 2000,
        #             "available_quantity": 2000,
        #             "avg_cost": 12.30,
        #             "current_price": 12.60,
        #             "market_value": 25200.0,
        #             "cost_value": 24600.0,
        #             "profit_loss": 600.0,
        #             "profit_loss_ratio": 2.44,
        #             "position_ratio": 48.00
        #         },
        #         {
        #             "stock_code": "002415.SZ",
        #             "stock_name": "海康威视",
        #             "quantity": 500,
        #             "available_quantity": 500,
        #             "avg_cost": 32.20,
        #             "current_price": 33.10,
        #             "market_value": 16550.0,
        #             "cost_value": 16100.0,
        #             "profit_loss": 450.0,
        #             "profit_loss_ratio": 2.80,
        #             "position_ratio": 31.52
        #         }
        #     ],
        #     "source": "database",
        #     "timestamp": datetime.now().isoformat()
        # }
        
        # 缓存数据（30秒过期）
        cache.set_json(cache_key, positions, expire=30)
        
        return ApiResponse(
            message="获取持仓信息成功",
            data=positions
        ).to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/positions/{stock_code}")
async def get_position(stock_code: str):
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
        
        # 从XtQuant获取指定股票的真实持仓数据
        try:
            global xtquant_service_instance
            if xtquant_service_instance is None:
                from services.xtquant_service import XtQuantService
                xtquant_service_instance = XtQuantService()
            
            # 获取所有持仓，然后筛选指定股票
            position_list = await xtquant_service_instance.get_positions()
            
            position = None
            for pos in position_list:
                if pos.get("stock_code") == stock_code:
                    position = pos
                    break
            
            if position:
                position["source"] = "xtquant"
                position["timestamp"] = datetime.now().isoformat()
                
                # 缓存数据（30秒过期）
                cache.set_json(cache_key, position, expire=30)
                
                return ApiResponse(
                    message="获取持仓信息成功",
                    data=position
                ).to_dict()
            else:
                # 没有找到该股票的持仓
                return ApiResponse(
                    message="未找到该股票的持仓信息",
                    data={
                        "stock_code": stock_code,
                        "quantity": 0,
                        "available_quantity": 0,
                        "avg_cost": 0.0,
                        "current_price": 0.0,
                        "market_value": 0.0,
                        "cost_value": 0.0,
                        "profit_loss": 0.0,
                        "profit_loss_ratio": 0.0,
                        "source": "xtquant",
                        "timestamp": datetime.now().isoformat(),
                        "status": "no_position"
                    }
                ).to_dict()
                
        except Exception as e:
            logger.error(f"获取股票{stock_code}持仓失败: {e}")
            # 返回错误状态
            return ApiResponse(
                message=f"获取持仓信息失败: {str(e)}",
                data={
                    "stock_code": stock_code,
                    "quantity": 0,
                    "available_quantity": 0,
                    "avg_cost": 0.0,
                    "current_price": 0.0,
                    "market_value": 0.0,
                    "cost_value": 0.0,
                    "profit_loss": 0.0,
                    "profit_loss_ratio": 0.0,
                    "source": "xtquant",
                    "timestamp": datetime.now().isoformat(),
                    "status": "error",
                    "error": str(e)
                }
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
async def startup_event():
    """应用启动时初始化服务"""
    try:
        log_info("Smart Trader FastAPI服务启动中...")
        log_info("应用名称: {}".format(settings.app_name))
        log_info("版本: {}".format(settings.version))
        
        log_info("初始化本地缓存...")
        init_cache()
        
        log_info("初始化DuckDB数据库...")
        init_duckdb()
        
        # 初始化XtQuant服务
        log_info("初始化XtQuant服务...")
        try:
            from services.xtquant_service import XtQuantService
            from services.trading_service import TradingService
            
            # 创建并启动XtQuant服务（单例模式）
            global xtquant_service_instance
            xtquant_service_instance = XtQuantService()
            await xtquant_service_instance.start()
            
            # 创建并启动交易服务
            trading_service = TradingService()
            await trading_service.start()
            
            # 初始化数据服务并设置到data_routes
            from services.data_service import DataService
            from api.data_routes import set_data_service
            data_service = DataService()
            await data_service.start()
            set_data_service(data_service)
            
            xtquant_service = xtquant_service_instance
            
            if xtquant_service.is_trading_connected:
                log_info("XtQuant交易服务连接成功")
            else:
                log_warning("XtQuant交易服务连接失败，可能的原因:")
                log_warning("1. xtquant包未安装或版本不兼容 (当前Python版本: 3.13, xtquant要求: <3.13)")
                log_warning("2. MiniQMT客户端未运行")
                log_warning("3. 配置路径不正确")
                log_warning("系统将以模拟模式运行")
                
        except ImportError as e:
            log_warning("XtQuant模块导入失败: {}".format(e))
            log_warning("请安装xtquant包或使用兼容的Python版本 (建议Python 3.11或3.12)")
        except Exception as e:
            log_error("XtQuant服务初始化失败: {}".format(e))
        
        log_info("所有服务初始化完成")
    except Exception as e:
        log_error("服务初始化失败: {}".format(e))
        raise

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    log_info("Smart Trader FastAPI服务正在关闭...")
    
    try:
        # 停止XtQuant服务
        from services.xtquant_service import XtQuantService
        from services.trading_service import TradingService
        
        # 这里需要获取服务实例并停止它们
        # 注意：由于服务实例是在startup中创建的，这里可能需要全局变量或单例模式
        log_info("正在停止XtQuant服务...")
        
    except Exception as e:
        log_error("停止服务时发生错误: {}".format(e))
    
    log_info("服务已关闭")

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