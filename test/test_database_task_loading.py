#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试从数据库加载任务功能

验证调度服务是否能正确从数据库加载任务而不是硬编码创建任务
"""

import asyncio
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import init_database, get_db, ScheduledTask
from services.scheduler_service import SchedulerService
from utils.logger import get_logger

logger = get_logger(__name__)

async def test_database_task_loading():
    """测试从数据库加载任务"""
    try:
        # 初始化数据库
        init_database()
        logger.info("数据库初始化完成")
        
        # 清理现有任务（可选）
        db_gen = get_db()
        db = next(db_gen)
        try:
            existing_tasks = db.query(ScheduledTask).all()
            logger.info(f"数据库中现有任务数量: {len(existing_tasks)}")
            
            for task in existing_tasks:
                logger.info(f"现有任务: {task.name} (ID: {task.task_id}, 函数: {task.task_function}, 活跃: {task.is_active})")
        finally:
            db.close()
        
        # 如果没有任务，先创建一些测试任务
        if len(existing_tasks) == 0:
            logger.info("数据库中没有任务，创建默认任务...")
            from core.task_manager import TaskManager
            task_manager = TaskManager()
            task_manager.create_default_tasks()
            
            # 重新查询任务
            db_gen = get_db()
            db = next(db_gen)
            try:
                existing_tasks = db.query(ScheduledTask).all()
                logger.info(f"创建默认任务后，数据库中任务数量: {len(existing_tasks)}")
            finally:
                db.close()
        
        # 创建调度服务并启动
        logger.info("\n=== 启动调度服务，测试从数据库加载任务 ===")
        scheduler_service = SchedulerService()
        
        # 启动服务（这里会调用_load_tasks_from_database）
        await scheduler_service.start()
        
        # 等待一段时间观察日志
        await asyncio.sleep(2)
        
        # 获取所有任务状态
        all_tasks = await scheduler_service.get_all_tasks()
        logger.info(f"\n=== 调度服务中加载的任务状态 ===")
        for task_status in all_tasks:
            logger.info(f"任务: {task_status['name']} - 状态: {task_status['status']} - 活跃: {task_status['is_active']}")
        
        # 停止调度服务
        await scheduler_service.stop()
        logger.info("\n=== 调度服务已停止 ===")
        
        logger.info("\n✅ 从数据库加载任务测试完成")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    print("开始测试从数据库加载任务功能...")
    asyncio.run(test_database_task_loading())
    print("测试完成！")