#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调度服务模块
负责管理和执行定时任务
基于数据库的任务调度系统
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from loguru import logger

from core.time_utils import TimeUtils
from core.task_manager import TaskManager
from core.task_functions import get_task_functions
from services.notification_service import NotificationService, NotificationType, NotificationLevel
from services.data_service import DataService
from strategies.custom_stock_selection import CustomStockSelectionStrategy


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 正在执行
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"        # 执行失败
    CANCELLED = "cancelled"  # 已取消


class TaskType(Enum):
    """任务类型"""
    STOCK_SELECTION = "stock_selection"  # 选股任务
    DATA_UPDATE = "data_update"          # 数据更新任务
    STRATEGY_EXECUTION = "strategy_execution"  # 策略执行任务
    NOTIFICATION = "notification"        # 通知任务


@dataclass
class ScheduledTask:
    """定时任务配置"""
    task_id: str
    name: str
    description: str
    task_type: TaskType
    cron_expression: str
    task_function: Callable
    task_params: Dict[str, Any]
    is_active: bool = True
    last_run_time: Optional[datetime] = None
    next_run_time: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    error_message: Optional[str] = None
    created_time: datetime = None
    
    def __post_init__(self):
        if self.created_time is None:
            self.created_time = datetime.now()
        self._update_next_run_time()
    
    def _update_next_run_time(self):
        """更新下次执行时间"""
        try:
            cron = croniter(self.cron_expression, datetime.now())
            self.next_run_time = cron.get_next(datetime)
        except Exception as e:
            logger.error(f"更新任务{self.task_id}下次执行时间失败: {e}")
            self.next_run_time = None


class SchedulerService:
    """调度服务 - 基于数据库的任务调度系统"""
    
    def __init__(self):
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._task_manager: Optional[TaskManager] = None
        self._notification_service = NotificationService()
        self._running = False
        self._task_check_interval = 60  # 每60秒检查一次待执行任务
        
    async def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("调度服务已经在运行")
            return
            
        logger.info("启动基于数据库的调度服务")
        
        try:
            # 初始化任务管理器
            self._task_manager = TaskManager()
            
            # 注册任务执行函数
            task_functions = get_task_functions()
            for func_name, func in task_functions.items():
                self._task_manager.register_task_function(func_name, func)
                
            # 从数据库加载并注册任务
            self._load_tasks_from_database()
            
            # 初始化调度器
            self._scheduler = AsyncIOScheduler()
            
            # 添加定期检查任务的作业
            self._scheduler.add_job(
                self._check_and_execute_tasks,
                trigger=IntervalTrigger(seconds=self._task_check_interval),
                id='task_checker',
                name='定期检查并执行任务',
                max_instances=1
            )
            
            # 启动调度器
            self._scheduler.start()
            self._running = True
            
            logger.info("调度服务启动完成")
            
            # 立即执行一次任务检查
            await self._check_and_execute_tasks()
            
        except Exception as e:
            logger.error(f"调度服务启动失败: {e}")
            raise
        
    async def stop(self):
        """停止调度器"""
        if not self._running:
            return
            
        logger.info("停止调度服务")
        self._running = False
        
        try:
            if self._scheduler:
                self._scheduler.shutdown(wait=True)
                
            logger.info("调度服务已停止")
            
        except Exception as e:
            logger.error(f"停止调度服务时出错: {e}")
        
    def is_running(self) -> bool:
        """检查调度服务是否正在运行"""
        return self._running
        
    def _load_tasks_from_database(self):
        """从数据库加载任务并验证任务函数"""
        try:
            from core.database import get_db, ScheduledTask
            
            db_gen = get_db()
            db = next(db_gen)
            try:
                # 获取所有活跃任务
                tasks = db.query(ScheduledTask).filter(
                    ScheduledTask.is_active == True
                ).all()
                
                logger.info(f"从数据库加载了 {len(tasks)} 个活跃任务")
                
                # 验证每个任务的函数是否已注册
                missing_functions = []
                for task in tasks:
                    if not self._task_manager or task.task_function not in self._task_manager._task_functions:
                        missing_functions.append(task.task_function)
                        logger.warning(f"任务 {task.name} 的函数 {task.task_function} 未注册")
                    else:
                        logger.info(f"任务 {task.name} 已加载，函数: {task.task_function}")
                
                if missing_functions:
                    logger.error(f"以下任务函数未注册: {missing_functions}")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"从数据库加载任务失败: {e}")
            # 如果数据库中没有任务，创建默认任务
            logger.info("尝试创建默认任务...")
            if self._task_manager:
                self._task_manager.create_default_tasks()


        
    async def _check_and_execute_tasks(self):
        """检查并执行待执行的任务"""
        if not self._task_manager:
            return
            
        try:
            # 获取待执行的任务
            pending_tasks = self._task_manager.get_pending_tasks()
            
            if not pending_tasks:
                logger.debug("没有待执行的任务")
                return
                
            logger.info(f"发现 {len(pending_tasks)} 个待执行任务")
            
            # 并发执行任务
            tasks = []
            for task in pending_tasks:
                task_coroutine = self._task_manager.execute_task(task)
                tasks.append(asyncio.create_task(task_coroutine))
                
            # 等待所有任务完成
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 统计执行结果
                success_count = sum(1 for result in results if result is True)
                failed_count = len(results) - success_count
                
                logger.info(f"任务执行完成: 成功 {success_count}, 失败 {failed_count}")
                
                # 发送执行结果通知
                if failed_count > 0:
                    await self._notification_service.send_notification(
                        title="任务执行结果",
                        message=f"任务执行完成: 成功 {success_count}, 失败 {failed_count}",
                        notification_type=NotificationType.TASK_COMPLETION,
                        level=NotificationLevel.WARNING if failed_count > 0 else NotificationLevel.INFO
                    )
                    
        except Exception as e:
            logger.error(f"检查和执行任务时出错: {e}")
            
            # 发送错误通知
            await self._notification_service.send_notification(
                title="任务调度错误",
                message=f"任务调度过程中发生错误: {str(e)}",
                notification_type=NotificationType.ERROR,
                level=NotificationLevel.ERROR
            )
                
    async def force_execute_task(self, task_id: str) -> bool:
        """强制执行指定任务"""
        if not self._task_manager:
            return False
            
        try:
            from core.database import get_db, ScheduledTask
            
            db_gen = get_db()
            db = next(db_gen)
            try:
                task = db.query(ScheduledTask).filter(
                    ScheduledTask.task_id == task_id
                ).first()
                
                if not task:
                    logger.warning(f"任务不存在: {task_id}")
                    return False
                    
                # 强制执行任务
                result = await self._task_manager.execute_task(task, force=True)
                logger.info(f"强制执行任务完成: {task_id}, 结果: {result}")
                return result
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"强制执行任务失败: {e}")
            return False
            
    async def add_task(self, task_data: Dict[str, Any]) -> bool:
        """添加新任务到数据库"""
        try:
            from croniter import croniter
            from core.database import get_db, ScheduledTask
            
            # 验证cron表达式
            try:
                cron = croniter(task_data['cron_expression'])
                next_run_time = cron.get_next(datetime)
            except Exception as e:
                logger.error(f"无效的cron表达式: {task_data['cron_expression']}, 错误: {e}")
                return False
                
            db_gen = get_db()
            db = next(db_gen)
            try:
                # 检查任务是否已存在
                existing_task = db.query(ScheduledTask).filter(
                    ScheduledTask.task_id == task_data['task_id']
                ).first()
                
                if existing_task:
                    logger.warning(f"任务已存在: {task_data['task_id']}")
                    return False
                    
                # 创建新任务
                new_task = ScheduledTask(
                    task_id=task_data['task_id'],
                    name=task_data['name'],
                    description=task_data.get('description'),
                    task_type=task_data['task_type'],
                    cron_expression=task_data['cron_expression'],
                    task_function=task_data['task_function'],
                    task_params=task_data.get('task_params', '{}'),
                    next_run_time=next_run_time
                )
                
                db.add(new_task)
                db.commit()
            except Exception as db_e:
                db.rollback()
                logger.error(f"数据库操作失败: {db_e}")
                return False
            finally:
                db.close()
                
                logger.info(f"成功添加任务: {task_data['name']}")
                return True
                
        except Exception as e:
            logger.error(f"添加任务失败: {e}")
            return False
            
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if not self._task_manager:
            return None
            
        return self._task_manager.get_task_status(task_id)
        
    async def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务状态"""
        if not self._task_manager:
            return []
            
        return self._task_manager.get_all_tasks_status()
        
    async def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        try:
            from core.database import get_db, ScheduledTask
            
            db_gen = get_db()
            db = next(db_gen)
            try:
                task = db.query(ScheduledTask).filter(
                    ScheduledTask.task_id == task_id
                ).first()
                
                if not task:
                    logger.warning(f"任务不存在: {task_id}")
                    return False
                    
                task.is_active = True
                task.updated_at = datetime.now()
                db.commit()
            except Exception as db_e:
                db.rollback()
                logger.error(f"数据库操作失败: {db_e}")
                return False
            finally:
                db.close()
                
                logger.info(f"成功启用任务: {task_id}")
                return True
                
        except Exception as e:
            logger.error(f"启用任务失败: {e}")
            return False
            
    async def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        try:
            from core.database import get_db, ScheduledTask
            
            db_gen = get_db()
            db = next(db_gen)
            try:
                task = db.query(ScheduledTask).filter(
                    ScheduledTask.task_id == task_id
                ).first()
                
                if not task:
                    logger.warning(f"任务不存在: {task_id}")
                    return False
                    
                task.is_active = False
                task.updated_at = datetime.now()
                db.commit()
            except Exception as db_e:
                db.rollback()
                logger.error(f"数据库操作失败: {db_e}")
                return False
            finally:
                db.close()
                
                logger.info(f"成功禁用任务: {task_id}")
                return True
                
        except Exception as e:
            logger.error(f"禁用任务失败: {e}")
            return False
            
    async def remove_task(self, task_id: str) -> bool:
        """从数据库中移除任务"""
        try:
            from core.database import get_db, ScheduledTask
            
            db_gen = get_db()
            db = next(db_gen)
            try:
                task = db.query(ScheduledTask).filter(
                    ScheduledTask.task_id == task_id
                ).first()
                
                if not task:
                    logger.warning(f"任务不存在: {task_id}")
                    return False
                    
                db.delete(task)
                db.commit()
            except Exception as db_e:
                db.rollback()
                logger.error(f"数据库操作失败: {db_e}")
                return False
            finally:
                db.close()
                
                logger.info(f"成功移除任务: {task_id}")
                return True
                
        except Exception as e:
             logger.error(f"移除任务失败: {e}")
             return False