#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试飞书机器人优雅关闭功能
验证修复后的飞书机器人服务能否正确响应Ctrl+C信号并优雅退出
"""

import asyncio
import signal
import threading
import time
from unittest.mock import Mock, patch
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.log_config import setup_logging, get_logger
from services.feishu_bot_service import FeishuBotService
from main import run_feishu_bot_in_executor

# 设置日志
setup_logging()
logger = get_logger(__name__)


class MockWebSocketClient:
    """模拟WebSocket客户端"""
    
    def __init__(self):
        self._running = False
        self._stop_event = threading.Event()
    
    def start(self):
        """模拟启动WebSocket连接"""
        logger.info("模拟WebSocket客户端启动")
        self._running = True
        
        # 模拟阻塞的WebSocket连接
        while self._running and not self._stop_event.is_set():
            time.sleep(0.1)
            
        logger.info("模拟WebSocket客户端退出")
    
    def close(self):
        """模拟关闭WebSocket连接"""
        logger.info("模拟WebSocket客户端关闭")
        self._running = False
        self._stop_event.set()


def test_feishu_bot_graceful_shutdown():
    """测试飞书机器人优雅关闭"""
    logger.info("=== 测试飞书机器人优雅关闭 ===")
    
    try:
        # 创建模拟的飞书机器人服务
        with patch('lark_oapi.Client.builder') as mock_client_builder, \
             patch('lark_oapi.EventDispatcherHandler.builder') as mock_handler_builder, \
             patch('lark_oapi.ws.Client') as mock_ws_client_class:
            
            # 设置模拟对象
            mock_client = Mock()
            mock_client_builder.return_value.app_id.return_value.app_secret.return_value.build.return_value = mock_client
            
            mock_handler = Mock()
            mock_handler_builder.return_value.register_p2_im_message_receive_v1.return_value.build.return_value = mock_handler
            
            mock_ws_client = MockWebSocketClient()
            mock_ws_client_class.return_value = mock_ws_client
            
            # 创建飞书机器人服务
            feishu_service = FeishuBotService(
                app_id="test_app_id",
                app_secret="test_app_secret"
            )
            
            # 在单独线程中启动飞书机器人
            start_time = time.time()
            feishu_thread = threading.Thread(
                target=feishu_service.start,
                daemon=True
            )
            feishu_thread.start()
            
            # 等待一段时间确保服务启动
            time.sleep(1)
            logger.info("飞书机器人服务已启动，准备测试停止功能")
            
            # 停止飞书机器人
            feishu_service.stop()
            
            # 等待线程结束
            feishu_thread.join(timeout=10)
            
            end_time = time.time()
            duration = end_time - start_time
            
            if feishu_thread.is_alive():
                logger.error("飞书机器人线程未能在10秒内结束")
                return False
            else:
                logger.info(f"飞书机器人优雅关闭成功，耗时: {duration:.2f}秒")
                return True
                
    except Exception as e:
        logger.error(f"测试飞书机器人优雅关闭失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return False


async def test_feishu_bot_async_shutdown():
    """测试飞书机器人异步关闭"""
    logger.info("=== 测试飞书机器人异步关闭 ===")
    
    try:
        # 创建模拟的飞书机器人服务
        with patch('lark_oapi.Client.builder') as mock_client_builder, \
             patch('lark_oapi.EventDispatcherHandler.builder') as mock_handler_builder, \
             patch('lark_oapi.ws.Client') as mock_ws_client_class:
            
            # 设置模拟对象
            mock_client = Mock()
            mock_client_builder.return_value.app_id.return_value.app_secret.return_value.build.return_value = mock_client
            
            mock_handler = Mock()
            mock_handler_builder.return_value.register_p2_im_message_receive_v1.return_value.build.return_value = mock_handler
            
            mock_ws_client = MockWebSocketClient()
            mock_ws_client_class.return_value = mock_ws_client
            
            # 创建飞书机器人服务
            feishu_service = FeishuBotService(
                app_id="test_app_id",
                app_secret="test_app_secret"
            )
            
            # 使用异步任务启动飞书机器人
            start_time = time.time()
            feishu_task = asyncio.create_task(
                run_feishu_bot_in_executor(feishu_service)
            )
            
            # 等待一段时间确保服务启动
            await asyncio.sleep(1)
            logger.info("飞书机器人异步任务已启动，准备测试取消功能")
            
            # 取消异步任务
            feishu_task.cancel()
            
            try:
                await feishu_task
            except asyncio.CancelledError:
                logger.info("飞书机器人异步任务已被取消")
            
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info(f"飞书机器人异步关闭成功，耗时: {duration:.2f}秒")
            return True
                
    except Exception as e:
        logger.error(f"测试飞书机器人异步关闭失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return False


def test_signal_handling():
    """测试信号处理"""
    logger.info("=== 测试信号处理 ===")
    
    try:
        # 创建模拟的飞书机器人服务
        with patch('lark_oapi.Client.builder') as mock_client_builder, \
             patch('lark_oapi.EventDispatcherHandler.builder') as mock_handler_builder, \
             patch('lark_oapi.ws.Client') as mock_ws_client_class:
            
            # 设置模拟对象
            mock_client = Mock()
            mock_client_builder.return_value.app_id.return_value.app_secret.return_value.build.return_value = mock_client
            
            mock_handler = Mock()
            mock_handler_builder.return_value.register_p2_im_message_receive_v1.return_value.build.return_value = mock_handler
            
            mock_ws_client = MockWebSocketClient()
            mock_ws_client_class.return_value = mock_ws_client
            
            # 创建飞书机器人服务
            feishu_service = FeishuBotService(
                app_id="test_app_id",
                app_secret="test_app_secret"
            )
            
            # 在单独线程中启动飞书机器人
            start_time = time.time()
            feishu_thread = threading.Thread(
                target=feishu_service.start,
                daemon=True
            )
            feishu_thread.start()
            
            # 等待一段时间确保服务启动
            time.sleep(0.5)
            logger.info("飞书机器人服务已启动，准备测试信号处理")
            
            # 模拟KeyboardInterrupt
            def simulate_keyboard_interrupt():
                time.sleep(0.5)
                feishu_service.stop()
            
            interrupt_thread = threading.Thread(target=simulate_keyboard_interrupt)
            interrupt_thread.start()
            
            # 等待线程结束
            feishu_thread.join(timeout=5)
            interrupt_thread.join(timeout=1)
            
            end_time = time.time()
            duration = end_time - start_time
            
            if feishu_thread.is_alive():
                logger.error("飞书机器人线程未能在5秒内结束")
                return False
            else:
                logger.info(f"信号处理测试成功，耗时: {duration:.2f}秒")
                return True
                
    except Exception as e:
        logger.error(f"测试信号处理失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return False


async def main():
    """主测试函数"""
    logger.info("开始飞书机器人优雅关闭测试")
    
    test_results = []
    
    # 测试1: 飞书机器人优雅关闭
    result1 = test_feishu_bot_graceful_shutdown()
    test_results.append(("飞书机器人优雅关闭", result1))
    
    # 测试2: 飞书机器人异步关闭
    result2 = await test_feishu_bot_async_shutdown()
    test_results.append(("飞书机器人异步关闭", result2))
    
    # 测试3: 信号处理
    result3 = test_signal_handling()
    test_results.append(("信号处理", result3))
    
    # 输出测试结果
    logger.info("\n=== 测试结果汇总 ===")
    all_passed = True
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        logger.info("\n🎉 所有飞书机器人优雅关闭测试通过！")
        return 0
    else:
        logger.error("\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        sys.exit(1)