#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库测试脚本
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# 创建基础类
Base = declarative_base()

class TestStrategy(Base):
    """测试策略表"""
    __tablename__ = "test_strategies"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

def test_database():
    """测试数据库"""
    try:
        print("开始数据库测试...")
        
        # 创建内存数据库
        engine = create_engine("sqlite:///:memory:", echo=True)
        
        # 创建表
        Base.metadata.create_all(engine)
        print("表创建成功")
        
        # 创建会话
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # 插入测试数据
        test_strategy = TestStrategy(
            name="测试策略",
            description="这是一个测试策略",
            is_active=True
        )
        session.add(test_strategy)
        session.commit()
        print("测试数据插入成功")
        
        # 查询数据
        strategies = session.query(TestStrategy).all()
        print(f"查询到 {len(strategies)} 个策略")
        
        for strategy in strategies:
            print(f"策略: {strategy.name} - {strategy.description}")
        
        session.close()
        engine.dispose()
        
        print("数据库测试完成！")
        
    except Exception as e:
        print(f"数据库测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_database()