#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的数据库测试脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database import init_database, get_duckdb_connection
from loguru import logger


def test_database_connection():
    """测试数据库连接"""
    print("\n=== 测试数据库连接 ===")
    
    try:
        # 初始化数据库
        init_database()
        print("✓ 数据库初始化成功")
        
        # 获取连接
        conn = get_duckdb_connection()
        print("✓ 数据库连接成功")
        
        # 测试基本查询
        result = conn.execute("SELECT 1 as test").fetchone()
        print(f"✓ 基本查询测试: {result}")
        
        conn.close()
        
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")


def test_stock_basic_info_table():
    """测试股票基础信息表"""
    print("\n=== 测试股票基础信息表 ===")
    
    try:
        conn = get_duckdb_connection()
        
        # 检查表是否存在
        tables = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'stock_basic_info'
        """).fetchall()
        
        if tables:
            print("✓ stock_basic_info 表存在")
            
            # 查看表结构
            columns = conn.execute("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'stock_basic_info'
                ORDER BY ordinal_position
            """).fetchall()
            
            print("\n表结构:")
            for col in columns:
                print(f"  {col[0]}: {col[1]} ({'可空' if col[2] == 'YES' else '不可空'})")
            
            # 查看记录数
            count = conn.execute("SELECT COUNT(*) FROM stock_basic_info").fetchone()[0]
            print(f"\n记录总数: {count}")
            
            # 如果有数据，显示前几条
            if count > 0:
                records = conn.execute("""
                    SELECT stock_code, stock_name, exchange, is_st, is_trading 
                    FROM stock_basic_info 
                    LIMIT 5
                """).fetchall()
                
                print("\n前5条记录:")
                for record in records:
                    print(f"  {record[0]} | {record[1]} | {record[2]} | ST:{record[3]} | 交易:{record[4]}")
            
        else:
            print("✗ stock_basic_info 表不存在")
        
        conn.close()
        
    except Exception as e:
        print(f"✗ 测试股票基础信息表失败: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")


def test_insert_sample_data():
    """测试插入示例数据"""
    print("\n=== 测试插入示例数据 ===")
    
    try:
        conn = get_duckdb_connection()
        
        # 插入测试数据
        test_data = [
            ('TEST01.SZ', '测试股票1', 'SZ', '2020-01-01', False, True, 0.01),
            ('TEST02.SH', '测试股票2', 'SH', '2020-01-02', True, True, 0.01),
        ]
        
        for data in test_data:
            # 检查是否已存在
            existing = conn.execute(
                "SELECT COUNT(*) FROM stock_basic_info WHERE stock_code = ?", 
                (data[0],)
            ).fetchone()[0]
            
            if existing == 0:
                conn.execute("""
                    INSERT INTO stock_basic_info 
                    (stock_code, stock_name, exchange, listing_date, is_st, is_trading, price_tick)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, data)
                print(f"✓ 插入测试数据: {data[0]}")
            else:
                print(f"- 测试数据已存在: {data[0]}")
        
        # 验证插入结果
        count = conn.execute("SELECT COUNT(*) FROM stock_basic_info WHERE stock_code LIKE 'TEST%'").fetchone()[0]
        print(f"\n测试数据总数: {count}")
        
        conn.close()
        
    except Exception as e:
        print(f"✗ 插入示例数据失败: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")


def main():
    """主测试函数"""
    print("股票基础信息数据库简单测试")
    print("=" * 50)
    
    # 测试数据库连接
    test_database_connection()
    
    # 测试股票基础信息表
    test_stock_basic_info_table()
    
    # 测试插入示例数据
    test_insert_sample_data()
    
    # 再次查看表状态
    test_stock_basic_info_table()
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    main()