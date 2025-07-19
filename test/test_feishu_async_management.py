#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书机器人异步管理测试
测试改进后的飞书机器人异步任务管理功能
"""

import asyncio
import pytest
import sys
import os
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from main import run_feishu_bot_in_executor
from services.feishu_bot_service import FeishuBotService
from utils.log_config import setup_logging, get_logger

# 设置日志
setup_logging()
logger = get_logger(__name__)


class TestFeishuAsyncManagement:
    """飞书机器人异步管理测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.mock_app_id = "test_app_id"
        self.mock_app_secret = "test_app_secret"
    
    @pytest.mark.asyncio
    async def test_run_feishu_bot_in_executor_success(self):
        """测试在执行器中成功运行飞书机器人"""
        logger.info("测试: 在执行器中成功运行飞书机器人")
        
        # 创建模拟的飞书机器人服务
        mock_feishu_service = Mock()
        mock_feishu_service.start = Mock()
        
        # 模拟start方法执行成功
        def mock_start():
            logger.info("模拟飞书机器人启动成功")
            return True
        
        mock_feishu_service.start.side_effect = mock_start
        
        # 测试在执行器中运行
        try:
            await run_feishu_bot_in_executor(mock_feishu_service)
            logger.info("✅ 在执行器中运行飞书机器人成功")
        except Exception as e:
            logger.error(f"❌ 在执行器中运行飞书机器人失败: {e}")
            raise
        
        # 验证start方法被调用
        mock_feishu_service.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_feishu_bot_in_executor_exception(self):
        """测试在执行器中运行飞书机器人时的异常处理"""
        logger.info("测试: 在执行器中运行飞书机器人异常处理")
        
        # 创建模拟的飞书机器人服务
        mock_feishu_service = Mock()
        
        # 模拟start方法抛出异常
        def mock_start_with_exception():
            raise Exception("模拟启动异常")
        
        mock_feishu_service.start.side_effect = mock_start_with_exception
        
        # 测试异常处理
        with pytest.raises(Exception, match="模拟启动异常"):
            await run_feishu_bot_in_executor(mock_feishu_service)
        
        logger.info("✅ 异常处理测试通过")
    
    @pytest.mark.asyncio
    async def test_feishu_task_cancellation(self):
        """测试飞书机器人任务取消"""
        logger.info("测试: 飞书机器人任务取消")
        
        # 创建模拟的飞书机器人服务
        mock_feishu_service = Mock()
        
        # 模拟一个长时间运行的start方法
        async def mock_long_running_start():
            await asyncio.sleep(10)  # 模拟长时间运行
        
        mock_feishu_service.start = lambda: asyncio.run(mock_long_running_start())
        
        # 创建任务
        task = asyncio.create_task(
            run_feishu_bot_in_executor(mock_feishu_service)
        )
        
        # 等待一小段时间后取消任务
        await asyncio.sleep(0.1)
        task.cancel()
        
        # 验证任务被取消
        with pytest.raises(asyncio.CancelledError):
            await task
        
        assert task.cancelled()
        logger.info("✅ 任务取消测试通过")
    
    @pytest.mark.asyncio
    async def test_multiple_feishu_tasks(self):
        """测试多个飞书机器人任务管理"""
        logger.info("测试: 多个飞书机器人任务管理")
        
        tasks = []
        
        # 创建多个模拟的飞书机器人服务
        for i in range(3):
            mock_feishu_service = Mock()
            mock_feishu_service.start = Mock()
            
            def mock_start(service_id=i):
                logger.info(f"模拟飞书机器人服务 {service_id} 启动")
                return True
            
            mock_feishu_service.start.side_effect = mock_start
            
            # 创建任务
            task = asyncio.create_task(
                run_feishu_bot_in_executor(mock_feishu_service)
            )
            tasks.append((task, mock_feishu_service))
        
        # 等待所有任务完成
        try:
            await asyncio.gather(*[task for task, _ in tasks])
            logger.info("✅ 所有飞书机器人任务完成")
        except Exception as e:
            logger.error(f"❌ 多任务管理失败: {e}")
            raise
        
        # 验证所有服务的start方法都被调用
        for task, mock_service in tasks:
            mock_service.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_feishu_service_integration(self):
        """测试飞书机器人服务集成"""
        logger.info("测试: 飞书机器人服务集成")
        
        # 使用真实的FeishuBotService类，但模拟其依赖
        with patch('services.feishu_bot_service.lark') as mock_lark:
            # 模拟lark客户端
            mock_client = Mock()
            mock_ws_client = Mock()
            mock_ws_client.start = Mock()
            
            mock_lark.Client.builder.return_value.app_id.return_value.app_secret.return_value.build.return_value = mock_client
            mock_lark.ws.Client.return_value = mock_ws_client
            mock_lark.EventDispatcherHandler.builder.return_value.register_p2_im_message_receive_v1.return_value.build.return_value = Mock()
            
            # 创建飞书机器人服务
            feishu_service = FeishuBotService(
                app_id=self.mock_app_id,
                app_secret=self.mock_app_secret
            )
            
            # 模拟start方法不阻塞
            def mock_start():
                logger.info("模拟飞书机器人服务启动")
                return True
            
            feishu_service.start = mock_start
            
            # 测试在执行器中运行
            try:
                await run_feishu_bot_in_executor(feishu_service)
                logger.info("✅ 飞书机器人服务集成测试通过")
            except Exception as e:
                logger.error(f"❌ 飞书机器人服务集成测试失败: {e}")
                raise


def run_tests():
    """运行所有测试"""
    logger.info("开始飞书机器人异步管理测试...")
    
    try:
        # 运行pytest
        exit_code = pytest.main([
            __file__,
            "-v",
            "--tb=short",
            "-x"  # 遇到第一个失败就停止
        ])
        
        if exit_code == 0:
            logger.info("✅ 所有飞书机器人异步管理测试通过")
        else:
            logger.error("❌ 部分飞书机器人异步管理测试失败")
        
        return exit_code
        
    except Exception as e:
        logger.error(f"运行测试时发生错误: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)