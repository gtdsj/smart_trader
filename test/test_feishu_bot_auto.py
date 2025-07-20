#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书机器人服务自动化测试脚本

自动运行飞书机器人的基本功能测试，无需用户交互
"""

import sys
import os
import asyncio
from unittest.mock import Mock, AsyncMock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.feishu_bot_service import FeishuBotService
from loguru import logger


async def test_feishu_bot_service():
    """自动化测试飞书机器人服务"""
    logger.info("开始飞书机器人服务自动化测试...")
    
    try:
        # 创建模拟的服务依赖
        mock_strategy_manager = Mock()
        mock_stock_screener = Mock()
        mock_data_service = Mock()
        
        # 创建模拟策略管理器类
        class MockStrategyManager:
            def __init__(self):
                self.strategies = {
            "趋势跟踪策略": {
                "id": 1,
                "name": "趋势跟踪策略",
                "type": "技术分析",
                "description": "基于移动平均线的趋势跟踪策略",
                "parameters": {
                    "ma_period": 20,
                    "stop_loss": 0.05
                },
                "performance": {
                    "annual_return": "15.2%",
                    "sharpe_ratio": "1.25",
                    "max_drawdown": "8.5%",
                    "win_rate": "65%"
                },
                "created_at": "2024-01-01",
                "updated_at": "2024-01-15"
            },
            "均值回归策略": {
                "id": 2,
                "name": "均值回归策略",
                "type": "统计套利",
                "description": "基于价格均值回归的交易策略",
                "parameters": {
                    "lookback_period": 30,
                    "threshold": 2.0
                },
                "performance": {
                    "annual_return": "12.8%",
                    "sharpe_ratio": "1.15",
                    "max_drawdown": "6.2%",
                    "win_rate": "58%"
                },
                "created_at": "2024-01-05",
                "updated_at": "2024-01-20"
            },
            "动量策略": {
                "id": 3,
                "name": "动量策略",
                "type": "技术分析",
                "description": "基于动量的交易策略",
                "parameters": {
                    "momentum_period": 14,
                    "threshold": 0.02
                },
                "performance": {
                    "annual_return": "18.5%",
                    "sharpe_ratio": "1.35",
                    "max_drawdown": "10.2%",
                    "win_rate": "62%"
                },
                "created_at": "2024-01-10",
                "updated_at": "2024-01-25"
            }
                }
            
            async def get_strategies(self):
                """异步获取策略列表"""
                return [
                    {"id": 1, "name": "趋势跟踪策略", "description": "基于趋势的交易策略"},
                    {"id": 2, "name": "均值回归策略", "description": "基于均值回归的交易策略"},
                    {"id": 3, "name": "动量策略", "description": "基于动量的交易策略"}
                ]
            
            async def get_strategy_by_id(self, strategy_id):
                """异步根据ID获取策略"""
                for strategy in self.strategies.values():
                    if strategy["id"] == strategy_id:
                        return strategy
                return None
        
        # 创建模拟股票筛选服务类
        class MockStockScreener:
            def __init__(self):
                pass
            
            async def screen_stocks_by_strategy(self, strategy_id, stock_list=None, limit=20, date=None):
                """模拟股票筛选"""
                return {
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
                }
        
        # 创建模拟服务实例
        mock_strategy_manager = MockStrategyManager()
        mock_stock_screener = MockStockScreener()
        
        # 使用模拟的飞书客户端
        with patch('services.feishu_bot_service.Client'), \
             patch('services.feishu_bot_service.Config'):
            
            # 创建飞书机器人服务
            bot_service = FeishuBotService(
                app_id="test_app_id",
                app_secret="test_app_secret"
            )
            
            # 设置依赖服务
            bot_service.set_strategy_manager(mock_strategy_manager)
            bot_service.set_stock_screener(mock_stock_screener)
            bot_service.set_data_service(mock_data_service)
            
            logger.info("✅ 飞书机器人服务初始化成功")
            
            # 测试各种消息处理
            test_cases = [
                {
                    "message": "获取可用策略列表",
                    "expected_keywords": ["可用策略列表", "趋势跟踪策略", "均值回归策略", "动量策略"]
                },
                {
                    "message": "根据id为1的策略筛选股票",
                    "expected_keywords": ["策略筛选结果", "平安银行", "万科A"]
                },
                {
                    "message": "根据策略'趋势跟踪策略'筛选股票",
                    "expected_keywords": ["策略筛选结果", "趋势跟踪策略"]
                },
                {
                    "message": "获取策略1详情",
                    "expected_keywords": ["策略详情", "趋势跟踪策略"]
                },
                {
                    "message": "帮助",
                    "expected_keywords": ["智能量化交易助手", "获取可用策略列表", "根据id为1的策略筛选股票"]
                },
                {
                    "message": "未知指令",
                    "expected_keywords": ["抱歉，我不理解您的指令", "帮助"]
                }
            ]
            
            success_count = 0
            total_count = len(test_cases)
            
            for i, test_case in enumerate(test_cases, 1):
                message = test_case["message"]
                expected_keywords = test_case["expected_keywords"]
                
                logger.info(f"\n测试 {i}/{total_count}: {message}")
                
                try:
                    response = await bot_service._process_message(message)
                    
                    # 检查响应是否包含期望的关键词
                    missing_keywords = []
                    for keyword in expected_keywords:
                        if keyword not in response:
                            missing_keywords.append(keyword)
                    
                    if missing_keywords:
                        logger.warning(f"❌ 测试失败 - 缺少关键词: {missing_keywords}")
                        logger.info(f"响应内容: {response[:200]}...")
                    else:
                        logger.info(f"✅ 测试通过")
                        success_count += 1
                    
                    logger.info(f"响应长度: {len(response)} 字符")
                    
                except Exception as e:
                    logger.error(f"❌ 测试失败 - 异常: {e}")
                    import traceback
                    logger.error(f"错误详情: {traceback.format_exc()}")
                
                logger.info("-" * 50)
            
            # 输出测试结果总结
            logger.info(f"\n📊 测试结果总结:")
            logger.info(f"总测试数: {total_count}")
            logger.info(f"成功数: {success_count}")
            logger.info(f"失败数: {total_count - success_count}")
            logger.info(f"成功率: {success_count/total_count*100:.1f}%")
            
            if success_count == total_count:
                logger.info("🎉 所有测试通过！")
            else:
                logger.warning(f"⚠️ 有 {total_count - success_count} 个测试失败")
            
            return success_count == total_count
            
    except Exception as e:
        logger.error(f"❌ 测试过程中发生异常: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return False


def main():
    """主函数"""
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    logger.info("🚀 启动飞书机器人服务自动化测试")
    logger.info("=" * 60)
    
    # 运行异步测试
    success = asyncio.run(test_feishu_bot_service())
    
    logger.info("=" * 60)
    if success:
        logger.info("🎉 自动化测试完成 - 所有测试通过")
        sys.exit(0)
    else:
        logger.error("❌ 自动化测试完成 - 存在失败的测试")
        sys.exit(1)


if __name__ == "__main__":
    main()