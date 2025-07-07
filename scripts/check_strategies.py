# -*- coding: utf-8 -*-
"""
检查数据库中的策略
"""

from core.database import init_database, get_db
from sqlalchemy import text

def check_strategies():
    """检查数据库中的策略"""
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
            
            if strategies:
                print("\n策略列表:")
                for strategy in strategies:
                    print(f"ID: {strategy[0]}, 名称: {strategy[1]}, 类型: {strategy[3]}, 分类: {strategy[4]}")
            else:
                print("数据库中没有策略")
                
            # 查询策略条件表
            result = db.execute(text("SELECT * FROM strategy_conditions"))
            conditions = result.fetchall()
            print(f"\n策略条件数量: {len(conditions)}")
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"检查策略失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_strategies()