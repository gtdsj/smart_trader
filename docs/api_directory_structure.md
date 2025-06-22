# Smart Trader API 目录结构设计

## 概述

本文档描述了 Smart Trader 量化交易系统的新 API 目录结构设计。新架构按功能类型将 API 模块组织到不同的目录中，提高了代码的可维护性和可扩展性。

## 目录结构

```
api/
├── __init__.py                 # API包初始化
├── routes.py                   # 主路由聚合器
├── system/                     # 系统级API模块
│   ├── __init__.py            # 系统模块路由聚合
│   ├── health.py              # 健康检查API
│   ├── status.py              # 系统状态API
│   └── monitoring.py          # 系统监控API
├── config/                     # 配置管理API模块
│   ├── __init__.py            # 配置模块路由聚合
│   ├── database.py            # 数据库配置API
│   ├── trading.py             # 交易配置API
│   ├── notification.py        # 通知配置API
│   └── xtquant.py             # XtQuant配置API
├── business/                   # 业务功能API模块
│   ├── __init__.py            # 业务模块路由聚合
│   ├── trading.py             # 交易业务API
│   ├── data.py                # 数据业务API
│   ├── strategy.py            # 策略业务API
│   ├── backtest.py            # 回测业务API
│   └── notification.py        # 通知业务API
└── v1/                        # 旧版本兼容（已废弃）
    └── __init__.py            # 向后兼容保留
```

## 模块分类说明

### 1. 系统级模块 (`/api/system/`)

**用途**: 提供系统基础功能和监控能力

**路由前缀**: `/api/`

**包含模块**:
- `health.py`: 健康检查相关API
  - `/api/health` - 整体健康状态
  - `/api/health/cache` - 缓存健康状态
  - `/api/health/database` - 数据库健康状态
  - `/api/health/readiness` - 就绪检查
  - `/api/health/liveness` - 存活检查

- `status.py`: 系统状态相关API
  - `/api/status` - 系统整体状态
  - `/api/status/info` - 详细系统信息
  - `/api/status/version` - 版本信息
  - `/api/status/uptime` - 运行时间

- `monitoring.py`: 系统监控相关API
  - `/api/monitoring` - 监控概览
  - `/api/monitoring/cache` - 缓存监控
  - `/api/monitoring/database` - 数据库监控
  - `/api/monitoring/performance` - 性能指标
  - `/api/monitoring/cache/clear` - 清理缓存

### 2. 配置管理模块 (`/api/config/`)

**用途**: 提供系统配置管理功能

**路由前缀**: `/api/config/`

**包含模块**:
- `database.py`: 数据库配置管理
  - `/api/config/database` - 获取/更新数据库配置
  - `/api/config/database/status` - 数据库状态
  - `/api/config/database/test` - 测试数据库连接

- `trading.py`: 交易配置管理
  - `/api/config/trading` - 获取/更新交易配置
  - `/api/config/trading/validate` - 验证交易配置
  - `/api/config/trading/risk` - 风控配置
  - `/api/config/trading/status` - 交易状态

- `notification.py`: 通知配置管理
  - `/api/config/notification` - 获取/更新通知配置
  - `/api/config/notification/dingtalk` - 钉钉配置
  - `/api/config/notification/email` - 邮件配置
  - `/api/config/notification/test` - 测试通知

- `xtquant.py`: XtQuant配置管理
  - `/api/config/xtquant` - 获取/更新XtQuant配置
  - `/api/config/xtquant/connect` - 连接XtQuant
  - `/api/config/xtquant/disconnect` - 断开连接
  - `/api/config/xtquant/test` - 测试连接
  - `/api/config/xtquant/accounts` - 账户信息

### 3. 业务功能模块 (`/api/business/`)

**用途**: 提供核心业务功能

**路由前缀**: `/api/v1/`

**包含模块**:
- `trading.py`: 交易业务功能
  - `/api/v1/trading` - 交易概览
  - `/api/v1/trading/order` - 下单
  - `/api/v1/trading/orders` - 订单列表
  - `/api/v1/trading/positions` - 持仓列表
  - `/api/v1/trading/trades` - 成交记录
  - `/api/v1/trading/assets` - 资产信息

- `data.py`: 数据业务功能
  - `/api/v1/data` - 数据概览
  - `/api/v1/data/stocks` - 股票列表
  - `/api/v1/data/history` - 历史数据
  - `/api/v1/data/realtime` - 实时数据
  - `/api/v1/data/market` - 市场状态

- `strategy.py`: 策略业务功能
  - `/api/v1/strategy` - 策略概览
  - `/api/v1/strategy/list` - 策略列表
  - `/api/v1/strategy/create` - 创建策略
  - `/api/v1/strategy/{id}` - 策略详情
  - `/api/v1/strategy/{id}/start` - 启动策略
  - `/api/v1/strategy/{id}/stop` - 停止策略

- `backtest.py`: 回测业务功能
  - `/api/v1/backtest` - 回测概览
  - `/api/v1/backtest/list` - 回测列表
  - `/api/v1/backtest/create` - 创建回测
  - `/api/v1/backtest/{id}` - 回测详情
  - `/api/v1/backtest/{id}/start` - 启动回测
  - `/api/v1/backtest/{id}/results` - 回测结果

- `notification.py`: 通知业务功能
  - `/api/v1/notification` - 通知概览
  - `/api/v1/notification/list` - 通知列表
  - `/api/v1/notification/send` - 发送通知
  - `/api/v1/notification/templates` - 通知模板
  - `/api/v1/notification/rules` - 通知规则

## 设计原则

### 1. 功能分离
- **系统级功能**: 基础设施相关，如健康检查、监控、状态查询
- **配置管理**: 系统配置相关，如数据库、交易、通知配置
- **业务功能**: 核心业务逻辑，如交易、策略、回测等

### 2. 路由层次
- **系统级**: `/api/` - 直接挂载到API根路径
- **配置级**: `/api/config/` - 配置管理专用路径
- **业务级**: `/api/v1/` - 版本化的业务API路径

### 3. 模块独立性
- 每个模块都有独立的路由器
- 模块间依赖最小化
- 便于单独测试和维护

### 4. 可扩展性
- 新功能可以轻松添加到对应目录
- 支持多版本API共存
- 便于功能模块的插拔

## 路由聚合机制

### 1. 模块级聚合
每个目录的 `__init__.py` 文件负责聚合该目录下的所有路由：

```python
# api/system/__init__.py
from fastapi import APIRouter
from . import health, status, monitoring

router = APIRouter()
router.include_router(health.router)
router.include_router(status.router)
router.include_router(monitoring.router)
```

### 2. 主路由聚合
`api/routes.py` 负责聚合所有模块的路由：

```python
# api/routes.py
from fastapi import APIRouter
from .system import router as system_router
from .config import router as config_router
from .business import router as business_router

router = APIRouter()
router.include_router(system_router, prefix="")
router.include_router(config_router, prefix="/config")
router.include_router(business_router, prefix="/v1")
```

## 迁移指南

### 从旧结构迁移

1. **系统级API**: 从根目录文件迁移到 `api/system/` 目录
2. **配置API**: 从 `config_routes.py` 迁移到 `api/config/` 目录
3. **业务API**: 从 `*_routes.py` 文件迁移到 `api/business/` 目录

### 向后兼容

- 保留 `api/v1/` 目录用于向后兼容
- 旧的路由文件可以逐步迁移
- API路径保持不变，确保客户端兼容性

## 最佳实践

### 1. 文件命名
- 使用描述性的文件名
- 避免过长的文件名
- 保持命名一致性

### 2. 路由设计
- 每个文件专注单一功能领域
- 使用合适的HTTP方法
- 提供清晰的API文档

### 3. 错误处理
- 统一的错误响应格式
- 适当的HTTP状态码
- 详细的错误信息

### 4. 性能考虑
- 避免循环导入
- 合理使用缓存
- 优化数据库查询

## 扩展指南

### 添加新的系统级API
1. 在 `api/system/` 目录创建新文件
2. 在 `api/system/__init__.py` 中注册路由
3. 使用 `/api/` 前缀

### 添加新的配置API
1. 在 `api/config/` 目录创建新文件
2. 在 `api/config/__init__.py` 中注册路由
3. 使用 `/api/config/` 前缀

### 添加新的业务API
1. 在 `api/business/` 目录创建新文件
2. 在 `api/business/__init__.py` 中注册路由
3. 使用 `/api/v1/` 前缀

### 版本升级
1. 创建新的版本目录（如 `api/v2/`）
2. 复制需要的业务模块
3. 在主路由中注册新版本

## 总结

新的目录结构设计提供了：
- **清晰的功能分离**: 系统、配置、业务功能分别管理
- **良好的可维护性**: 模块化设计便于维护和测试
- **强大的可扩展性**: 支持功能扩展和版本升级
- **向后兼容性**: 保持现有API的兼容性

这种设计为 Smart Trader 系统的长期发展奠定了坚实的基础。