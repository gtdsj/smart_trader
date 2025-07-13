#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：创建股票基础信息表

创建时间：2024-12-19
描述：为支持股票基础信息存储和ST股票判断功能，新增stock_basic_info表
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import init_database, get_duckdb_connection
from loguru import logger


def create_stock_basic_info_table():
    """创建股票基础信息表"""
    
    # 创建表的SQL语句
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS stock_basic_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stock_code TEXT NOT NULL UNIQUE,
        instrument_name TEXT,
        exchange_id TEXT,
        exchange_code TEXT,
        product_id TEXT,
        product_name TEXT,
        underlying_code TEXT,
        extend_name TEXT,
        rzrk_code TEXT,
        uni_code TEXT,
        create_date TEXT,
        open_date TEXT,
        expire_date TEXT,
        pre_close REAL DEFAULT 0.0,
        settlement_price REAL DEFAULT 0.0,
        up_stop_price REAL DEFAULT 0.0,
        down_stop_price REAL DEFAULT 0.0,
        float_volume INTEGER DEFAULT 0,
        total_volume INTEGER DEFAULT 0,
        long_margin_ratio REAL DEFAULT 0.0,
        short_margin_ratio REAL DEFAULT 0.0,
        price_tick REAL DEFAULT 0.0,
        volume_multiple INTEGER DEFAULT 1,
        main_contract INTEGER DEFAULT 0,
        last_volume INTEGER DEFAULT 0,
        instrument_status INTEGER DEFAULT 0,
        is_trading BOOLEAN DEFAULT FALSE,
        is_recent BOOLEAN DEFAULT FALSE,
        product_trade_quota INTEGER DEFAULT 0,
        contract_trade_quota INTEGER DEFAULT 0,
        product_open_interest_quota INTEGER DEFAULT 0,
        contract_open_interest_quota INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # 创建索引的SQL语句
    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_stock_basic_info_stock_code ON stock_basic_info(stock_code);",
        "CREATE INDEX IF NOT EXISTS idx_stock_basic_info_exchange_id ON stock_basic_info(exchange_id);",
        "CREATE INDEX IF NOT EXISTS idx_stock_basic_info_instrument_name ON stock_basic_info(instrument_name);",
        "CREATE INDEX IF NOT EXISTS idx_stock_basic_info_is_trading ON stock_basic_info(is_trading);",
        "CREATE INDEX IF NOT EXISTS idx_stock_basic_info_updated_at ON stock_basic_info(updated_at);"
    ]
    
    try:
        # 初始化数据库连接
        init_database()
        
        logger.info("开始创建股票基础信息表...")
        
        # 获取DuckDB连接
        conn = get_duckdb_connection()
        
        # 执行创建表语句
        conn.execute(create_table_sql)
        logger.info("股票基础信息表创建成功")
        
        # 创建索引
        logger.info("开始创建索引...")
        for index_sql in create_indexes_sql:
            conn.execute(index_sql)
        logger.info("索引创建完成")
        
        # 验证表是否创建成功（DuckDB使用information_schema）
        verify_sql = "SELECT table_name FROM information_schema.tables WHERE table_name='stock_basic_info';"
        result = conn.execute(verify_sql).fetchone()
        
        if result:
            logger.info("✓ 股票基础信息表创建验证成功")
            
            # 查看表结构（DuckDB使用DESCRIBE）
            structure_sql = "DESCRIBE stock_basic_info;"
            columns = conn.execute(structure_sql).fetchall()
            
            logger.info("表结构信息:")
            for column in columns:
                logger.info(f"  {column[0]} {column[1]} {'NOT NULL' if 'NOT NULL' in str(column[2]) else 'NULL'}")
            
            conn.close()
            return True
        else:
            logger.error("✗ 股票基础信息表创建验证失败")
            conn.close()
            return False
            
    except Exception as e:
        logger.error(f"创建股票基础信息表失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False


def rollback_stock_basic_info_table():
    """回滚股票基础信息表（删除表）"""
    
    try:
        # 初始化数据库连接
        init_database()
        
        logger.info("开始回滚股票基础信息表...")
        
        # 获取DuckDB连接
        conn = get_duckdb_connection()
        
        # 删除表
        drop_table_sql = "DROP TABLE IF EXISTS stock_basic_info;"
        conn.execute(drop_table_sql)
        
        conn.close()
        logger.info("✓ 股票基础信息表回滚成功")
        return True
        
    except Exception as e:
        logger.error(f"回滚股票基础信息表失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False


def main():
    """主函数"""
    print("股票基础信息表迁移脚本")
    print("=" * 40)
    
    while True:
        print("\n请选择操作:")
        print("1. 创建股票基础信息表")
        print("2. 回滚股票基础信息表")
        print("3. 退出")
        
        choice = input("\n请输入选择 (1-3): ").strip()
        
        if choice == '1':
            print("\n开始创建股票基础信息表...")
            success = create_stock_basic_info_table()
            if success:
                print("✓ 股票基础信息表创建成功！")
            else:
                print("✗ 股票基础信息表创建失败！")
                
        elif choice == '2':
            confirm = input("\n确认要删除股票基础信息表吗？这将删除所有数据！(y/N): ").strip().lower()
            if confirm == 'y':
                print("\n开始回滚股票基础信息表...")
                success = rollback_stock_basic_info_table()
                if success:
                    print("✓ 股票基础信息表回滚成功！")
                else:
                    print("✗ 股票基础信息表回滚失败！")
            else:
                print("取消回滚操作")
                
        elif choice == '3':
            print("退出迁移脚本")
            break
            
        else:
            print("无效选择，请重新输入")


if __name__ == "__main__":
    main()