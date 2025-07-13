# 股票基础信息系统使用说明

## 概述

本系统为A股量化交易提供股票基础信息的获取、存储和自动更新功能。系统采用简洁的表结构设计，专注于A股交易所需的核心信息。

## 功能特性

### 1. 数据库表结构

股票基础信息表 (`stock_basic_info`) 包含以下字段：

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| id | INTEGER | 主键，自增 | 1 |
| stock_code | VARCHAR | 股票代码（含交易所后缀） | 000001.SZ |
| stock_name | VARCHAR | 股票名称 | 平安银行 |
| exchange | VARCHAR | 交易所代码 | SZ/SH |
| listing_date | VARCHAR | 上市日期 | 1991-04-03 |
| is_st | BOOLEAN | 是否为ST股票 | false |
| is_trading | BOOLEAN | 是否可交易 | true |
| price_tick | DOUBLE | 价格最小变动单位 | 0.01 |
| created_at | TIMESTAMP | 创建时间 | 2025-01-01 10:00:00 |
| updated_at | TIMESTAMP | 更新时间 | 2025-01-01 10:00:00 |

### 2. 核心组件

- **XtQuantService**: 负责从xtquant获取股票基础信息
- **StockInfoUpdater**: 负责定时更新和批量处理
- **数据库层**: 使用DuckDB存储，支持高性能查询

## 使用方法

### 1. 手动获取股票信息

```python
from services.xtquant_service import XtQuantService

# 创建服务实例
xtquant_service = XtQuantService()

# 获取单只股票信息
stock_info = await xtquant_service.get_stock_basic_info('000001.SZ')
print(stock_info)

# 强制从xtquant更新
stock_info = await xtquant_service.get_stock_basic_info('000001.SZ', force_update=True)
```

### 2. 批量更新股票信息

```python
from services.stock_info_updater import StockInfoUpdater

# 创建更新器实例
updater = StockInfoUpdater()

# 手动更新指定股票
stock_codes = ['000001.SZ', '000002.SZ', '600000.SH']
result = await updater.manual_update_stock_info(stock_codes)
print(f"更新结果: {result}")
```

### 3. 启动定时更新服务

#### 方法一：使用启动脚本

```bash
# 在项目根目录下运行
python scripts/start_stock_updater.py
```

#### 方法二：编程方式启动

```python
from services.stock_info_updater import StockInfoUpdater

# 创建更新器
updater = StockInfoUpdater()

# 启动调度器（每个交易日09:00自动更新）
await updater.start_scheduler()

# 停止调度器
await updater.stop_scheduler()
```

### 4. 查看更新状态

```python
from services.stock_info_updater import StockInfoUpdater

updater = StockInfoUpdater()
status = await updater.get_update_status()

print(f"最后更新时间: {status['last_update']}")
print(f"总股票数量: {status['total_count']}")
print(f"ST股票数量: {status['st_count']}")
print(f"可交易股票数量: {status['trading_count']}")
print(f"调度器状态: {status['is_scheduler_running']}")
```

## 测试脚本

### 1. 基础功能测试

```bash
# 测试股票信息更新功能
python test/test_stock_updater.py

# 测试数据库连接和表结构
python test/test_database_simple.py
```

### 2. 数据库迁移

```bash
# 自动创建股票基础信息表
python migrations/auto_create_stock_basic_info_table.py
```

## 配置说明

### 1. 数据库配置

系统使用DuckDB作为数据库，配置文件位于 `config.json`：

```json
{
  "database": {
    "url": "duckdb:///D:/smart_trader/data/smart_trader.db"
  }
}
```

### 2. 更新时间配置

默认更新时间为每个交易日的09:00，可在 `StockInfoUpdater` 类中修改：

```python
# 在 start_scheduler 方法中修改
scheduler.add_job(
    self._daily_update_job,
    'cron',
    hour=9,  # 修改小时
    minute=0,  # 修改分钟
    timezone='Asia/Shanghai'
)
```

## 性能优化

### 1. 批量处理

- 系统支持批量更新，避免频繁的数据库连接
- 每次API调用后添加0.1秒延迟，避免请求过于频繁

### 2. 缓存机制

- 优先从数据库获取信息，减少API调用
- 支持强制更新模式，确保数据最新

### 3. 错误处理

- 完善的异常处理和日志记录
- 数据库连接失败时自动重试
- 支持部分更新失败的情况

## 监控和维护

### 1. 日志监控

系统使用loguru记录详细日志，包括：
- 数据库连接状态
- 股票信息更新结果
- 错误信息和堆栈跟踪

### 2. 数据质量检查

```python
# 检查数据完整性
from core.database import get_duckdb_connection

conn = get_duckdb_connection()

# 检查空值
empty_names = conn.execute(
    "SELECT COUNT(*) FROM stock_basic_info WHERE stock_name IS NULL OR stock_name = ''"
).fetchone()[0]

# 检查重复数据
duplicates = conn.execute(
    "SELECT stock_code, COUNT(*) FROM stock_basic_info GROUP BY stock_code HAVING COUNT(*) > 1"
).fetchall()
```

### 3. 定期维护

建议定期执行以下维护操作：

1. **数据备份**: 定期备份DuckDB数据库文件
2. **数据清理**: 清理无效或过期的股票信息
3. **性能优化**: 根据查询模式优化索引

## 扩展功能

### 1. 添加新字段

如需添加新字段，需要：
1. 修改 `core/database.py` 中的 `StockBasicInfo` 类
2. 更新表创建SQL语句
3. 修改 `services/xtquant_service.py` 中的数据处理逻辑

### 2. 支持其他市场

当前系统专注于A股，如需支持其他市场：
1. 扩展股票代码识别逻辑
2. 添加市场特定的字段
3. 更新数据获取逻辑

## 故障排除

### 1. 常见问题

**问题**: 数据库连接失败
```
解决方案:
1. 检查数据库文件路径是否正确
2. 确保目录有写入权限
3. 检查DuckDB是否正确安装
```

**问题**: xtquant模块未找到
```
解决方案:
1. 安装xtquant: pip install xtquant
2. 检查xtquant配置是否正确
3. 确认网络连接正常
```

**问题**: 股票信息更新失败
```
解决方案:
1. 检查股票代码格式是否正确
2. 确认xtquant服务是否正常
3. 查看详细错误日志
```

### 2. 调试模式

启用详细日志记录：

```python
from loguru import logger

# 设置日志级别为DEBUG
logger.remove()
logger.add(sys.stderr, level="DEBUG")
```

## 总结

本股票基础信息系统提供了完整的A股股票信息管理解决方案，具有以下优势：

1. **简洁高效**: 专注于A股交易必需信息，表结构简洁
2. **自动更新**: 支持定时自动更新，确保数据时效性
3. **容错性强**: 完善的错误处理和恢复机制
4. **易于扩展**: 模块化设计，便于功能扩展
5. **性能优化**: 使用DuckDB提供高性能查询能力

通过合理使用本系统，可以为量化交易策略提供可靠的股票基础信息支持。