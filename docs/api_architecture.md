# Smart Trader API 路由架构设计

## 概述

本文档描述了 Smart Trader 量化交易系统的 API 路由架构设计。新的模块化架构将原有的单文件路由重构为按功能模块组织的多层次路由结构，提高了代码的可维护性和可扩展性。

## 架构设计原则

### 1. 模块化分离
- 按业务功能将API分为不同模块
- 每个模块独立管理自己的路由
- 便于团队协作开发和维护

### 2. 版本化管理
- 采用版本前缀区分不同API版本
- 支持API向后兼容
- 便于API升级和迁移

### 3. 统一规范
- 统一的响应格式
- 统一的错误处理
- 统一的文档标准

## 路由层次结构

```
/
├── /                           # 根路径，API概览
├── /docs                       # Swagger UI 文档
├── /redoc                      # ReDoc 文档
├── /openapi.json              # OpenAPI 规范
│
├── /api/                       # 系统级API
│   ├── /status                 # 系统状态
│   ├── /health                 # 健康检查
│   ├── /info                   # 系统信息
│   ├── /routes                 # 路由信息
│   ├── /cache/info             # 缓存信息
│   ├── /cache/clear            # 清空缓存
│   └── /database/info          # 数据库信息
│
├── /api/config/                # 配置管理API
│   ├── /                       # 所有配置
│   ├── /database               # 数据库配置
│   ├── /trading                # 交易配置
│   ├── /xtquant                # XtQuant配置
│   └── /notification           # 通知配置
│
└── /api/v1/                    # 业务API v1版本
    ├── /trading/               # 交易服务
    │   ├── /orders             # 订单管理
    │   ├── /positions          # 持仓管理
    │   ├── /account            # 账户信息
    │   └── /balance            # 资金余额
    │
    ├── /data/                  # 数据服务
    │   ├── /stocks             # 股票列表
    │   ├── /realtime           # 实时数据
    │   ├── /historical         # 历史数据
    │   └── /market             # 市场数据
    │
    ├── /strategy/              # 策略服务
    │   ├── /list               # 策略列表
    │   ├── /create             # 创建策略
    │   ├── /run                # 运行策略
    │   └── /signals            # 策略信号
    │
    ├── /backtest/              # 回测服务
    │   ├── /create             # 创建回测
    │   ├── /run                # 运行回测
    │   ├── /results            # 回测结果
    │   └── /reports            # 回测报告
    │
    └── /notification/          # 通知服务
        ├── /send               # 发送通知
        ├── /history            # 通知历史
        └── /settings           # 通知设置
```

## 模块说明

### 系统级模块 (`/api/`)

**职责**: 提供系统基础功能和监控

**主要功能**:
- 系统状态检查
- 健康检查
- 缓存管理
- 数据库信息
- 路由信息查询

**文件**: `api/system.py`

### 配置管理模块 (`/api/config/`)

**职责**: 管理系统各项配置

**主要功能**:
- 数据库配置管理
- 交易参数配置
- XtQuant连接配置
- 通知系统配置

**文件**: `api/config.py`

### 交易服务模块 (`/api/v1/trading/`)

**职责**: 处理股票交易相关业务

**主要功能**:
- 下单、撤单
- 订单查询
- 持仓管理
- 账户信息
- 资金查询

**文件**: `api/trading_routes.py`

### 数据服务模块 (`/api/v1/data/`)

**职责**: 提供股票数据服务

**主要功能**:
- 股票列表
- 实时行情
- 历史数据
- 市场数据
- 技术指标

**文件**: `api/data_routes.py`

### 策略服务模块 (`/api/v1/strategy/`)

**职责**: 管理交易策略

**主要功能**:
- 策略创建和管理
- 策略运行
- 信号生成
- 策略扫描
- 性能分析

**文件**: `api/strategy_routes.py` (已删除，功能整合到业务模块)

### 回测服务模块 (`/api/v1/backtest/`)

**职责**: 提供策略回测功能

**主要功能**:
- 回测任务创建
- 回测执行
- 结果分析
- 报告生成
- 性能评估

**文件**: `api/backtest_routes.py`

### 通知服务模块 (`/api/v1/notification/`)

**职责**: 处理消息通知

**主要功能**:
- 消息发送
- 通知历史
- 通知设置
- 多渠道推送

**文件**: `api/notification_routes.py`

## 文件组织结构

```
api/
├── __init__.py                 # API模块初始化
├── routes.py                   # 主路由管理器
├── system.py                   # 系统级路由
├── config.py                   # 配置管理路由
├── trading_routes.py           # 交易服务路由
├── data_routes.py              # 数据服务路由
# strategy_routes.py 已删除，功能整合到 api/business/strategy.py
├── backtest_routes.py          # 回测服务路由
├── notification_routes.py      # 通知服务路由
├── config_routes.py            # 配置路由（旧版，待迁移）
└── v1/
    └── __init__.py             # v1版本路由集合
```

## 响应格式规范

### 成功响应
```json
{
    "success": true,
    "message": "操作成功",
    "data": {
        // 具体数据
    },
    "timestamp": "2024-01-01T12:00:00"
}
```

### 错误响应
```json
{
    "success": false,
    "message": "错误描述",
    "data": {
        "error": "详细错误信息"
    },
    "timestamp": "2024-01-01T12:00:00"
}
```

## 使用方式

### 启动新版本服务

```bash
# 使用模块化架构的新版本
python main_fastapi_modular.py
```

### 访问API文档

- Swagger UI: http://localhost:8888/docs
- ReDoc: http://localhost:8888/redoc
- 路由信息: http://localhost:8888/api/routes

### API调用示例

```bash
# 系统状态
curl http://localhost:8888/api/status

# 获取股票数据
curl http://localhost:8888/api/v1/data/stocks

# 查询持仓
curl http://localhost:8888/api/v1/trading/positions

# 运行策略
curl -X POST http://localhost:8888/api/v1/strategy/run \
  -H "Content-Type: application/json" \
  -d '{"strategy_name": "ma_cross"}'
```

## 迁移指南

### 从旧版本迁移

1. **URL更新**: 业务API需要添加 `/v1` 前缀
   - 旧: `/api/trading/orders`
   - 新: `/api/v1/trading/orders`

2. **配置API**: 配置相关API保持不变
   - `/api/config/*` 路径不变

3. **系统API**: 系统级API路径不变
   - `/api/status`, `/api/health` 等保持不变

### 兼容性说明

- 新架构向后兼容
- 旧版本API仍可正常使用
- 建议逐步迁移到新版本

## 扩展指南

### 添加新模块

1. 在 `api/` 目录下创建新的路由文件
2. 在 `api/v1/__init__.py` 中注册新路由
3. 更新 `api/routes.py` 中的路由信息
4. 更新本文档

### 添加新版本

1. 创建 `api/v2/` 目录
2. 复制并修改相关路由文件
3. 在主应用中注册新版本路由
4. 更新文档和测试

## 最佳实践

1. **路由命名**: 使用清晰、一致的命名规范
2. **文档完善**: 为每个端点提供详细的文档
3. **错误处理**: 统一的错误处理和响应格式
4. **版本管理**: 合理规划API版本升级策略
5. **测试覆盖**: 为每个模块编写完整的测试用例

## 总结

新的模块化路由架构具有以下优势：

- **清晰的结构**: 按功能模块组织，便于理解和维护
- **良好的扩展性**: 易于添加新功能和新版本
- **团队协作**: 不同团队可以独立开发不同模块
- **版本管理**: 支持API版本化，便于升级和兼容
- **统一规范**: 统一的响应格式和错误处理

这种架构设计为 Smart Trader 系统的长期发展奠定了坚实的基础。