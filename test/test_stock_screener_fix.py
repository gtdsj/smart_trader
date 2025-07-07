#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试StockScreener修复
验证股票列表类型转换问题是否已解决
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from loguru import logger
from services.data_service import DataService
from services.stock_screener import StockScreener

async def test_stock_list_format():
    """测试股票列表格式"""
    logger.info("=== 测试股票列表格式 ===")
    
    try:
        # 获取DataService实例
        data_service = DataService.get_instance()
        
        # 测试get_stock_list返回格式
        logger.info("测试DataService.get_stock_list()返回格式...")
        stock_list_data = await data_service.get_stock_list()
        
        if stock_list_data:
            logger.info(f"获取到{len(stock_list_data)}只股票")
            logger.info(f"第一个元素类型: {type(stock_list_data[0])}")
            logger.info(f"第一个元素内容: {stock_list_data[0]}")
        else:
            logger.warning("未获取到股票列表")
            
        # 测试StockScreener的_get_all_stock_list方法
        logger.info("测试StockScreener._get_all_stock_list()返回格式...")
        screener = StockScreener(data_service)
        stock_codes = await screener._get_all_stock_list()
        
        if stock_codes:
            logger.info(f"获取到{len(stock_codes)}只股票代码")
            logger.info(f"第一个股票代码类型: {type(stock_codes[0])}")
            logger.info(f"第一个股票代码: {stock_codes[0]}")
            
            # 验证所有元素都是字符串
            all_strings = all(isinstance(code, str) for code in stock_codes)
            logger.info(f"所有股票代码都是字符串: {all_strings}")
            
            if all_strings:
                logger.success("✅ 股票列表格式正确")
                return True
            else:
                logger.error("❌ 股票列表包含非字符串元素")
                return False
        else:
            logger.warning("未获取到股票代码列表")
            return False
            
    except Exception as e:
        logger.error(f"测试失败: {e}")
        return False

async def test_batch_historical_data():
    """测试批量获取历史数据"""
    logger.info("=== 测试批量获取历史数据 ===")
    
    try:
        # 获取DataService实例
        data_service = DataService.get_instance()
        
        # 测试股票代码
        test_stocks = ['600000.SH', '000001.SZ']
        start_date = '2024-01-01'
        end_date = '2024-01-31'
        
        logger.info(f"测试批量获取{len(test_stocks)}只股票的历史数据...")
        
        batch_data = await data_service.get_batch_historical_data(
            stock_codes=test_stocks,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"批量获取结果: {len(batch_data)}只股票")
        
        for stock_code, df in batch_data.items():
            logger.info(f"股票{stock_code}: {len(df)}条数据")
            
        logger.success("✅ 批量获取历史数据成功")
        return True
        
    except Exception as e:
        logger.error(f"批量获取历史数据失败: {e}")
        return False

async def test_stock_screening():
    """测试股票筛选功能"""
    logger.info("=== 测试股票筛选功能 ===")
    
    try:
        # 获取DataService实例
        data_service = DataService.get_instance()
        screener = StockScreener(data_service)
        
        # 使用少量股票进行测试
        test_stocks = ['600000.SH', '000001.SZ']
        
        # 测试表达式筛选
        logger.info("测试表达式筛选...")
        expression = "close > 10"  # 简单的筛选条件
        
        result = await screener.screen_stocks_by_expression(
            expression=expression,
            stock_list=test_stocks
        )
        
        logger.info(f"筛选结果: {result}")
        
        if result.get('success'):
            logger.success("✅ 股票筛选功能正常")
            return True
        else:
            logger.error(f"❌ 股票筛选失败: {result.get('message')}")
            return False
            
    except Exception as e:
        logger.error(f"股票筛选测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    logger.info("开始测试StockScreener修复...")
    
    # 重置DataService单例
    DataService.reset_instance()
    
    tests = [
        ("股票列表格式", test_stock_list_format),
        ("批量获取历史数据", test_batch_historical_data),
        ("股票筛选功能", test_stock_screening)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"开始测试: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"测试{test_name}异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果
    logger.info(f"\n{'='*50}")
    logger.info("测试结果汇总")
    logger.info(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        logger.success("🎉 所有测试通过！StockScreener修复成功")
    else:
        logger.error(f"⚠️  {total - passed} 个测试失败，需要进一步检查")

if __name__ == "__main__":
    asyncio.run(main())