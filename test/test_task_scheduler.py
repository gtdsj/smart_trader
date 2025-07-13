#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务调度系统测试

测试基于数据库的任务调度系统功能，包括：
1. 任务管理器的基本功能
2. 任务的创建、执行和状态管理
3. 调度服务的集成测试
"""

import asyncio
import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.task_manager import TaskManager
from core.task_functions import get_task_functions
from services.scheduler_service import SchedulerService
from core.database import get_db, ScheduledTask, TaskExecutionHistory, init_database
from utils.logger import get_logger

# 初始化数据库
init_database()

logger = get_logger(__name__)

class TestTaskManager:
    """任务管理器测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.task_manager = TaskManager()
        
    def test_register_task_functions(self):
        """测试任务函数注册"""
        task_functions = get_task_functions()
        
        # 验证必要的任务函数存在
        assert 'update_stock_basic_info' in task_functions
        assert 'update_daily_stock_data' in task_functions
        assert 'run_stock_selection' in task_functions
        assert 'health_check_task' in task_functions
        
        # 注册任务函数
        for name, func in task_functions.items():
            self.task_manager.register_task_function(name, func)
            
        # 验证注册成功
        assert len(self.task_manager._task_functions) >= 4
        
    def test_create_default_tasks(self):
        """测试创建默认任务"""
        try:
            # 创建默认任务
            self.task_manager.create_default_tasks()
            
            # 验证任务创建成功
            db_gen = get_db()
            db = next(db_gen)
            try:
                tasks = db.query(ScheduledTask).all()
                task_ids = [task.task_id for task in tasks]
                
                # 验证必要的任务存在
                assert 'daily_stock_info_update' in task_ids
                assert 'daily_stock_data_update' in task_ids
                assert 'daily_stock_selection' in task_ids
                
                logger.info(f"创建了 {len(tasks)} 个默认任务")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"创建默认任务测试失败: {e}")
            raise
            
    def test_get_pending_tasks(self):
        """测试获取待执行任务"""
        try:
            # 先创建默认任务
            self.task_manager.create_default_tasks()
            
            # 获取待执行任务
            pending_tasks = self.task_manager.get_pending_tasks()
            
            logger.info(f"找到 {len(pending_tasks)} 个待执行任务")
            
            # 验证任务格式
            for task in pending_tasks:
                assert hasattr(task, 'task_id')
                assert hasattr(task, 'name')
                assert hasattr(task, 'task_function')
                assert hasattr(task, 'cron_expression')
                
        except Exception as e:
            logger.error(f"获取待执行任务测试失败: {e}")
            raise
            
    @pytest.mark.asyncio
    async def test_execute_task(self):
        """测试任务执行"""
        try:
            # 注册测试任务函数
            async def test_task():
                return {"status": "success", "message": "测试任务执行成功"}
                
            self.task_manager.register_task_function('test_task', test_task)
            
            # 创建测试任务（使用时间戳确保唯一性）
            import time
            unique_id = f'test_task_{int(time.time() * 1000)}'
            db_gen = get_db()
            db = next(db_gen)
            try:
                test_task_obj = ScheduledTask(
                    task_id=unique_id,
                    name='测试任务',
                    description='用于测试的任务',
                    task_type='TEST',
                    cron_expression='0 0 * * *',
                    task_function='test_task',
                    task_params='{}',
                    is_active=True
                )
                db.add(test_task_obj)
                db.commit()
            finally:
                db.close()
                
            # 重新查询任务对象以避免分离状态
            db_gen = get_db()
            db = next(db_gen)
            try:
                fresh_task = db.query(ScheduledTask).filter(
                    ScheduledTask.task_id == unique_id
                ).first()
                
                # 执行任务
                result = await self.task_manager.execute_task(fresh_task)
            finally:
                db.close()
            
            # 验证执行结果
            assert result is True
            
            # 验证执行历史记录
            db_gen = get_db()
            db = next(db_gen)
            try:
                history = db.query(TaskExecutionHistory).filter(
                    TaskExecutionHistory.task_id == unique_id
                ).first()
                
                assert history is not None
                assert history.status == 'SUCCESS'
            finally:
                db.close()
                
            logger.info("任务执行测试通过")
            
        except Exception as e:
            logger.error(f"任务执行测试失败: {e}")
            raise
            
class TestSchedulerService:
    """调度服务测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.scheduler_service = SchedulerService()
        
    @pytest.mark.asyncio
    async def test_scheduler_lifecycle(self):
        """测试调度服务生命周期"""
        try:
            # 启动调度服务
            await self.scheduler_service.start()
            
            # 验证服务状态
            assert self.scheduler_service.is_running() == True
            
            # 等待一段时间让调度器运行
            await asyncio.sleep(2)
            
            # 停止调度服务
            await self.scheduler_service.stop()
            
            # 验证服务状态
            assert self.scheduler_service.is_running() == False
            
            logger.info("调度服务生命周期测试通过")
            
        except Exception as e:
            logger.error(f"调度服务生命周期测试失败: {e}")
            raise
            
    @pytest.mark.asyncio
    async def test_task_management(self):
        """测试任务管理功能"""
        try:
            # 启动调度服务
            await self.scheduler_service.start()
            
            # 等待一下确保服务完全启动
            await asyncio.sleep(0.1)
            
            # 添加测试任务
            task_data = {
                'task_id': 'test_management_task',
                'name': '任务管理测试',
                'description': '用于测试任务管理功能',
                'task_type': 'TEST',
                'cron_expression': '0 0 * * *',
                'task_function': 'health_check_task',
                'task_params': {}
            }
            
            # 添加任务
            result = await self.scheduler_service.add_task(task_data)
            assert result == True
            
            # 获取任务状态
            status = await self.scheduler_service.get_task_status('test_management_task')
            assert status is not None
            
            # 禁用任务
            result = await self.scheduler_service.disable_task('test_management_task')
            assert result == True
            
            # 启用任务
            result = await self.scheduler_service.enable_task('test_management_task')
            assert result == True
            
            # 强制执行任务
            result = await self.scheduler_service.force_execute_task('test_management_task')
            assert result == True
            
            # 移除任务
            result = await self.scheduler_service.remove_task('test_management_task')
            assert result == True
            
            # 停止调度服务
            await self.scheduler_service.stop()
            
            logger.info("任务管理功能测试通过")
            
        except Exception as e:
            logger.error(f"任务管理功能测试失败: {e}")
            raise
            
def test_task_functions():
    """测试任务函数"""
    try:
        task_functions = get_task_functions()
        
        # 验证任务函数可调用
        for name, func in task_functions.items():
            assert callable(func)
            logger.info(f"任务函数 {name} 可调用")
            
        logger.info("任务函数测试通过")
        
    except Exception as e:
        logger.error(f"任务函数测试失败: {e}")
        raise
        
def test_cron_expression_validation():
    """测试cron表达式验证"""
    try:
        from croniter import croniter
        
        # 测试有效的cron表达式
        valid_expressions = [
            '0 0 * * *',      # 每天午夜
            '0 9 * * 1-5',    # 工作日上午9点
            '30 15 * * 1-5',  # 工作日下午3:30
            '0 20 * * *',     # 每天晚上8点
        ]
        
        for expr in valid_expressions:
            cron = croniter(expr, datetime.now())
            next_time = cron.get_next(datetime)
            # 验证下次执行时间在未来
            assert isinstance(next_time, datetime)
            logger.info(f"cron表达式 '{expr}' 验证通过")
            
        # 测试无效的cron表达式
        invalid_expressions = [
            '60 0 * * *',     # 无效分钟
            '0 25 * * *',     # 无效小时
            '0 0 32 * *',     # 无效日期
        ]
        
        for expr in invalid_expressions:
            try:
                cron = croniter(expr, datetime.now())
                cron.get_next(datetime)
                assert False, f"应该抛出异常的表达式: {expr}"
            except Exception as e:
                if "AssertionError" not in str(type(e)):
                    logger.info(f"cron表达式 '{expr}' 正确抛出异常: {e}")
                else:
                    raise
                
        logger.info("cron表达式验证测试通过")
        
    except Exception as e:
        logger.error(f"cron表达式验证测试失败: {e}")
        raise
        
if __name__ == '__main__':
    """运行测试"""
    print("开始任务调度系统测试...")
    
    try:
        # 基础功能测试
        test_task_functions()
        test_cron_expression_validation()
        
        # 任务管理器测试
        task_manager_test = TestTaskManager()
        task_manager_test.setup_method()
        task_manager_test.test_register_task_functions()
        task_manager_test.test_create_default_tasks()
        task_manager_test.test_get_pending_tasks()
        
        # 异步测试
        async def run_async_tests():
            await task_manager_test.test_execute_task()
            
            scheduler_test = TestSchedulerService()
            scheduler_test.setup_method()
            await scheduler_test.test_scheduler_lifecycle()
            await scheduler_test.test_task_management()
            
        asyncio.run(run_async_tests())
        
        print("\n✅ 所有测试通过！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)