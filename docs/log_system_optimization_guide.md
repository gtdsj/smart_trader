# 日志系统优化指南

## 概述

本文档描述了量化交易系统日志管理的优化方案实施过程，采用方案1：保持现状并优化。

## 优化目标

1. **保持现有的 loguru 使用模式**
2. **提供统一的日志配置和格式**
3. **优化日志文件管理和错误追踪**
4. **逐步迁移少数使用 utils/logger.py 的文件**

## 实施方案

### 1. 新增统一日志配置模块

创建了 `utils/log_config.py` 模块，提供：

- **LogConfig 类**：统一的日志配置管理器
- **setup_logging() 函数**：便捷的日志设置接口
- **get_logger() 函数**：获取 logger 实例的统一接口

#### 主要特性

```python
# 统一的日志格式
# 控制台：彩色输出，包含时间、级别、模块、函数、行号
# 文件：结构化输出，便于日志分析

# 自动文件管理
# - 按天轮转
# - 自动压缩
# - 保留期限管理
# - 错误日志单独存储

# 灵活配置
# - 支持不同环境的日志级别
# - 可选择启用/禁用控制台或文件输出
# - 从配置文件自动读取参数
```

### 2. 主应用日志配置优化

修改了 `main.py`：

```python
# 原来的配置
from loguru import logger
# 手动配置 logger.add()

# 优化后的配置
from utils.log_config import setup_logging, get_logger
logger = get_logger()
# 在启动时调用 setup_logging()
```

### 3. 日志格式统一

#### 控制台输出格式
```
2024-01-15 10:30:45 | INFO     | module:function:123 - 日志消息
```

#### 文件输出格式
```
2024-01-15 10:30:45 | INFO     | module:function:123 - 日志消息
```

#### 错误日志增强
- 单独的错误日志文件
- 更长的保留期限
- 包含完整的堆栈跟踪信息

## 迁移计划

### 阶段1：核心模块优化（已完成）

- [x] 创建统一日志配置模块
- [x] 优化主应用日志配置
- [x] 测试新的日志系统

### 阶段2：逐步迁移现有文件

需要迁移的文件（使用 `from utils.logger import get_logger`）：

1. **API 模块**
   - `api/unified_backfill_routes.py`
   - `api/scheduler_routes.py`

2. **服务模块**
   - `services/optimized_backfill_service.py`

3. **测试模块**
   - `test/test_break_board_condition.py`
   - `test/test_singleton_integration.py`
   - `test/test_database_task_loading.py`
   - `test/test_stock_updater_singleton.py`
   - `test/test_task_scheduler.py`

#### 迁移步骤

对于每个文件：

```python
# 原来的导入
from utils.logger import get_logger
logger = get_logger(__name__)

# 迁移后的导入
from utils.log_config import get_logger
logger = get_logger()

# 或者直接使用 loguru
from loguru import logger
```

### 阶段3：清理和优化

- [ ] 完成所有文件迁移后，评估是否需要保留 `utils/logger.py`
- [ ] 更新项目文档和开发指南
- [ ] 添加日志最佳实践说明

## 使用指南

### 新项目或新文件

推荐直接使用 loguru：

```python
from loguru import logger

# 直接使用，无需额外配置
logger.info("这是一条信息日志")
logger.error("这是一条错误日志")
```

### 需要自定义配置的场景

```python
from utils.log_config import setup_logging, get_logger

# 自定义配置
setup_logging(
    log_level="DEBUG",
    enable_console=True,
    enable_file=True
)

logger = get_logger()
```

### 测试环境

```python
from utils.log_config import LogConfig

# 测试前重置日志配置
LogConfig.reset()
LogConfig.setup_logger(
    log_level="DEBUG",
    enable_file=False  # 测试时只输出到控制台
)
```

## 配置参数

### 从配置文件读取的参数

- `log_level`：日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- `log_dir`：日志文件目录
- `log_file_prefix`：日志文件名前缀
- `max_log_files`：最大保留的日志文件数

### 可选参数

- `enable_console`：是否启用控制台输出（默认：True）
- `enable_file`：是否启用文件输出（默认：True）

## 日志文件结构

```
logs/
├── smart_trader_2024-01-15.log          # 常规日志
├── smart_trader_2024-01-15.log.zip       # 压缩的历史日志
├── smart_trader_error_2024-01-15.log     # 错误日志
└── smart_trader_error_2024-01-15.log.zip # 压缩的历史错误日志
```

## 最佳实践

### 1. 日志级别使用

- **DEBUG**：详细的调试信息，仅在开发和调试时使用
- **INFO**：一般信息，记录程序的正常运行状态
- **WARNING**：警告信息，程序仍能正常运行但可能存在问题
- **ERROR**：错误信息，程序遇到错误但仍能继续运行
- **CRITICAL**：严重错误，程序可能无法继续运行

### 2. 错误日志记录

```python
try:
    # 业务逻辑
    result = some_operation()
except Exception as e:
    logger.error(f"操作失败: {e}")
    # loguru 会自动记录堆栈信息
    raise  # 重新抛出异常
```

### 3. 结构化日志

```python
# 推荐：包含上下文信息
logger.info(f"用户 {user_id} 执行策略 {strategy_id}，结果: {result}")

# 避免：信息不足
logger.info("策略执行完成")
```

### 4. 性能考虑

```python
# 对于复杂的日志消息，使用条件判断
if logger.level("DEBUG").no >= logger.level("DEBUG").no:
    expensive_debug_info = generate_debug_info()
    logger.debug(f"调试信息: {expensive_debug_info}")
```

## 监控和维护

### 日志文件监控

- 定期检查日志文件大小和数量
- 监控错误日志的增长趋势
- 设置日志文件清理策略

### 性能监控

- 监控日志写入性能
- 避免在高频操作中记录过多日志
- 合理设置日志级别

## 故障排除

### 常见问题

1. **日志文件权限问题**
   - 确保应用有写入日志目录的权限
   - 检查日志目录是否存在

2. **日志文件过大**
   - 检查日志轮转配置
   - 调整日志级别
   - 优化日志消息内容

3. **性能问题**
   - 减少DEBUG级别日志的使用
   - 避免在循环中记录大量日志
   - 考虑异步日志写入

## 总结

通过实施方案1，我们成功地：

1. **保持了现有代码的兼容性**：大部分文件无需修改
2. **提供了统一的日志配置**：便于管理和维护
3. **增强了日志功能**：错误日志分离、自动压缩、更好的格式化
4. **制定了清晰的迁移路径**：逐步优化，降低风险

这种渐进式的优化方案既保证了系统的稳定性，又提升了日志管理的效率和可维护性。