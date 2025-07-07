# STRUCT类型转换错误修复报告

## 问题描述

在调用 `/api/screener/screen-by-strategy` 接口执行选股策略时，出现以下错误：

```
2025-07-07 23:52:17 | ERROR | core.duckdb_adapter:fetchdf:202 - 查询DataFrame失败: 
         SELECT stock_code, trade_date, open_price, high_price, low_price, 
                close_price, volume, amount, turnover_rate, pe_ratio, pb_ratio 
         FROM daily_stock_data 
         WHERE stock_code = ? AND trade_date BETWEEN ? AND ? 
         ORDER BY trade_date 
         , 错误: Conversion Error: Type VARCHAR with value '600629.SH' can't be cast to the destination type STRUCT(stock_code VARCHAR, stock_name VARCHAR, market VARCHAR) 
 
 LINE 5:             WHERE stock_code = ? AND trade_date BETWEEN ? AND ?
```

## 问题根因分析

### 1. 数据类型不匹配

- **数据库中的实际情况**：`daily_stock_data` 表中的 `stock_code` 字段类型为 `VARCHAR`
- **传入参数的问题**：`StockScreener` 向 DuckDB 传入的 `stock_code` 参数被识别为 `STRUCT` 类型

### 2. 数据流追踪

1. `DataService.get_stock_list()` 返回 `List[Dict[str, Any]]` 类型数据
2. `StockScreener._get_all_stock_list()` 直接返回字典列表，而不是股票代码字符串列表
3. `StockScreener` 在调用 `get_batch_historical_data()` 时传入字典对象
4. DuckDB 将字典对象识别为 `STRUCT` 类型，导致类型转换错误

### 3. 类型转换链路

```
DataService.get_stock_list() 
  ↓ 返回 List[Dict[str, Any]]
StockScreener._get_all_stock_list()
  ↓ 直接返回字典列表
StockScreener.get_batch_historical_data()
  ↓ 传入字典对象作为stock_code
DuckDB查询
  ↓ 将字典识别为STRUCT类型
❌ 类型转换错误
```

## 修复方案

### 1. 修改 `StockScreener._get_all_stock_list()` 方法

**文件**: `services/stock_screener.py`

**修改前**:
```python
async def _get_all_stock_list(self) -> List[str]:
    """获取所有股票列表"""
    stock_list_data = await self.data_service.get_stock_list()
    return stock_list_data  # 直接返回字典列表
```

**修改后**:
```python
async def _get_all_stock_list(self) -> List[str]:
    """获取所有股票列表"""
    stock_list_data = await self.data_service.get_stock_list()
    
    if not stock_list_data:
        return []
    
    # 确保返回股票代码字符串列表
    stock_codes = []
    for item in stock_list_data:
        if isinstance(item, dict):
            # 从字典中提取股票代码
            code = item.get('stock_code') or item.get('code') or item.get('symbol')
            if code:
                stock_codes.append(str(code))
        elif isinstance(item, str):
            # 如果已经是字符串，直接添加
            stock_codes.append(item)
    
    logger.info(f"获取股票列表成功，共{len(stock_codes)}只股票")
    return stock_codes
```

### 2. 修改 API 路由单例模式使用

**文件**: `api/stock_screener_routes.py`

**修改前**:
```python
def get_stock_screener():
    data_service = DataService()  # 直接实例化
    return StockScreener(data_service)
```

**修改后**:
```python
def get_stock_screener():
    data_service = DataService.get_instance()  # 使用单例模式
    return StockScreener(data_service)
```

## 修复验证

### 1. 类型转换测试

创建了专门的测试脚本 `test/test_type_conversion_fix.py`，验证：

- ✅ 股票代码类型转换正确
- ✅ DuckDB 查询不再出现 STRUCT 类型错误
- ✅ 批量历史数据获取正常
- ✅ API 端点模拟测试通过

### 2. 测试结果

```
🎉 类型转换修复验证成功！
原始的STRUCT类型转换错误已解决
总计: 2/2 个测试通过
```

### 3. API 修复验证

创建了 `test/test_api_fix.py` 进行最终验证：

```
🎉 API修复验证成功！
原始的STRUCT类型转换错误已解决
```

## 修复效果

### 修复前的错误流程

```
API调用 → StockScreener → 传入Dict对象 → DuckDB识别为STRUCT → ❌ 类型转换错误
```

### 修复后的正确流程

```
API调用 → StockScreener → 提取股票代码字符串 → DuckDB正确识别为VARCHAR → ✅ 查询成功
```

## 相关文件修改清单

1. **services/stock_screener.py**
   - 修改 `_get_all_stock_list()` 方法，确保返回字符串列表

2. **api/stock_screener_routes.py**
   - 修改 `get_stock_screener()` 函数，使用 DataService 单例模式

3. **test/test_type_conversion_fix.py** (新增)
   - 类型转换修复验证测试

4. **test/test_api_fix.py** (新增)
   - API 修复效果验证测试

## 总结

通过修改数据类型转换逻辑，确保传递给 DuckDB 的 `stock_code` 参数始终为字符串类型，成功解决了 STRUCT 类型转换错误。修复后的系统能够正常执行选股策略，不再出现类型转换相关的错误。

**关键改进点**：
- 数据类型一致性：确保股票代码在整个调用链中保持字符串类型
- 单例模式：统一使用 DataService 单例，避免实例不一致问题
- 错误处理：增强了数据格式兼容性和错误处理能力
- 测试覆盖：添加了专门的测试用例验证修复效果