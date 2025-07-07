#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复strategy_executions表缺少execution_time字段的问题
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from core.duckdb_adapter import get_duckdb

def check_execution_time_column():
    """检查execution_time字段是否存在"""
    try:
        db = get_duckdb()
        result = db.execute('DESCRIBE strategy_executions').fetchall()
        columns = [row[0] for row in result]
        return 'execution_time' in columns
    except Exception as e:
        logger.error(f"检查字段失败: {e}")
        return False

def add_execution_time_column():
    """添加execution_time字段"""
    try:
        db = get_duckdb()
        db.execute('ALTER TABLE strategy_executions ADD COLUMN execution_time DOUBLE')
        logger.success("已成功添加execution_time字段")
        return True
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info("execution_time字段已存在，无需添加")
            return True
        else:
            logger.error(f"添加字段失败: {e}")
            return False

def verify_table_structure():
    """验证表结构"""
    try:
        db = get_duckdb()
        result = db.execute('DESCRIBE strategy_executions').fetchall()
        
        logger.info("strategy_executions表结构:")
        for row in result:
            logger.info(f"  {row[0]}: {row[1]}")
        
        # 检查必要字段
        columns = [row[0] for row in result]
        required_fields = [
            'id', 'strategy_id', 'execution_type', 'status', 
            'start_time', 'end_time', 'execution_time', 
            'total_stocks', 'signal_count', 'success_rate',
            'error_message', 'result_data', 'created_at'
        ]
        
        missing_fields = [field for field in required_fields if field not in columns]
        if missing_fields:
            logger.error(f"缺少字段: {missing_fields}")
            return False
        else:
            logger.success("表结构验证通过，所有必要字段都存在")
            return True
            
    except Exception as e:
        logger.error(f"验证表结构失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("开始修复strategy_executions表...")
    
    # 1. 检查字段是否存在
    logger.info("1. 检查execution_time字段是否存在...")
    if check_execution_time_column():
        logger.info("execution_time字段已存在")
    else:
        logger.warning("execution_time字段不存在，需要添加")
        
        # 2. 添加字段
        logger.info("2. 添加execution_time字段...")
        if not add_execution_time_column():
            logger.error("修复失败")
            return False
    
    # 3. 验证表结构
    logger.info("3. 验证表结构...")
    if verify_table_structure():
        logger.success("🎉 strategy_executions表修复完成！")
        return True
    else:
        logger.error("表结构验证失败")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        logger.info("修复脚本执行成功")
    else:
        logger.error("修复脚本执行失败")
        sys.exit(1)