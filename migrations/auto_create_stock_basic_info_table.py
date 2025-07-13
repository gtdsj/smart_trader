#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动创建股票基础信息表的迁移脚本
简化版本，无需用户交互，直接执行创建操作
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database import init_database, get_duckdb_connection
from loguru import logger


def create_stock_basic_info_table():
    """创建股票基础信息表"""
    try:
        logger.info("开始创建股票基础信息表...")
        
        # 初始化数据库连接
        init_database()
        conn = get_duckdb_connection()
        
        # 创建序列
        logger.info("创建序列...")
        conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS stock_basic_info_id_seq
        """)
        
        # 创建表
        logger.info("创建表...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_basic_info (
                id INTEGER PRIMARY KEY DEFAULT nextval('stock_basic_info_id_seq'),
                stock_code VARCHAR(20) NOT NULL UNIQUE,
                stock_name VARCHAR(100) NOT NULL,
                exchange VARCHAR(10) NOT NULL,
                listing_date VARCHAR(20),
                is_st BOOLEAN DEFAULT FALSE,
                is_trading BOOLEAN DEFAULT TRUE,
                price_tick DOUBLE DEFAULT 0.01,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        logger.info("创建索引...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_stock_basic_info_stock_code ON stock_basic_info(stock_code)",
            "CREATE INDEX IF NOT EXISTS idx_stock_basic_info_exchange ON stock_basic_info(exchange)",
            "CREATE INDEX IF NOT EXISTS idx_stock_basic_info_stock_name ON stock_basic_info(stock_name)",
            "CREATE INDEX IF NOT EXISTS idx_stock_basic_info_is_st ON stock_basic_info(is_st)",
            "CREATE INDEX IF NOT EXISTS idx_stock_basic_info_is_trading ON stock_basic_info(is_trading)",
            "CREATE INDEX IF NOT EXISTS idx_stock_basic_info_updated_at ON stock_basic_info(updated_at)"
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
        
        # 验证表创建
        logger.info("验证表创建...")
        result = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'stock_basic_info'
        """).fetchall()
        
        if result:
            logger.success("✓ stock_basic_info 表创建成功")
            
            # 显示表结构
            columns = conn.execute("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'stock_basic_info' 
                ORDER BY ordinal_position
            """).fetchall()
            
            logger.info("表结构:")
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                logger.info(f"  {col[0]} {col[1]} {nullable}")
                
        else:
            logger.error("✗ 表创建失败")
            return False
            
        conn.close()
        logger.success("股票基础信息表创建完成")
        return True
        
    except Exception as e:
        logger.error(f"创建股票基础信息表失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False


def check_table_exists():
    """检查表是否已存在"""
    try:
        init_database()
        conn = get_duckdb_connection()
        
        result = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'stock_basic_info'
        """).fetchall()
        
        conn.close()
        return len(result) > 0
        
    except Exception as e:
        logger.error(f"检查表存在性失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("=== 股票基础信息表自动创建脚本 ===")
    
    # 检查表是否已存在
    if check_table_exists():
        logger.info("stock_basic_info 表已存在，无需创建")
        return True
    
    # 创建表
    success = create_stock_basic_info_table()
    
    if success:
        logger.success("迁移完成")
    else:
        logger.error("迁移失败")
        
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)