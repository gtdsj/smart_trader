# 策略管理系统使用指南

## 概述

策略管理系统是量化交易平台的核心模块，提供了完整的策略创建、管理、执行和监控功能。系统支持通过JSON格式灵活配置各种交易策略，包括选股策略和买卖策略。

## 系统架构

### 核心组件

1. **策略管理器 (StrategyManager)**: 负责策略的CRUD操作
2. **策略执行器 (StrategyExecutor)**: 负责策略的执行和信号生成
3. **数据库模型**: 存储策略配置、执行记录和信号数据
4. **API接口**: 提供RESTful API服务

### 数据库表结构

- `strategies`: 策略基本信息
- `strategy_conditions`: 策略条件配置
- `strategy_executions`: 策略执行记录
- `strategy_signals`: 策略生成的交易信号

## 快速开始

### 1. 系统初始化

```bash
# 运行初始化脚本
python scripts/init_strategy_system.py
```

初始化脚本会：
- 创建数据库表
- 创建示例策略
- 初始化服务实例
- 运行系统测试

### 2. 启动API服务

```bash
# 启动FastAPI服务
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 策略配置

### 策略分类

- `STOCK_SELECTION`: 选股策略
- `BUY_SELL`: 买卖策略
- `RISK_MANAGEMENT`: 风险管理策略
- `PORTFOLIO_OPTIMIZATION`: 组合优化策略

### 条件类型

- `technical`: 技术指标条件
- `fundamental`: 基本面条件
- `market`: 市场条件
- `custom`: 自定义条件

### 支持的技术指标

- `ma`: 移动平均线
- `ema`: 指数移动平均线
- `rsi`: 相对强弱指数
- `macd`: MACD指标
- `kdj`: KDJ指标
- `bollinger`: 布林带
- `volume`: 成交量
- `turnover_rate`: 换手率
- `price_change`: 价格变化
- `price_change_pct`: 价格变化百分比

### 操作符

- `>`: 大于
- `<`: 小于
- `>=`: 大于等于
- `<=`: 小于等于
- `==`: 等于
- `!=`: 不等于
- `between`: 介于范围内
- `in`: 包含于列表
- `not_in`: 不包含于列表

## API接口使用

### 1. 创建策略

```http
POST /api/v1/strategy-manager/strategies
Content-Type: application/json

{
  "name": "趋势突破策略",
  "description": "基于移动平均线和成交量的趋势突破策略",
  "category": "STOCK_SELECTION",
  "conditions": [
    {
      "condition_type": "technical",
      "indicator": "ma",
      "operator": ">",
      "value": {"period": 20, "compare_to": "close_price"},
      "logic_operator": "AND",
      "weight": 1.0,
      "is_active": true,
      "description": "收盘价突破20日均线"
    },
    {
      "condition_type": "technical",
      "indicator": "volume",
      "operator": ">",
      "value": {"period": 20, "multiplier": 1.5},
      "logic_operator": "AND",
      "weight": 0.8,
      "is_active": true,
      "description": "成交量放大1.5倍"
    }
  ],
  "parameters": {
    "scan_frequency": "daily",
    "max_positions": 10,
    "risk_level": "medium"
  },
  "priority": 1,
  "created_by": "user",
  "version": "1.0"
}
```

### 2. 获取策略列表

```http
GET /api/v1/strategy-manager/strategies?category=STOCK_SELECTION&is_active=true&limit=20
```

### 3. 执行策略

```http
POST /api/v1/strategy-manager/execute
Content-Type: application/json

{
  "strategy_id": 1,
  "stock_codes": ["000001.SZ", "000002.SZ", "600000.SH"],
  "execution_type": "scan"
}
```

### 4. 获取策略信号

```http
GET /api/v1/strategy-manager/signals?strategy_id=1&signal_type=BUY&limit=50
```

## 策略示例

### 1. 趋势突破策略

```json
{
  "name": "趋势突破策略",
  "description": "基于移动平均线和成交量的趋势突破策略",
  "category": "STOCK_SELECTION",
  "conditions": [
    {
      "condition_type": "technical",
      "indicator": "ma",
      "operator": ">",
      "value": {"period": 20, "compare_to": "close_price"},
      "logic_operator": "AND",
      "weight": 1.0,
      "is_active": true,
      "description": "收盘价突破20日均线"
    },
    {
      "condition_type": "technical",
      "indicator": "volume",
      "operator": ">",
      "value": {"period": 20, "multiplier": 1.5},
      "logic_operator": "AND",
      "weight": 0.8,
      "is_active": true,
      "description": "成交量放大1.5倍"
    },
    {
      "condition_type": "technical",
      "indicator": "rsi",
      "operator": "between",
      "value": {"period": 14, "min": 50, "max": 80},
      "logic_operator": "AND",
      "weight": 0.6,
      "is_active": true,
      "description": "RSI在50-80之间"
    }
  ],
  "parameters": {
    "scan_frequency": "daily",
    "max_positions": 10,
    "risk_level": "medium"
  }
}
```

### 2. 超跌反弹策略

```json
{
  "name": "超跌反弹策略",
  "description": "基于RSI和布林带的超跌反弹策略",
  "category": "STOCK_SELECTION",
  "conditions": [
    {
      "condition_type": "technical",
      "indicator": "rsi",
      "operator": "<",
      "value": {"period": 14, "threshold": 30},
      "logic_operator": "AND",
      "weight": 1.0,
      "is_active": true,
      "description": "RSI小于30，超跌"
    },
    {
      "condition_type": "technical",
      "indicator": "bollinger",
      "operator": "<",
      "value": {"period": 20, "component": "lower"},
      "logic_operator": "AND",
      "weight": 0.9,
      "is_active": true,
      "description": "价格跌破布林带下轨"
    },
    {
      "condition_type": "technical",
      "indicator": "price_change_pct",
      "operator": "<",
      "value": {"period": 5, "threshold": -10},
      "logic_operator": "AND",
      "weight": 0.7,
      "is_active": true,
      "description": "5日内跌幅超过10%"
    }
  ],
  "parameters": {
    "scan_frequency": "daily",
    "max_positions": 5,
    "risk_level": "high"
  }
}
```

### 3. MACD金叉策略

```json
{
  "name": "MACD金叉策略",
  "description": "基于MACD指标的金叉买入策略",
  "category": "BUY_SELL",
  "conditions": [
    {
      "condition_type": "technical",
      "indicator": "macd",
      "operator": ">",
      "value": {"component": "line", "compare_to": "signal"},
      "logic_operator": "AND",
      "weight": 1.0,
      "is_active": true,
      "description": "MACD线上穿信号线（金叉）"
    },
    {
      "condition_type": "technical",
      "indicator": "macd",
      "operator": ">",
      "value": {"component": "histogram", "threshold": 0},
      "logic_operator": "AND",
      "weight": 0.8,
      "is_active": true,
      "description": "MACD柱状图为正"
    },
    {
      "condition_type": "technical",
      "indicator": "volume",
      "operator": ">",
      "value": {"period": 10, "multiplier": 1.2},
      "logic_operator": "AND",
      "weight": 0.6,
      "is_active": true,
      "description": "成交量放大"
    }
  ],
  "parameters": {
    "scan_frequency": "daily",
    "position_size": 0.1,
    "stop_loss": 0.05,
    "take_profit": 0.15
  }
}
```

## 高级功能

### 1. 条件组合逻辑

策略支持复杂的条件组合逻辑：

- **AND逻辑**: 所有条件都必须满足
- **OR逻辑**: 任一条件满足即可
- **权重系统**: 为不同条件分配权重
- **条件激活**: 可以动态启用/禁用特定条件

### 2. 参数化配置

策略参数支持灵活配置：

```json
{
  "parameters": {
    "scan_frequency": "daily",        // 扫描频率
    "max_positions": 10,             // 最大持仓数
    "risk_level": "medium",          // 风险等级
    "position_size": 0.1,            // 仓位大小
    "stop_loss": 0.05,               // 止损比例
    "take_profit": 0.15,             // 止盈比例
    "min_volume": 1000000,           // 最小成交量
    "min_market_cap": 5000000000     // 最小市值
  }
}
```

### 3. 策略模板

系统提供预定义的策略模板：

```http
GET /api/v1/strategy-manager/templates
```

### 4. 回测功能

支持策略历史回测：

```http
POST /api/v1/strategy-manager/backtest
Content-Type: application/json

{
  "strategy_id": 1,
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "initial_capital": 1000000,
  "benchmark": "000300.SH"
}
```

## 监控和告警

### 1. 执行监控

```http
GET /api/v1/strategy-manager/executions?status=RUNNING
```

### 2. 信号统计

```http
GET /api/v1/strategy-manager/signals/statistics?strategy_id=1&date_range=7d
```

### 3. 性能指标

```http
GET /api/v1/strategy-manager/performance?strategy_id=1
```

## 最佳实践

### 1. 策略设计原则

- **简单有效**: 避免过度复杂的条件组合
- **参数优化**: 通过回测优化参数设置
- **风险控制**: 设置合理的止损和仓位管理
- **多样化**: 组合多种不同类型的策略

### 2. 性能优化

- **批量处理**: 使用批量API减少请求次数
- **缓存机制**: 利用本地内存缓存提高响应速度
- **异步执行**: 使用异步处理提高并发性能
- **数据预处理**: 提前计算技术指标减少实时计算

### 3. 错误处理

- **数据验证**: 严格验证输入参数
- **异常捕获**: 完善的异常处理机制
- **日志记录**: 详细的操作日志
- **故障恢复**: 自动重试和故障恢复

## 故障排除

### 常见问题

1. **策略执行失败**
   - 检查数据源连接
   - 验证策略条件配置
   - 查看执行日志

2. **信号生成异常**
   - 检查技术指标计算
   - 验证股票数据完整性
   - 确认条件逻辑正确性

3. **性能问题**
   - 优化数据库查询
   - 减少不必要的计算
   - 使用缓存机制

### 日志查看

```bash
# 查看策略执行日志
tail -f logs/strategy_executor.log

# 查看API访问日志
tail -f logs/api.log

# 查看系统错误日志
tail -f logs/error.log
```

## 扩展开发

### 1. 自定义指标

```python
# 在 StrategyExecutor 中添加新的技术指标
def _calculate_custom_indicator(self, df: pd.DataFrame, params: Any) -> pd.DataFrame:
    """计算自定义指标"""
    # 实现自定义指标计算逻辑
    pass

# 注册到计算器映射
self.technical_calculators["custom_indicator"] = self._calculate_custom_indicator
```

### 2. 新增条件类型

```python
# 在 StrategyManager 中扩展条件类型
class ConditionType(Enum):
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    MARKET = "market"
    CUSTOM = "custom"
    NEWS_SENTIMENT = "news_sentiment"  # 新增新闻情感条件
```

### 3. 集成外部数据源

```python
# 扩展数据服务以支持更多数据源
class DataService:
    def __init__(self):
        self.xtquant_service = None
        self.tushare_service = None  # 新增Tushare数据源
        self.wind_service = None     # 新增Wind数据源
```

## 总结

策略管理系统提供了完整的量化交易策略解决方案，支持：

- ✅ 灵活的策略配置
- ✅ 多种技术指标支持
- ✅ 复杂条件组合逻辑
- ✅ 实时策略执行
- ✅ 完整的信号管理
- ✅ 详细的执行监控
- ✅ RESTful API接口
- ✅ 高性能异步处理

通过本系统，用户可以快速构建、测试和部署各种量化交易策略，实现自动化的股票选择和交易决策。