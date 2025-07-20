#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书机器人服务优化测试脚本

测试优化后的FeishuBotService是否能正常工作
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s')
logger = logging.getLogger(__name__)

def test_bot_initialization():
    """测试飞书机器人初始化"""
    try:
        logger.info("🚀 开始测试飞书机器人初始化...")
        
        # Mock所有依赖的服务
        with patch('services.data_service.DataService') as mock_data_service, \
             patch('services.strategy_manager.StrategyManager') as mock_strategy_manager, \
             patch('services.stock_screener.StockScreener') as mock_stock_screener:
            
            # 设置mock返回值
            mock_data_service.get_instance.return_value = Mock()
            mock_strategy_manager.return_value = Mock()
            mock_stock_screener.return_value = Mock()
            
            # 导入FeishuBotService
            from services.feishu_bot_service import FeishuBotService
            
            # 创建机器人服务实例
            bot_service = FeishuBotService(
                app_id="test_app_id",
                app_secret="test_app_secret"
            )
            
            # 验证初始化成功
            assert bot_service is not None, "机器人服务初始化失败"
            assert bot_service.app_id == "test_app_id", "App ID设置错误"
            assert bot_service.app_secret == "test_app_secret", "App Secret设置错误"
            assert hasattr(bot_service, 'data_service'), "数据服务未初始化"
            assert hasattr(bot_service, 'strategy_manager'), "策略管理器未初始化"
            assert hasattr(bot_service, 'stock_screener'), "股票筛选器未初始化"
            
            logger.info("✅ 飞书机器人初始化测试通过")
            return True
            
    except Exception as e:
        logger.error(f"❌ 飞书机器人初始化测试失败: {e}")
        logger.error(f"Traceback: {e.__class__.__name__}: {str(e)}")
        return False

def test_message_processing():
    """测试消息处理功能"""
    try:
        logger.info("🚀 开始测试消息处理功能...")
        
        # Mock所有依赖的服务
        with patch('services.data_service.DataService') as mock_data_service, \
             patch('services.strategy_manager.StrategyManager') as mock_strategy_manager, \
             patch('services.stock_screener.StockScreener') as mock_stock_screener:
            
            # 设置mock返回值
            mock_data_service.get_instance.return_value = Mock()
            mock_strategy_manager_instance = Mock()
            mock_strategy_manager.return_value = mock_strategy_manager_instance
            mock_stock_screener.return_value = Mock()
            
            # 模拟策略管理器返回数据
            mock_strategy_manager_instance.get_strategies.return_value = [
                {"id": "1", "name": "测试策略1", "description": "这是一个测试策略"}
            ]
            
            # 导入FeishuBotService
            from services.feishu_bot_service import FeishuBotService
            
            # 创建机器人服务实例
            bot_service = FeishuBotService(
                app_id="test_app_id",
                app_secret="test_app_secret"
            )
            
            # Mock消息事件
            mock_event = Mock()
            mock_event.event.message.message_type = "text"
            mock_event.event.message.content = '{"text": "策略列表"}'
            mock_event.event.message.chat_id = "test_chat_id"
            mock_event.event.message.message_id = "test_message_id"
            
            # Mock发送响应方法
            with patch.object(bot_service, '_send_response') as mock_send:
                # 测试消息处理
                bot_service._handle_message(mock_event)
                
                # 验证发送响应被调用
                assert mock_send.called, "消息处理后未发送响应"
                
            logger.info("✅ 消息处理功能测试通过")
            return True
            
    except Exception as e:
        logger.error(f"❌ 消息处理功能测试失败: {e}")
        logger.error(f"Traceback: {e.__class__.__name__}: {str(e)}")
        return False

def test_bot_lifecycle():
    """测试机器人生命周期管理"""
    try:
        logger.info("🚀 开始测试机器人生命周期管理...")
        
        # Mock所有依赖的服务
        with patch('services.data_service.DataService') as mock_data_service, \
             patch('services.strategy_manager.StrategyManager') as mock_strategy_manager, \
             patch('services.stock_screener.StockScreener') as mock_stock_screener:
            
            # 设置mock返回值
            mock_data_service.get_instance.return_value = Mock()
            mock_strategy_manager.return_value = Mock()
            mock_stock_screener.return_value = Mock()
            
            # 导入FeishuBotService
            from services.feishu_bot_service import FeishuBotService
            
            # 创建机器人服务实例
            bot_service = FeishuBotService(
                app_id="test_app_id",
                app_secret="test_app_secret"
            )
            
            # 验证初始状态
            assert not bot_service._running, "机器人初始状态应该是未运行"
            
            # Mock WebSocket客户端
            with patch.object(bot_service, 'ws_client') as mock_ws_client:
                mock_ws_client.start.return_value = None
                mock_ws_client.stop.return_value = None
                
                # 测试启动
                bot_service.start()
                assert bot_service._running, "机器人启动后状态应该是运行中"
                
                # 测试停止
                bot_service.stop()
                assert not bot_service._running, "机器人停止后状态应该是未运行"
                
            logger.info("✅ 机器人生命周期管理测试通过")
            return True
            
    except Exception as e:
        logger.error(f"❌ 机器人生命周期管理测试失败: {e}")
        logger.error(f"Traceback: {e.__class__.__name__}: {str(e)}")
        return False

def main():
    """主测试函数"""
    logger.info("")
    logger.info("============================================================")
    logger.info("🤖 飞书机器人服务优化测试")
    logger.info("============================================================")
    logger.info("")
    
    # 运行所有测试
    tests = [
        ("飞书机器人初始化", test_bot_initialization),
        ("消息处理功能", test_message_processing),
        ("机器人生命周期管理", test_bot_lifecycle)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"📋 正在测试: {test_name}")
        result = test_func()
        results.append((test_name, result))
        logger.info(f"{'✅ 通过' if result else '❌ 失败'} - {test_name}")
        logger.info("")
    
    # 输出测试总结
    logger.info("")
    logger.info("============================================================")
    logger.info("📊 测试总结")
    logger.info("============================================================")
    
    passed_count = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{status} - {test_name}")
        if result:
            passed_count += 1
    
    logger.info("")
    logger.info(f"📈 测试结果: {passed_count}/{len(tests)} 通过")
    
    if passed_count == len(tests):
        logger.info("🎉 所有测试通过！飞书机器人服务优化成功")
        return True
    else:
        failed_count = len(tests) - passed_count
        logger.error(f"⚠️ {failed_count} 个测试失败，需要检查问题")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)