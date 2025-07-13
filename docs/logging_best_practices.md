# 量化交易系统日志最佳实践指南

## 概述

本文档提供了量化交易系统中日志使用的最佳实践指南，基于统一的 `loguru` 日志配置。

## 快速开始

### 在新文件中使用日志

```python
# 推荐方式：使用统一日志配置
from utils.log_config import get_logger

logger = get_logger()

# 使用日志
logger.info("这是一条信息日志")
logger.warning("这是一条警告日志")
logger.error("这是一条错误日志")
```

### 兼容方式（现有代码）

```python
# 现有代码仍然可以继续使用
from loguru import logger

logger.info("现有代码无需修改")
```

## 日志级别使用指南

### DEBUG
- **用途**：详细的调试信息
- **场景**：开发和调试阶段
- **示例**：
```python
logger.debug(f"处理股票数据: {stock_code}, 价格: {price}")
logger.debug(f"策略参数: {strategy_params}")
```

### INFO
- **用途**：一般信息记录
- **场景**：正常业务流程、重要状态变化
- **示例**：
```python
logger.info("开始执行回测")
logger.info(f"策略 {strategy_name} 执行完成")
logger.info(f"数据更新完成，共处理 {count} 条记录")
```

### WARNING
- **用途**：警告信息，不影响程序运行但需要注意
- **场景**：数据异常、性能问题、配置问题
- **示例**：
```python
logger.warning(f"股票 {stock_code} 数据缺失，使用默认值")
logger.warning(f"策略执行时间过长: {execution_time}s")
```

### ERROR
- **用途**：错误信息，影响程序正常运行
- **场景**：异常处理、业务逻辑错误
- **示例**：
```python
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"操作失败: {e}")
    logger.error(f"错误详情: {traceback.format_exc()}")
```

### CRITICAL
- **用途**：严重错误，可能导致程序崩溃
- **场景**：系统级错误、数据库连接失败
- **示例**：
```python
logger.critical("数据库连接失败，系统无法继续运行")
logger.critical(f"关键配置缺失: {missing_config}")
```

## 日志内容最佳实践

### 1. 结构化日志

```python
# 好的做法：结构化信息
logger.info(f"交易执行 - 股票: {stock_code}, 数量: {quantity}, 价格: {price}, 方向: {direction}")

# 避免：信息不完整
logger.info("交易执行")
```

### 2. 包含上下文信息

```python
# 好的做法：包含足够的上下文
logger.error(f"策略 {strategy_name} 在处理股票 {stock_code} 时失败: {error_msg}")

# 避免：缺少上下文
logger.error("策略失败")
```

### 3. 使用合适的日志级别

```python
# 好的做法：根据重要性选择级别
logger.debug(f"计算技术指标: MA5={ma5}, MA20={ma20}")
logger.info(f"生成交易信号: {signal}")
logger.warning(f"数据延迟: {delay}ms")
logger.error(f"订单提交失败: {error}")

# 避免：滥用ERROR级别
logger.error("正常的业务逻辑")  # 应该使用INFO
```

### 4. 异常处理日志

```python
# 推荐的异常处理模式
try:
    result = execute_strategy()
    logger.info(f"策略执行成功: {result}")
except ValidationError as e:
    logger.warning(f"数据验证失败: {e}")
except ConnectionError as e:
    logger.error(f"网络连接错误: {e}")
    logger.error(f"错误堆栈: {traceback.format_exc()}")
except Exception as e:
    logger.critical(f"未预期的错误: {e}")
    logger.critical(f"完整堆栈: {traceback.format_exc()}")
    raise
```

## 性能考虑

### 1. 避免昂贵的字符串操作

```python
# 好的做法：使用f-string或延迟格式化
logger.debug(f"处理数据: {data}")

# 避免：在不需要时进行复杂计算
if logger.level <= logging.DEBUG:
    expensive_debug_info = calculate_complex_metrics()
    logger.debug(f"复杂指标: {expensive_debug_info}")
```

### 2. 批量日志记录

```python
# 对于大量数据，考虑批量记录
processed_count = 0
for stock in stocks:
    process_stock(stock)
    processed_count += 1
    
    # 每100条记录一次
    if processed_count % 100 == 0:
        logger.info(f"已处理 {processed_count} 只股票")

logger.info(f"处理完成，总计 {processed_count} 只股票")
```

## 敏感信息处理

### 1. 避免记录敏感数据

```python
# 好的做法：脱敏处理
logger.info(f"用户登录: {username[:3]}***")
logger.info(f"API密钥: {api_key[:8]}...")

# 避免：记录完整敏感信息
logger.info(f"密码: {password}")  # 绝对不要这样做
```

### 2. 交易信息记录

```python
# 记录交易相关信息时要小心
logger.info(f"订单提交 - ID: {order_id}, 股票: {stock_code}, 数量: {quantity}")
# 避免记录账户余额等敏感财务信息
```

## 日志文件管理

### 当前配置

- **主日志文件**：`logs/smart_trader_YYYY-MM-DD.log`
- **错误日志文件**：`logs/smart_trader_error_YYYY-MM-DD.log`
- **轮转策略**：每天轮转
- **保留策略**：保留30天
- **文件大小限制**：100MB

### 日志文件结构

```
logs/
├── smart_trader_2025-07-13.log      # 主日志文件
├── smart_trader_error_2025-07-13.log # 错误日志文件
├── smart_trader_2025-07-12.log      # 历史日志
└── ...
```

## 监控和告警

### 1. 关键错误监控

```python
# 对于关键错误，考虑添加额外的通知机制
def critical_error_handler(error_msg: str):
    logger.critical(error_msg)
    # 可以在这里添加邮件通知、短信告警等
    # send_alert_notification(error_msg)
```

### 2. 性能监控

```python
import time

def monitor_performance(func_name: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                if execution_time > 5.0:  # 超过5秒记录警告
                    logger.warning(f"{func_name} 执行时间过长: {execution_time:.2f}s")
                else:
                    logger.debug(f"{func_name} 执行时间: {execution_time:.2f}s")
                    
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"{func_name} 执行失败 (耗时: {execution_time:.2f}s): {e}")
                raise
        return wrapper
    return decorator

# 使用示例
@monitor_performance("策略回测")
def run_backtest(strategy):
    # 策略回测逻辑
    pass
```

## 调试技巧

### 1. 条件日志记录

```python
# 使用环境变量控制详细日志
import os

DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

if DEBUG_MODE:
    logger.debug(f"详细调试信息: {debug_data}")
```

### 2. 临时日志标记

```python
# 在调试时使用特殊标记
logger.info(f"[DEBUG_TEMP] 临时调试信息: {temp_data}")
# 记得在提交代码前移除这些临时日志
```

## 代码审查检查清单

在代码审查时，请检查以下日志相关项目：

- [ ] 是否使用了正确的日志级别
- [ ] 日志信息是否包含足够的上下文
- [ ] 是否避免了记录敏感信息
- [ ] 异常处理是否包含适当的日志记录
- [ ] 是否移除了临时调试日志
- [ ] 日志格式是否一致
- [ ] 是否考虑了性能影响

## 故障排查

### 常见问题

1. **日志文件过大**
   - 检查是否有过多的DEBUG日志
   - 考虑调整日志级别
   - 检查轮转配置

2. **日志丢失**
   - 检查磁盘空间
   - 检查文件权限
   - 检查日志配置

3. **性能问题**
   - 减少DEBUG级别日志
   - 避免在循环中记录大量日志
   - 使用异步日志记录（如需要）

### 日志分析工具

```bash
# 查看错误日志
grep "ERROR\|CRITICAL" logs/smart_trader_*.log

# 统计日志级别分布
grep -o "INFO\|WARNING\|ERROR\|CRITICAL\|DEBUG" logs/smart_trader_*.log | sort | uniq -c

# 查看特定时间段的日志
grep "2025-07-13 14:" logs/smart_trader_2025-07-13.log
```

## 总结

良好的日志实践对于量化交易系统的维护和调试至关重要。遵循本指南中的最佳实践，可以帮助团队：

- 快速定位和解决问题
- 监控系统性能和健康状态
- 审计交易活动和系统行为
- 提高代码质量和可维护性

记住：日志是代码的一部分，需要像对待代码一样认真对待日志的质量和一致性。