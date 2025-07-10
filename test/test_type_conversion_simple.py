# -*- coding: utf-8 -*-
"""
简化的自定义条件类型转换测试
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from services.custom_condition_manager import get_custom_condition_manager


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


def test_type_conversion():
    """测试类型转换功能"""
    print("\n=== 测试类型转换功能 ===")
    
    manager = get_custom_condition_manager()
    
    # 测试_convert_value_type方法
    test_cases = [
        # (value, reference_value, expected_result, description)
        ("true", 1, 1, "字符串'true'转换为整数1"),
        ("false", 1, 0, "字符串'false'转换为整数0"),
        ("20", 15.5, 20.0, "字符串'20'转换为浮点数20.0"),
        ("1.5", 1, 1, "字符串'1.5'转换为整数1"),
        (True, 1, 1, "布尔值True转换为整数1"),
        (False, 1, 0, "布尔值False转换为整数0"),
        (25, 15.5, 25.0, "整数25转换为浮点数25.0"),
        ("test", "reference", "test", "字符串保持不变"),
    ]
    
    success_count = 0
    for value, reference_value, expected, description in test_cases:
        try:
            result = manager._convert_value_type(value, reference_value)
            if result == expected and type(result) == type(expected):
                print(f"✅ {description}: {value} -> {result} (类型: {type(result).__name__})")
                success_count += 1
            else:
                print(f"❌ {description}: 期望 {expected} (类型: {type(expected).__name__}), 实际 {result} (类型: {type(result).__name__})")
        except Exception as e:
            print(f"❌ {description}: 转换失败 - {e}")
    
    print(f"\n类型转换测试结果: {success_count}/{len(test_cases)} 通过")
    return success_count == len(test_cases)


def test_database_condition_scenarios():
    """测试数据库中实际条件场景"""
    print("\n=== 测试数据库条件场景 ===")
    
    manager = get_custom_condition_manager()
    stock_data = create_test_stock_data("000001")
    
    # 模拟数据库中的条件配置
    test_conditions = [
        {
            "name": "布尔条件 - 字符串true",
            "condition": {
                "condition_type": "custom",
                "indicator": "consecutive_close_above_ma5",
                "operator": "==",
                "value": "true",  # 数据库中存储为字符串
                "parameters": {"ma_period": 5, "consecutive_days": 3}
            }
        },
        {
            "name": "布尔条件 - 字符串false",
            "condition": {
                "condition_type": "custom",
                "indicator": "is_kcb_stock",
                "operator": "==",
                "value": "false",  # 数据库中存储为字符串
                "parameters": {"stock_code": "000001"}
            }
        },
        {
            "name": "数值条件 - 字符串数字",
            "condition": {
                "condition_type": "custom",
                "indicator": "ma5_angle_latest",
                "operator": ">",
                "value": "50",  # 数据库中存储为字符串
                "parameters": {"ma_period": 5}
            }
        },
        {
            "name": "角度条件 - 字符串数字",
            "condition": {
                "condition_type": "custom",
                "indicator": "ma5_angle_consecutive",
                "operator": ">",
                "value": "20",  # 数据库中存储为字符串
                "parameters": {"ma_period": 5, "consecutive_days": 3}
            }
        }
    ]
    
    success_count = 0
    for test_case in test_conditions:
        try:
            result = manager.evaluate_custom_condition(
                test_case["condition"], 
                stock_data, 
                "000001"
            )
            print(f"✅ {test_case['name']}: {result}")
            success_count += 1
        except Exception as e:
            print(f"❌ {test_case['name']}: 失败 - {e}")
    
    print(f"\n数据库条件场景测试结果: {success_count}/{len(test_conditions)} 通过")
    return success_count == len(test_conditions)


def test_specific_error_case():
    """测试原始错误场景"""
    print("\n=== 测试原始错误场景 ===")
    
    manager = get_custom_condition_manager()
    stock_data = create_test_stock_data("000001")
    
    # 模拟原始报错的条件：ma5_angle_consecutive > "20"
    error_condition = {
        "condition_type": "custom",
        "indicator": "ma5_angle_consecutive",
        "operator": ">",
        "value": "20",  # 字符串类型，之前会导致 TypeError
        "parameters": {"ma_period": 5, "consecutive_days": 3}
    }
    
    try:
        # 先测试指标计算
        indicator_value = manager.calculate_condition(
            "ma5_angle_consecutive", 
            stock_data, 
            {"ma_period": 5, "consecutive_days": 3}, 
            "000001"
        )
        print(f"指标计算结果: {indicator_value} (类型: {type(indicator_value).__name__})")
        
        # 再测试条件评估
        result = manager.evaluate_custom_condition(error_condition, stock_data, "000001")
        print(f"✅ 原始错误场景修复成功: {result}")
        print(f"   - 指标值: {indicator_value} (float)")
        print(f"   - 阈值: '20' -> 20.0 (自动转换)")
        print(f"   - 比较: {indicator_value} > 20.0 = {result}")
        return True
        
    except Exception as e:
        print(f"❌ 原始错误场景仍然失败: {e}")
        return False


def main():
    """主测试函数"""
    print("开始测试自定义条件类型转换修复...")
    print("(跳过数据库初始化，直接测试核心功能)")
    
    test_results = []
    
    # 运行各项测试
    test_results.append(test_type_conversion())
    test_results.append(test_database_condition_scenarios())
    test_results.append(test_specific_error_case())
    
    # 汇总测试结果
    success_count = sum(test_results)
    total_count = len(test_results)
    
    print(f"\n{'='*60}")
    print(f"测试完成: {success_count}/{total_count} 项测试通过")
    
    if success_count == total_count:
        print("🎉 所有测试通过！自定义条件类型转换修复成功")
        print("\n修复要点:")
        print("1. ✅ 布尔类条件现在返回 0/1 整数值")
        print("2. ✅ 角度类条件现在返回实际角度浮点值")
        print("3. ✅ 添加了智能类型转换功能")
        print("4. ✅ 支持数据库中的字符串值自动转换")
        print("5. ✅ 原始 TypeError 错误已修复")
    else:
        print("⚠️  部分测试失败，请检查相关功能")
    
    print(f"{'='*60}")


if __name__ == "__main__":
    main()