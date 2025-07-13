#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略API修复验证测试
验证策略API中的AttributeError修复是否成功
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import pytest
from loguru import logger
from services.strategy_service import StrategyService


class TestStrategyAPIFix:
    """策略API修复测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.strategy_service = StrategyService()
    
    @pytest.mark.asyncio
    async def test_get_strategies_returns_dict_list(self):
        """测试get_strategies方法返回字典列表"""
        logger.info("测试get_strategies方法返回格式")
        
        strategies = await self.strategy_service.get_strategies()
        
        # 验证返回类型
        assert isinstance(strategies, list), "get_strategies应该返回列表"
        
        if strategies:
            # 验证列表中的元素是字典
            first_strategy = strategies[0]
            assert isinstance(first_strategy, dict), "策略应该是字典格式"
            
            # 验证字典包含必要的键
            required_keys = ['id', 'name', 'description', 'strategy_type', 'parameters', 'is_active']
            for key in required_keys:
                assert key in first_strategy, f"策略字典应该包含键: {key}"
            
            # 验证可以通过字典键访问属性（这是修复的核心）
            strategy_id = first_strategy['id']
            strategy_name = first_strategy['name']
            is_active = first_strategy['is_active']
            
            logger.info(f"策略ID: {strategy_id}, 名称: {strategy_name}, 激活状态: {is_active}")
            
        logger.info("✅ get_strategies方法返回格式测试通过")
    
    @pytest.mark.asyncio
    async def test_create_strategy_success(self):
        """测试创建策略功能"""
        logger.info("测试创建策略功能")
        
        # 创建测试策略
        result = await self.strategy_service.create_strategy(
            name="测试策略",
            description="这是一个测试策略",
            strategy_type="technical",
            parameters={"test_param": "test_value"}
        )
        
        # 验证创建结果
        assert isinstance(result, bool), "create_strategy应该返回布尔值"
        logger.info(f"策略创建结果: {result}")
        
        logger.info("✅ 创建策略功能测试通过")
    
    @pytest.mark.asyncio
    async def test_strategy_statistics(self):
        """测试策略统计功能"""
        logger.info("测试策略统计功能")
        
        stats = await self.strategy_service.get_strategy_statistics()
        
        # 验证统计信息格式
        assert isinstance(stats, dict), "统计信息应该是字典格式"
        
        required_stats = ['total_strategies', 'active_strategies', 'inactive_strategies', 'available_strategy_types']
        for key in required_stats:
            assert key in stats, f"统计信息应该包含键: {key}"
            assert isinstance(stats[key], int), f"统计值{key}应该是整数"
        
        logger.info(f"策略统计信息: {stats}")
        logger.info("✅ 策略统计功能测试通过")
    
    def test_available_strategy_types(self):
        """测试获取可用策略类型"""
        logger.info("测试获取可用策略类型")
        
        strategy_types = self.strategy_service.get_available_strategy_types()
        
        # 验证返回格式
        assert isinstance(strategy_types, list), "策略类型应该是列表格式"
        assert len(strategy_types) > 0, "应该有可用的策略类型"
        
        for strategy_type in strategy_types:
            assert isinstance(strategy_type, str), "策略类型应该是字符串"
        
        logger.info(f"可用策略类型: {strategy_types}")
        logger.info("✅ 获取可用策略类型测试通过")
    
    def test_available_strategies(self):
        """测试获取可用策略实现"""
        logger.info("测试获取可用策略实现")
        
        strategies = self.strategy_service.get_available_strategies()
        
        # 验证返回格式
        assert isinstance(strategies, list), "策略实现应该是列表格式"
        assert len(strategies) > 0, "应该有可用的策略实现"
        
        for strategy in strategies:
            assert isinstance(strategy, str), "策略名称应该是字符串"
        
        logger.info(f"可用策略实现: {strategies}")
        logger.info("✅ 获取可用策略实现测试通过")


def test_strategy_api_fix_sync():
    """同步测试函数 - 验证策略API修复"""
    logger.info("\n=== 策略API修复验证测试 ===")
    
    async def run_tests():
        test_instance = TestStrategyAPIFix()
        test_instance.setup_method()
        
        try:
            # 测试策略列表格式
            await test_instance.test_get_strategies_returns_dict_list()
            
            # 测试策略统计
            await test_instance.test_strategy_statistics()
            
            # 测试可用策略类型
            test_instance.test_available_strategy_types()
            
            # 测试可用策略实现
            test_instance.test_available_strategies()
            
            logger.info("\n✅ 所有策略API修复验证测试通过")
            return True
            
        except Exception as e:
            logger.error(f"\n❌ 策略API修复验证测试失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return False
    
    # 运行异步测试
    try:
        result = asyncio.run(run_tests())
        assert result, "策略API修复验证失败"
    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        raise


if __name__ == "__main__":
    test_strategy_api_fix_sync()
    logger.info("策略API修复验证完成")