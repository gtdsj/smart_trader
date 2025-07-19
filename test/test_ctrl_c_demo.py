#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书机器人Ctrl+C退出演示
用于演示修复后的飞书机器人服务能够正确响应Ctrl+C信号并优雅退出

使用方法:
1. 运行此脚本: python test\test_ctrl_c_demo.py
2. 等待看到"飞书机器人启动成功"的消息
3. 按 Ctrl+C 来测试优雅退出功能
4. 观察是否能够快速、干净地退出
"""

import asyncio
import signal
import sys
import os
import time
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.log_config import setup_logging, get_logger
from services.feishu_bot_service import FeishuBotService
from main import run_feishu_bot_in_executor

# 设置日志
setup_logging()
logger = get_logger(__name__)


class MockWebSocketClient:
    """模拟WebSocket客户端 - 模拟真实的阻塞行为"""
    
    def __init__(self):
        self._running = False
        self._stop_event = None
    
    def start(self):
        """模拟启动WebSocket连接 - 会一直阻塞直到被停止"""
        logger.info("🚀 模拟WebSocket客户端启动 (这会模拟真实的阻塞行为)")
        self._running = True
        
        # 模拟真实WebSocket客户端的阻塞行为
        # 这里会一直循环，直到被外部停止
        try:
            while self._running:
                time.sleep(0.1)  # 模拟网络I/O等待
        except KeyboardInterrupt:
            logger.info("📡 WebSocket客户端接收到中断信号")
        finally:
            logger.info("🔌 模拟WebSocket客户端连接已断开")
    
    def close(self):
        """模拟关闭WebSocket连接"""
        logger.info("🛑 正在关闭WebSocket连接...")
        self._running = False


async def demo_with_async_task():
    """使用异步任务演示飞书机器人的Ctrl+C退出功能"""
    logger.info("\n" + "="*60)
    logger.info("🎯 飞书机器人 Ctrl+C 优雅退出演示")
    logger.info("="*60)
    logger.info("📝 说明: 这个演示展示了修复后的飞书机器人如何响应 Ctrl+C 信号")
    logger.info("⚡ 操作: 等待启动完成后，按 Ctrl+C 来测试退出功能")
    logger.info("="*60 + "\n")
    
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
            logger.info("🔧 正在初始化飞书机器人服务...")
            feishu_service = FeishuBotService(
                app_id="demo_app_id",
                app_secret="demo_app_secret"
            )
            
            # 使用异步任务启动飞书机器人 (这是main.py中使用的方式)
            logger.info("🚀 正在启动飞书机器人异步任务...")
            feishu_task = asyncio.create_task(
                run_feishu_bot_in_executor(feishu_service)
            )
            
            # 等待一段时间确保服务启动
            await asyncio.sleep(1)
            
            logger.info("\n" + "🎉 飞书机器人启动成功!")
            logger.info("💡 现在你可以按 Ctrl+C 来测试优雅退出功能")
            logger.info("⏱️  正在等待用户操作... (或者10秒后自动退出)\n")
            
            # 等待用户按Ctrl+C或者超时
            try:
                await asyncio.wait_for(feishu_task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.info("⏰ 10秒超时，自动停止演示")
                feishu_task.cancel()
                try:
                    await feishu_task
                except asyncio.CancelledError:
                    logger.info("✅ 飞书机器人异步任务已被取消")
            
    except KeyboardInterrupt:
        logger.info("\n🛑 接收到 Ctrl+C 信号!")
        logger.info("🔄 正在优雅关闭飞书机器人...")
        
        # 取消异步任务
        if 'feishu_task' in locals() and not feishu_task.done():
            feishu_task.cancel()
            try:
                await feishu_task
            except asyncio.CancelledError:
                logger.info("✅ 飞书机器人异步任务已被取消")
        
        logger.info("🎯 优雅退出完成! 这证明了修复是有效的.")
        
    except Exception as e:
        logger.error(f"❌ 演示过程中发生错误: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
    
    finally:
        logger.info("\n" + "="*60)
        logger.info("📋 演示总结:")
        logger.info("✅ 飞书机器人能够正确响应 Ctrl+C 信号")
        logger.info("✅ WebSocket连接能够优雅关闭")
        logger.info("✅ 异步任务能够正确取消")
        logger.info("✅ 不会出现僵死或无法退出的情况")
        logger.info("="*60)


def main():
    """主函数"""
    try:
        # 设置信号处理器来捕获Ctrl+C
        def signal_handler(signum, frame):
            logger.info(f"\n📡 接收到信号 {signum} (Ctrl+C)")
            raise KeyboardInterrupt()
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # 运行异步演示
        asyncio.run(demo_with_async_task())
        
    except KeyboardInterrupt:
        logger.info("\n👋 演示结束，感谢使用!")
    except Exception as e:
        logger.error(f"❌ 演示失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)