# -*- coding: utf-8 -*-
"""
测试自定义条件管理器功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

from services.custom_condition_manager import get_custom_condition_manager
from services.stock_screener import StockScreener
from services.data_service import DataService
from core.database import init_database


def create_test_stock_data(stock_code: str = "000001") -> pd.DataFrame:
    """创建测试股票数据"""
    dates = pd.date_range(start='2024-01-01', end='2024-01-30', freq='D')
    n_days = len(dates)
    
    # 生成模拟股票数据
    np.random.seed(42)  # 固定随机种子以便重现
    
    # 基础价格
    base_price = 10.0
    price_changes = np.random.normal(0, 0.02, n_days)  # 2%的日波动
    prices = [base_price]
    
    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 0.1))  # 确保价格不为负
    
    # 生成开高低收数据
    close_prices = prices
    open_prices = [close_prices[0]] + close_prices[:-1]  # 开盘价为前一日收盘价
    
    high_prices = []
    low_prices = []
    volumes = []
    
    for i in range(n_days):
        open_price = open_prices[i]
        close_price = close_prices[i]
        
        # 最高价和最低价
        daily_range = abs(close_price - open_price) * 0.5
        high_price = max(open_price, close_price) + np.random.uniform(0, daily_range)
        low_price = min(open_price, close_price) - np.random.uniform(0, daily_range)
        
        high_prices.append(high_price)
        low_prices.append(max(low_price, 0.1))  # 确保最低价不为负
        
        # 成交量
        base_volume = 1000000
        volume_change = np.random.uniform(0.5, 2.0)
        volumes.append(int(base_volume * volume_change))
    
    stock_data = pd.DataFrame({
        'date': dates,
        'open_price': open_prices,
        'high_price': high_prices,
        'low_price': low_prices,
        'close_price': close_prices,
        'volume': volumes
    })
    
    # 添加股票代码信息
    stock_data.attrs = {'stock_code': stock_code}
    
    return stock_data


def test_custom_condition_manager():
    """测试自定义条件管理器基本功能"""
    print("\n=== 测试自定义条件管理器基本功能 ===")
    
    manager = get_custom_condition_manager()
    
    # 列出所有注册的条件
    conditions = manager.list_conditions()
    print(f"已注册的自定义条件数量: {len(conditions)}")
    
    for condition in conditions:
        print(f"  - {condition['name']}: {condition['description']}")
    
    return True


def test_individual_conditions():
    """测试各个自定义条件"""
    print("\n=== 测试各个自定义条件 ===")
    
    manager = get_custom_condition_manager()
    stock_data = create_test_stock_data("000001")
    
    test_cases = [
        {
            "name": "连续收盘价高于MA5",
            "condition": {
                "condition_type": "custom",
                "indicator": "consecutive_close_above_ma5",
                "operator": "==",
                "value": True,
                "parameters": {"ma_period": 5, "consecutive_days": 3}
            }
        },
        {
            "name": "科创板股票判断",
            "condition": {
                "condition_type": "custom",
                "indicator": "is_kcb_stock",
                "operator": "==",
                "value": False,
                "parameters": {"stock_code": "000001"}
            }
        },
        {
            "name": "北交所股票判断",
            "condition": {
                "condition_type": "custom",
                "indicator": "is_bse_stock",
                "operator": "==",
                "value": False,
                "parameters": {"stock_code": "000001"}
            }
        },
        {
            "name": "连续收盘价高于开盘价",
            "condition": {
                "condition_type": "custom",
                "indicator": "consecutive_close_above_open",
                "operator": "==",
                "value": True,
                "parameters": {"consecutive_days": 2}
            }
        },
        {
            "name": "MA5角度最新值",
            "condition": {
                "condition_type": "custom",
                "indicator": "ma5_angle_latest",
                "operator": ">",
                "value": 0,
                "parameters": {"ma_period": 5}
            }
        },
        {
            "name": "最低价高于MA5",
            "condition": {
                "condition_type": "custom",
                "indicator": "low_above_ma5",
                "operator": "==",
                "value": True,
                "parameters": {"ma_period": 5}
            }
        }
    ]
    
    results = []
    for test_case in test_cases:
        try:
            result = manager.evaluate_custom_condition(
                test_case["condition"], 
                stock_data, 
                "000001"
            )
            results.append(result)
            print(f"✅ {test_case['name']}: {result}")
        except Exception as e:
            results.append(False)
            print(f"❌ {test_case['name']}: 失败 - {e}")
    
    success_count = sum(1 for r in results if r is not False)
    print(f"\n测试结果: {success_count}/{len(test_cases)} 个条件测试成功")
    
    return success_count == len(test_cases)


def test_stock_screener_integration():
    """测试与StockScreener的集成"""
    print("\n=== 测试与StockScreener的集成 ===")
    
    try:
        # 创建测试策略
        test_strategy = {
            "id": 999,
            "name": "自定义条件测试策略",
            "condition_details": [
                {
                    "condition_type": "custom",
                    "indicator": "is_kcb_stock",
                    "operator": "==",
                    "value": False,
                    "logic_operator": "AND",
                    "is_active": True
                },
                {
                    "condition_type": "custom",
                    "indicator": "consecutive_close_above_open",
                    "operator": "==",
                    "value": True,
                    "logic_operator": "AND",
                    "is_active": True,
                    "parameters": {"consecutive_days": 2}
                }
            ]
        }
        
        # 创建StockScreener实例
        screener = StockScreener()
        
        # 测试单只股票筛选
        result = screener._check_single_stock_strategy("000001", test_strategy, "2024-01-30")
        
        print(f"单只股票筛选结果: {result}")
        
        if result.get("matched") is not None:
            print("✅ StockScreener集成测试成功")
            return True
        else:
            print("❌ StockScreener集成测试失败")
            return False
            
    except Exception as e:
        print(f"❌ StockScreener集成测试失败: {e}")
        return False


def test_condition_registration():
    """测试条件注册功能"""
    print("\n=== 测试条件注册功能 ===")
    
    from services.custom_condition_manager import CustomConditionBase
    
    class TestCustomCondition(CustomConditionBase):
        """测试自定义条件"""
        
        def calculate(self, stock_data: pd.DataFrame, parameters: dict = None) -> bool:
            return True  # 简单返回True
        
        def get_name(self) -> str:
            return "test_condition"
        
        def get_description(self) -> str:
            return "测试条件"
    
    manager = get_custom_condition_manager()
    
    # 注册前的条件数量
    before_count = len(manager.list_conditions())
    
    # 注册新条件
    test_condition = TestCustomCondition()
    manager.register_condition(test_condition)
    
    # 注册后的条件数量
    after_count = len(manager.list_conditions())
    
    # 验证注册成功
    if after_count == before_count + 1:
        print("✅ 条件注册功能测试成功")
        
        # 测试注销功能
        manager.unregister_condition("test_condition")
        final_count = len(manager.list_conditions())
        
        if final_count == before_count:
            print("✅ 条件注销功能测试成功")
            return True
        else:
            print("❌ 条件注销功能测试失败")
            return False
    else:
        print("❌ 条件注册功能测试失败")
        return False


def test_user_strategy_conditions():
    """测试用户策略中的所有自定义条件"""
    print("\n=== 测试用户策略中的所有自定义条件 ===")
    
    # 从user_strategy_config.json中提取的自定义条件
    user_conditions = [
        "consecutive_close_above_ma5",
        "is_kcb_stock",
        "is_bse_stock",
        "is_st_stock",
        "consecutive_close_above_open",
        "ma5_angle_consecutive",
        "ma5_angle_latest",
        "ma10_angle_consecutive",
        "is_break_board",
        "main_fund_inflow",
        "low_above_ma5"
    ]
    
    manager = get_custom_condition_manager()
    stock_data = create_test_stock_data("000001")
    
    implemented_count = 0
    total_count = len(user_conditions)
    
    for condition_name in user_conditions:
        try:
            condition = manager.get_condition(condition_name)
            if condition:
                # 测试计算功能
                result = manager.calculate_condition(condition_name, stock_data, {}, "000001")
                if result is not None:
                    print(f"✅ {condition_name}: 已实现并可正常计算")
                    implemented_count += 1
                else:
                    print(f"⚠️  {condition_name}: 已注册但计算失败")
            else:
                print(f"❌ {condition_name}: 未找到实现")
        except Exception as e:
            print(f"❌ {condition_name}: 测试失败 - {e}")
    
    print(f"\n用户策略条件实现状态: {implemented_count}/{total_count}")
    
    return implemented_count == total_count


def main():
    """主测试函数"""
    print("开始测试自定义条件管理器...")
    
    # 初始化数据库（如果需要）
    try:
        init_database()
    except Exception as e:
        logger.warning(f"数据库初始化失败，继续测试: {e}")
    
    test_results = []
    
    # 运行各项测试
    test_results.append(test_custom_condition_manager())
    test_results.append(test_individual_conditions())
    test_results.append(test_stock_screener_integration())
    test_results.append(test_condition_registration())
    test_results.append(test_user_strategy_conditions())
    
    # 汇总测试结果
    success_count = sum(test_results)
    total_count = len(test_results)
    
    print(f"\n{'='*50}")
    print(f"测试完成: {success_count}/{total_count} 项测试通过")
    
    if success_count == total_count:
        print("🎉 所有测试通过！自定义条件管理器功能正常")
    else:
        print("⚠️  部分测试失败，请检查相关功能")
    
    print(f"{'='*50}")


if __name__ == "__main__":
    main()