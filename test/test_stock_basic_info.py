#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票基础信息获取功能测试

测试内容：
1. 股票基础信息获取和存储
2. ST股票判断功能
3. 数据库存储和查询
"""

import asyncio
import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.xtquant_service import XtQuantService
from services.custom_condition_manager import IsSTStockCondition
from core.database import get_db, StockBasicInfo
from loguru import logger


async def test_stock_basic_info_retrieval():
    """测试股票基础信息获取"""
    print("\n=== 测试股票基础信息获取 ===")
    
    try:
        xt_service = XtQuantService()
        
        # 测试股票代码列表（包含一些可能的ST股票）
        test_stocks = [
            '000001.SZ',  # 平安银行
            '600000.SH',  # 浦发银行
            '000002.SZ',  # 万科A
        ]
        
        for stock_code in test_stocks:
            print(f"\n获取股票基础信息: {stock_code}")
            
            # 强制从xtquant获取最新信息
            stock_info = await xt_service.get_stock_basic_info(stock_code, force_update=True)
            
            if stock_info:
                print(f"  股票代码: {stock_info['stock_code']}")
                print(f"  股票名称: {stock_info['stock_name']}")
                print(f"  交易所: {stock_info['exchange']}")
                print(f"  上市日期: {stock_info['listing_date']}")
                print(f"  是否ST股票: {stock_info['is_st']}")
                print(f"  是否交易中: {stock_info['is_trading']}")
                print(f"  价格最小变动: {stock_info['price_tick']}")
                
                # 测试从数据库获取
                print("  从数据库获取信息...")
                db_info = await xt_service.get_stock_basic_info(stock_code, force_update=False)
                if db_info:
                    print(f"  数据库中的股票名称: {db_info['stock_name']}")
                    print(f"  数据库中的ST状态: {db_info['is_st']}")
                else:
                    print("  数据库中未找到信息")
            else:
                print(f"  获取失败: {stock_code}")
        
        print("\n股票基础信息获取测试完成")
        return True
        
    except Exception as e:
        print(f"股票基础信息获取测试失败: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
        return False


async def test_st_stock_condition():
    """测试ST股票判断条件"""
    print("\n=== 测试ST股票判断条件 ===")
    
    try:
        # 创建ST股票判断条件
        st_condition = IsSTStockCondition()
        
        # 测试股票代码（需要包含一些ST股票进行测试）
        test_stocks = [
            '000001.SZ',  # 平安银行（非ST）
            '600000.SH',  # 浦发银行（非ST）
            '000002.SZ',  # 万科A（非ST）
        ]
        
        for stock_code in test_stocks:
            print(f"\n测试股票: {stock_code}")
            
            # 创建模拟股票数据
            stock_data = pd.DataFrame({
                'trade_date': [datetime.now().date()],
                'open_price': [10.0],
                'close_price': [10.5],
                'high_price': [11.0],
                'low_price': [9.8],
                'volume': [1000000]
            })
            
            # 测试ST股票判断
            parameters = {'stock_code': stock_code}
            result = await st_condition.calculate(stock_data, parameters)
            
            print(f"  ST股票判断结果: {result} ({'是ST股票' if result == 1 else '非ST股票'})")
        
        print("\nST股票判断测试完成")
        return True
        
    except Exception as e:
        print(f"ST股票判断测试失败: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
        return False


async def test_batch_update():
    """测试批量更新股票基础信息"""
    print("\n=== 测试批量更新股票基础信息 ===")
    
    try:
        xt_service = XtQuantService()
        
        # 批量更新测试股票
        test_stocks = [
            '000001.SZ',
            '600000.SH',
            '000002.SZ'
        ]
        
        print(f"批量更新 {len(test_stocks)} 只股票的基础信息...")
        results = await xt_service.batch_update_stock_basic_info(test_stocks)
        
        print("\n批量更新结果:")
        for stock_code, success in results.items():
            print(f"  {stock_code}: {'成功' if success else '失败'}")
        
        success_count = sum(1 for success in results.values() if success)
        print(f"\n批量更新完成: 成功 {success_count}/{len(test_stocks)}")
        
        return success_count > 0
        
    except Exception as e:
        print(f"批量更新测试失败: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
        return False


def test_database_structure():
    """测试数据库表结构"""
    print("\n=== 测试数据库表结构 ===")
    
    try:
        from core.database import get_duckdb_connection
        
        conn = get_duckdb_connection()
        
        # 检查表是否存在
        result = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_name='stock_basic_info'").fetchall()
        if result:
            print("✓ stock_basic_info 表已存在")
            
            # 查看表结构
            columns = conn.execute("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name='stock_basic_info' ORDER BY ordinal_position").fetchall()
            print("\n表结构:")
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                print(f"  {col[0]} {col[1]} {nullable}")
                
            # 查看记录数
            count = conn.execute("SELECT COUNT(*) FROM stock_basic_info").fetchone()[0]
            print(f"\n当前记录数: {count}")
            
            # 显示部分数据示例
            if count > 0:
                sample_data = conn.execute("SELECT stock_code, stock_name, exchange, is_st, is_trading FROM stock_basic_info LIMIT 5").fetchall()
                print("\n数据示例:")
                for row in sample_data:
                    print(f"  {row[0]} | {row[1]} | {row[2]} | ST:{row[3]} | 交易:{row[4]}")
            
        else:
            print("✗ stock_basic_info 表不存在")
            
        conn.close()
        
        print("数据库表结构测试完成")
        return True
        
    except Exception as e:
        print(f"数据库表结构测试失败: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
        return False


async def main():
    """主测试函数"""
    print("开始股票基础信息功能测试...")
    
    # 测试结果
    results = []
    
    # 1. 测试数据库表结构
    results.append(test_database_structure())
    
    # 2. 测试股票基础信息获取
    results.append(await test_stock_basic_info_retrieval())
    
    # 3. 测试ST股票判断
    results.append(await test_st_stock_condition())
    
    # 4. 测试批量更新
    results.append(await test_batch_update())
    
    # 输出测试结果
    print("\n" + "="*50)
    print("测试结果汇总:")
    test_names = [
        "数据库表结构测试",
        "股票基础信息获取测试", 
        "ST股票判断测试",
        "批量更新测试"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{i+1}. {name}: {status}")
    
    success_count = sum(results)
    print(f"\n总体结果: {success_count}/{len(results)} 个测试通过")
    
    if success_count == len(results):
        print("🎉 所有测试通过！股票基础信息功能工作正常。")
    else:
        print("⚠️  部分测试失败，请检查相关功能。")


if __name__ == "__main__":
    asyncio.run(main())