#!/usr/bin/env python3
# coding=utf-8
"""
添加自定义选股策略到数据库
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database import get_db, init_database, Strategy
from services.strategy_manager import StrategyCategory


def create_custom_stock_selection_strategy():
    """
    创建自定义选股策略
    """
    strategy_config = {
        "selection_criteria": {
            "basic_filters": {
                "exclude_kcb": True,  # 排除科创板
                "exclude_bse": True,  # 排除北交所
                "exclude_st": True,   # 排除ST股
                "exclude_broken_board": True  # 排除破板股
            },
            "technical_filters": {
                "close_above_ma5_days": 3,  # 3个交易日收盘价不低于5日均线
                "change_pct_range": [-5.0, 6.1],  # 涨跌幅范围
                "consecutive_yang_days": 2,  # 连续阳线天数
                "ma5_angle_threshold": 20,  # 5日均线角度阈值
                "ma5_angle_recent_threshold": 50,  # 最近一日5日均线角度阈值
                "ma5_angle_consecutive_days": 3,  # 5日均线角度连续天数
                "ma10_angle_threshold": 10,  # 10日均线角度阈值
                "ma10_angle_consecutive_days": 3,  # 10日均线角度连续天数
                "low_above_ma5": True  # 最低价高于5日均线
            },
            "fund_flow_filters": {
                "main_fund_inflow": True  # 主力资金净流入
            }
        },
        "scoring_weights": {
            "base_score": 20,
            "change_pct_weight": 20,
            "volume_weight": 20,
            "ma_angle_weight": 20,
            "price_position_weight": 20
        },
        "output_settings": {
            "max_stocks": 50,  # 最大选股数量
            "min_score": 60,   # 最低评分
            "sort_by": "score"  # 排序方式
        }
    }
    
    strategy_conditions = [
        {
            "condition_type": "basic_filter",
            "field": "stock_code",
            "operator": "not_starts_with",
            "value": "688",
            "description": "排除科创板股票"
        },
        {
            "condition_type": "basic_filter",
            "field": "stock_code",
            "operator": "not_starts_with",
            "value": ["8", "43"],
            "description": "排除北交所股票"
        },
        {
            "condition_type": "technical_indicator",
            "field": "close_vs_ma5",
            "operator": "greater_than",
            "value": 0,
            "period": 3,
            "description": "3个交易日收盘价不低于5日均线"
        },
        {
            "condition_type": "technical_indicator",
            "field": "change_pct",
            "operator": "between",
            "value": [-5.0, 6.1],
            "description": "涨跌幅在-5%到6.1%之间"
        },
        {
            "condition_type": "technical_indicator",
            "field": "close_vs_open",
            "operator": "greater_than",
            "value": 0,
            "period": 2,
            "description": "最近两个交易日收盘价高于开盘价"
        },
        {
            "condition_type": "technical_indicator",
            "field": "ma5_angle",
            "operator": "greater_than",
            "value": 20,
            "period": 3,
            "description": "连续3个交易日五日均线角度>20"
        },
        {
            "condition_type": "technical_indicator",
            "field": "ma5_angle",
            "operator": "greater_than",
            "value": 50,
            "period": 1,
            "description": "最近一个交易日五日均线角度>50"
        },
        {
            "condition_type": "technical_indicator",
            "field": "ma10_angle",
            "operator": "greater_than",
            "value": 10,
            "period": 3,
            "description": "连续3个交易日十日均线角度>10"
        },
        {
            "condition_type": "fund_flow",
            "field": "main_fund_net_inflow",
            "operator": "greater_than",
            "value": 0,
            "description": "最近一个交易日主力资金净流入"
        },
        {
            "condition_type": "technical_indicator",
            "field": "low_vs_ma5",
            "operator": "greater_than",
            "value": 0,
            "description": "最近一个交易日最低股价高于五日均线"
        }
    ]
    
    return {
        "name": "角度趋势选股",
        "description": "基于技术面、资金面等多维度条件的综合选股策略，包含基础过滤、技术指标和资金流向等多重筛选条件",
        "category": StrategyCategory.STOCK_SELECTION.value,
        "strategy_type": "custom_stock_selection",
        "config": strategy_config,
        "conditions": strategy_conditions,
        "is_active": True,
        "risk_level": "medium",
        "expected_return": 0.15,
        "max_drawdown": 0.08,
        "tags": ["选股", "技术分析", "多维度", "趋势", "资金流向"]
    }


def add_strategy_to_database():
    """
    将策略添加到数据库
    """
    try:
        strategy_data = create_custom_stock_selection_strategy()
        
        db_session = next(get_db())
        try:
            # 检查是否已存在同名策略
            existing_strategy = db_session.query(Strategy).filter(
                Strategy.name == strategy_data["name"]
            ).first()
            
            if existing_strategy:
                print(f"[WARNING] 策略'{strategy_data['name']}'已存在，将更新配置")
                
                # 更新现有策略
                for key, value in strategy_data.items():
                    if key != "conditions":  # conditions需要特殊处理
                        setattr(existing_strategy, key, value)
                        
                existing_strategy.updated_at = datetime.now()
                strategy = existing_strategy
                
            else:
                # 创建新策略
                strategy = Strategy(
                    name=strategy_data["name"],
                    description=strategy_data["description"],
                    category=strategy_data["category"],
                    strategy_type=strategy_data["strategy_type"],
                    parameters=strategy_data["config"],  # 使用parameters字段
                    conditions=strategy_data["conditions"],  # 添加conditions字段
                    is_active=strategy_data["is_active"],
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                db_session.add(strategy)
                
            db_session.commit()
            
            print(f"[INFO] 策略'{strategy_data['name']}'已成功添加到数据库，ID: {strategy.id}")
            
            # 打印策略信息
            print(f"\n策略信息:")
            print(f"ID: {strategy.id}")
            print(f"名称: {strategy.name}")
            print(f"描述: {strategy.description}")
            print(f"类别: {strategy.category}")
            print(f"类型: {strategy.strategy_type}")
            print(f"是否激活: {strategy.is_active}")
            print(f"优先级: {strategy.priority}")
            print(f"版本: {strategy.version}")
            print(f"创建时间: {strategy.created_at}")
            
            # 打印选股条件
            print(f"\n选股条件:")
            for i, condition in enumerate(strategy_data["conditions"], 1):
                print(f"{i}. {condition['description']}")
                
            return strategy.id
        finally:
            db_session.close()
            
    except Exception as e:
        print(f"[ERROR] 添加策略到数据库失败: {e}")
        raise


def main():
    """
    主函数
    """
    print("开始添加自定义选股策略到数据库...")
    
    # 初始化数据库
    print("初始化数据库...")
    init_database()
    
    try:
        strategy_id = add_strategy_to_database()
        print(f"\n✅ 策略添加成功！策略ID: {strategy_id}")
        
        print("\n📋 策略特点:")
        print("1. 多维度筛选：技术面 + 资金面 + 基本面")
        print("2. 严格的风控条件：排除高风险股票")
        print("3. 趋势跟踪：基于均线角度判断趋势强度")
        print("4. 资金确认：要求主力资金净流入")
        print("5. 智能评分：综合多个指标进行量化评分")
        
        print("\n🔧 使用方式:")
        print("1. 通过API接口 /api/v1/scheduler/stock-selection/run 手动执行")
        print("2. 通过定时任务每日自动执行（交易日9:00和15:30）")
        print("3. 结果将通过钉钉机器人推送")
        
        print("\n⚠️  注意事项:")
        print("1. 确保已配置钉钉机器人webhook和secret")
        print("2. 确保数据服务正常运行，有足够的历史数据")
        print("3. 建议在实盘使用前进行充分的回测验证")
        
    except Exception as e:
        print(f"\n❌ 策略添加失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()