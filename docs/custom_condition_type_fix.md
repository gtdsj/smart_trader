# 自定义条件类型转换修复文档

## 问题描述

在原始实现中，自定义条件管理器存在类型不匹配的错误：

```
TypeError: '>' not supported between instances of 'bool' and 'str'
```

**问题根源：**
- 自定义条件的 `calculate` 方法返回布尔值（True/False）
- 数据库中存储的阈值为字符串类型（如 "20"、"true"）
- 在 `evaluate_custom_condition` 中直接比较布尔值和字符串导致类型错误

## 修复方案

### 1. 重新设计自定义条件返回值

**修改前：**
```python
# 布尔类条件返回 True/False
def calculate(self, stock_data: pd.DataFrame, parameters: dict, stock_code: str) -> bool:
    # ... 计算逻辑
    return consecutive_count >= required_days  # 返回布尔值
```

**修改后：**
```python
# 布尔类条件返回 0/1 整数
def calculate(self, stock_data: pd.DataFrame, parameters: dict, stock_code: str) -> int:
    # ... 计算逻辑
    return 1 if consecutive_count >= required_days else 0  # 返回整数

# 角度类条件返回实际角度值
def calculate(self, stock_data: pd.DataFrame, parameters: dict, stock_code: str) -> float:
    # ... 计算逻辑
    return angle_value  # 返回实际角度值
```

### 2. 添加智能类型转换

新增 `_convert_value_type` 方法，实现智能类型转换：

```python
def _convert_value_type(self, value, reference_value):
    """根据参考值的类型转换目标值的类型"""
    if isinstance(reference_value, (int, np.integer)):
        if isinstance(value, str):
            if value.lower() == 'true':
                return 1
            elif value.lower() == 'false':
                return 0
            else:
                return int(float(value))
        elif isinstance(value, bool):
            return int(value)
        else:
            return int(value)
    elif isinstance(reference_value, (float, np.floating)):
        if isinstance(value, str):
            if value.lower() == 'true':
                return 1.0
            elif value.lower() == 'false':
                return 0.0
            else:
                return float(value)
        elif isinstance(value, bool):
            return float(value)
        else:
            return float(value)
    else:
        return value
```

### 3. 修改条件评估逻辑

在 `evaluate_custom_condition` 中使用类型转换：

```python
# 类型转换确保比较兼容性
converted_value = self._convert_value_type(value, indicator_value)

# 执行比较操作
if operator == '>':
    return indicator_value > converted_value
elif operator == '>=':
    return indicator_value >= converted_value
# ... 其他操作符
```

## 修复的自定义条件

### 布尔类条件（返回 0/1）

1. **ConsecutiveCloseAboveMA5Condition** - 连续收盘价高于MA5
2. **IsKCBStockCondition** - 是否为科创板股票
3. **IsBJStockCondition** - 是否为北交所股票
4. **IsSTStockCondition** - 是否为ST股票
5. **ConsecutiveCloseAboveOpenCondition** - 连续收盘价高于开盘价
6. **BrokenBoardStockCondition** - 是否为破板股票
7. **MainCapitalInflowCondition** - 主力资金流入
8. **LowestPriceAboveMA5Condition** - 最低价高于MA5

### 数值类条件（返回实际数值）

1. **MA5AngleConsecutiveCondition** - MA5连续角度
2. **MA10AngleConsecutiveCondition** - MA10连续角度
3. **MA5AngleLatestCondition** - MA5最新角度

## 测试验证

### 测试用例覆盖

1. **类型转换测试**
   - 字符串 "true"/"false" → 整数 1/0
   - 字符串数字 "20" → 浮点数 20.0
   - 布尔值 True/False → 整数 1/0

2. **数据库条件场景测试**
   - 布尔条件与字符串阈值比较
   - 数值条件与字符串阈值比较
   - 角度条件与字符串阈值比较

3. **原始错误场景测试**
   - 验证 `ma5_angle_consecutive > "20"` 不再报错
   - 确认类型转换正确执行

### 测试结果

```
测试完成: 3/3 项测试通过
🎉 所有测试通过！自定义条件类型转换修复成功

修复要点:
1. ✅ 布尔类条件现在返回 0/1 整数值
2. ✅ 角度类条件现在返回实际角度浮点值
3. ✅ 添加了智能类型转换功能
4. ✅ 支持数据库中的字符串值自动转换
5. ✅ 原始 TypeError 错误已修复
```

## 数据库配置建议

### 当前数据库结构

```csv
strategy_id,condition_type,indicator,operator,value,parameters
1,custom,consecutive_close_above_ma5,==,true,"{""ma_period"": 5, ""consecutive_days"": 3}"
2,custom,ma5_angle_consecutive,>,20,"{""ma_period"": 5, ""consecutive_days"": 3}"
```

### 优化建议

1. **标准化数据类型**
   ```sql
   -- 为条件表添加值类型字段
   ALTER TABLE strategy_conditions ADD COLUMN value_type VARCHAR(20) DEFAULT 'string';
   
   -- 可能的值类型：'boolean', 'integer', 'float', 'string'
   ```

2. **条件参数标准化**
   ```sql
   -- 创建条件参数模板表
   CREATE TABLE condition_templates (
       indicator VARCHAR(100) PRIMARY KEY,
       description TEXT,
       return_type VARCHAR(20),  -- 'boolean', 'integer', 'float'
       default_parameters JSON,
       parameter_schema JSON
   );
   ```

3. **阈值配置灵活化**
   ```sql
   -- 支持多阈值配置
   CREATE TABLE condition_thresholds (
       id INTEGER PRIMARY KEY,
       indicator VARCHAR(100),
       threshold_name VARCHAR(50),
       threshold_value DECIMAL(10,4),
       description TEXT
   );
   ```

## 扩展性改进

### 1. 条件注册机制

```python
# 支持动态注册新条件
@register_custom_condition("new_indicator")
class NewIndicatorCondition(CustomConditionBase):
    def calculate(self, stock_data: pd.DataFrame, parameters: dict, stock_code: str) -> float:
        # 实现新指标逻辑
        return calculated_value
```

### 2. 参数验证

```python
class CustomConditionBase(ABC):
    @classmethod
    def validate_parameters(cls, parameters: dict) -> bool:
        """验证参数有效性"""
        return True
    
    @classmethod
    def get_parameter_schema(cls) -> dict:
        """获取参数模式"""
        return {}
```

### 3. 缓存机制

```python
class CustomConditionManager:
    def __init__(self):
        self._calculation_cache = {}
    
    def calculate_condition_with_cache(self, indicator: str, stock_data: pd.DataFrame, 
                                     parameters: dict, stock_code: str):
        """带缓存的条件计算"""
        cache_key = self._generate_cache_key(indicator, stock_data, parameters, stock_code)
        if cache_key in self._calculation_cache:
            return self._calculation_cache[cache_key]
        
        result = self.calculate_condition(indicator, stock_data, parameters, stock_code)
        self._calculation_cache[cache_key] = result
        return result
```

## 性能优化建议

1. **批量计算优化**
   - 对于相同指标的多个股票，可以批量计算技术指标
   - 使用向量化操作替代循环计算

2. **内存管理**
   - 对于大量股票数据，考虑分批处理
   - 及时清理不需要的中间计算结果

3. **并行处理**
   - 对于独立的条件计算，可以使用多线程并行处理
   - 考虑使用 `concurrent.futures` 或 `multiprocessing`

## 总结

通过重新设计自定义条件的返回值类型和添加智能类型转换机制，成功解决了原始的 `TypeError` 问题。修复后的系统具有以下优势：

1. **类型安全**：消除了类型不匹配错误
2. **灵活配置**：支持数据库中的字符串阈值自动转换
3. **易于扩展**：新增条件只需实现计算逻辑，类型转换自动处理
4. **向后兼容**：现有数据库配置无需修改即可正常工作
5. **性能优化**：数值类条件返回实际计算值，提供更多信息

这个修复为量化交易系统的自定义条件功能奠定了坚实的基础，支持更复杂和灵活的策略开发需求。