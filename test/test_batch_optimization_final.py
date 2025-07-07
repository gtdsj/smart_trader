#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量优化最终测试脚本
测试StockScreener的批量数据获取和DataFrame计算优化
"""

import sys
import os
import asyncio
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from services.data_service import DataService
from services.stock_screener import StockScreener

class MockDataService:
    """模拟数据服务，用于测试"""
    
    def __init__(self):
        self.call_count = 0
        
    async def get_batch_historical_data(self, stock_codes: List[str], start_date: str, 
                                      end_date: str, period: str = "1d") -> Dict[str, pd.DataFrame]:
        """模拟批量获取历史数据"""
        self.call_count += 1
        logger.info(f"模拟批量获取 {len(stock_codes)} 只股票数据")
        
        result = {}
        for stock_code in stock_codes:
            # 生成模拟数据
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            data = {
                'open_price': [10.0 + i * 0.1 for i in range(len(dates))],
                'high_price': [10.5 + i * 0.1 for i in range(len(dates))],
                'low_price': [9.5 + i * 0.1 for i in range(len(dates))],
                'close_price': [10.2 + i * 0.1 for i in range(len(dates))],
                'volume': [1000000 + i * 10000 for i in range(len(dates))],
                'amount': [10000000 + i * 100000 for i in range(len(dates))],
                'stock_code': [stock_code] * len(dates)
            }
            df = pd.DataFrame(data, index=dates)
            result[stock_code] = df
            
        return result
    
    async def get_stock_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """模拟获取单个股票数据"""
        batch_result = await self.get_batch_historical_data([stock_code], start_date, end_date)
        return batch_result.get(stock_code, pd.DataFrame())

async def test_batch_data_service():
    """测试批量数据获取服务"""
    logger.info("=== 测试批量数据获取服务 ===")
    
    mock_service = MockDataService()
    test_stocks = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '000858.SZ']
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    start_time = time.time()
    batch_data = await mock_service.get_batch_historical_data(
        stock_codes=test_stocks,
        start_date=start_date,
        end_date=end_date
    )
    duration = time.time() - start_time
    
    logger.info(f"批量获取 {len(test_stocks)} 只股票数据耗时: {duration:.3f}秒")
    logger.info(f"获取到 {len(batch_data)} 只股票的数据")
    
    # 验证数据格式
    for stock_code, df in batch_data.items():
        if not df.empty:
            logger.info(f"{stock_code}: {len(df)} 条数据, 列: {list(df.columns)}")
        else:
            logger.warning(f"{stock_code}: 无数据")
    
    return batch_data

async def test_stock_screener_batch():
    """测试StockScreener的批量处理功能"""
    logger.info("=== 测试StockScreener批量处理 ===")
    
    # 创建模拟数据服务
    mock_data_service = MockDataService()
    
    # 创建StockScreener实例
    screener = StockScreener(mock_data_service)
    
    # 测试股票列表
    test_stocks = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '000858.SZ']
    screen_date = datetime.now().strftime('%Y-%m-%d')
    
    # 测试策略筛选
    logger.info("测试批量策略筛选...")
    test_strategy = {
        "conditions": [
            {
                "condition_type": "fundamental",
                "indicator": "close_price",
                "operator": ">",
                "value": 10.0
            }
        ]
    }
    
    start_time = time.time()
    strategy_results = await screener._process_stock_batch_strategy(
        stock_batch=test_stocks,
        strategy=test_strategy,
        screen_date=screen_date
    )
    strategy_duration = time.time() - start_time
    
    logger.info(f"批量策略筛选耗时: {strategy_duration:.3f}秒")
    logger.info(f"策略筛选结果: {len(strategy_results)} 只股票符合条件")
    
    # 测试表达式筛选
    logger.info("测试批量表达式筛选...")
    test_expression = "close_price > 10.0"
    
    start_time = time.time()
    try:
        expression_results = await screener._process_stock_batch_expression(
            stock_batch=test_stocks,
            expression=test_expression,
            screen_date=screen_date
        )
        expression_duration = time.time() - start_time
        
        logger.info(f"批量表达式筛选耗时: {expression_duration:.3f}秒")
        logger.info(f"表达式筛选结果: {len(expression_results)} 只股票符合条件")
    except Exception as e:
        logger.warning(f"表达式筛选测试失败: {e}")
        expression_results = []
    
    return {
        "strategy_results": strategy_results,
        "expression_results": expression_results,
        "strategy_duration": strategy_duration,
        "data_service_calls": mock_data_service.call_count
    }

async def test_performance_comparison():
    """测试性能对比"""
    logger.info("=== 性能对比测试 ===")
    
    mock_data_service = MockDataService()
    screener = StockScreener(mock_data_service)
    
    # 测试不同规模的股票批次
    test_sizes = [5, 10, 20]
    screen_date = datetime.now().strftime('%Y-%m-%d')
    
    test_strategy = {
        "conditions": [
            {
                "condition_type": "fundamental",
                "indicator": "close_price",
                "operator": ">",
                "value": 10.0
            }
        ]
    }
    
    for size in test_sizes:
        test_stocks = [f"00000{i}.SZ" for i in range(1, size + 1)]
        
        # 重置调用计数
        mock_data_service.call_count = 0
        
        start_time = time.time()
        results = await screener._process_stock_batch_strategy(
            stock_batch=test_stocks,
            strategy=test_strategy,
            screen_date=screen_date
        )
        duration = time.time() - start_time
        
        logger.info(f"处理 {size} 只股票: 耗时 {duration:.3f}秒, 数据服务调用 {mock_data_service.call_count} 次, 符合条件 {len(results)} 只")

async def main():
    """主测试函数"""
    logger.info("开始批量优化最终测试")
    
    try:
        # 测试批量数据获取
        await test_batch_data_service()
        
        # 测试StockScreener批量处理
        screener_results = await test_stock_screener_batch()
        
        # 性能对比测试
        await test_performance_comparison()
        
        logger.info("=== 测试总结 ===")
        logger.info(f"数据服务总调用次数: {screener_results['data_service_calls']}")
        logger.info(f"策略筛选耗时: {screener_results['strategy_duration']:.3f}秒")
        logger.info(f"策略筛选结果: {len(screener_results['strategy_results'])} 只股票")
        logger.info(f"表达式筛选结果: {len(screener_results['expression_results'])} 只股票")
        
        logger.success("批量优化测试完成！")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())