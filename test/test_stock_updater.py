#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试股票基础信息更新功能
"""

import asyncio
import sys
import pytest
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.stock_info_updater import StockInfoUpdater
from services.xtquant_service import XtQuantService
from loguru import logger


@pytest.mark.asyncio
async def test_stock_updater():
    """测试股票信息更新器"""
    print("\n=== 测试股票信息更新器 ===")
    
    updater = StockInfoUpdater()
    
    # 测试手动更新几只股票
    test_stocks = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH']
    print(f"\n测试更新股票: {test_stocks}")
    
    try:
        result = await updater.manual_update_stock_info(test_stocks)
        print(f"更新结果: {result}")
        
        if result.get('success'):
            print(f"✓ 更新成功: {result['success_count']}/{result['total_count']}")
            
            # 显示详细结果
            for stock_code, success in result.get('results', {}).items():
                status = "成功" if success else "失败"
                print(f"  {stock_code}: {status}")
        else:
            print(f"✗ 更新失败: {result.get('message', '未知错误')}")
            
    except Exception as e:
        print(f"测试更新器失败: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")


@pytest.mark.asyncio
async def test_xtquant_service():
    """测试XtQuant服务的股票信息获取"""
    print("\n=== 测试XtQuant服务 ===")
    
    xtquant_service = XtQuantService()
    
    # 测试获取单只股票信息
    test_stock = '000001.SZ'
    print(f"\n获取股票 {test_stock} 的基础信息:")
    
    try:
        # 强制从xtquant获取最新信息
        info = await xtquant_service.get_stock_basic_info(test_stock, force_update=True)
        
        if info:
            print(f"  股票代码: {info.get('stock_code')}")
            print(f"  股票名称: {info.get('stock_name')}")
            print(f"  交易所: {info.get('exchange')}")
            print(f"  上市日期: {info.get('listing_date')}")
            print(f"  是否ST股票: {info.get('is_st')}")
            print(f"  是否可交易: {info.get('is_trading')}")
            print(f"  价格最小变动: {info.get('price_tick')}")
            print("✓ 获取成功")
        else:
            print("✗ 获取失败")
            
    except Exception as e:
        print(f"测试XtQuant服务失败: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")


@pytest.mark.asyncio
async def test_update_status():
    """测试获取更新状态"""
    print("\n=== 测试更新状态 ===")
    
    updater = StockInfoUpdater()
    
    try:
        status = await updater.get_update_status()
        print(f"更新状态: {status}")
        
        print(f"  最后更新时间: {status.get('last_update', '未知')}")
        print(f"  总股票数量: {status.get('total_count', 0)}")
        print(f"  ST股票数量: {status.get('st_count', 0)}")
        print(f"  可交易股票数量: {status.get('trading_count', 0)}")
        print(f"  调度器运行状态: {status.get('is_scheduler_running', False)}")
        
        if status.get('error'):
            print(f"  错误信息: {status['error']}")
            
    except Exception as e:
        print(f"测试更新状态失败: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")


async def main():
    """主测试函数"""
    print("开始股票基础信息更新功能测试...")
    
    # 测试XtQuant服务
    await test_xtquant_service()
    
    # 测试更新器
    await test_stock_updater()
    
    # 测试更新状态
    await test_update_status()
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())