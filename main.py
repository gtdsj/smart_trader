# -*- coding: utf-8 -*-
"""
量化交易系统主入口
"""

import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import get_settings, SystemConfig
from utils.log_config import setup_logging, get_logger

# 获取logger实例
logger = get_logger()
from core.database import init_database
from core.cache_adapter import init_cache
from api.unified_backfill_routes import router as unified_backfill_router
from api.config_routes import router as config_router
from api.scheduler_routes import router as scheduler_router
from api.stock_screener_routes import router as stock_screener_router
from api.routes import router as main_api_router
from services.notification_service import NotificationService
from services.data_service import DataService
from services.trading_service import TradingService
from services.strategy_service import StrategyService
from services.backtest_service import BacktestService
from services.xtquant_service import XtQuantService
from services.strategy_manager import StrategyManager
from services.strategy_executor import StrategyExecutor
from services.scheduler_service import SchedulerService
from services.stock_info_cache_service import StockInfoCacheService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    try:
        settings = get_settings()
        
        # 启动时初始化
        logger.info(f"启动 {settings.app_name} v{settings.version}")
        
        # 初始化数据库
        init_database()
        logger.info("数据库初始化完成")
        
        # 初始化缓存
        await init_cache()
        logger.info("缓存初始化完成")
        
        # 初始化服务
        logger.info("开始初始化XtQuant服务...")
        xtquant_service = XtQuantService()
        logger.info("XtQuant服务初始化完成")
        
        logger.info("开始初始化通知服务...")
        notification_service = NotificationService()
        logger.info("通知服务初始化完成")
        
        logger.info("开始初始化交易服务...")
        trading_service = TradingService()
        logger.info("交易服务初始化完成")
        
        logger.info("开始初始化数据服务...")
        data_service = DataService()
        await data_service.start()
        logger.info("数据服务初始化完成")
        
        logger.info("开始初始化策略服务...")
        strategy_service = StrategyService()
        logger.info("策略服务初始化完成")
        
        # 初始化回测服务
        logger.info("开始初始化回测服务...")
        backtest_service = BacktestService()
        logger.info("回测服务初始化完成")
        
        logger.info("开始初始化策略管理器...")
        strategy_manager = StrategyManager()
        logger.info("策略管理器初始化完成")
        
        logger.info("开始初始化策略执行器...")
        strategy_executor = StrategyExecutor()
        logger.info("策略执行器初始化完成")
        
        # 初始化调度器服务
        logger.info("开始初始化调度器服务...")
        scheduler_service = SchedulerService()
        await scheduler_service.start()
        logger.info("调度器服务初始化完成")
        
        # 初始化股票信息缓存服务
        logger.info("开始初始化股票信息缓存服务...")
        stock_cache_service = StockInfoCacheService()
        await stock_cache_service.initialize()
        logger.info("股票信息缓存服务初始化完成")
        
        # 设置服务依赖
        strategy_executor.set_data_service(data_service)
        strategy_executor.set_strategy_manager(strategy_manager)
        
        # 设置服务间依赖关系
        backtest_service.set_data_service(data_service)
        backtest_service.set_strategy_service(strategy_service)
        
        # 服务实例已通过新的API路由系统自动管理
        
        # 保存服务实例到app.state以便在关闭时使用
        app.state.scheduler_service = scheduler_service
        app.state.backtest_service = backtest_service
        app.state.strategy_service = strategy_service
        app.state.data_service = data_service
        app.state.trading_service = trading_service
        app.state.notification_service = notification_service
        app.state.xtquant_service = xtquant_service
        app.state.stock_cache_service = stock_cache_service
        
        logger.info("所有服务启动完成")
        
        yield
    except Exception as e:
        logger.error(f"服务启动失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        raise
    finally:
        # 停止服务
        logger.info("开始停止所有服务...")
        
        if hasattr(app.state, 'scheduler_service'):
            try:
                await app.state.scheduler_service.stop()
                logger.info("调度器服务已停止")
            except Exception as e:
                logger.error(f"停止调度器服务失败: {e}")
        
        if hasattr(app.state, 'data_service'):
            try:
                await app.state.data_service.stop()
                logger.info("数据服务已停止")
            except Exception as e:
                logger.error(f"停止数据服务失败: {e}")
        
        if hasattr(app.state, 'xtquant_service'):
            try:
                app.state.xtquant_service.stop()
                logger.info("XtQuant服务已停止")
            except Exception as e:
                logger.error(f"停止XtQuant服务失败: {e}")
        
        if hasattr(app.state, 'backtest_service'):
            try:
                await app.state.backtest_service.stop()
                logger.info("回测服务已停止")
            except Exception as e:
                logger.error(f"停止回测服务失败: {e}")
        
        if hasattr(app.state, 'strategy_service'):
            try:
                await app.state.strategy_service.stop()
                logger.info("策略服务已停止")
            except Exception as e:
                logger.error(f"停止策略服务失败: {e}")
        
        if hasattr(app.state, 'trading_service'):
            try:
                await app.state.trading_service.stop()
                logger.info("交易服务已停止")
            except Exception as e:
                logger.error(f"停止交易服务失败: {e}")
        
        if hasattr(app.state, 'notification_service'):
            try:
                await app.state.notification_service.stop()
                logger.info("通知服务已停止")
            except Exception as e:
                logger.error(f"停止通知服务失败: {e}")
        
        logger.info("所有服务已停止")


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
    # 注册新的统一API路由系统
    app.include_router(main_api_router, prefix="/api")
    
    # 保留必要的独立路由
    app.include_router(unified_backfill_router)
    app.include_router(config_router)
    app.include_router(scheduler_router)
    app.include_router(stock_screener_router)
    
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
    import signal
    import sys
    from pathlib import Path
    
    settings = get_settings()
    
    # 设置统一日志配置
    setup_logging()
    
    try:
        logger.info("启动量化交易系统...")
        logger.info(f"请使用以下命令启动服务:")
        logger.info(f"uvicorn main:app --host {settings.api_host} --port {settings.api_port} --log-level {settings.log_level.lower()}")
        
        # 直接使用uvicorn.run启动
        uvicorn.run(
            app,
            host=settings.api_host,
            port=settings.api_port,
            log_level=settings.log_level.lower(),
            reload=False
        )
    except KeyboardInterrupt:
        logger.info("接收到键盘中断，程序正在退出...")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        sys.exit(1)
    finally:
        logger.info("程序已退出")