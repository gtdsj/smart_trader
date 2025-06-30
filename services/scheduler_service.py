# coding=utf-8
"""
定时任务调度服务
用于管理和执行定时任务，包括选股任务、数据更新等
"""

import asyncio
from datetime import datetime, time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import json
from croniter import croniter

# from utils.logger import logger  # 使用简单的print替代
from services.notification_service import NotificationService, NotificationType, NotificationLevel
from strategies.custom_stock_selection import CustomStockSelectionStrategy
from services.data_service import DataService


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
            print(f"[ERROR] 更新任务{self.task_id}下次执行时间失败: {e}")
            self.next_run_time = None


class SchedulerService:
    """定时任务调度服务"""
    
    def __init__(self, data_service: DataService, notification_service: NotificationService):
        self.data_service = data_service
        self.notification_service = notification_service
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.is_running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        
        # 初始化选股策略
        self.stock_selection_strategy = CustomStockSelectionStrategy(data_service)
        
        # 注册默认任务
        self._register_default_tasks()
        
    async def start(self):
        """启动调度器"""
        if self.is_running:
            print("[WARNING] 调度器已在运行中")
            return
            
        self.is_running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        print("[INFO] 定时任务调度器已启动")
        
    async def stop(self):
        """停止调度器"""
        if not self.is_running:
            return
            
        self.is_running = False
        
        # 取消调度器任务
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
                
        # 取消所有运行中的任务
        for task_id, task in self.running_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
        self.running_tasks.clear()
        print("[INFO] 定时任务调度器已停止")
        
    def add_task(self, task: ScheduledTask) -> bool:
        """
        添加定时任务
        
        Args:
            task: 任务配置
            
        Returns:
            是否添加成功
        """
        try:
            # 验证cron表达式
            croniter(task.cron_expression)
            
            self.tasks[task.task_id] = task
            print(f"[INFO] 添加定时任务: {task.name} ({task.task_id})")
            return True
            
        except Exception as e:
            print(f"[ERROR] 添加定时任务失败: {e}")
            return False
            
    def remove_task(self, task_id: str) -> bool:
        """
        移除定时任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否移除成功
        """
        try:
            if task_id in self.tasks:
                # 如果任务正在运行，先取消
                if task_id in self.running_tasks:
                    self.running_tasks[task_id].cancel()
                    del self.running_tasks[task_id]
                    
                del self.tasks[task_id]
                print(f"[INFO] 移除定时任务: {task_id}")
                return True
            else:
                print(f"[WARNING] 任务{task_id}不存在")
                return False
                
        except Exception as e:
            print(f"[ERROR] 移除定时任务失败: {e}")
            return False
            
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        if task_id not in self.tasks:
            return None
            
        task = self.tasks[task_id]
        return {
            'task_id': task.task_id,
            'name': task.name,
            'description': task.description,
            'task_type': task.task_type.value,
            'cron_expression': task.cron_expression,
            'is_active': task.is_active,
            'status': task.status.value,
            'last_run_time': task.last_run_time.isoformat() if task.last_run_time else None,
            'next_run_time': task.next_run_time.isoformat() if task.next_run_time else None,
            'error_message': task.error_message,
            'created_time': task.created_time.isoformat(),
            'is_running': task_id in self.running_tasks
        }
        
    def list_tasks(self) -> List[Dict[str, Any]]:
        """
        获取所有任务列表
        
        Returns:
            任务列表
        """
        return [self.get_task_status(task_id) for task_id in self.tasks.keys()]
        
    async def run_task_now(self, task_id: str) -> bool:
        """
        立即执行任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否启动成功
        """
        if task_id not in self.tasks:
            print(f"[ERROR] 任务{task_id}不存在")
            return False
            
        if task_id in self.running_tasks:
            print(f"[WARNING] 任务{task_id}正在运行中")
            return False
            
        task = self.tasks[task_id]
        self.running_tasks[task_id] = asyncio.create_task(
            self._execute_task(task)
        )
        
        print(f"[INFO] 手动执行任务: {task.name}")
        return True
        
    async def _scheduler_loop(self):
        """调度器主循环"""
        print("[INFO] 调度器主循环已启动")
        
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # 检查需要执行的任务
                for task_id, task in self.tasks.items():
                    if not task.is_active:
                        continue
                        
                    if task_id in self.running_tasks:
                        continue
                        
                    if task.next_run_time and current_time >= task.next_run_time:
                        # 执行任务
                        self.running_tasks[task_id] = asyncio.create_task(
                            self._execute_task(task)
                        )
                        
                        # 更新下次执行时间
                        task._update_next_run_time()
                        
                # 清理已完成的任务
                completed_tasks = []
                for task_id, running_task in self.running_tasks.items():
                    if running_task.done():
                        completed_tasks.append(task_id)
                        
                for task_id in completed_tasks:
                    del self.running_tasks[task_id]
                    
                # 等待一分钟后再次检查
                await asyncio.sleep(60)
                
            except Exception as e:
                print(f"[ERROR] 调度器循环出错: {e}")
                await asyncio.sleep(60)
                
    async def _execute_task(self, task: ScheduledTask):
        """
        执行任务
        
        Args:
            task: 任务配置
        """
        task.status = TaskStatus.RUNNING
        task.last_run_time = datetime.now()
        task.error_message = None
        
        print(f"[INFO] 开始执行任务: {task.name}")
        
        try:
            # 执行任务函数
            result = await task.task_function(**task.task_params)
            
            task.status = TaskStatus.COMPLETED
            print(f"[INFO] 任务执行完成: {task.name}")
            
            # 发送成功通知
            if task.task_type == TaskType.STOCK_SELECTION:
                await self._send_stock_selection_notification(task, result)
                
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            print(f"[ERROR] 任务执行失败: {task.name}, 错误: {e}")
            
            # 发送失败通知
            await self._send_task_failure_notification(task, e)
            
    async def _send_stock_selection_notification(self, task: ScheduledTask, result: List[Dict]):
        """
        发送选股结果通知
        
        Args:
            task: 任务配置
            result: 选股结果
        """
        try:
            if not result:
                content = "今日未发现符合条件的股票"
            else:
                # 构建选股结果消息
                content_lines = [f"**今日选股结果（共{len(result)}只）**\n"]
                
                for i, stock in enumerate(result[:10], 1):  # 只显示前10只
                    content_lines.append(
                        f"{i}. **{stock['stock_name']}({stock['stock_code']})**\n"
                        f"   - 最新价格: {stock['latest_price']:.2f}\n"
                        f"   - 涨跌幅: {stock['change_pct']:.2f}%\n"
                        f"   - 评分: {stock['score']:.1f}\n"
                        f"   - 选股理由: {stock['selection_reason']}\n"
                    )
                    
                if len(result) > 10:
                    content_lines.append(f"\n... 还有{len(result) - 10}只股票")
                    
                content = "\n".join(content_lines)
                
            await self.notification_service.send_dingtalk_notification(
                title=f"📈 {task.name}结果",
                content=content,
                notification_type=NotificationType.TRADE_SIGNAL,
                level=NotificationLevel.INFO
            )
            
        except Exception as e:
            print(f"[ERROR] 发送选股通知失败: {e}")
            
    async def _send_task_failure_notification(self, task: ScheduledTask, error: Exception):
        """
        发送任务失败通知
        
        Args:
            task: 任务配置
            error: 错误信息
        """
        try:
            content = f"**任务执行失败**\n\n"
            content += f"**任务名称**: {task.name}\n"
            content += f"**任务类型**: {task.task_type.value}\n"
            content += f"**失败时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            content += f"**错误信息**: {str(error)}\n"
            
            await self.notification_service.send_dingtalk_notification(
                title=f"❌ 任务执行失败",
                content=content,
                notification_type=NotificationType.SYSTEM_ERROR,
                level=NotificationLevel.ERROR
            )
            
        except Exception as e:
            print(f"[ERROR] 发送任务失败通知失败: {e}")
            
    def _register_default_tasks(self):
        """
        注册默认任务
        """
        # 每日选股任务（交易日上午9:00执行）
        stock_selection_task = ScheduledTask(
            task_id="daily_stock_selection",
            name="每日选股任务",
            description="基于多维度条件的每日选股任务",
            task_type=TaskType.STOCK_SELECTION,
            cron_expression="0 9 * * 1-5",  # 周一到周五上午9点
            task_function=self._run_stock_selection,
            task_params={}
        )
        
        self.add_task(stock_selection_task)
        
        # 盘后选股任务（交易日下午15:30执行）
        after_market_task = ScheduledTask(
            task_id="after_market_stock_selection",
            name="盘后选股任务",
            description="盘后基于当日数据的选股任务",
            task_type=TaskType.STOCK_SELECTION,
            cron_expression="30 15 * * 1-5",  # 周一到周五下午3:30
            task_function=self._run_stock_selection,
            task_params={}
        )
        
        self.add_task(after_market_task)
        
    async def _run_stock_selection(self) -> List[Dict[str, Any]]:
        """
        执行选股任务
        
        Returns:
            选股结果
        """
        return await self.stock_selection_strategy.screen_stocks()