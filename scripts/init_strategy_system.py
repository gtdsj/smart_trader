# -*- coding: utf-8 -*-
"""
策略管理系统初始化脚本
用于创建数据库表和初始化服务实例
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from config import get_settings
from core.database import (
    Base, Strategy, StrategyCondition, StrategyExecution, 
    StrategySignal, StockData, TradingOrder, Position
)
from services.strategy_manager import StrategyManager, StrategyCategory
from services.strategy_executor import StrategyExecutor
from services.data_service import DataService
from services.xtquant_service import XtQuantService


def create_database_tables():
    """创建数据库表"""
    try:
        settings = get_settings()
        
        # 创建数据库引擎
        # 使用DuckDB作为数据库
        database_url = settings.database.url
        engine = create_engine(
            database_url,
            echo=True
        )
        
        # 创建所有表
        Base.metadata.create_all(engine)
        
        logger.info("数据库表创建成功")
        
        # 关闭引擎
        engine.dispose()
        
    except Exception as e:
        logger.error(f"创建数据库表失败: {e}")
        raise


def create_sample_strategies():
    """创建示例策略"""
    try:
        from services.strategy_manager import StrategyManager
        from core.database import init_database, SessionLocal
        
        # 初始化数据库
        init_database()
        
        strategy_manager = StrategyManager()
        
        # 创建数据库会话
        session = SessionLocal()
        strategy_manager.session = session
        
        try:
            # 示例策略1：趋势突破策略
            trend_strategy = {
            "name": "趋势突破策略",
            "description": "基于移动平均线和成交量的趋势突破策略",
            "category": StrategyCategory.STOCK_SELECTION.value,
            "conditions": [
                {
                    "condition_type": "technical",
                    "indicator": "ma",
                    "operator": ">",
                    "value": {"period": 20, "compare_to": "close_price"},
                    "logic_operator": "AND",
                    "weight": 1.0,
                    "is_active": True,
                    "description": "收盘价突破20日均线"
                },
                {
                    "condition_type": "technical",
                    "indicator": "volume",
                    "operator": ">",
                    "value": {"period": 20, "multiplier": 1.5},
                    "logic_operator": "AND",
                    "weight": 0.8,
                    "is_active": True,
                    "description": "成交量放大1.5倍"
                },
                {
                    "condition_type": "technical",
                    "indicator": "rsi",
                    "operator": "between",
                    "value": {"period": 14, "min": 50, "max": 80},
                    "logic_operator": "AND",
                    "weight": 0.6,
                    "is_active": True,
                    "description": "RSI在50-80之间"
                }
            ],
            "parameters": {
                "scan_frequency": "daily",
                "max_positions": 10,
                "risk_level": "medium"
            },
            "priority": 1,
            "created_by": "system",
            "version": "1.0"
        }
        
            result1 = strategy_manager.create_strategy(trend_strategy)
            if result1["success"]:
                logger.info(f"创建趋势突破策略成功，ID: {result1['data']['id']}")
            
            # 示例策略2：超跌反弹策略
            oversold_strategy = {
            "name": "超跌反弹策略",
            "description": "基于RSI和布林带的超跌反弹策略",
            "category": StrategyCategory.STOCK_SELECTION.value,
            "conditions": [
                {
                    "condition_type": "technical",
                    "indicator": "rsi",
                    "operator": "<",
                    "value": {"period": 14, "threshold": 30},
                    "logic_operator": "AND",
                    "weight": 1.0,
                    "is_active": True,
                    "description": "RSI小于30，超跌"
                },
                {
                    "condition_type": "technical",
                    "indicator": "bollinger",
                    "operator": "<",
                    "value": {"period": 20, "component": "lower"},
                    "logic_operator": "AND",
                    "weight": 0.9,
                    "is_active": True,
                    "description": "价格跌破布林带下轨"
                },
                {
                    "condition_type": "technical",
                    "indicator": "price_change_pct",
                    "operator": "<",
                    "value": {"period": 5, "threshold": -10},
                    "logic_operator": "AND",
                    "weight": 0.7,
                    "is_active": True,
                    "description": "5日内跌幅超过10%"
                }
            ],
            "parameters": {
                "scan_frequency": "daily",
                "max_positions": 5,
                "risk_level": "high"
            },
            "priority": 2,
            "created_by": "system",
            "version": "1.0"
        }
        
            result2 = strategy_manager.create_strategy(oversold_strategy)
            if result2["success"]:
                logger.info(f"创建超跌反弹策略成功，ID: {result2['data']['id']}")
            
            # 示例策略3：MACD金叉策略
            macd_strategy = {
            "name": "MACD金叉策略",
            "description": "基于MACD指标的金叉买入策略",
            "category": StrategyCategory.BUY_SELL.value,
            "conditions": [
                {
                    "condition_type": "technical",
                    "indicator": "macd",
                    "operator": ">",
                    "value": {"component": "line", "compare_to": "signal"},
                    "logic_operator": "AND",
                    "weight": 1.0,
                    "is_active": True,
                    "description": "MACD线上穿信号线（金叉）"
                },
                {
                    "condition_type": "technical",
                    "indicator": "macd",
                    "operator": ">",
                    "value": {"component": "histogram", "threshold": 0},
                    "logic_operator": "AND",
                    "weight": 0.8,
                    "is_active": True,
                    "description": "MACD柱状图为正"
                },
                {
                    "condition_type": "technical",
                    "indicator": "volume",
                    "operator": ">",
                    "value": {"period": 10, "multiplier": 1.2},
                    "logic_operator": "AND",
                    "weight": 0.6,
                    "is_active": True,
                    "description": "成交量放大"
                }
            ],
            "parameters": {
                "scan_frequency": "daily",
                "position_size": 0.1,
                "stop_loss": 0.05,
                "take_profit": 0.15
            },
            "priority": 1,
            "created_by": "system",
            "version": "1.0"
        }
        
            result3 = strategy_manager.create_strategy(macd_strategy)
            if result3["success"]:
                logger.info(f"创建MACD金叉策略成功，ID: {result3['data']['id']}")
            
            # 提交事务
            session.commit()
            logger.info("示例策略创建完成")
            
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"创建示例策略失败: {e}")
        raise


def initialize_services():
    """初始化服务实例"""
    try:
        # 创建服务实例
        xtquant_service = XtQuantService()
        data_service = DataService()
        strategy_manager = StrategyManager()
        strategy_executor = StrategyExecutor()
        
        # 设置服务依赖关系
        data_service.set_xtquant_service(xtquant_service)
        strategy_executor.set_data_service(data_service)
        strategy_executor.set_strategy_manager(strategy_manager)
        
        logger.info("服务实例初始化完成")
        
        return {
            "xtquant_service": xtquant_service,
            "data_service": data_service,
            "strategy_manager": strategy_manager,
            "strategy_executor": strategy_executor
        }
        
    except Exception as e:
        logger.error(f"初始化服务实例失败: {e}")
        raise


def test_strategy_system():
    """测试策略系统"""
    try:
        # 初始化服务
        services = initialize_services()
        strategy_manager = services["strategy_manager"]
        strategy_executor = services["strategy_executor"]
        
        # 获取策略列表
        strategies = strategy_manager.get_strategies()
        logger.info(f"当前策略数量: {len(strategies)}")
        
        if strategies:
            # 测试执行第一个策略
            first_strategy = strategies[0]
            logger.info(f"测试执行策略: {first_strategy['name']}")
            
            # 执行策略（使用少量测试股票）
            test_stocks = ["000001.SZ", "000002.SZ", "600000.SH"]
            result = strategy_executor.execute_strategy(
                strategy_id=first_strategy["id"],
                stock_codes=test_stocks,
                execution_type="test"
            )
            
            if result["success"]:
                logger.info(f"策略执行成功，发现 {result['data']['signal_count']} 个信号")
                
                # 获取信号详情
                signals = strategy_executor.get_strategy_signals(
                    strategy_id=first_strategy["id"],
                    limit=10
                )
                
                logger.info(f"获取到 {len(signals)} 个信号记录")
                for signal in signals[:3]:  # 显示前3个信号
                    logger.info(f"信号: {signal['stock_code']} - {signal['signal_type']} - {signal['reason']}")
            else:
                logger.error(f"策略执行失败: {result['message']}")
        
        logger.info("策略系统测试完成")
        
    except Exception as e:
        logger.error(f"测试策略系统失败: {e}")
        raise


def main():
    """主函数"""
    try:
        logger.info("开始初始化策略管理系统...")
        
        # 1. 创建数据库表
        logger.info("步骤1: 创建数据库表")
        create_database_tables()
        
        # 2. 创建示例策略
        logger.info("步骤2: 创建示例策略")
        create_sample_strategies()
        
        # 3. 初始化服务
        logger.info("步骤3: 初始化服务实例")
        initialize_services()
        
        # 4. 测试策略系统
        logger.info("步骤4: 测试策略系统")
        test_strategy_system()
        
        logger.info("策略管理系统初始化完成！")
        
        print("\n=== 策略管理系统初始化完成 ===")
        print("可用的API接口:")
        print("1. 策略管理: /api/v1/strategy-manager/")
        print("   - POST /strategies - 创建策略")
        print("   - GET /strategies - 获取策略列表")
        print("   - GET /strategies/{id} - 获取策略详情")
        print("   - PUT /strategies/{id} - 更新策略")
        print("   - DELETE /strategies/{id} - 删除策略")
        print("   - POST /strategies/{id}/activate - 激活策略")
        print("   - POST /strategies/{id}/deactivate - 停用策略")
        print("")
        print("2. 策略执行: /api/v1/strategy-manager/")
        print("   - POST /execute - 执行策略")
        print("   - GET /signals - 获取策略信号")
        print("   - GET /executions - 获取执行历史")
        print("")
        print("3. 策略配置: /api/v1/strategy-manager/")
        print("   - GET /categories - 获取策略分类")
        print("   - GET /indicators - 获取可用指标")
        print("   - GET /operators - 获取操作符")
        print("   - GET /templates - 获取策略模板")
        
    except Exception as e:
        logger.error(f"初始化策略管理系统失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 配置日志
    logger.add(
        "logs/strategy_init.log",
        rotation="1 day",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
    )
    
    # 运行初始化
    main()