# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为strategy_conditions表添加parameters字段
并迁移现有的硬编码参数到新字段中
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from sqlalchemy import text
from core.database import get_db, init_database
from loguru import logger


def add_parameters_column():
    """为strategy_conditions表添加parameters字段"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        
        # 检查parameters字段是否已存在
        check_column_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'strategy_conditions' 
        AND column_name = 'parameters'
        """
        
        result = db.execute(text(check_column_sql)).fetchone()
        
        if result:
            logger.info("parameters字段已存在，跳过添加")
            return True
        
        # 添加parameters字段
        alter_sql = "ALTER TABLE strategy_conditions ADD COLUMN parameters TEXT"
        db.execute(text(alter_sql))
        db.commit()
        
        logger.info("成功添加parameters字段到strategy_conditions表")
        return True
        
    except Exception as e:
        logger.error(f"添加parameters字段失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def migrate_existing_conditions():
    """迁移现有条件的硬编码参数到parameters字段"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        
        # 获取所有custom类型的条件
        select_sql = """
        SELECT id, indicator, value 
        FROM strategy_conditions 
        WHERE condition_type = 'custom' 
        AND (parameters IS NULL OR parameters = '')
        """
        
        conditions = db.execute(text(select_sql)).fetchall()
        
        logger.info(f"找到 {len(conditions)} 个需要迁移的条件")
        
        # 定义各个指标的默认参数
        default_parameters = {
            'consecutive_close_above_ma5': {
                'ma_period': 5,
                'consecutive_days': 3
            },
            'consecutive_close_above_open': {
                'consecutive_days': 3
            },
            'ma5_angle_consecutive': {
                'ma_period': 5,
                'consecutive_days': 3,
                'return_type': 'boolean'  # 修改为布尔类型，符合原意
            },
            'ma5_angle_latest': {
                'ma_period': 5
            },
            'ma10_angle_consecutive': {
                'ma_period': 10,
                'consecutive_days': 3,
                'return_type': 'boolean'
            },
            'low_above_ma5': {
                'ma_period': 5
            },
            'is_kcb_stock': {},
            'is_bse_stock': {},
            'is_st_stock': {},
            'is_break_board': {},
            'main_fund_inflow': {}
        }
        
        updated_count = 0
        
        for condition in conditions:
            condition_id, indicator, value = condition
            
            # 获取该指标的默认参数
            params = default_parameters.get(indicator, {})
            
            # 对于角度类条件，将value中的阈值添加到parameters中
            if 'angle' in indicator and value:
                try:
                    threshold_value = float(value)
                    params['threshold'] = threshold_value
                except (ValueError, TypeError):
                    logger.warning(f"无法解析条件 {condition_id} 的阈值: {value}")
            
            # 将参数转换为JSON字符串
            parameters_json = json.dumps(params, ensure_ascii=False)
            
            # 更新数据库
            update_sql = """
            UPDATE strategy_conditions 
            SET parameters = :parameters 
            WHERE id = :condition_id
            """
            
            db.execute(text(update_sql), {
                'parameters': parameters_json,
                'condition_id': condition_id
            })
            
            updated_count += 1
            logger.info(f"更新条件 {condition_id} ({indicator}): {parameters_json}")
        
        db.commit()
        logger.info(f"成功迁移 {updated_count} 个条件的参数")
        return True
        
    except Exception as e:
        logger.error(f"迁移现有条件失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def verify_migration():
    """验证迁移结果"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        
        # 检查迁移后的数据
        verify_sql = """
        SELECT id, indicator, value, parameters 
        FROM strategy_conditions 
        WHERE condition_type = 'custom'
        ORDER BY id
        """
        
        conditions = db.execute(text(verify_sql)).fetchall()
        
        logger.info("\n=== 迁移结果验证 ===")
        logger.info(f"总共 {len(conditions)} 个custom条件:")
        
        for condition in conditions:
            condition_id, indicator, value, parameters = condition
            logger.info(f"ID: {condition_id}, 指标: {indicator}, 值: {value}")
            logger.info(f"  参数: {parameters}")
            
            # 验证JSON格式
            if parameters:
                try:
                    parsed_params = json.loads(parameters)
                    logger.info(f"  解析成功: {parsed_params}")
                except json.JSONDecodeError as e:
                    logger.error(f"  JSON解析失败: {e}")
            else:
                logger.warning(f"  参数为空")
            
            logger.info("")
        
        return True
        
    except Exception as e:
        logger.error(f"验证迁移结果失败: {e}")
        return False
    finally:
        db.close()


def create_backup():
    """创建数据备份"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        
        # 创建备份表
        backup_sql = """
        CREATE TABLE IF NOT EXISTS strategy_conditions_backup AS 
        SELECT * FROM strategy_conditions
        """
        
        db.execute(text(backup_sql))
        db.commit()
        
        logger.info("成功创建strategy_conditions_backup备份表")
        return True
        
    except Exception as e:
        logger.error(f"创建备份失败: {e}")
        return False
    finally:
        db.close()


def main():
    """主函数"""
    logger.info("开始数据库迁移：添加parameters字段")
    
    try:
        # 初始化数据库
        logger.info("初始化数据库连接...")
        init_database()
        
        # 步骤1：创建备份
        logger.info("\n步骤1：创建数据备份...")
        if not create_backup():
            logger.error("备份失败，终止迁移")
            return False
        
        # 步骤2：添加parameters字段
        logger.info("\n步骤2：添加parameters字段...")
        if not add_parameters_column():
            logger.error("添加字段失败，终止迁移")
            return False
        
        # 步骤3：迁移现有数据
        logger.info("\n步骤3：迁移现有条件参数...")
        if not migrate_existing_conditions():
            logger.error("迁移数据失败")
            return False
        
        # 步骤4：验证迁移结果
        logger.info("\n步骤4：验证迁移结果...")
        if not verify_migration():
            logger.error("验证失败")
            return False
        
        logger.info("\n🎉 数据库迁移完成！")
        logger.info("\n迁移要点:")
        logger.info("1. ✅ 添加了parameters字段到strategy_conditions表")
        logger.info("2. ✅ 迁移了现有条件的硬编码参数")
        logger.info("3. ✅ 为角度类条件添加了threshold参数")
        logger.info("4. ✅ 创建了备份表strategy_conditions_backup")
        logger.info("5. ✅ 验证了迁移结果的正确性")
        
        return True
        
    except Exception as e:
        logger.error(f"迁移过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)