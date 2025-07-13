#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试StockInfoUpdater单例模式实现

验证单例模式是否正确工作，确保全局只有一个实例
"""

import sys
import os
import asyncio
import pytest
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.stock_info_updater import StockInfoUpdater
from utils.logger import get_logger

logger = get_logger(__name__)

def test_singleton_pattern():
    """测试单例模式"""
    print("=== 测试StockInfoUpdater单例模式 ===")
    
    # 测试1: 多次实例化应该返回同一个对象
    print("\n1. 测试多次实例化...")
    updater1 = StockInfoUpdater()
    updater2 = StockInfoUpdater()
    updater3 = StockInfoUpdater.get_instance()
    
    print(f"updater1 id: {id(updater1)}")
    print(f"updater2 id: {id(updater2)}")
    print(f"updater3 id: {id(updater3)}")
    
    # 验证是否为同一个实例
    assert updater1 is updater2, "updater1 和 updater2 应该是同一个实例"
    assert updater2 is updater3, "updater2 和 updater3 应该是同一个实例"
    assert updater1 is updater3, "updater1 和 updater3 应该是同一个实例"
    print("✅ 多次实例化返回同一个对象")
    
    # 测试2: 验证状态共享
    print("\n2. 测试状态共享...")
    updater1.test_attribute = "test_value"
    assert hasattr(updater2, 'test_attribute'), "updater2 应该有 test_attribute 属性"
    assert updater2.test_attribute == "test_value", "updater2.test_attribute 应该等于 'test_value'"
    print("✅ 实例间状态共享正常")
    
    # 测试3: 验证初始化只执行一次
    print("\n3. 测试初始化状态...")
    print(f"_initialized 状态: {updater1._initialized}")
    print(f"is_running 状态: {updater1.is_running}")
    assert updater1._initialized == True, "实例应该已初始化"
    print("✅ 初始化状态正确")
    
    # 测试4: 验证类方法
    print("\n4. 测试类方法获取实例...")
    updater4 = StockInfoUpdater.get_instance()
    assert updater4 is updater1, "通过类方法获取的实例应该与直接实例化的相同"
    print("✅ 类方法获取实例正常")
    
    print("\n=== 单例模式测试通过 ===")

@pytest.mark.asyncio
async def test_singleton_in_async_context():
    """测试异步环境下的单例模式"""
    print("\n=== 测试异步环境下的单例模式 ===")
    
    async def create_updater(name):
        """异步创建更新器"""
        updater = StockInfoUpdater()
        print(f"{name} 创建的实例 id: {id(updater)}")
        return updater
    
    # 并发创建多个实例
    tasks = [
        create_updater("Task1"),
        create_updater("Task2"),
        create_updater("Task3")
    ]
    
    updaters = await asyncio.gather(*tasks)
    
    # 验证所有实例都是同一个
    for i, updater in enumerate(updaters):
        assert updater is updaters[0], f"updaters[{i}] 应该与 updaters[0] 是同一个实例"
    
    print("✅ 异步环境下单例模式正常")

@pytest.mark.asyncio
async def test_singleton_functionality():
    """测试单例的功能性"""
    print("\n=== 测试单例功能性 ===")
    
    updater = StockInfoUpdater()
    
    # 测试获取状态
    try:
        status = await updater.get_update_status()
        print(f"更新状态: {status}")
        print("✅ 获取状态功能正常")
    except Exception as e:
        print(f"⚠️ 获取状态失败（可能是数据库未初始化）: {e}")
    
    # 测试调度器状态
    print(f"调度器运行状态: {updater.is_running}")
    print("✅ 调度器状态访问正常")

def test_import_singleton():
    """测试导入的全局实例"""
    print("\n=== 测试导入的全局实例 ===")
    
    from services.stock_info_updater import stock_info_updater
    
    # 创建新实例
    new_updater = StockInfoUpdater()
    
    # 验证是否为同一个实例
    assert stock_info_updater is new_updater, "全局实例应该与新创建的实例相同"
    print(f"全局实例 id: {id(stock_info_updater)}")
    print(f"新实例 id: {id(new_updater)}")
    print("✅ 全局实例单例模式正常")

async def main():
    """主测试函数"""
    try:
        # 同步测试
        test_singleton_pattern()
        test_import_singleton()
        
        # 异步测试
        await test_singleton_in_async_context()
        await test_singleton_functionality()
        
        print("\n🎉 所有测试通过！StockInfoUpdater单例模式实现正确")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    print("开始测试StockInfoUpdater单例模式...")
    asyncio.run(main())
    print("测试完成！")