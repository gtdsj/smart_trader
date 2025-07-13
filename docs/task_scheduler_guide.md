# 任务调度系统使用指南

## 概述

本系统实现了基于数据库的任务调度功能，支持定时执行各种量化交易相关的任务。系统在 `python main.py` 启动时会自动从数据库加载任务并按计划执行。

## 系统架构

### 核心组件

1. **TaskManager** (`core/task_manager.py`)
   - 负责任务的创建、管理和执行
   - 处理任务函数的注册和调用
   - 管理任务执行历史记录

2. **SchedulerService** (`services/scheduler_service.py`)
   - 基于 APScheduler 的调度服务
   - 定期检查数据库中的待执行任务
   - 提供任务管理的 API 接口

3. **TaskFunctions** (`core/task_functions.py`)
   - 定义具体的任务执行函数
   - 包含股票数据更新、选股等业务逻辑

### 数据库表结构

#### scheduled_tasks 表
```sql
CREATE TABLE scheduled_tasks (
    id INTEGER PRIMARY KEY,
    task_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    task_type VARCHAR(50) NOT NULL,
    cron_expression VARCHAR(100) NOT NULL,
    task_function VARCHAR(100) NOT NULL,
    task_params TEXT DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    next_run_time TIMESTAMP,
    last_run_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### task_execution_history 表
```sql
CREATE TABLE task_execution_history (
    id INTEGER PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL,
    execution_date DATE NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    result_data TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 默认任务

系统启动时会自动创建以下默认任务：

### 1. 股票基础信息更新
- **任务ID**: `update_stock_basic_info`
- **执行时间**: 每天凌晨 2:00
- **功能**: 更新全量A股股票基本信息
- **Cron表达式**: `0 2 * * *`

### 2. 日线数据更新
- **任务ID**: `update_daily_stock_data`
- **执行时间**: 交易日下午 4:00
- **功能**: 更新所有股票当天的日线数据
- **Cron表达式**: `0 16 * * 1-5`

### 3. 每日选股任务
- **任务ID**: `run_stock_selection`
- **执行时间**: 每天晚上 8:00
- **功能**: 执行选股策略，筛选符合条件的股票
- **Cron表达式**: `0 20 * * *`

### 4. 系统健康检查
- **任务ID**: `health_check_task`
- **执行时间**: 每小时
- **功能**: 检查系统各组件运行状态
- **Cron表达式**: `0 * * * *`

## 使用方法

### 启动系统

```bash
python main.py
```

系统启动时会：
1. 初始化数据库表结构
2. 创建默认任务（如果不存在）
3. 启动调度服务
4. 开始执行待执行的任务

### 任务管理 API

#### 添加新任务

```python
from services.scheduler_service import SchedulerService

scheduler = SchedulerService()

task_data = {
    'task_id': 'custom_task_001',
    'name': '自定义任务',
    'description': '这是一个自定义任务',
    'task_type': 'CUSTOM',
    'cron_expression': '0 12 * * *',  # 每天中午12点
    'task_function': 'my_custom_function',
    'task_params': {'param1': 'value1'}
}

result = await scheduler.add_task(task_data)
```

#### 获取任务状态

```python
# 获取单个任务状态
status = await scheduler.get_task_status('task_id')

# 获取所有任务状态
all_tasks = await scheduler.get_all_tasks()
```

#### 启用/禁用任务

```python
# 启用任务
result = await scheduler.enable_task('task_id')

# 禁用任务
result = await scheduler.disable_task('task_id')
```

#### 强制执行任务

```python
# 立即执行任务（不等待计划时间）
result = await scheduler.force_execute_task('task_id')
```

#### 删除任务

```python
result = await scheduler.remove_task('task_id')
```

### 自定义任务函数

#### 1. 创建任务函数

```python
# 在 core/task_functions.py 中添加
class TaskFunctions:
    @staticmethod
    async def my_custom_function(**kwargs):
        """自定义任务函数"""
        try:
            # 执行具体业务逻辑
            result = do_something()
            
            return {
                'status': 'success',
                'message': '任务执行成功',
                'data': result
            }
        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            raise
```

#### 2. 注册任务函数

```python
# 在 get_task_functions() 中添加
def get_task_functions():
    return {
        'my_custom_function': TaskFunctions.my_custom_function,
        # ... 其他函数
    }
```

## Cron 表达式说明

Cron 表达式格式：`分钟 小时 日 月 星期`

### 常用示例

- `0 0 * * *` - 每天午夜
- `0 9 * * 1-5` - 工作日上午9点
- `30 15 * * 1-5` - 工作日下午3:30
- `0 */2 * * *` - 每2小时
- `0 0 1 * *` - 每月1号午夜
- `0 0 * * 0` - 每周日午夜

### 特殊字符

- `*` - 匹配任何值
- `?` - 不指定值（仅用于日和星期）
- `-` - 范围（如 1-5）
- `,` - 列表（如 1,3,5）
- `/` - 步长（如 */2）

## 任务执行逻辑

### 启动时检查

系统启动时会检查所有活跃任务：

1. 如果任务的下次执行时间已过，且当天未执行过，则立即执行
2. 如果任务的执行时间已过且当天已执行过，则跳过
3. 计算下次执行时间并安排调度

### 执行状态

任务执行状态包括：
- `PENDING` - 等待执行
- `RUNNING` - 正在执行
- `COMPLETED` - 执行完成
- `FAILED` - 执行失败
- `CANCELLED` - 已取消

### 错误处理

- 任务执行失败时会记录错误信息
- 系统会发送通知（如果配置了通知服务）
- 失败的任务不会影响其他任务的执行

## 监控和日志

### 日志记录

系统会记录详细的执行日志：

```
2024-01-15 09:00:00 [INFO] 开始执行任务: update_stock_basic_info
2024-01-15 09:05:30 [INFO] 任务执行完成: update_stock_basic_info, 耗时: 5.5秒
2024-01-15 09:05:30 [INFO] 更新了 5000 只股票的基础信息
```

### 执行历史

所有任务执行记录都保存在 `task_execution_history` 表中，包括：
- 执行时间
- 执行状态
- 执行结果
- 错误信息（如果有）

### 性能监控

可以通过查询执行历史来监控任务性能：

```sql
-- 查看任务执行统计
SELECT 
    task_id,
    COUNT(*) as execution_count,
    AVG(JULIANDAY(end_time) - JULIANDAY(start_time)) * 86400 as avg_duration_seconds,
    SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failure_count
FROM task_execution_history 
WHERE execution_date >= date('now', '-30 days')
GROUP BY task_id;
```

## 最佳实践

### 1. 任务设计原则

- **幂等性**: 任务应该可以安全地重复执行
- **原子性**: 任务应该是原子操作，要么全部成功要么全部失败
- **超时处理**: 长时间运行的任务应该有超时机制
- **资源清理**: 任务结束后应该清理占用的资源

### 2. 错误处理

```python
async def robust_task_function(**kwargs):
    """健壮的任务函数示例"""
    try:
        # 参数验证
        validate_parameters(kwargs)
        
        # 执行业务逻辑
        result = await execute_business_logic()
        
        # 验证结果
        validate_result(result)
        
        return {
            'status': 'success',
            'data': result
        }
        
    except ValidationError as e:
        logger.error(f"参数验证失败: {e}")
        raise
    except BusinessLogicError as e:
        logger.error(f"业务逻辑执行失败: {e}")
        raise
    except Exception as e:
        logger.error(f"未知错误: {e}")
        raise
    finally:
        # 清理资源
        cleanup_resources()
```

### 3. 性能优化

- 避免在任务中执行长时间的同步操作
- 使用批量操作减少数据库访问次数
- 合理设置任务执行频率，避免资源竞争
- 监控任务执行时间，及时优化慢任务

### 4. 安全考虑

- 任务参数应该经过验证和清理
- 避免在任务中执行危险的系统命令
- 限制任务的资源使用（内存、CPU、网络）
- 记录详细的审计日志

## 故障排除

### 常见问题

#### 1. 任务不执行

**可能原因**:
- 任务被禁用
- Cron表达式错误
- 任务函数不存在
- 数据库连接问题

**解决方法**:
```python
# 检查任务状态
status = await scheduler.get_task_status('task_id')
print(status)

# 检查任务是否活跃
if not status.get('is_active'):
    await scheduler.enable_task('task_id')
```

#### 2. 任务执行失败

**可能原因**:
- 业务逻辑错误
- 网络连接问题
- 数据源不可用
- 权限不足

**解决方法**:
```sql
-- 查看错误日志
SELECT * FROM task_execution_history 
WHERE task_id = 'task_id' AND status = 'FAILED'
ORDER BY start_time DESC LIMIT 10;
```

#### 3. 任务执行时间过长

**可能原因**:
- 数据量过大
- 网络延迟
- 算法效率低
- 资源竞争

**解决方法**:
- 优化算法逻辑
- 分批处理数据
- 增加并发处理
- 调整执行时间

## 扩展开发

### 添加新的任务类型

1. 在 `TaskType` 枚举中添加新类型
2. 实现对应的任务函数
3. 在 `get_task_functions()` 中注册
4. 创建任务实例

### 集成外部调度系统

可以通过 API 接口与外部调度系统集成：

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/tasks")

@router.post("/execute/{task_id}")
async def execute_task(task_id: str):
    """通过API执行任务"""
    result = await scheduler.force_execute_task(task_id)
    return {"success": result}
```

### 自定义通知方式

可以扩展通知功能，支持更多通知渠道：

```python
class CustomNotificationService:
    async def send_task_notification(self, task_id: str, status: str, message: str):
        """发送任务通知"""
        # 实现自定义通知逻辑
        pass
```

## 总结

本任务调度系统提供了完整的定时任务管理功能，支持：

- ✅ 基于数据库的任务持久化
- ✅ 灵活的 Cron 表达式调度
- ✅ 完整的任务生命周期管理
- ✅ 详细的执行历史记录
- ✅ 健壮的错误处理机制
- ✅ 易于扩展的架构设计

通过合理使用本系统，可以实现量化交易系统中各种定时任务的自动化执行，提高系统的可靠性和运维效率。