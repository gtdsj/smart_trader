# -*- coding: utf-8 -*-
"""
添加用户策略到数据库
"""

import json
import asyncio
from typing import Dict, Any
from loguru import logger

from core.database import init_database
from services.strategy_manager import StrategyManager
from strategy_config_generator import generate_user_strategy_config


def add_strategy_to_database():
    """
    将用户策略配置添加到数据库
    """
    try:
        # 初始化数据库
        logger.info("初始化数据库...")
        init_database()
        
        # 生成策略配置
        strategy_config = generate_user_strategy_config()
        
        # 打印配置用于调试
        print("\n=== 调试信息 ===")
        for i, condition in enumerate(strategy_config['conditions'], 1):
            print(f"条件{i}: {condition['indicator']} {condition['operator']} {condition['value']}")
            if condition['operator'] == 'between':
                print(f"  区间值类型: {type(condition['value'])}, 内容: {condition['value']}")
        
        # 创建策略管理器
        strategy_manager = StrategyManager()
        
        # 准备数据库格式的策略数据
        db_strategy_data = {
            "name": strategy_config["name"],
            "description": strategy_config["description"],
            "strategy_type": strategy_config["strategy_type"],
            "category": strategy_config["category"],
            "parameters": strategy_config["parameters"],
            "priority": strategy_config["priority"],
            "created_by": strategy_config["created_by"],
            "version": strategy_config["version"],
            "conditions": []
        }
        
        # 转换条件格式（保持原始数据类型用于验证）
        for condition in strategy_config["conditions"]:
            db_condition = {
                "condition_type": condition["condition_type"],
                "indicator": condition["indicator"],
                "operator": condition["operator"],
                "value": condition["value"],  # 保持原始类型
                "logic_operator": condition["logic_operator"],
                "is_active": condition["is_active"]
            }
            db_strategy_data["conditions"].append(db_condition)
        
        # 创建策略
        print("\n开始创建策略...")
        result = strategy_manager.create_strategy(db_strategy_data)
        print(f"策略创建结果: {result}")
        
        if result["success"]:
            logger.info(f"策略创建成功: {result}")
            print(f"✅ 策略 '{strategy_config['name']}' 已成功添加到数据库")
            print(f"策略ID: {result['data']['strategy_id']}")
        else:
            logger.error(f"策略创建失败: {result}")
            print(f"❌ 策略创建失败: {result['message']}")
            print(f"详细错误信息: {result}")
            
    except Exception as e:
        logger.error(f"添加策略到数据库失败: {e}")
        print(f"❌ 添加策略到数据库失败: {e}")


def show_implementation_status():
    """
    显示实现状态
    """
    try:
        with open("implementation_summary.json", 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        print("\n" + "="*50)
        print("策略条件实现状态总结")
        print("="*50)
        
        print(f"\n📊 总体统计:")
        print(f"   总条件数: {summary['total_conditions']}")
        print(f"   已实现: {len(summary['implemented_conditions'])}")
        print(f"   需要实现: {len(summary['need_implementation'])}")
        print(f"   需要数据源: {len(summary['need_data_source'])}")
        
        print(f"\n✅ 已实现的条件:")
        for condition in summary['implemented_conditions']:
            print(f"   • {condition}")
        
        print(f"\n🔧 需要实现的条件:")
        for item in summary['need_implementation']:
            print(f"   • {item['condition']}")
            print(f"     状态: {item['status']}")
            print(f"     复杂度: {item['complexity']}")
            print()
        
        print(f"📡 需要数据源的条件:")
        for item in summary['need_data_source']:
            print(f"   • {item['condition']}")
            print(f"     所需数据: {item['required_data']}")
            print(f"     复杂度: {item['complexity']}")
            print()
        
        print(f"💡 建议:")
        for i, recommendation in enumerate(summary['recommendations'], 1):
            print(f"   {i}. {recommendation}")
        
        print("\n" + "="*50)
        
    except Exception as e:
        logger.error(f"显示实现状态失败: {e}")
        print(f"❌ 显示实现状态失败: {e}")


def main():
    """
    主函数
    """
    print("开始添加用户策略到数据库...")
    
    # 显示实现状态
    show_implementation_status()
    
    # 添加策略到数据库
    add_strategy_to_database()
    
    print("\n操作完成！")


if __name__ == "__main__":
    main()