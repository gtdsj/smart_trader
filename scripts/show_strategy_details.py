# -*- coding: utf-8 -*-
"""
显示策略详细信息
"""

from core.database import init_database, get_db
from sqlalchemy import text
import json

def show_strategy_details():
    """显示策略详细信息"""
    try:
        # 初始化数据库
        init_database()
        
        # 获取数据库连接
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # 查询策略表
            result = db.execute(text("SELECT * FROM strategies"))
            strategies = result.fetchall()
            
            print(f"数据库中的策略数量: {len(strategies)}")
            
            for strategy in strategies:
                print(f"\n{'='*60}")
                print(f"策略ID: {strategy[0]}")
                print(f"策略名称: {strategy[1]}")
                print(f"策略描述: {strategy[2]}")
                print(f"策略类型: {strategy[3]}")
                print(f"策略分类: {strategy[4]}")
                print(f"参数: {strategy[5]}")
                print(f"优先级: {strategy[7]}")
                print(f"创建者: {strategy[8]}")
                print(f"版本: {strategy[9]}")
                print(f"是否激活: {strategy[10]}")
                print(f"创建时间: {strategy[11]}")
                print(f"更新时间: {strategy[12]}")
                
                # 查询策略条件
                strategy_id = strategy[0]
                condition_result = db.execute(text(
                    "SELECT * FROM strategy_conditions WHERE strategy_id = :strategy_id ORDER BY order_index"
                ), {"strategy_id": strategy_id})
                conditions = condition_result.fetchall()
                
                print(f"\n策略条件 ({len(conditions)}个):")
                print("-" * 40)
                
                for i, condition in enumerate(conditions, 1):
                    print(f"{i:2d}. 条件ID: {condition[0]}")
                    print(f"    条件类型: {condition[2]}")
                    print(f"    指标: {condition[3]}")
                    print(f"    操作符: {condition[4]}")
                    print(f"    值: {condition[5]}")
                    print(f"    逻辑操作符: {condition[6]}")
                    print(f"    顺序: {condition[7]}")
                    print(f"    是否激活: {condition[8]}")
                    print(f"    创建时间: {condition[9]}")
                    print()
                
        finally:
            db.close()
            
    except Exception as e:
        print(f"显示策略详情失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    show_strategy_details()