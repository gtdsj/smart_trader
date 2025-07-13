#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：移除stock_basic_info表中的abbreviation字段

由于xtdata.get_instrument_detail函数不返回Abbreviation字段，
需要从数据库表中移除该字段以保持数据一致性。
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database import get_duckdb_connection, init_database
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def remove_abbreviation_field():
    """
    从stock_basic_info表中移除abbreviation字段
    """
    try:
        # 初始化数据库
        init_database()
        
        # 获取DuckDB连接
        conn = get_duckdb_connection()
        if not conn:
            logger.error("无法获取数据库连接")
            return False
            
        logger.info("开始移除abbreviation字段...")
        
        # 检查表是否存在
        result = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'stock_basic_info'
        """).fetchone()
        
        if not result:
            logger.warning("stock_basic_info表不存在，无需迁移")
            return True
            
        # 检查abbreviation字段是否存在
        columns_result = conn.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'stock_basic_info' AND column_name = 'abbreviation'
        """).fetchone()
        
        if not columns_result:
            logger.info("abbreviation字段不存在，无需移除")
            return True
            
        logger.info("检测到abbreviation字段，开始移除...")
        
        # 创建新表（不包含abbreviation字段）
        conn.execute("""
            CREATE TABLE stock_basic_info_new AS 
            SELECT 
                id,
                stock_code,
                stock_name,
                exchange,
                listing_date,
                is_st,
                is_trading,
                price_tick,
                created_at,
                updated_at
            FROM stock_basic_info
        """)
        
        # 删除原表
        conn.execute("DROP TABLE stock_basic_info")
        
        # 重命名新表
        conn.execute("ALTER TABLE stock_basic_info_new RENAME TO stock_basic_info")
        
        # 重新创建索引
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_stock_basic_info_code 
            ON stock_basic_info(stock_code)
        """)
        
        logger.info("✓ 成功移除abbreviation字段")
        
        # 验证表结构
        columns = conn.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'stock_basic_info'
            ORDER BY ordinal_position
        """).fetchall()
        
        logger.info("当前表结构:")
        for column_name, data_type in columns:
            logger.info(f"  {column_name}: {data_type}")
            
        # 检查数据完整性
        count = conn.execute("SELECT COUNT(*) FROM stock_basic_info").fetchone()[0]
        logger.info(f"表中共有 {count} 条记录")
        
        return True
        
    except Exception as e:
        logger.error(f"移除abbreviation字段失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def main():
    """
    主函数
    """
    logger.info("开始数据库迁移：移除abbreviation字段")
    
    success = remove_abbreviation_field()
    
    if success:
        logger.info("✓ 数据库迁移完成")
        return 0
    else:
        logger.error("✗ 数据库迁移失败")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)