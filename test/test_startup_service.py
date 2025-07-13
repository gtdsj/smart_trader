#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试系统启动服务
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from services.startup_service import StartupService
from services.stock_info_cache_service import StockInfoCacheService


async def test_startup_service():
    """测试系统启动服务"""
    try:
        logger.info("开始测试系统启动服务...")
        
        # 创建启动服务实例
        startup_service = StartupService()
        
        # 测试系统初始化
        logger.info("\n=== 测试系统初始化 ===")
        init_result = await startup_service.initialize_system()
        logger.info(f"初始化结果: {init_result}")
        
        if not init_result['success']:
            logger.error("系统初始化失败，停止测试")
            return
        
        # 获取系统状态
        logger.info("\n=== 获取系统状态 ===")
        status = startup_service.get_system_status()
        logger.info(f"系统状态: {status}")
        
        # 测试缓存功能
        logger.info("\n=== 测试缓存功能 ===")
        cache_service = StockInfoCacheService()
        
        # 获取缓存状态
        cache_status = cache_service.get_cache_status()
        logger.info(f"缓存状态: {cache_status}")
        
        # 测试获取股票信息
        test_codes = ['000001.SZ', '000002.SZ', '600000.SH']
        for code in test_codes:
            stock_info = cache_service.get_stock_info(code)
            if stock_info:
                logger.info(f"股票 {code}: {stock_info['stock_name']} - 交易: {stock_info['is_trading']} - ST: {stock_info['is_st']}")
            else:
                logger.warning(f"未找到股票 {code} 的信息")
        
        # 测试按条件查询
        logger.info("\n=== 测试条件查询 ===")
        
        # 查询总数
        all_stocks = cache_service.get_all_stocks()
        logger.info(f"缓存中总股票数: {len(all_stocks)}")
        
        # 查询ST股票
        st_stocks = cache_service.get_stocks_by_condition(is_st=True)
        logger.info(f"ST股票数量: {len(st_stocks)}")
        
        # 查询停牌股票
        suspended_stocks = cache_service.get_stocks_by_condition(is_trading=False)
        logger.info(f"停牌股票数量: {len(suspended_stocks)}")
        
        # 查询深圳股票
        sz_stocks = cache_service.get_stocks_by_condition(market='SZ')
        logger.info(f"深圳股票数量: {len(sz_stocks)}")
        
        # 查询上海股票
        sh_stocks = cache_service.get_stocks_by_condition(market='SH')
        logger.info(f"上海股票数量: {len(sh_stocks)}")
        
        # 测试搜索功能
        logger.info("\n=== 测试搜索功能 ===")
        search_keywords = ['银行', '科技', '医药']
        for keyword in search_keywords:
            results = cache_service.search_stocks(keyword)
            logger.info(f"搜索'{keyword}': {len(results)} 只股票")
            if results:
                # 显示前3个结果
                for stock in results[:3]:
                    logger.info(f"  {stock['stock_code']} - {stock['stock_name']}")
        
        # 等待一段时间，观察定时更新器
        logger.info("\n=== 等待观察定时更新器 ===")
        logger.info("等待10秒，观察系统运行状态...")
        await asyncio.sleep(10)
        
        # 再次获取系统状态
        status_after_wait = startup_service.get_system_status()
        logger.info(f"等待后系统状态: {status_after_wait}")
        
        # 测试系统关闭
        logger.info("\n=== 测试系统关闭 ===")
        shutdown_result = await startup_service.shutdown_system()
        logger.info(f"关闭结果: {shutdown_result}")
        
        # 验证关闭后状态
        final_status = startup_service.get_system_status()
        logger.info(f"关闭后系统状态: {final_status}")
        
        logger.info("\n系统启动服务测试完成")
        
    except Exception as e:
        logger.error(f"测试系统启动服务失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        
        # 尝试关闭系统
        try:
            startup_service = StartupService()
            await startup_service.shutdown_system()
        except:
            pass


async def test_performance():
    """测试缓存性能"""
    try:
        logger.info("\n=== 性能测试 ===")
        
        # 初始化系统
        startup_service = StartupService()
        await startup_service.initialize_system()
        
        cache_service = StockInfoCacheService()
        
        # 测试单次查询性能
        import time
        
        # 预热
        cache_service.get_stock_info('000001.SZ')
        
        # 测试单次查询
        start_time = time.time()
        for _ in range(1000):
            cache_service.get_stock_info('000001.SZ')
        single_query_time = time.time() - start_time
        logger.info(f"1000次单次查询耗时: {single_query_time:.4f}秒")
        
        # 测试批量查询
        test_codes = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH'] * 250  # 1000只股票
        start_time = time.time()
        batch_results = cache_service.get_stocks_info(test_codes)
        batch_query_time = time.time() - start_time
        logger.info(f"批量查询1000只股票耗时: {batch_query_time:.4f}秒")
        
        # 测试条件查询性能
        start_time = time.time()
        st_stocks = cache_service.get_stocks_by_condition(is_st=True)
        condition_query_time = time.time() - start_time
        logger.info(f"条件查询ST股票耗时: {condition_query_time:.4f}秒，找到 {len(st_stocks)} 只")
        
        # 测试搜索性能
        start_time = time.time()
        search_results = cache_service.search_stocks('银行')
        search_time = time.time() - start_time
        logger.info(f"搜索'银行'耗时: {search_time:.4f}秒，找到 {len(search_results)} 只")
        
        # 关闭系统
        await startup_service.shutdown_system()
        
        logger.info("性能测试完成")
        
    except Exception as e:
        logger.error(f"性能测试失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")


if __name__ == "__main__":
    # 运行基本功能测试
    asyncio.run(test_startup_service())
    
    # 运行性能测试
    asyncio.run(test_performance())