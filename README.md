# Smart Trader - 智能量化交易系统

## 项目简介

Smart Trader 是一个基于 Python 的智能量化交易系统，集成了数据获取、策略开发、回测分析、实盘交易和通知提醒等功能。系统采用模块化设计，使用 FastAPI 框架提供 RESTful API 接口。

## 系统架构

### 核心模块

- **数据服务 (DataService)**: 负责股票数据的获取、缓存和管理
- **交易服务 (TradingService)**: 集成 XtQuant 进行实盘交易
- **策略服务 (StrategyService)**: 提供多种技术分析策略
- **回测服务 (BacktestService)**: 策略回测和性能分析
- **通知服务 (NotificationService)**: 钉钉群机器人通知
- **配置模块**: 系统配置管理

### 技术栈

- **Web框架**: FastAPI
- **数据库**: PostgreSQL + SQLAlchemy ORM
- **缓存**: Redis
- **数据源**: XtQuant (迅投量化)
- **通知**: 钉钉群机器人
- **数据分析**: pandas, numpy, talib
- **机器学习**: scikit-learn

## 项目结构

```
smart_trader/
├── main.py                 # 应用入口
├── config.py              # 配置文件
├── requirements.txt       # 依赖包
├── core/                  # 核心模块
│   ├── database.py        # 数据库连接和ORM模型
│   └── redis_client.py    # Redis客户端
├── services/              # 业务服务
│   ├── data_service.py    # 数据服务
│   ├── trading_service.py # 交易服务
│   ├── strategy_service.py# 策略服务
│   ├── backtest_service.py# 回测服务
│   └── notification_service.py # 通知服务
└── api/                   # API路由
    ├── data_routes.py     # 数据API
    ├── trading_routes.py  # 交易API
    ├── strategy_routes.py # 策略API
    ├── backtest_routes.py # 回测API
    ├── notification_routes.py # 通知API
    └── config_routes.py   # 配置API
```

## 安装和配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

确保 PostgreSQL 和 Redis 服务正在运行，并在 `config.py` 中配置相应的连接信息。

### 3. 配置 XtQuant

在 `config.py` 中配置 XtQuant 的安装路径和账户信息：

```python
class XtQuantConfig(BaseModel):
    path: str = "D:\\迅投极速交易终端 睿智融科版\\userdata_mini"
    session_id: int = 123456
    account_id: str = "1000000365"
```

### 4. 配置钉钉通知

在 `config.py` 中配置钉钉群机器人的 Webhook 和密钥：

```python
class DingTalkConfig(BaseModel):
    webhook: str = "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
    secret: str = "YOUR_SECRET"
```

## 运行系统

### 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

### API 文档

访问 `http://localhost:8000/docs` 查看自动生成的 API 文档。

## 主要功能

### 1. 数据服务

- 获取实时和历史股票数据
- 数据缓存和管理
- 股票池管理

### 2. 策略服务

内置多种技术分析策略：
- 移动平均线交叉
- RSI 超卖策略
- 布林带策略
- 成交量突破
- 动量策略
- 均值回归
- MACD 策略
- KDJ 策略

### 3. 交易服务

- 实盘下单和撤单
- 持仓和资产查询
- 风险控制
- 交易记录管理

### 4. 回测服务

- 策略回测
- 性能指标计算
- 回测结果比较
- 交易记录分析

### 5. 通知服务

- 交易信号通知
- 订单状态通知
- 系统警报
- 自定义消息

## API 使用示例

### 获取股票实时数据

```bash
curl -X GET "http://localhost:8000/api/v1/data/realtime/000001.SZ"
```

### 创建策略

```bash
curl -X POST "http://localhost:8000/api/v1/strategy/create" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MA交叉策略",
    "strategy_type": "MA_CROSS",
    "parameters": {"short_period": 5, "long_period": 20}
  }'
```

### 下单交易

```bash
curl -X POST "http://localhost:8000/api/v1/trading/order" \
  -H "Content-Type: application/json" \
  -d '{
    "stock_code": "000001.SZ",
    "order_type": "BUY",
    "volume": 100,
    "price_type": "LIMIT",
    "price": 10.5
  }'
```

## 注意事项

1. 确保 XtQuant 客户端已正确安装和配置
2. 交易功能需要有效的证券账户
3. 生产环境中请妥善保管账户信息和API密钥
4. 建议先在模拟环境中测试策略

## 开发计划

- [ ] 增加更多技术指标和策略
- [ ] 实现机器学习策略
- [ ] 添加风险管理模块
- [ ] 支持多账户交易
- [ ] 增加Web界面
- [ ] 实现实时监控面板

## 许可证

本项目仅供学习和研究使用，请勿用于实际投资决策。投资有风险，入市需谨慎。