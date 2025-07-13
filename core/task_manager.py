#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务管理器模块
负责管理和执行基于数据库的定时任务
"""

import json
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from croniter import croniter
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from core.database import get_db, ScheduledTask, TaskExecutionHistory
from core.time_utils import TimeUtils


class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self._task_functions: Dict[str, Callable] = {}
        self._running_tasks: Dict[str, bool] = {}
        
    def register_task_function(self, function_name: str, function: Callable):
        """注册任务执行函数"""
        self._task_functions[function_name] = function
        logger.info(f"注册任务函数: {function_name}")
        
    def create_default_tasks(self):
        """创建默认的定时任务"""
        default_tasks = [
            {
                'task_id': 'daily_stock_info_update',
                'name': '每日股票基础信息更新',
                'description': '每天更新全量A股股票基础信息',
                'task_type': 'DATA_UPDATE',
                'cron_expression': '0 8 * * *',  # 每天早上8点
                'task_function': 'update_stock_basic_info',
                'task_params': '{}'
            },
            {
                'task_id': 'daily_stock_data_update',
                'name': '每日股票数据更新',
                'description': '每个交易日收盘后更新所有股票当天的日线数据',
                'task_type': 'DATA_UPDATE',
                'cron_expression': '0 16 * * 1-5',  # 工作日下午4点
                'task_function': 'update_daily_stock_data',
                'task_params': '{}'
            },
            {
                'task_id': 'daily_stock_selection',
                'name': '每日选股任务',
                'description': '每天执行选股任务',
                'task_type': 'STOCK_SELECTION',
                'cron_expression': '0 20 * * *',  # 每天晚上8点
                'task_function': 'run_stock_selection',
                'task_params': '{}'
            }
        ]
        
        db_gen = get_db()
        db = next(db_gen)
        try:
            for task_data in default_tasks:
                existing_task = db.query(ScheduledTask).filter(
                    ScheduledTask.task_id == task_data['task_id']
                ).first()
                
                if not existing_task:
                    # 计算下次执行时间
                    cron = croniter(task_data['cron_expression'], datetime.now())
                    next_run_time = cron.get_next(datetime)
                    
                    task = ScheduledTask(
                        task_id=task_data['task_id'],
                        name=task_data['name'],
                        description=task_data['description'],
                        task_type=task_data['task_type'],
                        cron_expression=task_data['cron_expression'],
                        task_function=task_data['task_function'],
                        task_params=task_data['task_params'],
                        next_run_time=next_run_time
                    )
                    db.add(task)
                    logger.info(f"创建默认任务: {task_data['name']}")
                else:
                    logger.info(f"任务已存在: {task_data['name']}")
            
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"创建默认任务失败: {e}")
            raise e
        finally:
            db.close()
            
    def get_pending_tasks(self) -> List[ScheduledTask]:
        """获取待执行的任务"""
        now = datetime.now()
        
        db_gen = get_db()
        db = next(db_gen)
        try:
            tasks = db.query(ScheduledTask).filter(
                and_(
                    ScheduledTask.is_active == True,
                    ScheduledTask.next_run_time <= now,
                    or_(
                        ScheduledTask.status == 'PENDING',
                        ScheduledTask.status == 'FAILED'
                    )
                )
            ).all()
            
            return tasks
        finally:
            db.close()
            
    def should_execute_task(self, task: ScheduledTask) -> bool:
        """判断任务是否应该执行"""
        now = datetime.now()
        today = now.date()
        
        # 检查今天是否已经执行过
        db_gen = get_db()
        db = next(db_gen)
        try:
            today_execution = db.query(TaskExecutionHistory).filter(
                and_(
                    TaskExecutionHistory.task_id == task.task_id,
                    TaskExecutionHistory.execution_date == today,
                    TaskExecutionHistory.status == 'SUCCESS'
                )
            ).first()
            
            if today_execution:
                logger.info(f"任务 {task.name} 今天已经成功执行过，跳过")
                return False
        except Exception as db_e:
            logger.error(f"检查任务执行历史失败: {db_e}")
        finally:
            db.close()
                
        # 对于交易日相关的任务，检查是否为交易日
        if task.task_type == 'DATA_UPDATE' and 'stock_data' in task.task_id:
            if not TimeUtils.is_trading_day(today):
                logger.info(f"今日非交易日，跳过任务: {task.name}")
                return False
                
        return True
        
    async def execute_task(self, task: ScheduledTask, force: bool = False) -> bool:
        """执行单个任务"""
        if task.task_id in self._running_tasks and self._running_tasks[task.task_id]:
            logger.warning(f"任务 {task.name} 正在执行中，跳过")
            return False
            
        if not force and not self.should_execute_task(task):
            # 更新下次执行时间
            self._update_next_run_time(task)
            return False
            
        self._running_tasks[task.task_id] = True
        start_time = datetime.now()
        execution_date = start_time.date()
        
        try:
            logger.info(f"开始执行任务: {task.name}")
            
            # 获取任务函数
            if task.task_function not in self._task_functions:
                raise ValueError(f"未找到任务函数: {task.task_function}")
                
            task_function = self._task_functions[task.task_function]
            
            # 解析任务参数
            task_params = {}
            if task.task_params:
                try:
                    task_params = json.loads(task.task_params)
                except json.JSONDecodeError:
                    logger.warning(f"任务参数解析失败: {task.task_params}")
                    
            # 执行任务
            if asyncio.iscoroutinefunction(task_function):
                result = await task_function(**task_params)
            else:
                result = task_function(**task_params)
                
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 记录执行历史
            self._record_execution_history(
                task.task_id, execution_date, start_time, end_time,
                'SUCCESS', str(result) if result else None, None, duration
            )
            
            # 更新任务状态
            self._update_task_status(task, 'COMPLETED', None, start_time)
            
            logger.info(f"任务执行成功: {task.name}, 耗时: {duration:.2f}秒")
            return True
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            
            # 记录执行历史
            self._record_execution_history(
                task.task_id, execution_date, start_time, end_time,
                'FAILED', None, error_msg, duration
            )
            
            # 更新任务状态
            self._update_task_status(task, 'FAILED', error_msg, start_time)
            
            logger.error(f"任务执行失败: {task.name}, 错误: {error_msg}")
            return False
            
        finally:
            self._running_tasks[task.task_id] = False
            # 更新下次执行时间
            self._update_next_run_time(task)
            
    def _record_execution_history(self, task_id: str, execution_date: datetime.date,
                                 start_time: datetime, end_time: datetime,
                                 status: str, result_data: Optional[str],
                                 error_message: Optional[str], duration: float):
        """记录任务执行历史"""
        db_gen = get_db()
        db = next(db_gen)
        try:
            history = TaskExecutionHistory(
                task_id=task_id,
                execution_date=execution_date,
                start_time=start_time,
                end_time=end_time,
                status=status,
                result_data=result_data,
                error_message=error_message,
                execution_duration=duration
            )
            db.add(history)
            db.commit()
        except Exception as db_e:
            db.rollback()
            logger.error(f"记录任务执行历史失败: {db_e}")
        finally:
            db.close()
            
    def _update_task_status(self, task: ScheduledTask, status: str,
                           error_message: Optional[str], last_run_time: datetime):
        """更新任务状态"""
        db_gen = get_db()
        db = next(db_gen)
        try:
            db_task = db.query(ScheduledTask).filter(
                ScheduledTask.task_id == task.task_id
            ).first()
            
            if db_task:
                db_task.status = status
                db_task.error_message = error_message
                db_task.last_run_time = last_run_time
                db_task.run_count += 1
                if status == 'COMPLETED':
                    db_task.success_count += 1
                db_task.updated_at = datetime.now()
                db.commit()
        except Exception as db_e:
            db.rollback()
            logger.error(f"更新任务状态失败: {db_e}")
        finally:
            db.close()
                
    def _update_next_run_time(self, task: ScheduledTask):
        """更新下次执行时间"""
        try:
            cron = croniter(task.cron_expression, datetime.now())
            next_run_time = cron.get_next(datetime)
            
            db_gen = get_db()
            db = next(db_gen)
            try:
                db_task = db.query(ScheduledTask).filter(
                    ScheduledTask.task_id == task.task_id
                ).first()
                
                if db_task:
                    db_task.next_run_time = next_run_time
                    db_task.updated_at = datetime.now()
                    db.commit()
            except Exception as db_e:
                db.rollback()
                logger.error(f"更新任务下次执行时间失败: {db_e}")
            finally:
                db.close()
                    
        except Exception as e:
            logger.error(f"更新任务下次执行时间失败: {task.task_id}, 错误: {e}")
            
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        db_gen = get_db()
        db = next(db_gen)
        try:
            task = db.query(ScheduledTask).filter(
                ScheduledTask.task_id == task_id
            ).first()
            
            if not task:
                return None
                
            # 获取最近的执行历史
            recent_history = db.query(TaskExecutionHistory).filter(
                TaskExecutionHistory.task_id == task_id
            ).order_by(TaskExecutionHistory.start_time.desc()).limit(5).all()
            
            return {
                'task_id': task.task_id,
                'name': task.name,
                'status': task.status,
                'is_active': task.is_active,
                'last_run_time': task.last_run_time,
                'next_run_time': task.next_run_time,
                'run_count': task.run_count,
                'success_count': task.success_count,
                'error_message': task.error_message,
                'recent_executions': [
                    {
                        'execution_date': h.execution_date,
                        'start_time': h.start_time,
                        'end_time': h.end_time,
                        'status': h.status,
                        'duration': h.execution_duration,
                        'error_message': h.error_message
                    } for h in recent_history
                ]
            }
        except Exception as db_e:
            logger.error(f"获取任务状态失败: {db_e}")
            return None
        finally:
            db.close()
            
    def get_all_tasks_status(self) -> List[Dict[str, Any]]:
        """获取所有任务状态"""
        db_gen = get_db()
        db = next(db_gen)
        try:
            tasks = db.query(ScheduledTask).all()
            return [self.get_task_status(task.task_id) for task in tasks]
        except Exception as db_e:
            logger.error(f"获取所有任务状态失败: {db_e}")
            return []
        finally:
            db.close()


# 导入asyncio模块
import asyncio