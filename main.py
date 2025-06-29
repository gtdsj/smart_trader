# -*- coding: utf-8 -*-
"""
量化交易系统主入口
"""

import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from config import get_settings, SystemConfig
from core.database import init_database
from core.redis_client import init_redis
from api.data_routes import router as data_router, set_data_service
from api.trading_routes import router as trading_router, set_trading_service
from api.strategy_manager_routes import (
    router as strategy_manager_router,
    set_strategy_manager,
    set_strategy_executor
)
from api.strategy_routes import router as strategy_router, set_strategy_service
from api.backtest_routes import router as backtest_router, set_backtest_service
from api.notification_routes import router as notification_router, set_notification_service
from api.config_routes import router as config_router
from services.notification_service import NotificationService
from services.data_service import DataService
from services.trading_service import TradingService
from services.strategy_service import StrategyService
from services.backtest_service import BacktestService
from services.xtquant_service import XtQuantService
from services.strategy_manager import StrategyManager
from services.strategy_executor import StrategyExecutor


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    settings = get_settings()
    
    # 启动时初始化
    logger.info(f"启动 {settings.app_name} v{settings.version}")
    
    # 初始化数据库
    init_database()
    logger.info("数据库初始化完成")
    
    # 初始化Redis
    await init_redis()
    logger.info("Redis初始化完成")
    
    # 初始化服务
    xtquant_service = XtQuantService()
    notification_service = NotificationService()
    
    trading_service = TradingService()
    
    data_service = DataService()
    await data_service.start()
    
    strategy_service = StrategyService()
   # 初始化回测服务
    backtest_service = BacktestService()
    
    strategy_manager = StrategyManager()
    strategy_executor = StrategyExecutor()
    
    # 设置服务依赖
    strategy_executor.set_data_service(data_service)
    strategy_executor.set_strategy_manager(strategy_manager)
    
    # 设置服务间依赖关系
    backtest_service.set_data_service(data_service)
    backtest_service.set_strategy_service(strategy_service)
    
    # 设置API路由的服务实例
    set_data_service(data_service)
    set_trading_service(trading_service)
    set_strategy_service(strategy_service)
    set_backtest_service(backtest_service)
    set_notification_service(notification_service)
    set_strategy_manager(strategy_manager)
    set_strategy_executor(strategy_executor)
    
    logger.info("所有服务启动完成")
    
    yield
    
    # 停止服务
    if hasattr(app.state, 'backtest_service'):
        await app.state.backtest_service.stop()
    
    if hasattr(app.state, 'strategy_service'):
        await app.state.strategy_service.stop()
    
    if hasattr(app.state, 'data_service'):
        await app.state.data_service.stop()
    
    if hasattr(app.state, 'trading_service'):
        await app.state.trading_service.stop()
    
    if hasattr(app.state, 'notification_service'):
        await app.state.notification_service.stop()


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="智能量化交易系统API",
        lifespan=lifespan
    )
    
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(data_router)
    app.include_router(trading_router)
    app.include_router(strategy_manager_router)
    app.include_router(strategy_router)
    app.include_router(backtest_router)
    app.include_router(notification_router)
    app.include_router(config_router)
    
    @app.get("/", tags=["系统"])
    async def root():
        """系统根路径"""
        return {
            "message": f"欢迎使用{settings.app_name}",
            "version": settings.version,
            "status": "running"
        }
    
    @app.get("/health", tags=["系统"])
    async def health_check():
        """健康检查"""
        return {"status": "healthy"}
    
    return app


app = create_app()


if __name__ == "__main__":
    import os
    from pathlib import Path
    
    settings = get_settings()
    
    # 确保日志目录存在
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置日志
    logger.add(
        log_dir / f"{settings.log_file_prefix}_{{time:YYYY-MM-DD}}.log",
        rotation="1 day",
        retention=f"{settings.max_log_files} days",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )