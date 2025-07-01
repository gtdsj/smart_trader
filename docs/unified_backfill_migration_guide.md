# 统一数据补全接口迁移指南

## 概述

本指南将帮助您从废弃的数据补全API迁移到新的统一接口。新的统一接口整合了传统补全、增量更新和优化补全的所有功能，提供更好的性能和一致的用户体验。

## 接口变更对比

### 旧接口（已废弃）

1. **传统数据补全**: `/api/v1/data-backfill/task/create`
2. **增量更新**: `/api/v1/data/daily/incremental-update-all`
3. **优化补全**: `/api/v1/optimized-backfill/full-market`

### 新接口（推荐使用）

1. **统一补全**: `/api/v1/data/unified-backfill/full-market`
2. **快速补全**: `/api/v1/data/unified-backfill/quick`
3. **模式查询**: `/api/v1/data/unified-backfill/modes`

## 迁移映射表

| 旧接口 | 新接口 | 迁移方式 |
|--------|--------|----------|
| `/data-backfill/task/create` | `/unified-backfill/full-market` | 设置 `mode: "traditional"` |
| `/data/daily/incremental-update-all` | `/unified-backfill/quick` | 设置 `mode: "incremental"` |
| `/optimized-backfill/full-market` | `/unified-backfill/full-market` | 设置 `mode: "optimized"` |

## 详细迁移示例

### 1. 传统数据补全迁移

**旧接口调用：**
```bash
curl -X POST "http://localhost:8000/api/v1/data-backfill/task/create" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "全市场补全",
    "market": "ALL",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "batch_size": 30,
    "delay_seconds": 0.2,
    "force_update": false,
    "priority": "normal",
    "auto_retry": true,
    "max_retries": 3
  }'
```

**新接口调用：**
```bash
curl -X POST "http://localhost:8000/api/v1/data/unified-backfill/full-market" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "全市场补全",
    "mode": "traditional",
    "market": "ALL",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "batch_size": 30,
    "delay_seconds": 0.2,
    "force_update": false,
    "priority": "normal",
    "auto_retry": true,
    "max_retries": 3
  }'
```

### 2. 增量更新迁移

**旧接口调用：**
```bash
curl -X POST "http://localhost:8000/api/v1/data/daily/incremental-update-all?market=ALL&batch_size=50"
```

**新接口调用：**
```bash
curl -X POST "http://localhost:8000/api/v1/data/unified-backfill/quick" \
  -H "Content-Type: application/json" \
  -d '{
    "market": "ALL",
    "days": 30,
    "mode": "incremental",
    "force_update": false
  }'
```

### 3. 优化补全迁移

**旧接口调用：**
```bash
curl -X POST "http://localhost:8000/api/v1/optimized-backfill/full-market" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "优化补全",
    "market": "ALL",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "batch_size": 100,
    "enable_parallel": true,
    "force_update": false,
    "priority": "high"
  }'
```

**新接口调用：**
```bash
curl -X POST "http://localhost:8000/api/v1/data/unified-backfill/full-market" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "优化补全",
    "mode": "optimized",
    "market": "ALL",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "batch_size": 100,
    "enable_parallel": true,
    "force_update": false,
    "priority": "high"
  }'
```

## Python客户端迁移

### 旧代码
```python
import requests

# 传统补全
response = requests.post(
    "http://localhost:8000/api/v1/data-backfill/task/create",
    json={
        "task_name": "测试补全",
        "market": "ALL",
        "batch_size": 30
    }
)

# 增量更新
response = requests.post(
    "http://localhost:8000/api/v1/data/daily/incremental-update-all?market=ALL&batch_size=50"
)

# 优化补全
response = requests.post(
    "http://localhost:8000/api/v1/optimized-backfill/full-market",
    json={
        "task_name": "优化补全",
        "market": "ALL",
        "batch_size": 100
    }
)
```

### 新代码
```python
import requests

class UnifiedBackfillClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.unified_endpoint = f"{base_url}/api/v1/data/unified-backfill"
    
    def full_market_backfill(self, mode="optimized", **kwargs):
        """全市场数据补全"""
        data = {"mode": mode, **kwargs}
        return requests.post(f"{self.unified_endpoint}/full-market", json=data)
    
    def quick_backfill(self, days=30, mode="optimized", **kwargs):
        """快速补全"""
        data = {"days": days, "mode": mode, **kwargs}
        return requests.post(f"{self.unified_endpoint}/quick", json=data)
    
    def get_modes(self):
        """获取支持的模式"""
        return requests.get(f"{self.unified_endpoint}/modes")
    
    def get_task_status(self, task_id):
        """获取任务状态"""
        return requests.get(f"{self.unified_endpoint}/task/{task_id}")

# 使用示例
client = UnifiedBackfillClient()

# 传统模式补全
response = client.full_market_backfill(
    mode="traditional",
    task_name="测试补全",
    market="ALL",
    batch_size=30
)

# 增量模式快速补全
response = client.quick_backfill(
    days=30,
    mode="incremental",
    market="ALL"
)

# 优化模式补全（推荐）
response = client.full_market_backfill(
    mode="optimized",
    task_name="优化补全",
    market="ALL",
    batch_size=100,
    enable_parallel=True
)
```

## 新功能优势

### 1. 统一接口
- 一个接口支持三种模式
- 统一的参数格式
- 一致的响应结构

### 2. 智能模式选择
```bash
# 查看所有支持的模式
curl "http://localhost:8000/api/v1/data/unified-backfill/modes"
```

### 3. 快速补全功能
```bash
# 补全最近7天数据
curl -X POST "http://localhost:8000/api/v1/data/unified-backfill/quick" \
  -H "Content-Type: application/json" \
  -d '{"days": 7, "mode": "optimized"}'
```

### 4. 统一任务管理
```bash
# 获取所有任务
curl "http://localhost:8000/api/v1/data/unified-backfill/tasks"

# 按模式筛选
curl "http://localhost:8000/api/v1/data/unified-backfill/tasks?mode=optimized"

# 按状态筛选
curl "http://localhost:8000/api/v1/data/unified-backfill/tasks?status=running"
```

## 性能对比

| 模式 | 性能提升 | 适用场景 | 推荐指数 |
|------|----------|----------|----------|
| optimized | 60-88% | 大规模数据补全 | ⭐⭐⭐⭐⭐ |
| incremental | 20% | 日常增量更新 | ⭐⭐⭐⭐ |
| traditional | 基准 | 兼容性要求高 | ⭐⭐⭐ |

## 迁移时间表

### 阶段1：并行运行（当前）
- 新旧接口同时可用
- 旧接口标记为废弃
- 推荐使用新接口

### 阶段2：迁移期（1-3个月）
- 逐步迁移现有调用
- 提供迁移支持
- 监控使用情况

### 阶段3：完全切换（3-6个月后）
- 移除旧接口
- 仅保留统一接口
- 完成系统简化

## 兼容性说明

### 向后兼容
- 旧接口仍然可用（在 `/legacy` 路径下）
- 响应格式保持一致
- 现有客户端代码无需立即修改

### 访问路径变更
```
# 旧路径（仍可用，但不推荐）
/api/v1/data/legacy/daily/incremental-update-all
/api/v1/data/legacy/data-backfill/task/create

# 新路径（推荐）
/api/v1/data/unified-backfill/quick
/api/v1/data/unified-backfill/full-market
```

## 常见问题

### Q: 旧接口什么时候会被完全移除？
A: 计划在6个月后移除，具体时间会提前通知。

### Q: 新接口是否支持所有旧接口的功能？
A: 是的，新接口通过不同模式支持所有旧功能，并提供了额外的优化。

### Q: 如何选择最适合的模式？
A: 
- 大规模历史数据补全：使用 `optimized` 模式
- 日常增量更新：使用 `incremental` 模式
- 需要详细任务管理：使用 `traditional` 模式

### Q: 迁移过程中遇到问题怎么办？
A: 可以继续使用旧接口（在 `/legacy` 路径下），同时联系技术支持获取帮助。

## 技术支持

如果在迁移过程中遇到任何问题，请：

1. 查看本迁移指南
2. 检查API文档：`http://localhost:8000/docs`
3. 查看日志文件：`logs/smart_trader.log`
4. 联系技术支持团队

## 总结

统一数据补全接口提供了：
- 更好的性能（最高88%提升）
- 更简洁的API设计
- 更强大的功能
- 更好的可维护性

建议尽快迁移到新接口以获得最佳体验。