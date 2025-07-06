# 智能量化交易系统

一个基于Python 3.13的完整量化交易系统，专注于策略管理、选股筛选、回测分析和风险控制。

## 🚀 核心功能

### 1. 策略管理模块
- ✅ **可配置策略管理**：通过API接口添加、修改、删除各种策略
- ✅ **多种策略类型**：支持选股策略、交易策略等
- ✅ **策略模板**：提供趋势选股、价值选股等预设模板
- ✅ **策略验证**：自动验证策略配置的有效性

### 2. 指标管理模块
- ✅ **技术指标**：MA、EMA、RSI、MACD、KDJ、Bollinger、ATR、OBV等
- ✅ **基本面指标**：PE、PB、市值、营收增长率、ROE、负债率等
- ✅ **指标计算**：统一的指标计算接口和验证机制
- ✅ **自定义指标**：支持注册和扩展自定义指标

### 3. 操作符管理模块
- ✅ **比较操作符**：>、<、>=、<=、==、!=
- ✅ **区间操作符**：between、between_open、between_left_open、between_right_open
- ✅ **包含操作符**：in、not_in
- ✅ **逻辑操作符**：AND、OR、NOT、XOR
- ✅ **开闭区间支持**：完整的区间操作符定义

### 4. 表达式解析器
- ✅ **复杂表达式**：支持多条件逻辑组合
- ✅ **语法解析**：递归下降解析器，支持括号分组
- ✅ **表达式验证**：自动验证表达式语法和语义
- ✅ **表达式描述**：生成人类可读的表达式描述

### 5. 选股筛选模块
- ✅ **策略筛选**：根据预定义策略筛选全网股票
- ✅ **表达式筛选**：根据自定义表达式筛选股票
- ✅ **并发处理**：多线程并发处理，提高筛选效率
- ✅ **结果存储**：筛选结果持久化存储和查询
- ✅ **历史记录**：完整的筛选历史和统计信息

### 6. 数据管理
- ✅ **多数据源**：支持xtquant等数据接口
- ✅ **数据存储**：使用DuckDB高性能数据库
- ✅ **数据清洗**：自动处理缺失数据和异常值
- ✅ **实时数据**：支持实时和历史数据获取

## 📋 系统要求

- Python 3.13+
- Windows操作系统
- 8GB+ 内存推荐
- 足够的磁盘空间存储历史数据

## 🛠️ 安装和配置

### 1. 克隆项目
```bash
git clone <repository-url>
cd smart_trader
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境
复制并修改配置文件：
```bash
cp config/config.example.yaml config/config.yaml
```

### 4. 初始化数据库
```bash
python -c "from core.database import init_database; init_database()"
```

## 🚀 快速开始

### 1. 启动系统
```bash
python main.py
```

### 2. 访问API文档
启动后访问：http://localhost:8000/docs

### 3. 测试系统功能
```bash
python test_system.py
```

## 📚 API接口

### 策略管理API
- `POST /api/strategies/` - 创建策略
- `GET /api/strategies/` - 获取策略列表
- `GET /api/strategies/{id}` - 获取策略详情
- `PUT /api/strategies/{id}` - 更新策略
- `DELETE /api/strategies/{id}` - 删除策略
- `POST /api/strategies/{id}/activate` - 激活策略
- `POST /api/strategies/{id}/deactivate` - 停用策略

### 指标和操作符API
- `GET /api/available-indicators` - 获取可用指标
- `GET /api/available-operators` - 获取可用操作符
- `GET /api/strategy-categories` - 获取策略分类
- `GET /api/strategy-templates` - 获取策略模板

### 表达式解析API
- `POST /api/parse-expression` - 解析策略表达式
- `POST /api/evaluate-expression` - 评估策略表达式

### 选股筛选API
- `POST /api/screener/screen-by-strategy` - 根据策略筛选股票
- `POST /api/screener/screen-by-expression` - 根据表达式筛选股票
- `GET /api/screener/history` - 获取筛选历史
- `GET /api/screener/result/{execution_id}` - 获取筛选结果详情
- `GET /api/screener/stock-list` - 获取可筛选股票列表
- `GET /api/screener/statistics` - 获取筛选统计信息

## 💡 使用示例

### 1. 创建选股策略
```python
strategy_data = {
    "name": "趋势突破策略",
    "description": "基于移动平均线的趋势突破选股策略",
    "strategy_type": "stock_selection",
    "category": "technical",
    "conditions": [
        {
            "condition_type": "technical",
            "indicator": "MA",
            "operator": ">",
            "value": 20,
            "logic_operator": "AND"
        },
        {
            "condition_type": "technical",
            "indicator": "RSI",
            "operator": "<",
            "value": 70,
            "logic_operator": "AND"
        }
    ]
}
```

### 2. 使用表达式筛选股票
```python
expression = "MA(5) > MA(20) AND RSI < 30 AND volume > 1000000"
result = await screener.screen_stocks_by_expression(
    expression=expression,
    date="2024-01-15"
)
```

### 3. 复杂条件组合
```python
expression = "(MA(5) > MA(20) AND RSI < 30) OR (MACD > 0 AND volume > avg_volume)"
```

## 🏗️ 系统架构

```
智能量化交易系统
├── 核心模块 (core/)
│   ├── 数据库管理 (database.py)
│   └── 缓存适配器 (cache_adapter.py)
├── 服务层 (services/)
│   ├── 策略管理器 (strategy_manager.py)
│   ├── 指标管理器 (indicator_manager.py)
│   ├── 操作符管理器 (operator_manager.py)
│   ├── 表达式解析器 (strategy_expression_parser.py)
│   ├── 选股筛选器 (stock_screener.py)
│   ├── 数据服务 (data_service.py)
│   └── 其他服务...
├── API层 (api/)
│   ├── 策略管理路由 (strategy_manager_routes.py)
│   ├── 选股筛选路由 (stock_screener_routes.py)
│   └── 其他路由...
└── 配置和工具
    ├── 配置管理 (config.py)
    ├── 系统测试 (test_system.py)
    └── 主程序 (main.py)
```

## 🔧 配置说明

### 数据库配置
```yaml
database:
  url: "duckdb:///data/smart_trader.db"
  echo: false
```

### API配置
```yaml
api:
  host: "0.0.0.0"
  port: 8000
  debug: false
```

### 日志配置
```yaml
logging:
  level: "INFO"
  file_prefix: "smart_trader"
  max_files: 30
```

## 📊 性能特性

- **并发处理**：多线程并发筛选，支持大规模股票筛选
- **内存优化**：分批处理数据，避免内存溢出
- **缓存机制**：智能缓存常用数据和计算结果
- **异步处理**：异步I/O操作，提高系统响应速度

## 🛡️ 风险控制

- **参数验证**：严格的输入参数验证
- **异常处理**：完善的异常处理和错误恢复机制
- **日志审计**：详细的操作日志和审计跟踪
- **数据备份**：自动数据备份和恢复机制

## 🔮 扩展功能

### 自定义指标
```python
# 注册自定义指标
indicator_manager.register_custom_indicator(
    name="custom_indicator",
    category="technical",
    parameters={"period": 20},
    calculation_func=custom_calculation_function
)
```

### 自定义操作符
```python
# 注册自定义操作符
operator_manager.register_custom_operator(
    name="custom_op",
    operator_type="comparison",
    evaluation_func=custom_evaluation_function
)
```

## 📈 监控和统计

- **筛选统计**：筛选成功率、匹配率等统计信息
- **性能监控**：执行时间、内存使用等性能指标
- **错误跟踪**：详细的错误日志和异常跟踪
- **使用分析**：策略使用频率和效果分析

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持和联系

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件
- 项目讨论区

---

**注意**：本系统仅供学习和研究使用，实际交易请谨慎评估风险。

## 许可证

本项目仅供学习和研究使用，请勿用于实际投资决策。投资有风险，入市需谨慎。