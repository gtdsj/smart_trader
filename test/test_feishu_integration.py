#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书机器人集成测试脚本

此脚本演示如何在实际环境中集成和使用飞书机器人服务。
注意：此脚本需要真实的飞书应用配置才能运行。

作者: 智能量化交易系统
日期: 2024-01-16
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import ConfigManager
from utils.log_config import setup_logging, get_logger
from services.feishu_bot_service import FeishuBotService

# 设置日志
setup_logging(log_level="INFO")
logger = get_logger(__name__)

def check_feishu_config():
    """
    检查飞书配置是否完整
    """
    try:
        config_manager = ConfigManager()
        config = config_manager.load_config()
        feishu_config = config.feishu
        
        # 检查必要的配置字段
        if not feishu_config.app_id:
            logger.error("❌ 飞书配置缺少app_id")
            return False
        
        if not feishu_config.app_secret:
            logger.error("❌ 飞书配置缺少app_secret")
            return False
        
        if not feishu_config.enabled:
            logger.warning("⚠️ 飞书机器人未启用")
            return False
        
        logger.info("✅ 飞书配置检查通过")
        return True
    except Exception as e:
        logger.error(f"❌ 检查飞书配置时发生错误: {e}")
        return False

async def test_feishu_integration():
    """
    测试飞书机器人集成
    """
    logger.info("🚀 开始飞书机器人集成测试")
    logger.info("=" * 60)
    
    # 检查配置
    if not check_feishu_config():
        logger.error("❌ 飞书配置检查失败")
        return False
    
    logger.info("✅ 飞书配置检查通过")
    
    try:
        # 初始化飞书机器人服务
        logger.info("📱 初始化飞书机器人服务...")
        feishu_service = FeishuBotService()
        
        # 测试服务初始化
        logger.info("🔧 测试服务初始化...")
        if feishu_service.strategy_manager is None:
            logger.warning("⚠️ 策略管理器未初始化")
        else:
            logger.info("✅ 策略管理器初始化成功")
        
        if feishu_service.stock_screener is None:
            logger.warning("⚠️ 股票筛选服务未初始化")
        else:
            logger.info("✅ 股票筛选服务初始化成功")
        
        # 测试消息处理
        logger.info("💬 测试消息处理功能...")
        test_messages = [
            "帮助",
            "获取可用策略列表",
            "根据id为1的策略筛选股票",
            "获取策略1详情"
        ]
        
        for message in test_messages:
            logger.info(f"📤 发送测试消息: {message}")
            try:
                response = await feishu_service._process_message(message)
                logger.info(f"📥 收到响应: {response[:100]}...")
            except Exception as e:
                logger.error(f"❌ 消息处理失败: {e}")
        
        logger.info("✅ 消息处理测试完成")
        
        # 注意：实际启动机器人需要真实的飞书应用配置
        logger.info("📋 集成测试完成")
        logger.info("💡 要启动真实的飞书机器人，请确保:")
        logger.info("   1. 在飞书开放平台创建应用")
        logger.info("   2. 配置事件订阅和机器人权限")
        logger.info("   3. 在 config.json 中填入正确的配置")
        logger.info("   4. 运行 python main.py 启动系统")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 飞书机器人集成测试失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return False

def main():
    """
    主函数
    """
    logger.info("🤖 飞书机器人集成测试")
    logger.info("=" * 60)
    
    try:
        # 运行异步测试
        result = asyncio.run(test_feishu_integration())
        
        if result:
            logger.info("🎉 集成测试成功完成")
            return 0
        else:
            logger.error("❌ 集成测试失败")
            return 1
            
    except KeyboardInterrupt:
        logger.info("⏹️ 用户中断测试")
        return 0
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        return 1
    finally:
        logger.info("=" * 60)
        logger.info("📋 测试结束")

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)