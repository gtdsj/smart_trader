# -*- coding: utf-8 -*-
"""
策略配置生成器
根据用户需求生成策略配置
"""

import json
from typing import Dict, List, Any
from datetime import datetime


def generate_user_strategy_config() -> Dict[str, Any]:
    """
    生成用户要求的策略配置
    
    策略要求：
    1. 3个交易日内每天的收盘价不低于5日均线
    2. 非科创板
    3. 非北交所
    4. 最近一个交易日收盘价涨跌幅在-5%到6.1%之间
    5. 非ST股
    6. 最近两个交易日收盘价都高于开盘价
    7. 连续3个交易日五日均线角度>20且最近一个交易日五日均线角度>50
    8. 连续3个交易日十日均线角度>10
    9. 非破板股
    10. 最近一个交易日主力资金净流入
    11. 最近一个交易日最低股价高于五日均线
    
    Returns:
        策略配置字典
    """
    
    strategy_config = {
        "name": "多因子选股策略",
        "description": "基于技术指标和市场特征的多因子选股策略，筛选符合多重条件的优质股票",
        "strategy_type": "multi_factor_selection",
        "category": "stock_selection",
        "parameters": {
            "lookback_days": 10,  # 回看天数
            "min_trading_days": 3,  # 最少交易天数
            "ma5_period": 5,  # 5日均线周期
            "ma10_period": 10,  # 10日均线周期
            "angle_calculation_window": 3  # 角度计算窗口
        },
        "priority": 80,
        "created_by": "user",
        "version": "1.0",
        "conditions": [
            # 条件1: 3个交易日内每天的收盘价不低于5日均线
            {
                "condition_type": "custom",
                "indicator": "consecutive_close_above_ma5",
                "operator": "==",
                "value": True,
                "logic_operator": "AND",
                "is_active": True,
                "description": "连续3个交易日收盘价不低于5日均线",
                "implementation_status": "需要实现",
                "parameters": {
                    "ma_period": 5,
                    "consecutive_days": 3
                }
            },
            # 条件2: 非科创板
            {
                "condition_type": "custom",
                "indicator": "is_kcb_stock",
                "operator": "==",
                "value": False,
                "logic_operator": "AND",
                "is_active": True,
                "description": "非科创板股票",
                "implementation_status": "已实现"
            },
            # 条件3: 非北交所
            {
                "condition_type": "custom",
                "indicator": "is_bse_stock",
                "operator": "==",
                "value": False,
                "logic_operator": "AND",
                "is_active": True,
                "description": "非北交所股票",
                "implementation_status": "已实现"
            },
            # 条件4: 最近一个交易日收盘价涨跌幅在-5%到6.1%之间
            {
                "condition_type": "technical",
                "indicator": "price_change_pct",
                "operator": "between",
                "value": {"min": -5.0, "max": 6.1},
                "logic_operator": "AND",
                "is_active": True,
                "description": "最近一个交易日涨跌幅在-5%到6.1%之间",
                "implementation_status": "已实现"
            },
            # 条件5: 非ST股
            {
                "condition_type": "custom",
                "indicator": "is_st_stock",
                "operator": "==",
                "value": False,
                "logic_operator": "AND",
                "is_active": True,
                "description": "非ST股票",
                "implementation_status": "需要完善（需要股票名称数据）"
            },
            # 条件6: 最近两个交易日收盘价都高于开盘价
            {
                "condition_type": "custom",
                "indicator": "consecutive_close_above_open",
                "operator": "==",
                "value": True,
                "logic_operator": "AND",
                "is_active": True,
                "description": "最近两个交易日收盘价都高于开盘价",
                "implementation_status": "需要实现",
                "parameters": {
                    "consecutive_days": 2
                }
            },
            # 条件7: 连续3个交易日五日均线角度>20且最近一个交易日五日均线角度>50
            {
                "condition_type": "custom",
                "indicator": "ma5_angle_consecutive",
                "operator": ">",
                "value": 20,
                "logic_operator": "AND",
                "is_active": True,
                "description": "连续3个交易日五日均线角度>20",
                "implementation_status": "已实现",
                "parameters": {
                    "ma_period": 5,
                    "consecutive_days": 3,
                    "min_angle": 20
                }
            },
            {
                "condition_type": "custom",
                "indicator": "ma5_angle_latest",
                "operator": ">",
                "value": 50,
                "logic_operator": "AND",
                "is_active": True,
                "description": "最近一个交易日五日均线角度>50",
                "implementation_status": "已实现",
                "parameters": {
                    "ma_period": 5,
                    "min_angle": 50
                }
            },
            # 条件8: 连续3个交易日十日均线角度>10
            {
                "condition_type": "custom",
                "indicator": "ma10_angle_consecutive",
                "operator": ">",
                "value": 10,
                "logic_operator": "AND",
                "is_active": True,
                "description": "连续3个交易日十日均线角度>10",
                "implementation_status": "已实现",
                "parameters": {
                    "ma_period": 10,
                    "consecutive_days": 3,
                    "min_angle": 10
                }
            },
            # 条件9: 非破板股
            {
                "condition_type": "custom",
                "indicator": "is_break_board",
                "operator": "==",
                "value": False,
                "logic_operator": "AND",
                "is_active": True,
                "description": "非破板股",
                "implementation_status": "需要完善（需要涨停板数据）"
            },
            # 条件10: 最近一个交易日主力资金净流入
            {
                "condition_type": "custom",
                "indicator": "main_fund_inflow",
                "operator": "==",
                "value": True,
                "logic_operator": "AND",
                "is_active": True,
                "description": "最近一个交易日主力资金净流入",
                "implementation_status": "需要完善（需要资金流数据）"
            },
            # 条件11: 最近一个交易日最低股价高于五日均线
            {
                "condition_type": "custom",
                "indicator": "low_above_ma5",
                "operator": "==",
                "value": True,
                "logic_operator": "AND",
                "is_active": True,
                "description": "最近一个交易日最低股价高于五日均线",
                "implementation_status": "已实现",
                "parameters": {
                    "ma_period": 5
                }
            }
        ]
    }
    
    return strategy_config


def get_implementation_summary() -> Dict[str, Any]:
    """
    获取实现状态总结
    
    Returns:
        实现状态总结
    """
    
    summary = {
        "total_conditions": 11,
        "implemented_conditions": [
            "非科创板股票筛选",
            "非北交所股票筛选",
            "价格涨跌幅筛选",
            "移动平均线角度计算",
            "最低价高于均线检查"
        ],
        "need_implementation": [
            {
                "condition": "连续3个交易日收盘价不低于5日均线",
                "status": "需要实现连续条件检查逻辑",
                "complexity": "中等"
            },
            {
                "condition": "最近两个交易日收盘价都高于开盘价",
                "status": "需要实现连续条件检查逻辑",
                "complexity": "简单"
            }
        ],
        "need_data_source": [
            {
                "condition": "非ST股票筛选",
                "required_data": "股票名称数据或ST标识",
                "complexity": "简单（数据获取）"
            },
            {
                "condition": "非破板股筛选",
                "required_data": "涨停板数据和破板标识",
                "complexity": "中等（数据获取）"
            },
            {
                "condition": "主力资金净流入",
                "required_data": "主力资金流向数据",
                "complexity": "高（数据获取）"
            }
        ],
        "recommendations": [
            "优先实现基于现有数据的条件（连续条件检查）",
            "接入更多数据源以支持ST股、破板股、资金流等条件",
            "考虑使用第三方数据服务（如Wind、东方财富等）",
            "建立数据质量监控机制确保策略的可靠性"
        ]
    }
    
    return summary


def save_strategy_config_to_file(config: Dict[str, Any], filename: str = "user_strategy_config.json"):
    """
    保存策略配置到文件
    
    Args:
        config: 策略配置
        filename: 文件名
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"策略配置已保存到: {filename}")
    except Exception as e:
        print(f"保存策略配置失败: {e}")


if __name__ == "__main__":
    # 生成策略配置
    config = generate_user_strategy_config()
    
    # 获取实现状态总结
    summary = get_implementation_summary()
    
    # 打印配置信息
    print("=== 策略配置 ===")
    print(f"策略名称: {config['name']}")
    print(f"策略描述: {config['description']}")
    print(f"条件数量: {len(config['conditions'])}")
    
    print("\n=== 实现状态总结 ===")
    print(f"总条件数: {summary['total_conditions']}")
    print(f"已实现条件数: {len(summary['implemented_conditions'])}")
    print(f"需要实现条件数: {len(summary['need_implementation'])}")
    print(f"需要数据源条件数: {len(summary['need_data_source'])}")
    
    # 保存配置到文件
    save_strategy_config_to_file(config)
    
    # 保存总结到文件
    with open("implementation_summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print("\n配置文件已生成完成！")