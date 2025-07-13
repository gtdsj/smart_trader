#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试股票信息缓存服务
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from services.stock_info_cache_service import StockInfoCacheService
from core.database import init_database


async def test_stock_cache_service():
    """测试股票信息缓存服务"""
    try:
        logger.info("开始测试股票信息缓存服务...")
        
        # 初始化数据库
        init_database()
        
        # 创建缓存服务实例
        cache_service = StockInfoCacheService()
        
        # 测试初始化
        logger.info("测试缓存初始化...")
        await cache_service.initialize()
        
        # 获取缓存状态
        status = cache_service.get_cache_status()
        logger.info(f"缓存状态: {status}")
        
        # 测试获取股票信息
        test_codes = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH']
        
        for code in test_codes:
            stock_info = cache_service.get_stock_info(code)
            if stock_info:
                logger.info(f"股票 {code}: {stock_info['stock_name']} - 交易状态: {stock_info['is_trading']} - ST状态: {stock_info['is_st']}")
            else:
                logger.warning(f"未找到股票 {code} 的信息")
        
        # 测试批量获取
        logger.info("\n测试批量获取股票信息...")
        batch_info = cache_service.get_stocks_info(test_codes)
        logger.info(f"批量获取结果: 找到 {len(batch_info)} 只股票")
        
        # 测试按条件查询
        logger.info("\n测试按条件查询...")
        
        # 查询ST股票
        st_stocks = cache_service.get_stocks_by_condition(is_st=True)
        logger.info(f"ST股票数量: {len(st_stocks)}")
        if st_stocks:
            for stock in st_stocks[:5]:  # 只显示前5只
                logger.info(f"  ST股票: {stock['stock_code']} - {stock['stock_name']}")
        
        # 查询停牌股票
        suspended_stocks = cache_service.get_stocks_by_condition(is_trading=False)
        logger.info(f"停牌股票数量: {len(suspended_stocks)}")
        if suspended_stocks:
            for stock in suspended_stocks[:5]:  # 只显示前5只
                logger.info(f"  停牌股票: {stock['stock_code']} - {stock['stock_name']}")
        
        # 查询深圳股票
        sz_stocks = cache_service.get_stocks_by_condition(market='SZ')
        logger.info(f"深圳股票数量: {len(sz_stocks)}")
        
        # 查询上海股票
        sh_stocks = cache_service.get_stocks_by_condition(market='SH')
        logger.info(f"上海股票数量: {len(sh_stocks)}")
        
        # 测试模糊搜索
        logger.info("\n测试模糊搜索...")
        search_results = cache_service.search_stocks('平安')
        logger.info(f"搜索'平安'的结果: {len(search_results)} 只股票")
        for stock in search_results:
            logger.info(f"  搜索结果: {stock['stock_code']} - {stock['stock_name']}")
        
        # 测试更新单只股票信息
        logger.info("\n测试更新单只股票信息...")
        test_stock_info = {
            'stock_code': '000001.SZ',
            'stock_name': '平安银行(测试)',
            'market': 'SZ',
            'is_trading': True,
            'is_st': False
        }
        cache_service.update_stock_info('000001.SZ', test_stock_info)
        
        # 验证更新结果
        updated_info = cache_service.get_stock_info('000001.SZ')
        if updated_info:
            logger.info(f"更新后的股票信息: {updated_info['stock_name']}")
        
        # 测试刷新缓存
        logger.info("\n测试刷新缓存...")
        await cache_service.refresh_cache()
        
        # 再次获取缓存状态
        final_status = cache_service.get_cache_status()
        logger.info(f"刷新后缓存状态: {final_status}")
        
        # 清理缓存
        logger.info("\n清理缓存...")
        cache_service.clear_cache()
        
        # 验证清理结果
        cleared_status = cache_service.get_cache_status()
        logger.info(f"清理后缓存状态: {cleared_status}")
        
        logger.info("股票信息缓存服务测试完成")
        
    except Exception as e:
        logger.error(f"测试股票信息缓存服务失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(test_stock_cache_service())