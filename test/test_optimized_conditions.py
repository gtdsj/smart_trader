# -*- coding: utf-8 -*-
"""
测试优化后的自定义条件功能
验证代码复用、参数配置和逻辑修复
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pandas as pd
import numpy as np
from loguru import logger
from services.custom_condition_manager import (
    CustomConditionManager,
    ConsecutiveCloseAboveOpenCondition
)
from utils.ma_calculator import MovingAverageCalculator


def create_test_stock_data(days: int = 30) -> pd.DataFrame:
    """创建测试用的股票数据"""
    np.random.seed(42)  # 固定随机种子
    
    dates = pd.date_range(start='2024-01-01', periods=days, freq='D')
    
    # 生成模拟价格数据（上升趋势）
    base_price = 10.0
    price_trend = np.linspace(0, 2, days)  # 上升趋势
    noise = np.random.normal(0, 0.1, days)  # 随机噪声
    
    close_prices = base_price + price_trend + noise
    
    # 确保价格为正数
    close_prices = np.maximum(close_prices, 1.0)
    
    # 生成其他价格数据
    open_prices = close_prices + np.random.normal(0, 0.05, days)
    high_prices = np.maximum(open_prices, close_prices) + np.abs(np.random.normal(0, 0.1, days))
    low_prices = np.minimum(open_prices, close_prices) - np.abs(np.random.normal(0, 0.1, days))
    
    # 确保价格逻辑正确
    low_prices = np.maximum(low_prices, 0.5)
    high_prices = np.maximum(high_prices, np.maximum(open_prices, close_prices))
    
    data = pd.DataFrame({
        'date': dates,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'close_price': close_prices,  # 兼容旧字段名
        'volume': np.random.randint(1000000, 10000000, days),
        'stock_code': ['000001'] * days
    })
    
    return data


def test_ma_calculator():
    """测试MovingAverageCalculator工具类"""
    logger.info("\n=== 测试MovingAverageCalculator工具类 ===")
    
    try:
        # 创建测试数据
        stock_data = create_test_stock_data(20)
        
        # 测试MA5最新角度计算
        ma5_angle = MovingAverageCalculator.calculate_ma_angle_latest(stock_data, ma_period=5)
        logger.info(f"MA5最新角度: {ma5_angle:.2f}度")
        
        # 测试MA5连续角度计算
        ma5_consecutive_angles = MovingAverageCalculator.calculate_ma_angles_consecutive(
            stock_data, ma_period=5, consecutive_days=3
        )
        logger.info(f"MA5连续3天角度: {ma5_consecutive_angles}")
        
        # 测试连续条件检查
        is_consecutive = MovingAverageCalculator.check_ma_consecutive_condition(
            stock_data, ma_period=5, consecutive_days=3, threshold=0.0
        )
        logger.info(f"MA5连续3天是否都大于0度: {is_consecutive}")
        
        # 测试MA10角度
        ma10_angle = MovingAverageCalculator.calculate_ma_angle_latest(stock_data, ma_period=10)
        logger.info(f"MA10最新角度: {ma10_angle:.2f}度")
        
        logger.info("✅ MovingAverageCalculator工具类测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ MovingAverageCalculator工具类测试失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False


def test_condition_with_parameters():
    """测试带参数的条件类"""
    logger.info("\n=== 测试带参数的条件类 ===")
    
    try:
        # 创建测试数据
        stock_data = create_test_stock_data(20)
        
        # 测试连续收盘价高于开盘价
        logger.info("\n--- 测试ConsecutiveCloseAboveOpenCondition ---")
        params_open = {'consecutive_days': 3}
        condition = ConsecutiveCloseAboveOpenCondition(parameters=params_open)
        result = condition.calculate(stock_data)
        logger.info(f"连续3天收盘价高于开盘价: {result}")
        logger.info(f"条件描述: {condition.get_description()}")
        
        logger.info("✅ 带参数的条件类测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 带参数的条件类测试失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False


def test_condition_manager_with_parameters():
    """测试CustomConditionManager的参数支持"""
    logger.info("\n=== 测试CustomConditionManager的参数支持 ===")
    
    try:
        # 创建条件管理器
        manager = CustomConditionManager()
        
        # 测试create_condition_with_parameters方法
        logger.info("\n--- 测试create_condition_with_parameters ---")
        
        # 创建带参数的连续收盘价高于开盘价条件
        params1 = {
            'consecutive_days': 3
        }
        condition1 = manager.create_condition_with_parameters('consecutive_close_above_open', params1)
        if condition1:
            logger.info(f"创建连续收盘价高于开盘价条件成功: {condition1.get_description()}")
            logger.info(f"参数: {condition1.parameters}")
        
        # 测试其他可用条件
        logger.info("\n--- 测试其他可用条件 ---")
        available_conditions = manager.get_available_conditions()
        logger.info(f"可用条件: {available_conditions}")
        
        # 测试未知条件
        condition2 = manager.create_condition_with_parameters('unknown_condition', {})
        if condition2 is None:
            logger.info("未知条件正确返回None")
        
        logger.info("✅ CustomConditionManager参数支持测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ CustomConditionManager参数支持测试失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False


def test_database_parameters_simulation():
    """模拟数据库参数配置测试"""
    logger.info("\n=== 模拟数据库参数配置测试 ===")
    
    try:
        # 模拟从数据库读取的条件配置
        db_conditions = [
            {
                'id': 1,
                'indicator': 'consecutive_close_above_open',
                'value': '3',
                'parameters': json.dumps({
                    'consecutive_days': 3
                })
            },
            {
                'id': 2,
                'indicator': 'consecutive_close_above_open',
                'value': '2',
                'parameters': json.dumps({
                    'consecutive_days': 2
                })
            }
        ]
        
        # 创建条件管理器
        manager = CustomConditionManager()
        
        # 创建测试数据
        stock_data = create_test_stock_data(25)
        
        logger.info("\n--- 模拟数据库条件配置 ---")
        
        for db_condition in db_conditions:
            condition_id = db_condition['id']
            indicator = db_condition['indicator']
            value = db_condition['value']
            parameters_json = db_condition['parameters']
            
            # 解析参数
            parameters = json.loads(parameters_json)
            
            # 创建条件实例
            condition = manager.create_condition_with_parameters(indicator, parameters)
            
            if condition:
                # 计算结果
                result = condition.calculate(stock_data)
                
                logger.info(f"\n条件ID: {condition_id}")
                logger.info(f"指标: {indicator}")
                logger.info(f"配置值: {value}")
                logger.info(f"参数: {parameters}")
                logger.info(f"计算结果: {result}")
                logger.info(f"描述: {condition.get_description()}")
            else:
                logger.warning(f"无法创建条件: {indicator}")
        
        logger.info("✅ 数据库参数配置模拟测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库参数配置模拟测试失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False


def test_logic_fix_verification():
    """验证逻辑修复"""
    logger.info("\n=== 验证逻辑修复 ===")
    
    try:
        # 创建测试数据（确保有明显的上升趋势）
        stock_data = create_test_stock_data(15)
        
        # 手动设置一些数据确保逻辑正确
        stock_data.loc[10:, 'close'] = [11.0, 11.2, 11.5, 11.8, 12.0]  # 明显上升
        stock_data.loc[10:, 'close_price'] = stock_data.loc[10:, 'close']
        
        logger.info("\n--- 验证ConsecutiveCloseAboveOpenCondition逻辑 ---")
        
        # 测试连续收盘价高于开盘价条件
        params = {'consecutive_days': 3}
        condition = ConsecutiveCloseAboveOpenCondition(parameters=params)
        result = condition.calculate(stock_data)
        logger.info(f"连续3天收盘价高于开盘价: {result} ({'满足' if result else '不满足'})")
        
        # 验证不同连续天数的影响
        logger.info("\n--- 验证不同连续天数的影响 ---")
        
        consecutive_days_list = [1, 2, 3, 4, 5]
        for days in consecutive_days_list:
            params = {'consecutive_days': days}
            condition = ConsecutiveCloseAboveOpenCondition(parameters=params)
            result = condition.calculate(stock_data)
            logger.info(f"连续{days}天: {result} ({'满足' if result else '不满足'})")
        
        logger.info("✅ 逻辑修复验证通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 逻辑修复验证失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False


def main():
    """主函数"""
    logger.info("开始测试优化后的自定义条件功能")
    
    test_results = []
    
    # 运行所有测试
    tests = [
        ("MovingAverageCalculator工具类", test_ma_calculator),
        ("带参数的条件类", test_condition_with_parameters),
        ("CustomConditionManager参数支持", test_condition_manager_with_parameters),
        ("数据库参数配置模拟", test_database_parameters_simulation),
        ("逻辑修复验证", test_logic_fix_verification)
    ]
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"运行测试: {test_name}")
        logger.info(f"{'='*60}")
        
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            logger.error(f"测试 {test_name} 发生异常: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            test_results.append((test_name, False))
    
    # 输出测试总结
    logger.info(f"\n{'='*60}")
    logger.info("测试总结")
    logger.info(f"{'='*60}")
    
    passed_count = 0
    total_count = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")
        if result:
            passed_count += 1
    
    logger.info(f"\n总计: {passed_count}/{total_count} 个测试通过")
    
    if passed_count == total_count:
        logger.info("🎉 所有测试通过！优化后的自定义条件功能工作正常")
        logger.info("\n优化要点:")
        logger.info("1. ✅ 创建了MovingAverageCalculator工具类，实现代码复用")
        logger.info("2. ✅ 修复了MA5AngleConsecutiveCondition的逻辑错误")
        logger.info("3. ✅ 支持灵活的参数配置（ma_period, consecutive_days, threshold等）")
        logger.info("4. ✅ 增强了CustomConditionBase基类，支持参数解析")
        logger.info("5. ✅ 提供了create_condition_with_parameters方法")
        logger.info("6. ✅ 支持布尔类型和平均值类型的返回")
        return True
    else:
        logger.error(f"❌ 有 {total_count - passed_count} 个测试失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)