#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py异步集成测试
测试改进后的main.py中飞书机器人异步管理的集成功能
"""

import asyncio
import pytest
import sys
import os
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from fastapi.testclient import TestClient

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.log_config import setup_logging, get_logger

# 设置日志
setup_logging()
logger = get_logger(__name__)


class TestMainAsyncIntegration:
    """main.py异步集成测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.mock_settings = Mock()
        self.mock_settings.feishu.enabled = True
        self.mock_settings.feishu.app_id = "test_app_id"
        self.mock_settings.feishu.app_secret = "test_app_secret"
        self.mock_settings.app_name = "测试应用"
        self.mock_settings.version = "1.0.0"
        self.mock_settings.api_host = "127.0.0.1"
        self.mock_settings.api_port = 8000
        self.mock_settings.log_level = "INFO"
    
    @pytest.mark.asyncio
    async def test_lifespan_with_feishu_bot(self):
        """测试包含飞书机器人的应用生命周期"""
        logger.info("测试: 包含飞书机器人的应用生命周期")
        
        # 模拟所有必要的依赖
        with patch('main.get_settings') as mock_get_settings, \
             patch('main.FeishuBotService') as mock_feishu_service_class, \
             patch('main.run_feishu_bot_in_executor') as mock_run_feishu, \
             patch('main.DataService') as mock_data_service, \
             patch('main.TradingService') as mock_trading_service, \
             patch('main.NotificationService') as mock_notification_service, \
             patch('main.XtQuantService') as mock_xtquant_service, \
             patch('main.BacktestService') as mock_backtest_service, \
             patch('main.StrategyService') as mock_strategy_service, \
             patch('main.SchedulerService') as mock_scheduler_service, \
             patch('main.StrategyManager') as mock_strategy_manager, \
             patch('main.StrategyExecutor') as mock_strategy_executor, \
             patch('main.StockInfoCacheService') as mock_stock_cache_service:
            
            # 设置模拟返回值
            mock_get_settings.return_value = self.mock_settings
            
            # 模拟飞书机器人服务
            mock_feishu_service = Mock()
            mock_feishu_service.stop = Mock()
            mock_feishu_service_class.return_value = mock_feishu_service
            
            # 模拟异步执行器
            async def mock_async_executor(service):
                logger.info("模拟飞书机器人在异步执行器中运行")
                await asyncio.sleep(0.1)  # 模拟短暂运行
                return True
            
            mock_run_feishu.side_effect = mock_async_executor
            
            # 模拟其他服务
            mock_services = {
                'data_service': mock_data_service.return_value,
                'trading_service': mock_trading_service.return_value,
                'notification_service': mock_notification_service.return_value,
                'xtquant_service': mock_xtquant_service.return_value,
                'backtest_service': mock_backtest_service.return_value,
                'strategy_service': mock_strategy_service.return_value,
                'scheduler_service': mock_scheduler_service.return_value,
                'strategy_manager': mock_strategy_manager.return_value,
                'strategy_executor': mock_strategy_executor.return_value,
                'stock_cache_service': mock_stock_cache_service.return_value
            }
            
            # 为所有服务添加必要的方法
            for service_name, service in mock_services.items():
                if hasattr(service, 'initialize'):
                    service.initialize = AsyncMock()
                if hasattr(service, 'start'):
                    service.start = AsyncMock()
                if hasattr(service, 'stop'):
                    service.stop = AsyncMock()
                service.set_data_service = Mock()
                service.set_strategy_manager = Mock()
                service.set_strategy_service = Mock()
            
            # 导入并测试lifespan
            from main import lifespan, FastAPI
            
            app = FastAPI()
            
            # 测试lifespan上下文管理器
            async with lifespan(app):
                logger.info("应用启动阶段完成")
                
                # 验证飞书机器人服务被创建
                mock_feishu_service_class.assert_called_once_with(
                    app_id=self.mock_settings.feishu.app_id,
                    app_secret=self.mock_settings.feishu.app_secret
                )
                
                # 验证异步执行器被调用
                mock_run_feishu.assert_called_once_with(mock_feishu_service)
                
                # 验证app.state中保存了必要的服务
                assert hasattr(app.state, 'feishu_bot_service')
                assert hasattr(app.state, 'feishu_task')
                assert app.state.feishu_bot_service == mock_feishu_service
                
                logger.info("应用运行阶段验证完成")
            
            logger.info("应用关闭阶段完成")
            
            # 验证飞书机器人服务被停止
            mock_feishu_service.stop.assert_called_once()
            
            logger.info("✅ 包含飞书机器人的应用生命周期测试通过")
    
    @pytest.mark.asyncio
    async def test_lifespan_without_feishu_bot(self):
        """测试不包含飞书机器人的应用生命周期"""
        logger.info("测试: 不包含飞书机器人的应用生命周期")
        
        # 设置飞书机器人未启用
        self.mock_settings.feishu.enabled = False
        
        # 模拟所有必要的依赖
        with patch('main.get_settings') as mock_get_settings, \
             patch('main.FeishuBotService') as mock_feishu_service_class, \
             patch('main.DataService') as mock_data_service, \
             patch('main.TradingService') as mock_trading_service, \
             patch('main.NotificationService') as mock_notification_service, \
             patch('main.XtQuantService') as mock_xtquant_service, \
             patch('main.BacktestService') as mock_backtest_service, \
             patch('main.StrategyService') as mock_strategy_service, \
             patch('main.SchedulerService') as mock_scheduler_service, \
             patch('main.StrategyManager') as mock_strategy_manager, \
             patch('main.StrategyExecutor') as mock_strategy_executor, \
             patch('main.StockInfoCacheService') as mock_stock_cache_service:
            
            # 设置模拟返回值
            mock_get_settings.return_value = self.mock_settings
            
            # 模拟其他服务
            mock_services = {
                'data_service': mock_data_service.return_value,
                'trading_service': mock_trading_service.return_value,
                'notification_service': mock_notification_service.return_value,
                'xtquant_service': mock_xtquant_service.return_value,
                'backtest_service': mock_backtest_service.return_value,
                'strategy_service': mock_strategy_service.return_value,
                'scheduler_service': mock_scheduler_service.return_value,
                'strategy_manager': mock_strategy_manager.return_value,
                'strategy_executor': mock_strategy_executor.return_value,
                'stock_cache_service': mock_stock_cache_service.return_value
            }
            
            # 为所有服务添加必要的方法
            for service_name, service in mock_services.items():
                if hasattr(service, 'initialize'):
                    service.initialize = AsyncMock()
                if hasattr(service, 'start'):
                    service.start = AsyncMock()
                if hasattr(service, 'stop'):
                    service.stop = AsyncMock()
                service.set_data_service = Mock()
                service.set_strategy_manager = Mock()
                service.set_strategy_service = Mock()
            
            # 导入并测试lifespan
            from main import lifespan, FastAPI
            
            app = FastAPI()
            
            # 测试lifespan上下文管理器
            async with lifespan(app):
                logger.info("应用启动阶段完成")
                
                # 验证飞书机器人服务未被创建
                mock_feishu_service_class.assert_not_called()
                
                # 验证app.state中飞书相关服务为None
                assert app.state.feishu_bot_service is None
                assert app.state.feishu_task is None
                
                logger.info("应用运行阶段验证完成")
            
            logger.info("应用关闭阶段完成")
            logger.info("✅ 不包含飞书机器人的应用生命周期测试通过")
    
    @pytest.mark.asyncio
    async def test_feishu_bot_initialization_failure(self):
        """测试飞书机器人初始化失败的处理"""
        logger.info("测试: 飞书机器人初始化失败的处理")
        
        # 模拟所有必要的依赖
        with patch('main.get_settings') as mock_get_settings, \
             patch('main.FeishuBotService') as mock_feishu_service_class, \
             patch('main.DataService') as mock_data_service, \
             patch('main.TradingService') as mock_trading_service, \
             patch('main.NotificationService') as mock_notification_service, \
             patch('main.XtQuantService') as mock_xtquant_service, \
             patch('main.BacktestService') as mock_backtest_service, \
             patch('main.StrategyService') as mock_strategy_service, \
             patch('main.SchedulerService') as mock_scheduler_service, \
             patch('main.StrategyManager') as mock_strategy_manager, \
             patch('main.StrategyExecutor') as mock_strategy_executor, \
             patch('main.StockInfoCacheService') as mock_stock_cache_service:
            
            # 设置模拟返回值
            mock_get_settings.return_value = self.mock_settings
            
            # 模拟飞书机器人服务初始化失败
            mock_feishu_service_class.side_effect = Exception("飞书机器人初始化失败")
            
            # 模拟其他服务
            mock_services = {
                'data_service': mock_data_service.return_value,
                'trading_service': mock_trading_service.return_value,
                'notification_service': mock_notification_service.return_value,
                'xtquant_service': mock_xtquant_service.return_value,
                'backtest_service': mock_backtest_service.return_value,
                'strategy_service': mock_strategy_service.return_value,
                'scheduler_service': mock_scheduler_service.return_value,
                'strategy_manager': mock_strategy_manager.return_value,
                'strategy_executor': mock_strategy_executor.return_value,
                'stock_cache_service': mock_stock_cache_service.return_value
            }
            
            # 为所有服务添加必要的方法
            for service_name, service in mock_services.items():
                if hasattr(service, 'initialize'):
                    service.initialize = AsyncMock()
                if hasattr(service, 'start'):
                    service.start = AsyncMock()
                if hasattr(service, 'stop'):
                    service.stop = AsyncMock()
                service.set_data_service = Mock()
                service.set_strategy_manager = Mock()
                service.set_strategy_service = Mock()
            
            # 导入并测试lifespan
            from main import lifespan, FastAPI
            
            app = FastAPI()
            
            # 测试lifespan上下文管理器（应该能正常处理飞书机器人初始化失败）
            async with lifespan(app):
                logger.info("应用启动阶段完成（飞书机器人初始化失败但应用继续运行）")
                
                # 验证飞书机器人服务初始化被尝试
                mock_feishu_service_class.assert_called_once()
                
                # 验证app.state中飞书相关服务为None（因为初始化失败）
                assert app.state.feishu_bot_service is None
                assert app.state.feishu_task is None
                
                logger.info("应用运行阶段验证完成")
            
            logger.info("应用关闭阶段完成")
            logger.info("✅ 飞书机器人初始化失败处理测试通过")
    
    def test_create_app_basic(self):
        """测试基本的应用创建功能"""
        logger.info("测试: 基本的应用创建功能")
        
        with patch('main.get_settings') as mock_get_settings:
            mock_get_settings.return_value = self.mock_settings
            
            # 导入并测试create_app
            from main import create_app
            
            app = create_app()
            
            # 验证应用基本属性
            assert app.title == self.mock_settings.app_name
            assert app.version == self.mock_settings.version
            assert "智能量化交易系统API" in app.description
            
            logger.info("✅ 基本的应用创建功能测试通过")


def run_tests():
    """运行所有测试"""
    logger.info("开始main.py异步集成测试...")
    
    try:
        # 运行pytest
        exit_code = pytest.main([
            __file__,
            "-v",
            "--tb=short",
            "-x"  # 遇到第一个失败就停止
        ])
        
        if exit_code == 0:
            logger.info("✅ 所有main.py异步集成测试通过")
        else:
            logger.error("❌ 部分main.py异步集成测试失败")
        
        return exit_code
        
    except Exception as e:
        logger.error(f"运行测试时发生错误: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)