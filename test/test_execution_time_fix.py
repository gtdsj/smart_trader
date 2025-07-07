#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试execution_time字段修复
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from loguru import logger
from core.duckdb_adapter import get_duckdb

def test_execution_time_field():
    """测试execution_time字段"""
    try:
        db = get_duckdb()
        
        # 1. 检查表结构
        logger.info("1. 检查strategy_executions表结构...")
        result = db.execute('DESCRIBE strategy_executions').fetchall()
        columns = [row[0] for row in result]
        
        if 'execution_time' in columns:
            logger.success("✅ execution_time字段存在")
        else:
            logger.error("❌ execution_time字段不存在")
            return False
        
        # 2. 测试插入数据
        logger.info("2. 测试插入包含execution_time的记录...")
        
        test_data = {
            'strategy_id': 999,
            'execution_type': 'test',
            'status': 'completed',
            'start_time': datetime.now(),
            'end_time': datetime.now(),
            'execution_time': 1.23,
            'total_stocks': 100,
            'signal_count': 5,
            'created_at': datetime.now()
        }
        
        sql = """
        INSERT INTO strategy_executions 
        (strategy_id, execution_type, status, start_time, end_time, 
         execution_time, total_stocks, signal_count, created_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        db.execute(sql, (
            test_data['strategy_id'],
            test_data['execution_type'],
            test_data['status'],
            test_data['start_time'],
            test_data['end_time'],
            test_data['execution_time'],
            test_data['total_stocks'],
            test_data['signal_count'],
            test_data['created_at']
        ))
        
        logger.success("✅ 插入成功，execution_time字段问题已修复！")
        
        # 3. 验证插入的数据
        logger.info("3. 验证插入的数据...")
        result = db.fetchdf(
            'SELECT * FROM strategy_executions WHERE strategy_id = 999 ORDER BY id DESC LIMIT 1'
        )
        
        if not result.empty:
            record = result.iloc[0].to_dict()
            logger.info(f"插入的记录: {record}")
            
            if 'execution_time' in record and record['execution_time'] == 1.23:
                logger.success("✅ execution_time字段值正确保存")
                return True
            else:
                logger.error("❌ execution_time字段值保存异常")
                return False
        else:
            logger.error("❌ 未找到插入的记录")
            return False
            
    except Exception as e:
        error_msg = str(e)
        if "execution_time" in error_msg and "does not have a column" in error_msg:
            logger.error(f"❌ 仍然存在execution_time字段错误: {error_msg}")
            return False
        else:
            logger.error(f"测试过程中发生错误: {error_msg}")
            return False
    
    finally:
        # 清理测试数据
        try:
            db.execute('DELETE FROM strategy_executions WHERE strategy_id = 999')
            logger.info("测试数据已清理")
        except:
            pass

def main():
    """主函数"""
    logger.info("开始测试execution_time字段修复...")
    
    if test_execution_time_field():
        logger.success("🎉 execution_time字段修复验证成功！")
        logger.success("原始的'Table does not have a column with name execution_time'错误已解决")
    else:
        logger.error("❌ execution_time字段修复验证失败")
        logger.error("问题可能仍然存在")

if __name__ == "__main__":
    main()