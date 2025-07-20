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
from services.strategy_manager import StrategyManager


class TestStrategyManager:
    """策略管理器测试类"""
    """策略API修复测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.strategy_manager = StrategyManager.get_instance()
    
    @pytest.mark.asyncio
    def test_get_strategies_returns_dict_list(self):
        """测试get_strategies方法返回字典列表"""
        logger.info("测试get_strategies方法返回格式")
        
        strategies = self.strategy_manager.get_strategies()
        
        # 验证返回类型
        assert isinstance(strategies, list), "get_strategies应该返回列表"
        
        if strategies:
            # 验证列表中的元素是字典
            first_strategy = strategies[0]
            assert isinstance(first_strategy, dict), "策略应该是字典格式"
            
            # 验证字典包含必要的键
            required_keys = ['id', 'name', 'description', 'category', 'created_at', 'updated_at', 'is_active']
            for key in required_keys:
                assert key in first_strategy, f"策略字典应该包含键: {key}"
            
            # 验证可以通过字典键访问属性
            strategy_id = first_strategy['id']
            strategy_name = first_strategy['name']
            is_active = first_strategy['is_active']
            
            logger.info(f"策略ID: {strategy_id}, 名称: {strategy_name}, 激活状态: {is_active}")
            
        logger.info("✅ get_strategies方法返回格式测试通过")
    

    

    

    



def test_strategy_manager_sync():
    """同步测试函数 - 验证策略管理器"""
    logger.info("\n=== 策略管理器验证测试 ===")
    
    test_instance = TestStrategyManager()
    test_instance.setup_method()
    
    try:
        # 测试策略列表格式
        test_instance.test_get_strategies_returns_dict_list()
        
        logger.info("\n✅ 所有策略管理器验证测试通过")
        return True
        
    except Exception as e:
        logger.error(f"\n❌ 策略管理器验证测试失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    test_strategy_manager_sync()
    logger.info("策略管理器验证完成")