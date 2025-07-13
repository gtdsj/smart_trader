# 任务调度器强制执行功能修复

## 问题描述

在任务调度系统的测试中，`force_execute_task` 方法无法正确强制执行已经在当天成功执行过的任务。测试用例 `test_task_management` 失败，错误信息为 `AssertionError: assert False == True`。

## 根本原因

1. **数据库未初始化问题**：测试环境中数据库未正确初始化，导致 `SessionLocal` 为 `None`
2. **强制执行逻辑缺陷**：`force_execute_task` 方法调用 `execute_task` 时，仍然会通过 `should_execute_task` 检查任务是否应该执行，如果任务当天已经成功执行过，会返回 `False` 并跳过执行

## 解决方案

### 1. 修复数据库初始化问题

在测试文件 `test_task_scheduler.py` 中添加数据库初始化：

```python
from core.database import init_database

# 初始化数据库
init_database()
```

### 2. 修改任务执行逻辑

#### 修改 `TaskManager.execute_task` 方法

在 `core/task_manager.py` 中为 `execute_task` 方法添加 `force` 参数：

```python
async def execute_task(self, task: ScheduledTask, force: bool = False) -> bool:
    """执行单个任务"""
    if task.task_id in self._running_tasks and self._running_tasks[task.task_id]:
        logger.warning(f"任务 {task.name} 正在执行中，跳过")
        return False
        
    if not force and not self.should_execute_task(task):
        # 更新下次执行时间
        self._update_next_run_time(task)
        return False
```

#### 修改 `SchedulerService.force_execute_task` 方法

在 `services/scheduler_service.py` 中修改强制执行调用：

```python
# 强制执行任务
result = await self._task_manager.execute_task(task, force=True)
logger.info(f"强制执行任务完成: {task_id}, 结果: {result}")
return result
```

## 修复效果

- ✅ `test_task_management` 测试用例通过
- ✅ 所有任务调度相关测试通过（8个测试用例）
- ✅ 强制执行功能现在可以正确绕过"今天已执行"的检查
- ✅ 保持了正常调度执行的逻辑不变

## 测试验证

```bash
# 运行特定测试
python -m pytest test/test_task_scheduler.py::TestSchedulerService::test_task_management -v

# 运行所有任务调度测试
python -m pytest test/test_task_scheduler.py -v
```

## 相关文件

- `core/task_manager.py` - 任务管理器核心逻辑
- `services/scheduler_service.py` - 调度服务
- `test/test_task_scheduler.py` - 测试文件
- `core/database.py` - 数据库初始化

## 注意事项

1. `force=True` 参数只会绕过 `should_execute_task` 的检查，但仍然会检查任务是否正在运行中
2. 强制执行的任务仍然会记录执行历史和更新任务状态
3. 该修复保持了向后兼容性，不影响现有的调度逻辑