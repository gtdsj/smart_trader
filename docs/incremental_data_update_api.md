# A股历史日线数据增量补全API使用指南

## 概述

本文档介绍如何使用Smart Trader系统提供的API接口来增量补全A股所有股票的历史日线数据。

## 主要接口

### 1. 增量补全所有股票数据

**接口地址：** `POST /api/v1/data/daily/incremental-update-all`

**功能描述：** 自动获取A股所有股票列表，并对每只股票进行增量更新（从数据库最新日期补全到今天）

**请求参数：**
- `market` (可选): 市场代码，支持 "SH"、"SZ"、"ALL"，默认为 "ALL"
- `batch_size` (可选): 批量处理大小，范围1-100，默认为50

**请求示例：**
```bash
# 补全所有A股数据
curl -X POST "http://localhost:8000/api/v1/data/daily/incremental-update-all?market=ALL&batch_size=50"

# 只补全上海市场数据
curl -X POST "http://localhost:8000/api/v1/data/daily/incremental-update-all?market=SH&batch_size=30"

# 只补全深圳市场数据
curl -X POST "http://localhost:8000/api/v1/data/daily/incremental-update-all?market=SZ&batch_size=30"
```

**响应示例：**
```json
{
  "success": true,
  "message": "增量更新完成：处理4532只股票，成功4480只，失败52只，共更新125680条记录",
  "data": {
    "market": "ALL",
    "total_stocks": 4532,
    "success_count": 4480,
    "failed_count": 52,
    "total_records": 125680,
    "success_rate": 98.85,
    "batch_size": 50,
    "total_batches": 91,
    "failed_stocks": ["000001.SZ", "600000.SH"],
    "batch_details": [
      {
        "batch_num": 1,
        "stocks_in_batch": 50,
        "result": {
          "success_count": 48,
          "failed_count": 2,
          "total_records": 1440
        }
      }
    ]
  }
}
```

### 2. 获取数据库统计信息

**接口地址：** `GET /api/v1/data/daily/statistics`

**功能描述：** 获取数据库中日线数据的统计信息，包括总股票数、总记录数、数据范围等

**请求示例：**
```bash
curl -X GET "http://localhost:8000/api/v1/data/daily/statistics"
```

**响应示例：**
```json
{
  "success": true,
  "message": "数据库统计信息：4532只股票，1250000条记录",
  "data": {
    "total_stocks": 4532,
    "total_records": 1250000,
    "earliest_date": "2021-01-01",
    "latest_date": "2024-01-15",
    "data_span_days": 1110,
    "stocks_need_update_count": 15,
    "stocks_need_update": [
      {
        "stock_code": "000001.SZ",
        "latest_date": "2024-01-10",
        "days_behind": 5
      }
    ],
    "latest_data_by_stock": [
      {
        "stock_code": "600000.SH",
        "latest_date": "2024-01-15",
        "record_count": 756
      }
    ],
    "query_time": "2024-01-15 14:30:00"
  }
}
```

### 3. 批量更新指定股票

**接口地址：** `POST /api/v1/data/daily/batch`

**功能描述：** 批量更新指定股票列表的日线数据

**请求示例：**
```bash
curl -X POST "http://localhost:8000/api/v1/data/daily/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["000001.SZ", "600000.SH", "000002.SZ"],
    "start_date": null,
    "end_date": null
  }'
```

## 使用场景

### 1. 系统初始化

首次部署系统时，使用增量补全接口获取所有A股历史数据：

```bash
# 1. 先查看数据库状态
curl -X GET "http://localhost:8000/api/v1/data/daily/statistics"

# 2. 执行全量增量补全
curl -X POST "http://localhost:8000/api/v1/data/daily/incremental-update-all?market=ALL&batch_size=50"
```

### 2. 定时数据更新

设置定时任务，每日收盘后更新数据：

```bash
#!/bin/bash
# daily_update.sh

echo "开始每日数据更新 - $(date)"

# 增量更新所有股票数据
response=$(curl -s -X POST "http://localhost:8000/api/v1/data/daily/incremental-update-all?market=ALL&batch_size=100")

echo "更新结果: $response"

# 检查更新状态
stats=$(curl -s -X GET "http://localhost:8000/api/v1/data/daily/statistics")
echo "数据库状态: $stats"

echo "每日数据更新完成 - $(date)"
```

### 3. 特定市场更新

只更新特定市场的数据：

```bash
# 只更新上海市场
curl -X POST "http://localhost:8000/api/v1/data/daily/incremental-update-all?market=SH&batch_size=50"

# 只更新深圳市场
curl -X POST "http://localhost:8000/api/v1/data/daily/incremental-update-all?market=SZ&batch_size=50"
```

## 性能优化建议

### 1. 批量大小调整

- **小批量 (20-30)**: 适用于网络不稳定或服务器资源有限的环境
- **中批量 (50-70)**: 推荐的默认设置，平衡性能和稳定性
- **大批量 (80-100)**: 适用于高性能服务器和稳定网络环境

### 2. 分时段更新

避免在交易时间进行大量数据更新，建议在以下时间段执行：

- **最佳时间**: 每日收盘后 15:30-17:00
- **备选时间**: 早盘前 8:00-9:00
- **周末**: 可进行全量数据检查和补全

### 3. 错误处理

```bash
#!/bin/bash
# 带错误处理的更新脚本

max_retries=3
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    response=$(curl -s -X POST "http://localhost:8000/api/v1/data/daily/incremental-update-all?market=ALL&batch_size=50")
    
    if echo "$response" | grep -q '"success":true'; then
        echo "数据更新成功"
        break
    else
        retry_count=$((retry_count + 1))
        echo "更新失败，重试第 $retry_count 次"
        sleep 60  # 等待1分钟后重试
    fi
done

if [ $retry_count -eq $max_retries ]; then
    echo "数据更新失败，已达到最大重试次数"
    exit 1
fi
```

## 监控和告警

### 1. 数据完整性检查

```bash
# 检查需要更新的股票数量
stats=$(curl -s -X GET "http://localhost:8000/api/v1/data/daily/statistics")
outdated_count=$(echo "$stats" | jq '.data.stocks_need_update_count')

if [ "$outdated_count" -gt 100 ]; then
    echo "警告：有 $outdated_count 只股票数据过期，需要更新"
fi
```

### 2. 更新成功率监控

```bash
# 监控更新成功率
response=$(curl -s -X POST "http://localhost:8000/api/v1/data/daily/incremental-update-all?market=ALL&batch_size=50")
success_rate=$(echo "$response" | jq '.data.success_rate')

if (( $(echo "$success_rate < 95" | bc -l) )); then
    echo "警告：数据更新成功率过低：$success_rate%"
fi
```

## 注意事项

1. **API限制**: 单次批量请求最多支持100只股票
2. **网络稳定性**: 大量数据更新需要稳定的网络连接
3. **存储空间**: 确保数据库有足够的存储空间
4. **XtQuant连接**: 确保XtQuant服务正常运行
5. **交易时间**: 避免在交易时间进行大量数据更新，可能影响实时数据获取

## 故障排除

### 常见错误及解决方案

1. **"数据服务未初始化"**
   - 检查数据服务是否正常启动
   - 调用 `/api/v1/data/start` 启动数据服务

2. **"XtQuant数据服务未连接"**
   - 检查XtQuant客户端是否正常运行
   - 验证配置文件中的路径设置

3. **"获取股票列表失败"**
   - 检查网络连接
   - 验证XtQuant登录状态

4. **批量更新成功率低**
   - 减小batch_size参数
   - 检查网络稳定性
   - 查看具体失败的股票代码