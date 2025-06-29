#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的策略管理系统初始化脚本
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from config import get_settings

# 配置日志
logger.add(
    "logs/strategy_init.log",
    rotation="1 day",
    retention="30 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}"
)

def simple_init():
    """简单初始化"""
    try:
        settings = get_settings()
        logger.info("开始简化初始化...")
        
        # 1. 初始化数据库
        logger.info("步骤1: 初始化数据库")
        from core.database import init_database
        init_database()
        logger.info("数据库初始化完成")
        
        # 2. 测试数据库连接
        logger.info("步骤2: 测试数据库连接")
        from core.database import SessionLocal
        from sqlalchemy import text
        session = SessionLocal()
        try:
            # 简单查询测试
            result = session.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()[0]
            logger.info(f"数据库连接测试成功: {test_value}")
        finally:
            session.close()
        
        # 3. 测试服务初始化
        logger.info("步骤3: 测试服务初始化")
        from services.data_service import DataService
        from services.xtquant_service import XtQuantService
        
        # 创建服务实例
        xtquant_service = XtQuantService()
        data_service = DataService()
        
        logger.info("服务初始化完成")
        
        logger.info("简化初始化完成！")
        
        # 显示可用的API接口
        print("\n=== 策略管理系统API接口 ===")
        print("1. 策略管理:")
        print("   POST /api/strategy-manager/strategies - 创建策略")
        print("   GET  /api/strategy-manager/strategies - 获取策略列表")
        print("   GET  /api/strategy-manager/strategies/{id} - 获取策略详情")
        print("   PUT  /api/strategy-manager/strategies/{id} - 更新策略")
        print("   DELETE /api/strategy-manager/strategies/{id} - 删除策略")
        print("\n2. 策略执行:")
        print("   POST /api/strategy-manager/execute - 执行策略")
        print("   GET  /api/strategy-manager/signals - 获取策略信号")
        print("   GET  /api/strategy-manager/executions - 获取执行历史")
        print("\n3. 系统配置:")
        print("   GET  /api/strategy-manager/categories - 获取策略分类")
        print("   GET  /api/strategy-manager/indicators - 获取可用指标")
        print("   GET  /api/strategy-manager/operators - 获取操作符")
        print("\n启动API服务: python main.py")
        
    except Exception as e:
        logger.error(f"简化初始化失败: {e}")
        raise

if __name__ == "__main__":
    simple_init()