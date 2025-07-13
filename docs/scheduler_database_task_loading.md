# 调度服务从数据库加载任务功能实现

## 概述

本文档记录了将调度服务从硬编码任务创建改为从数据库动态加载任务的实现过程。

## 问题描述

原始的 `SchedulerService` 在启动时会硬编码创建默认任务，这种方式存在以下问题：

1. **缺乏灵活性**：任务配置固化在代码中，难以动态调整
2. **维护困难**：新增或修改任务需要修改代码并重新部署
3. **数据不一致**：代码中的任务配置可能与数据库中的任务记录不一致

## 解决方案

### 1. 修改调度服务启动逻辑

在 `services/scheduler_service.py` 中，将 `start()` 方法中的硬编码任务创建：

```python
# 原始代码（硬编码）
self._task_manager.create_default_tasks()

# 注册任务函数
self._task_manager.register_task_function('daily_stock_info_update', update_stock_basic_info)
self._task_manager.register_task_function('daily_stock_data_update', update_stock_data)
self._task_manager.register_task_function('daily_stock_selection', stock_selection_task)
self._task_manager.register_task_function('health_check_task', health_check_task)

# 获取所有活跃任务并添加到调度器
tasks = await self._task_manager.get_active_tasks()
for task in tasks:
    if task.task_function in self._task_manager._task_functions:
        self._scheduler.add_job(
            func=self._task_manager.execute_task,
            args=[task],
            trigger='cron',
            hour=task.schedule_time.hour,
            minute=task.schedule_time.minute,
            id=task.task_id,
            replace_existing=True
        )
```

改为调用新的数据库加载方法：

```python
# 新代码（从数据库加载）
await self._load_tasks_from_database()
```

### 2. 实现数据库任务加载方法

新增 `_load_tasks_from_database()` 方法，实现以下功能：

```python
async def _load_tasks_from_database(self):
    """从数据库加载任务并注册到调度器"""
    try:
        # 注册任务函数
        self._task_manager.register_task_function('daily_stock_info_update', update_stock_basic_info)
        self._task_manager.register_task_function('daily_stock_data_update', update_stock_data)
        self._task_manager.register_task_function('daily_stock_selection', stock_selection_task)
        self._task_manager.register_task_function('health_check_task', health_check_task)
        
        # 从数据库获取所有活跃任务
        tasks = await self._task_manager.get_active_tasks()
        
        if not tasks:
            self._logger.warning("数据库中没有找到活跃任务，尝试创建默认任务")
            self._task_manager.create_default_tasks()
            tasks = await self._task_manager.get_active_tasks()
        
        # 验证任务函数是否已注册
        unregistered_functions = []
        registered_tasks = []
        
        for task in tasks:
            if task.task_function in self._task_manager._task_functions:
                registered_tasks.append(task)
            else:
                unregistered_functions.append(task.task_function)
        
        if unregistered_functions:
            self._logger.error(f"以下任务函数未注册: {unregistered_functions}")
        
        # 将已注册的任务添加到调度器
        for task in registered_tasks:
            self._scheduler.add_job(
                func=self._task_manager.execute_task,
                args=[task],
                trigger='cron',
                hour=task.schedule_time.hour,
                minute=task.schedule_time.minute,
                id=task.task_id,
                replace_existing=True
            )
            self._logger.info(f"任务已添加到调度器: {task.name} (ID: {task.task_id})")
        
        self._logger.info(f"从数据库加载了 {len(registered_tasks)} 个任务")
        
    except Exception as e:
        self._logger.error(f"从数据库加载任务失败: {e}")
        # 如果加载失败，回退到创建默认任务
        self._logger.info("回退到创建默认任务")
        self._task_manager.create_default_tasks()
        # 重新尝试加载
        await self._load_tasks_from_database()
```

## 功能特点

### 1. 动态任务加载
- 从数据库中读取所有活跃任务
- 验证任务函数是否已注册
- 只加载有效的任务到调度器

### 2. 容错机制
- 如果数据库中没有任务，自动创建默认任务
- 如果加载失败，回退到默认任务创建逻辑
- 记录未注册的任务函数，便于调试

### 3. 日志记录
- 详细记录任务加载过程
- 记录成功加载的任务数量
- 记录错误和警告信息

## 测试验证

### 1. 单元测试
所有现有的调度服务测试用例均通过，确保功能兼容性。

### 2. 集成测试
创建了专门的测试脚本 `test/test_database_task_loading.py` 来验证：
- 数据库任务加载功能
- 任务状态显示
- 错误处理机制

### 3. 测试结果
```
=== 调度服务中加载的任务状态 ===
任务: 每日股票数据更新 - 状态: PENDING - 活跃: True
任务: 每日选股任务 - 状态: PENDING - 活跃: True
任务: 每日股票基础信息更新 - 状态: COMPLETED - 活跃: True
```

## 优势

1. **灵活性提升**：可以通过数据库动态管理任务，无需修改代码
2. **维护简化**：新增任务只需在数据库中添加记录
3. **数据一致性**：任务配置统一存储在数据库中
4. **可扩展性**：支持更复杂的任务管理需求
5. **向后兼容**：保持了原有的API和功能

## 注意事项

1. **任务函数注册**：新的任务函数需要在 `_load_tasks_from_database()` 方法中注册
2. **数据库依赖**：确保数据库连接正常，否则会回退到默认任务
3. **错误处理**：注意检查日志中的错误信息，特别是未注册的任务函数

## 后续改进

1. **动态函数注册**：考虑实现更灵活的任务函数注册机制
2. **任务热更新**：支持在运行时动态添加或移除任务
3. **任务依赖管理**：支持任务间的依赖关系
4. **任务分组**：支持任务分组和批量管理