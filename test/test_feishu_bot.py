#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书机器人服务测试脚本

测试飞书机器人的基本功能，包括:
1. 服务初始化
2. 消息处理逻辑
3. 策略列表获取
4. 股票筛选功能
"""

import sys
import os
import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.feishu_bot_service import FeishuBotService
from loguru import logger


class TestFeishuBotService(unittest.TestCase):
    """飞书机器人服务测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.app_id = "test_app_id"
        self.app_secret = "test_app_secret"
        
        # 创建模拟的服务依赖
        self.mock_strategy_service = Mock()
        self.mock_stock_screener = Mock()
        self.mock_data_service = Mock()
        
        # 模拟策略服务返回数据
        self.mock_strategy_service.strategies = {
            "趋势跟踪策略": Mock(),
            "均值回归策略": Mock(),
            "动量策略": Mock()
        }
        
        self.mock_strategy_service.get_strategies = AsyncMock(return_value=[
            {"id": 1, "name": "趋势跟踪策略", "description": "基于趋势的交易策略"},
            {"id": 2, "name": "均值回归策略", "description": "基于均值回归的交易策略"},
            {"id": 3, "name": "动量策略", "description": "基于动量的交易策略"}
        ])
        
        # 模拟股票筛选服务返回数据
        self.mock_stock_screener.screen_stocks_by_strategy = AsyncMock(return_value={
            "stocks": [
                {
                    "symbol": "000001.SZ",
                    "name": "平安银行",
                    "current_price": 12.50,
                    "change_percent": 2.5
                },
                {
                    "symbol": "000002.SZ",
                    "name": "万科A",
                    "current_price": 18.30,
                    "change_percent": -1.2
                }
            ],
            "timestamp": "2024-01-01 10:00:00",
            "total_count": 2
        })
    
    @patch('services.feishu_bot_service.Client')
    @patch('services.feishu_bot_service.Config')
    def test_init_feishu_bot_service(self, mock_config, mock_client):
        """测试飞书机器人服务初始化"""
        try:
            # 创建飞书机器人服务
            bot_service = FeishuBotService(
                app_id=self.app_id,
                app_secret=self.app_secret
            )
            
            # 设置依赖服务
            bot_service.set_strategy_service(self.mock_strategy_service)
            bot_service.set_stock_screener(self.mock_stock_screener)
            bot_service.set_data_service(self.mock_data_service)
            
            self.assertIsNotNone(bot_service)
            self.assertEqual(bot_service.app_id, self.app_id)
            self.assertEqual(bot_service.app_secret, self.app_secret)
            
            logger.info("✅ 飞书机器人服务初始化测试通过")
            
        except Exception as e:
            logger.error(f"❌ 飞书机器人服务初始化测试失败: {e}")
            raise
    
    @patch('services.feishu_bot_service.Client')
    @patch('services.feishu_bot_service.Config')
    def test_get_available_strategies(self, mock_config, mock_client):
        """测试获取可用策略列表"""
        async def run_test():
            try:
                # 创建飞书机器人服务
                bot_service = FeishuBotService(
                    app_id=self.app_id,
                    app_secret=self.app_secret
                )
                
                # 设置依赖服务
                bot_service.set_strategy_service(self.mock_strategy_service)
                bot_service.set_stock_screener(self.mock_stock_screener)
                bot_service.set_data_service(self.mock_data_service)
                
                # 测试获取策略列表
                response = await bot_service._process_message("获取可用策略列表")
                
                self.assertIn("可用策略列表", response)
                self.assertIn("趋势跟踪策略", response)
                self.assertIn("均值回归策略", response)
                self.assertIn("动量策略", response)
                
                logger.info("✅ 获取可用策略列表测试通过")
                logger.info(f"响应内容: {response}")
                
            except Exception as e:
                logger.error(f"❌ 获取可用策略列表测试失败: {e}")
                raise
        
        asyncio.run(run_test())
    
    @patch('services.feishu_bot_service.Client')
    @patch('services.feishu_bot_service.Config')
    def test_screen_stocks_by_strategy(self, mock_config, mock_client):
        """测试根据策略筛选股票"""
        async def run_test():
            try:
                # 创建飞书机器人服务
                bot_service = FeishuBotService(
                    app_id=self.app_id,
                    app_secret=self.app_secret
                )
                
                # 设置依赖服务
                bot_service.set_strategy_service(self.mock_strategy_service)
                bot_service.set_stock_screener(self.mock_stock_screener)
                bot_service.set_data_service(self.mock_data_service)
                
                # 测试根据策略ID筛选股票
                response = await bot_service._process_message("根据id为1的策略筛选股票")
                
                self.assertIn("策略筛选结果", response)
                self.assertIn("平安银行", response)
                self.assertIn("万科A", response)
                
                logger.info("✅ 根据策略筛选股票测试通过")
                logger.info(f"响应内容: {response}")
                
            except Exception as e:
                logger.error(f"❌ 根据策略筛选股票测试失败: {e}")
                raise
        
        asyncio.run(run_test())
    
    @patch('services.feishu_bot_service.Client')
    @patch('services.feishu_bot_service.Config')
    def test_help_message(self, mock_config, mock_client):
        """测试帮助信息"""
        async def run_test():
            try:
                # 创建飞书机器人服务
                bot_service = FeishuBotService(
                    app_id=self.app_id,
                    app_secret=self.app_secret
                )
                
                # 设置依赖服务
                bot_service.set_strategy_service(self.mock_strategy_service)
                bot_service.set_stock_screener(self.mock_stock_screener)
                bot_service.set_data_service(self.mock_data_service)
                
                # 测试帮助信息
                response = await bot_service._process_message("帮助")
                
                self.assertIn("智能量化交易助手", response)
                self.assertIn("获取可用策略列表", response)
                self.assertIn("根据id为X的策略筛选股票", response)
                
                logger.info("✅ 帮助信息测试通过")
                logger.info(f"响应内容: {response}")
                
            except Exception as e:
                logger.error(f"❌ 帮助信息测试失败: {e}")
                raise
        
        asyncio.run(run_test())
    
    @patch('services.feishu_bot_service.Client')
    @patch('services.feishu_bot_service.Config')
    def test_unknown_message(self, mock_config, mock_client):
        """测试未知消息处理"""
        async def run_test():
            try:
                # 创建飞书机器人服务
                bot_service = FeishuBotService(
                    app_id=self.app_id,
                    app_secret=self.app_secret
                )
                
                # 设置依赖服务
                bot_service.set_strategy_service(self.mock_strategy_service)
                bot_service.set_stock_screener(self.mock_stock_screener)
                bot_service.set_data_service(self.mock_data_service)
                
                # 测试未知消息
                response = await bot_service._process_message("这是一个未知的消息")
                
                self.assertIn("抱歉，我不理解您的指令", response)
                self.assertIn("帮助", response)
                
                logger.info("✅ 未知消息处理测试通过")
                logger.info(f"响应内容: {response}")
                
            except Exception as e:
                logger.error(f"❌ 未知消息处理测试失败: {e}")
                raise
        
        asyncio.run(run_test())


def run_manual_test():
    """手动测试函数"""
    logger.info("开始飞书机器人服务手动测试...")
    
    async def manual_test():
        try:
            # 创建模拟服务
            mock_strategy_service = Mock()
            mock_stock_screener = Mock()
            mock_data_service = Mock()
            
            # 模拟数据
            mock_strategy_service.strategies = {
                "趋势跟踪策略": Mock(),
                "均值回归策略": Mock()
            }
            
            mock_strategy_service.get_strategies = AsyncMock(return_value=[
                {"id": 1, "name": "趋势跟踪策略", "description": "基于趋势的交易策略"},
                {"id": 2, "name": "均值回归策略", "description": "基于均值回归的交易策略"}
            ])
            
            mock_stock_screener.screen_stocks_by_strategy = AsyncMock(return_value={
                "stocks": [
                    {
                        "symbol": "000001.SZ",
                        "name": "平安银行",
                        "current_price": 12.50,
                        "change_percent": 2.5
                    }
                ],
                "timestamp": "2024-01-01 10:00:00"
            })
            
            # 创建飞书机器人服务（使用模拟配置）
            with patch('services.feishu_bot_service.Client'), \
                 patch('services.feishu_bot_service.Config'):
                
                bot_service = FeishuBotService(
                    app_id="test_app_id",
                    app_secret="test_app_secret"
                )
                
                # 设置依赖服务
                bot_service.set_strategy_service(mock_strategy_service)
                bot_service.set_stock_screener(mock_stock_screener)
                bot_service.set_data_service(mock_data_service)
                
                # 测试各种消息
                test_messages = [
                    "获取可用策略列表",
                    "根据id为1的策略筛选股票",
                    "根据策略'趋势跟踪策略'筛选股票",
                    "获取策略1详情",
                    "帮助",
                    "未知指令"
                ]
                
                for message in test_messages:
                    logger.info(f"\n测试消息: {message}")
                    response = await bot_service._process_message(message)
                    logger.info(f"响应: {response}")
                    logger.info("-" * 50)
            
            logger.info("✅ 手动测试完成")
            
        except Exception as e:
            logger.error(f"❌ 手动测试失败: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
    
    asyncio.run(manual_test())


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    print("飞书机器人服务测试")
    print("=" * 50)
    print("1. 运行单元测试")
    print("2. 运行手动测试")
    print("=" * 50)
    
    choice = input("请选择测试类型 (1/2): ").strip()
    
    if choice == "1":
        # 运行单元测试
        unittest.main(argv=[''], exit=False, verbosity=2)
    elif choice == "2":
        # 运行手动测试
        run_manual_test()
    else:
        print("无效选择，运行手动测试")
        run_manual_test()