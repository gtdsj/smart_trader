# 股票信息缓存服务使用指南

## 概述

股票信息缓存服务（`StockInfoCacheService`）是一个高性能的内存缓存系统，用于快速访问股票基础信息。该服务在系统启动时将所有股票信息加载到内存中，并提供多种查询接口。

## 主要特性

- **高性能**: 所有数据存储在内存中，查询速度极快
- **单例模式**: 确保全局只有一个缓存实例
- **自动更新**: 支持定时刷新和数据库更新时同步更新
- **多种查询**: 支持单个查询、批量查询、条件查询和模糊搜索
- **线程安全**: 使用读写锁保证并发安全

## 基本使用

### 1. 初始化缓存服务

```python
from services.stock_info_cache_service import StockInfoCacheService

# 获取缓存服务实例（单例模式）
cache_service = StockInfoCacheService()

# 初始化缓存（从数据库加载数据）
await cache_service.initialize()
```

### 2. 获取单只股票信息

```python
# 获取单只股票信息
stock_info = cache_service.get_stock_info('000001.SZ')
if stock_info:
    print(f"股票名称: {stock_info['stock_name']}")
    print(f"交易状态: {stock_info['is_trading']}")
    print(f"ST状态: {stock_info['is_st']}")
    print(f"市场: {stock_info['market']}")
else:
    print("未找到股票信息")
```

### 3. 批量获取股票信息

```python
# 批量获取多只股票信息
stock_codes = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH']
stocks_info = cache_service.get_stocks_info(stock_codes)

for code, info in stocks_info.items():
    print(f"{code}: {info['stock_name']} - 交易: {info['is_trading']}")
```

### 4. 条件查询

```python
# 查询所有ST股票
st_stocks = cache_service.get_stocks_by_condition(is_st=True)
print(f"ST股票数量: {len(st_stocks)}")

# 查询停牌股票
suspended_stocks = cache_service.get_stocks_by_condition(is_trading=False)
print(f"停牌股票数量: {len(suspended_stocks)}")

# 查询深圳市场股票
sz_stocks = cache_service.get_stocks_by_condition(market='SZ')
print(f"深圳股票数量: {len(sz_stocks)}")

# 组合条件查询：深圳市场的非ST股票
sz_normal_stocks = cache_service.get_stocks_by_condition(
    market='SZ', 
    is_st=False
)
print(f"深圳非ST股票数量: {len(sz_normal_stocks)}")
```

### 5. 模糊搜索

```python
# 按股票名称搜索
bank_stocks = cache_service.search_stocks('银行')
print(f"包含'银行'的股票: {len(bank_stocks)}只")

for stock in bank_stocks[:5]:  # 显示前5只
    print(f"{stock['stock_code']}: {stock['stock_name']}")

# 搜索科技类股票
tech_stocks = cache_service.search_stocks('科技')
print(f"包含'科技'的股票: {len(tech_stocks)}只")
```

### 6. 获取所有股票

```python
# 获取所有股票信息
all_stocks = cache_service.get_all_stocks()
print(f"缓存中总股票数: {len(all_stocks)}")

# 遍历所有股票
for stock in all_stocks:
    print(f"{stock['stock_code']}: {stock['stock_name']}")
```

## 缓存管理

### 1. 获取缓存状态

```python
# 获取缓存状态信息
status = cache_service.get_cache_status()
print(f"缓存状态: {status}")

# 状态信息包括：
# - stock_count: 缓存中的股票数量
# - last_update_time: 最后更新时间
# - is_initialized: 是否已初始化
```

### 2. 刷新缓存

```python
# 从数据库重新加载所有数据
await cache_service.refresh_cache()
print("缓存刷新完成")
```

### 3. 更新单只股票信息

```python
# 更新单只股票信息（通常在数据库更新后调用）
stock_info = {
    'stock_code': '000001.SZ',
    'stock_name': '平安银行',
    'market': 'SZ',
    'is_trading': True,
    'is_st': False
}
cache_service.update_stock_info('000001.SZ', stock_info)
```

### 4. 清理缓存

```python
# 清空所有缓存数据
cache_service.clear_cache()
print("缓存已清理")
```

## 系统集成

### 1. 在系统启动时初始化

```python
from services.startup_service import StartupService

# 使用启动服务初始化整个系统
startup_service = StartupService()
result = await startup_service.initialize_system()

if result['success']:
    print("系统初始化成功，股票缓存已就绪")
else:
    print(f"系统初始化失败: {result['message']}")
```

### 2. 在其他服务中使用

```python
class TradingStrategy:
    def __init__(self):
        self.cache_service = StockInfoCacheService()
    
    def filter_tradable_stocks(self, stock_codes):
        """过滤可交易股票"""
        tradable_stocks = []
        
        for code in stock_codes:
            stock_info = self.cache_service.get_stock_info(code)
            if stock_info and stock_info['is_trading'] and not stock_info['is_st']:
                tradable_stocks.append(code)
        
        return tradable_stocks
    
    def get_sector_stocks(self, sector_keyword):
        """获取特定行业股票"""
        return self.cache_service.search_stocks(sector_keyword)
```

## 性能特点

### 查询性能

- **单次查询**: 微秒级响应时间
- **批量查询**: 支持一次查询数千只股票
- **条件查询**: 毫秒级完成复杂条件筛选
- **模糊搜索**: 快速全文搜索股票名称

### 内存使用

- 每只股票约占用几百字节内存
- 5000只股票约占用2-3MB内存
- 内存使用量随股票数量线性增长

### 并发安全

- 使用读写锁保证线程安全
- 支持多线程并发读取
- 写操作（更新、刷新）时会阻塞读操作

## 注意事项

1. **初始化顺序**: 必须先初始化数据库，再初始化缓存服务
2. **内存管理**: 缓存会占用一定内存，系统关闭时应清理缓存
3. **数据一致性**: 数据库更新后应及时同步更新缓存
4. **错误处理**: 查询不存在的股票会返回None，需要做好空值检查
5. **性能优化**: 对于频繁查询，建议使用批量查询接口

## 故障排除

### 常见问题

1. **缓存为空**
   - 检查数据库是否有数据
   - 确认是否调用了initialize()方法
   - 查看日志中的错误信息

2. **查询结果为空**
   - 确认股票代码格式正确（如：000001.SZ）
   - 检查股票是否存在于数据库中
   - 验证缓存是否已正确加载

3. **性能问题**
   - 避免在循环中频繁调用单次查询
   - 使用批量查询接口
   - 考虑缓存查询结果

### 调试方法

```python
# 检查缓存状态
status = cache_service.get_cache_status()
print(f"缓存状态: {status}")

# 检查特定股票是否存在
stock_info = cache_service.get_stock_info('000001.SZ')
if stock_info:
    print("股票存在于缓存中")
else:
    print("股票不存在于缓存中")

# 查看所有股票数量
all_stocks = cache_service.get_all_stocks()
print(f"缓存中总股票数: {len(all_stocks)}")
```

## 扩展功能

缓存服务支持扩展，可以根据需要添加新的查询方法：

```python
class ExtendedStockCache(StockInfoCacheService):
    def get_stocks_by_industry(self, industry):
        """按行业分类获取股票"""
        return self.search_stocks(industry)
    
    def get_large_cap_stocks(self, min_market_cap=None):
        """获取大盘股（需要市值数据）"""
        # 实现逻辑...
        pass
```

通过合理使用股票信息缓存服务，可以大大提高量化交易系统的查询性能和响应速度。