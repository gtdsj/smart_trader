# A股数据补全系统使用指南

## 概述

本系统提供了完整的A股历史数据补全解决方案，支持全市场数据补全、增量更新、智能分析等功能。基于XtQuant数据接口和DuckDB存储，提供高效、可靠的数据补全服务。

## 核心功能

### 1. 数据完整度分析
- 自动分析股票数据的完整度
- 识别缺失数据和需要更新的股票
- 提供数据质量评估和改进建议

### 2. 智能数据补全
- 支持全市场和指定股票的数据补全
- 智能优先级排序（按完整度、落后天数等）
- 批量处理和并发控制

### 3. 任务管理
- 异步任务执行和进度跟踪
- 任务状态监控和历史记录
- 支持任务取消和重试机制

### 4. 数据质量控制
- 数据格式验证和异常检测
- 价格逻辑关系检查
- 重复数据和空值处理

## API接口说明

### 基础数据接口

#### 1. 获取数据补全服务状态
```http
GET /api/v1/data-backfill/status
```

**响应示例：**
```json
{
  "success": true,
  "message": "获取数据补全服务状态成功",
  "data": {
    "service_status": "running",
    "data_completeness": 85.6,
    "incomplete_stocks_count": 234,
    "running_tasks_count": 1,
    "scheduled_tasks_count": 0,
    "system_recommendations": [
      "🟢 数据完整度良好，建议定期维护更新",
      "📊 有234只股票需要补全，建议分批处理"
    ]
  }
}
```

#### 2. 分析数据完整度
```http
POST /api/v1/data-backfill/analyze?market=ALL&detailed=true
```

**参数说明：**
- `market`: 市场代码（SH/SZ/ALL）
- `detailed`: 是否返回详细分析

**响应示例：**
```json
{
  "success": true,
  "message": "数据完整度分析完成，总体完整度：85.6%",
  "data": {
    "analysis_summary": {
      "overall_completeness": 85.6,
      "total_stocks": 4500,
      "incomplete_stocks_count": 234,
      "missing_records": 12500
    },
    "completeness_distribution": {
      "excellent": 3200,
      "good": 800,
      "fair": 300,
      "poor": 200
    },
    "recommendations": {
      "priority_classification": {
        "high_priority_count": 50,
        "medium_priority_count": 100,
        "low_priority_count": 84
      }
    }
  }
}
```

### 任务管理接口

#### 3. 创建数据补全任务
```http
POST /api/v1/data-backfill/task/create
```

**请求体：**
```json
{
  "task_name": "全市场数据补全",
  "market": "ALL",
  "start_date": "2021-01-01",
  "end_date": "2024-01-01",
  "stock_codes": null,
  "batch_size": 30,
  "delay_seconds": 0.2,
  "force_update": false,
  "priority": "normal",
  "auto_retry": true,
  "max_retries": 3
}
```

**参数说明：**
- `task_name`: 任务名称
- `market`: 市场代码（SH/SZ/ALL）
- `start_date`: 开始日期（可选）
- `end_date`: 结束日期（可选）
- `stock_codes`: 指定股票代码列表（可选，为空则处理全市场）
- `batch_size`: 批量处理大小（1-100）
- `delay_seconds`: 批次间延迟秒数（0.1-5.0）
- `force_update`: 是否强制更新已存在的数据
- `priority`: 任务优先级（low/normal/high）
- `auto_retry`: 是否自动重试失败的股票
- `max_retries`: 最大重试次数（1-5）

**响应示例：**
```json
{
  "success": true,
  "message": "数据补全任务'全市场数据补全'创建成功",
  "data": {
    "task_id": "backfill_20241201_143022_0",
    "task_name": "全市场数据补全",
    "status": "created",
    "estimated_duration": "约2.5小时"
  }
}
```

#### 4. 获取任务状态
```http
GET /api/v1/data-backfill/task/{task_id}
```

**响应示例：**
```json
{
  "success": true,
  "message": "获取任务状态成功",
  "data": {
    "task_id": "backfill_20241201_143022_0",
    "task_name": "全市场数据补全",
    "status": "running",
    "progress": 45,
    "total_stocks": 4500,
    "success_count": 1800,
    "failed_count": 225,
    "current_batch": "68/150",
    "start_time": "2024-12-01T14:30:22",
    "estimated_end_time": "2024-12-01T17:00:00"
  }
}
```

#### 5. 取消任务
```http
POST /api/v1/data-backfill/task/{task_id}/cancel
```

#### 6. 获取任务列表
```http
GET /api/v1/data-backfill/tasks?status=running&limit=20
```

**参数说明：**
- `status`: 任务状态过滤（可选）
- `limit`: 返回数量限制（1-100）

#### 7. 清理任务历史
```http
DELETE /api/v1/data-backfill/tasks/cleanup?keep_days=7
```

### 原有数据接口增强

#### 8. 全市场数据完整补全
```http
POST /api/v1/data/daily/full-market-backfill
```

**请求体：**
```json
{
  "market": "ALL",
  "start_date": "2021-01-01",
  "end_date": "2024-01-01",
  "batch_size": 50,
  "delay_seconds": 0.1,
  "force_update": false,
  "max_workers": 3
}
```

#### 9. 智能数据补全
```http
POST /api/v1/data/daily/smart-backfill
```

**请求体：**
```json
{
  "priority_mode": "completeness",
  "completeness_threshold": 80,
  "max_stocks": 100,
  "batch_size": 30
}
```

## 使用场景和最佳实践

### 1. 系统初始化

**场景：** 新系统部署，需要获取全市场历史数据

**推荐方案：**
```bash
# 1. 先分析数据完整度
curl -X POST "http://localhost:8000/api/v1/data-backfill/analyze?market=ALL&detailed=true"

# 2. 创建全市场补全任务
curl -X POST "http://localhost:8000/api/v1/data-backfill/task/create" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "系统初始化-全市场补全",
    "market": "ALL",
    "start_date": "2021-01-01",
    "batch_size": 20,
    "delay_seconds": 0.3,
    "priority": "high"
  }'
```

### 2. 日常维护更新

**场景：** 定期更新最新数据，保持数据时效性

**推荐方案：**
```bash
# 使用增量更新接口
curl -X POST "http://localhost:8000/api/v1/data/daily/incremental-update-all?market=ALL"

# 或创建增量更新任务
curl -X POST "http://localhost:8000/api/v1/data-backfill/task/create" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "日常增量更新",
    "market": "ALL",
    "batch_size": 50,
    "delay_seconds": 0.1,
    "force_update": false,
    "priority": "normal"
  }'
```

### 3. 特定股票补全

**场景：** 针对特定股票进行数据补全

**推荐方案：**
```bash
curl -X POST "http://localhost:8000/api/v1/data-backfill/task/create" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "重点股票补全",
    "stock_codes": ["000001.SZ", "600000.SH", "000002.SZ"],
    "batch_size": 10,
    "delay_seconds": 0.1,
    "force_update": true,
    "priority": "high"
  }'
```

### 4. 智能优先级补全

**场景：** 根据数据完整度智能选择需要补全的股票

**推荐方案：**
```bash
curl -X POST "http://localhost:8000/api/v1/data/daily/smart-backfill" \
  -H "Content-Type: application/json" \
  -d '{
    "priority_mode": "balanced",
    "completeness_threshold": 90,
    "max_stocks": 200,
    "batch_size": 30
  }'
```

## 配置参数说明

### 批量处理参数

- **batch_size**: 批量大小
  - 推荐值：20-50
  - 较小值：更稳定，但速度较慢
  - 较大值：速度较快，但可能增加失败率

- **delay_seconds**: 批次间延迟
  - 推荐值：0.1-0.5秒
  - 避免请求过于频繁导致限流

- **priority**: 任务优先级
  - `high`: 小批量，低延迟，高并发
  - `normal`: 中等批量，适中延迟
  - `low`: 大批量，高延迟，低并发

### 数据质量参数

- **force_update**: 强制更新
  - `true`: 重新获取所有数据
  - `false`: 只更新缺失或过期数据

- **completeness_threshold**: 完整度阈值
  - 用于智能补全，只处理完整度低于阈值的股票

## 监控和维护

### 1. 任务监控

```bash
# 查看服务状态
curl "http://localhost:8000/api/v1/data-backfill/status"

# 查看运行中的任务
curl "http://localhost:8000/api/v1/data-backfill/tasks?status=running"

# 查看特定任务详情
curl "http://localhost:8000/api/v1/data-backfill/task/{task_id}"
```

### 2. 数据质量监控

```bash
# 获取数据统计信息
curl "http://localhost:8000/api/v1/data/daily/statistics"

# 分析数据完整度
curl -X POST "http://localhost:8000/api/v1/data-backfill/analyze?detailed=true"
```

### 3. 系统维护

```bash
# 清理任务历史
curl -X DELETE "http://localhost:8000/api/v1/data-backfill/tasks/cleanup?keep_days=7"

# 清理缓存
curl -X POST "http://localhost:8000/api/v1/data/cache/clear" \
  -H "Content-Type: application/json" \
  -d '{"pattern": "stock_data:*"}'
```

## 错误处理和故障排除

### 常见错误

1. **连接超时**
   - 检查XtQuant服务是否正常运行
   - 调整batch_size和delay_seconds参数

2. **数据获取失败**
   - 检查股票代码格式是否正确
   - 验证日期范围是否合理

3. **任务执行缓慢**
   - 减小batch_size
   - 增加delay_seconds
   - 检查系统资源使用情况

### 故障恢复

1. **任务中断恢复**
   - 系统会自动记录进度
   - 可以重新创建任务，系统会跳过已有数据

2. **数据不一致**
   - 使用force_update=true重新获取数据
   - 检查数据质量报告

## 性能优化建议

### 1. 批量处理优化

- 根据网络状况调整batch_size
- 在非交易时间进行大批量更新
- 使用智能补全减少不必要的数据获取

### 2. 存储优化

- 定期清理过期的任务历史
- 使用数据压缩减少存储空间
- 合理设置缓存策略

### 3. 并发控制

- 避免同时运行多个大型补全任务
- 根据系统资源调整并发数量
- 监控内存使用情况

## 总结

本数据补全系统提供了完整的A股历史数据管理解决方案，支持：

- ✅ 全市场数据补全
- ✅ 智能增量更新
- ✅ 任务进度监控
- ✅ 数据质量控制
- ✅ 灵活的配置选项
- ✅ 完善的错误处理

通过合理使用这些功能，可以确保量化交易系统拥有完整、准确、及时的历史数据基础。