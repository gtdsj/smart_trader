# Smart Trader 量化交易系统数据库设计文档

## 概述

Smart Trader 量化交易系统使用 DuckDB 作为主要数据库引擎，具有以下特点：
- 高性能列式存储
- 支持 JSON 字段存储复杂数据
- 自动索引优化
- 外键约束保证数据完整性
- 自动时间戳管理

## 数据库表结构

### 1. 股票数据表

#### 1.1 daily_stock_data (日线数据表)

**用途**: 存储股票的日线行情数据，用于技术分析和策略回测

**字段说明**:
- `stock_code`: 股票代码 (如: 600000.SH)
- `trade_date`: 交易日期
- `open_price`: 开盘价
- `high_price`: 最高价
- `low_price`: 最低价
- `close_price`: 收盘价
- `volume`: 成交量
- `amount`: 成交金额
- `turnover_rate`: 换手率
- `pe_ratio`: 市盈率
- `pb_ratio`: 市净率
- `created_at`: 创建时间
- `updated_at`: 更新时间

**建表语句**:
```sql
CREATE TABLE IF NOT EXISTS daily_stock_data (
    stock_code VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    open_price DECIMAL(10,3),
    high_price DECIMAL(10,3),
    low_price DECIMAL(10,3),
    close_price DECIMAL(10,3),
    volume BIGINT,
    amount DECIMAL(15,2),
    turnover_rate DECIMAL(8,4),
    pe_ratio DECIMAL(8,2),
    pb_ratio DECIMAL(8,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (stock_code, trade_date)
);
```

#### 1.2 stock_data (股票数据表 - ORM模型)

**用途**: SQLAlchemy ORM 模型对应的股票数据表

**字段说明**:
- `id`: 主键ID
- `stock_code`: 股票代码
- `trade_date`: 交易日期
- `open_price`: 开盘价
- `high_price`: 最高价
- `low_price`: 最低价
- `close_price`: 收盘价
- `volume`: 成交量
- `amount`: 成交金额
- `turnover_rate`: 换手率
- `pe_ratio`: 市盈率
- `pb_ratio`: 市净率
- `created_at`: 创建时间
- `updated_at`: 更新时间

**建表语句**:
```sql
CREATE TABLE stock_data (
    id INTEGER NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    open_price DECIMAL(10, 3),
    high_price DECIMAL(10, 3),
    low_price DECIMAL(10, 3),
    close_price DECIMAL(10, 3),
    volume BIGINT,
    amount DECIMAL(15, 2),
    turnover_rate DECIMAL(8, 4),
    pe_ratio DECIMAL(8, 2),
    pb_ratio DECIMAL(8, 2),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id)
);
```

### 2. 交易相关表

#### 2.1 trading_orders (交易订单表)

**用途**: 记录所有交易订单的详细信息

**字段说明**:
- `id`: 主键ID
- `order_id`: 订单编号
- `stock_code`: 股票代码
- `order_type`: 订单类型 (买入/卖出)
- `price_type`: 价格类型 (限价/市价等)
- `order_price`: 委托价格
- `order_volume`: 委托数量
- `traded_volume`: 成交数量
- `order_status`: 订单状态
- `strategy_name`: 策略名称
- `remark`: 备注
- `created_at`: 创建时间
- `updated_at`: 更新时间

**建表语句**:
```sql
CREATE TABLE trading_orders (
    id INTEGER NOT NULL,
    order_id VARCHAR(50),
    stock_code VARCHAR(20) NOT NULL,
    order_type VARCHAR(10) NOT NULL,
    price_type VARCHAR(20),
    order_price DECIMAL(10, 3),
    order_volume INTEGER,
    traded_volume INTEGER,
    order_status VARCHAR(20),
    strategy_name VARCHAR(100),
    remark VARCHAR(500),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id)
);
```

#### 2.2 positions (持仓表)

**用途**: 记录当前持仓信息

**字段说明**:
- `id`: 主键ID
- `account_id`: 账户ID
- `stock_code`: 股票代码
- `volume`: 持仓数量
- `available_volume`: 可用数量
- `avg_price`: 平均成本价
- `market_value`: 市值
- `profit_loss`: 盈亏金额
- `profit_loss_ratio`: 盈亏比例
- `created_at`: 创建时间
- `updated_at`: 更新时间

**建表语句**:
```sql
CREATE TABLE positions (
    id INTEGER NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    volume INTEGER,
    available_volume INTEGER,
    avg_price DECIMAL(10, 3),
    market_value DECIMAL(15, 2),
    profit_loss DECIMAL(15, 2),
    profit_loss_ratio DECIMAL(8, 4),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id)
);
```

### 3. 策略管理表

#### 3.1 strategies (策略表)

**用途**: 存储量化交易策略的基本信息

**字段说明**:
- `id`: 主键ID
- `name`: 策略名称
- `description`: 策略描述
- `strategy_type`: 策略类型
- `status`: 策略状态 (active/inactive/paused)
- `config`: 策略配置 (JSON格式)
- `created_at`: 创建时间
- `updated_at`: 更新时间

**建表语句**:
```sql
CREATE TABLE strategies (
    id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50),
    status VARCHAR(20),
    config JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id)
);
```

#### 3.2 strategy_conditions (策略条件表)

**用途**: 存储策略的触发条件

**字段说明**:
- `id`: 主键ID
- `strategy_id`: 关联策略ID
- `condition_type`: 条件类型
- `field_name`: 字段名称
- `operator`: 操作符
- `value`: 条件值
- `logic_operator`: 逻辑操作符 (AND/OR)
- `created_at`: 创建时间

**建表语句**:
```sql
CREATE TABLE strategy_conditions (
    id INTEGER NOT NULL,
    strategy_id INTEGER NOT NULL,
    condition_type VARCHAR(50),
    field_name VARCHAR(100),
    operator VARCHAR(20),
    value VARCHAR(200),
    logic_operator VARCHAR(10),
    created_at TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY(strategy_id) REFERENCES strategies (id)
);
```

#### 3.3 strategy_executions (策略执行表)

**用途**: 记录策略的执行历史

**字段说明**:
    - `id`: 主键ID
    - `strategy_id`: 关联策略ID
    - `execution_time`: 执行时间
    - `status`: 执行状态
    - `result`: 执行结果 (JSON格式)
    - `error_message`: 错误信息
    - `created_at`: 创建时间

**建表语句**:
    ```sql
    CREATE TABLE strategy_executions (
        id INTEGER NOT NULL,
        strategy_id INTEGER NOT NULL,
        execution_time TIMESTAMP,
        status VARCHAR(20),
        result JSON,
        error_message TEXT,
        created_at TIMESTAMP,
        PRIMARY KEY (id),
        FOREIGN KEY(strategy_id) REFERENCES strategies (id)
    );
    ```

#### 3.4 strategy_signals (策略信号表)

**用途**: 存储策略产生的交易信号

**字段说明**:
- `id`: 主键ID
- `strategy_id`: 关联策略ID
- `stock_code`: 股票代码
- `signal_type`: 信号类型 (buy/sell/hold)
- `signal_strength`: 信号强度
- `price`: 信号价格
- `volume`: 建议数量
- `reason`: 信号原因
- `created_at`: 创建时间

**建表语句**:
```sql
CREATE TABLE strategy_signals (
    id INTEGER NOT NULL,
    strategy_id INTEGER NOT NULL,
    stock_code VARCHAR(20),
    signal_type VARCHAR(20),
    signal_strength DECIMAL(5, 2),
    price DECIMAL(10, 3),
    volume INTEGER,
    reason TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY(strategy_id) REFERENCES strategies (id)
);
```

### 4. 回测分析表

#### 4.1 backtest_results (回测结果表)

**用途**: 存储策略回测的结果数据

**字段说明**:
- `id`: 主键ID
- `strategy_id`: 关联策略ID
- `start_date`: 回测开始日期
- `end_date`: 回测结束日期
- `initial_cash`: 初始资金
- `final_cash`: 最终资金
- `total_return`: 总收益率
- `annual_return`: 年化收益率
- `max_drawdown`: 最大回撤
- `sharpe_ratio`: 夏普比率
- `win_rate`: 胜率
- `trade_count`: 交易次数
- `result_data`: 详细结果数据 (JSON格式)
- `created_at`: 创建时间

**建表语句**:
```sql
CREATE TABLE backtest_results (
    id INTEGER NOT NULL,
    strategy_id INTEGER NOT NULL,
    start_date DATE,
    end_date DATE,
    initial_cash DECIMAL(15, 2),
    final_cash DECIMAL(15, 2),
    total_return DECIMAL(8, 4),
    annual_return DECIMAL(8, 4),
    max_drawdown DECIMAL(8, 4),
    sharpe_ratio DECIMAL(8, 4),
    win_rate DECIMAL(8, 4),
    trade_count INTEGER,
    result_data JSON,
    created_at TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY(strategy_id) REFERENCES strategies (id)
);
```

### 5. 系统管理表

#### 5.1 notification_logs (通知日志表)

**用途**: 记录系统通知和告警信息

**字段说明**:
- `id`: 主键ID
- `notification_type`: 通知类型
- `title`: 通知标题
- `content`: 通知内容
- `recipient`: 接收者
- `status`: 发送状态
- `error_message`: 错误信息
- `created_at`: 创建时间

**建表语句**:
```sql
CREATE TABLE notification_logs (
    id INTEGER NOT NULL,
    notification_type VARCHAR(50),
    title VARCHAR(200),
    content TEXT,
    recipient VARCHAR(100),
    status VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (id)
);
```

## 数据库关系图

```
strategies (1) -----> (N) strategy_conditions
strategies (1) -----> (N) strategy_executions
strategies (1) -----> (N) strategy_signals
strategies (1) -----> (N) backtest_results

stock_code 字段关联:
- daily_stock_data.stock_code
- stock_data.stock_code
- trading_orders.stock_code
- positions.stock_code
- strategy_signals.stock_code
```

## 索引建议

为了提高查询性能，建议在以下字段上创建索引：

```sql
-- 股票数据表索引
CREATE INDEX idx_daily_stock_data_trade_date ON daily_stock_data(trade_date);
CREATE INDEX idx_stock_data_trade_date ON stock_data(trade_date);
CREATE INDEX idx_stock_data_stock_code ON stock_data(stock_code);

-- 交易订单表索引
CREATE INDEX idx_trading_orders_stock_code ON trading_orders(stock_code);
CREATE INDEX idx_trading_orders_created_at ON trading_orders(created_at);
CREATE INDEX idx_trading_orders_status ON trading_orders(order_status);

-- 持仓表索引
CREATE INDEX idx_positions_account_id ON positions(account_id);
CREATE INDEX idx_positions_stock_code ON positions(stock_code);

-- 策略表索引
CREATE INDEX idx_strategies_status ON strategies(status);
CREATE INDEX idx_strategy_signals_created_at ON strategy_signals(created_at);
CREATE INDEX idx_strategy_executions_execution_time ON strategy_executions(execution_time);
```

## 数据维护建议

1. **数据备份**: 定期备份 DuckDB 数据文件
2. **数据清理**: 定期清理过期的日志和执行记录
3. **性能监控**: 监控查询性能，适时调整索引
4. **数据完整性**: 定期检查外键约束和数据一致性

## 版本信息

- 文档版本: 1.0
- 创建日期: 2024年
- 数据库引擎: DuckDB
- ORM框架: SQLAlchemy