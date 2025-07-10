# 自定义条件优化设计方案

## 问题分析

### 1. 代码重复问题
- `MA5AngleLatestCondition` 和 `MA5AngleConsecutiveCondition` 都计算5日均线
- `MA5AngleConsecutiveCondition` 和 `MA10AngleConsecutiveCondition` 有相似的角度计算逻辑
- 缺乏统一的均线计算和角度计算工具类

### 2. 逻辑错误问题
- `MA5AngleConsecutiveCondition` 原意是判断连续N个交易日的五日均线角度是否均大于指定阈值
- 当前实现 `return sum(recent_angles) / len(recent_angles)` 返回平均角度，不符合原意
- 应该返回满足条件的连续天数或布尔判断结果

### 3. 配置灵活性问题
- 连续天数N硬编码在parameters中，没有在数据库表中配置
- 当前strategy_conditions表缺少parameters字段来存储复杂参数
- 需要支持更灵活的参数配置

## 优化方案设计

### 1. 数据库表结构优化

#### 方案A：扩展现有表（推荐）
在strategy_conditions表中添加parameters字段：

```sql
ALTER TABLE strategy_conditions ADD COLUMN parameters TEXT;
```

**优点：**
- 最小化表结构变更
- 向后兼容现有数据
- 支持JSON格式存储复杂参数

**字段用途：**
- `parameters`: JSON格式存储条件的详细参数，如 `{"ma_period": 5, "consecutive_days": 3, "threshold": 20}`
- `value`: 保持原有用途，存储主要阈值

#### 方案B：创建新的参数表（备选）
创建strategy_condition_parameters表：

```sql
CREATE TABLE strategy_condition_parameters (
    id INTEGER PRIMARY KEY,
    condition_id INTEGER REFERENCES strategy_conditions(id),
    parameter_name VARCHAR(50),
    parameter_value TEXT,
    parameter_type VARCHAR(20), -- 'int', 'float', 'string', 'json'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. 代码架构优化

#### 2.1 创建均线计算工具类

```python
class MovingAverageCalculator:
    """均线计算工具类"""
    
    @staticmethod
    def calculate_ma(data: pd.Series, period: int) -> pd.Series:
        """计算移动平均线"""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def calculate_ma_angle(ma_series: pd.Series, index: int = -1) -> float:
        """计算均线角度（斜率转角度）"""
        if len(ma_series) < 2 or index < 1:
            return 0.0
        
        if pd.notna(ma_series.iloc[index]) and pd.notna(ma_series.iloc[index-1]):
            slope = ma_series.iloc[index] - ma_series.iloc[index-1]
            angle = np.arctan(slope) * 180 / np.pi
            return angle
        return 0.0
    
    @staticmethod
    def calculate_consecutive_angles(ma_series: pd.Series, days: int) -> List[float]:
        """计算连续N天的均线角度"""
        angles = []
        for i in range(len(ma_series) - days + 1, len(ma_series)):
            angle = MovingAverageCalculator.calculate_ma_angle(ma_series, i)
            angles.append(angle)
        return angles
```

#### 2.2 重构自定义条件类

**基础条件类增强：**
```python
class CustomConditionBase(ABC):
    """自定义条件基类"""
    
    def __init__(self):
        self.ma_calculator = MovingAverageCalculator()
    
    @abstractmethod
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> Any:
        pass
    
    def parse_parameters(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """解析参数，提供默认值"""
        return parameters or {}
    
    @classmethod
    def get_default_parameters(cls) -> Dict[str, Any]:
        """获取默认参数"""
        return {}
```

### 3. 具体条件类重构

#### 3.1 MA5AngleLatestCondition 重构

```python
class MA5AngleLatestCondition(CustomConditionBase):
    """最近一个交易日五日均线角度"""
    
    @classmethod
    def get_default_parameters(cls) -> Dict[str, Any]:
        return {"ma_period": 5}
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> float:
        try:
            params = self.parse_parameters(parameters)
            ma_period = params.get('ma_period', 5)
            
            if len(stock_data) < ma_period + 1:
                return 0.0
            
            # 使用工具类计算均线和角度
            ma = self.ma_calculator.calculate_ma(stock_data['close_price'], ma_period)
            angle = self.ma_calculator.calculate_ma_angle(ma, -1)
            
            return angle
            
        except Exception as e:
            logger.error(f"计算MA5最新角度失败: {e}")
            return 0.0
```

#### 3.2 MA5AngleConsecutiveCondition 重构（修复逻辑错误）

```python
class MA5AngleConsecutiveCondition(CustomConditionBase):
    """连续N个交易日五日均线角度大于阈值的天数"""
    
    @classmethod
    def get_default_parameters(cls) -> Dict[str, Any]:
        return {
            "ma_period": 5,
            "consecutive_days": 3,
            "threshold": 20,
            "return_type": "count"  # "count": 返回满足条件天数, "boolean": 返回是否全部满足
        }
    
    def calculate(self, stock_data: pd.DataFrame, parameters: Dict[str, Any] = None) -> float:
        try:
            params = self.parse_parameters(parameters)
            ma_period = params.get('ma_period', 5)
            consecutive_days = params.get('consecutive_days', 3)
            threshold = params.get('threshold', 20)
            return_type = params.get('return_type', 'count')
            
            if len(stock_data) < ma_period + consecutive_days:
                return 0.0
            
            # 使用工具类计算均线
            ma = self.ma_calculator.calculate_ma(stock_data['close_price'], ma_period)
            
            # 计算最近consecutive_days天的角度
            recent_angles = self.ma_calculator.calculate_consecutive_angles(ma, consecutive_days)
            
            if return_type == 'boolean':
                # 返回是否全部满足条件（0或1）
                all_above_threshold = all(angle > threshold for angle in recent_angles)
                return 1.0 if all_above_threshold else 0.0
            else:
                # 返回满足条件的天数
                count = sum(1 for angle in recent_angles if angle > threshold)
                return float(count)
                
        except Exception as e:
            logger.error(f"计算MA5连续角度失败: {e}")
            return 0.0
```

### 4. 数据库配置示例

#### 4.1 新的strategy_conditions表数据格式

```csv
id,strategy_id,condition_type,indicator,operator,value,parameters,logic_operator,order_index,is_active,created_at
1,1,custom,ma5_angle_consecutive,>=,3,"{""ma_period"": 5, ""consecutive_days"": 3, ""threshold"": 20, ""return_type"": ""count""}",AND,0,true,2025-07-09 01:00:00
2,1,custom,ma5_angle_latest,>,50,"{""ma_period"": 5}",AND,1,true,2025-07-09 01:00:00
```

**字段说明：**
- `value`: 主要阈值（如期望的满足条件天数）
- `parameters`: JSON格式的详细参数配置
- `operator`: 与value进行比较的操作符

#### 4.2 参数配置灵活性

**场景1：判断连续3天MA5角度都大于20度**
```json
{
  "indicator": "ma5_angle_consecutive",
  "operator": "==",
  "value": "1",
  "parameters": {
    "ma_period": 5,
    "consecutive_days": 3,
    "threshold": 20,
    "return_type": "boolean"
  }
}
```

**场景2：要求连续5天中至少4天MA5角度大于15度**
```json
{
  "indicator": "ma5_angle_consecutive",
  "operator": ">=",
  "value": "4",
  "parameters": {
    "ma_period": 5,
    "consecutive_days": 5,
    "threshold": 15,
    "return_type": "count"
  }
}
```

### 5. 实施步骤

#### 阶段1：数据库结构升级
1. 添加parameters字段到strategy_conditions表
2. 创建数据迁移脚本
3. 更新现有条件数据，将硬编码参数移到parameters字段

#### 阶段2：代码重构
1. 创建MovingAverageCalculator工具类
2. 重构CustomConditionBase基类
3. 重构现有的MA相关条件类
4. 更新CustomConditionManager以支持parameters字段

#### 阶段3：测试验证
1. 单元测试覆盖所有重构的条件类
2. 集成测试验证数据库参数读取
3. 回归测试确保现有功能不受影响

#### 阶段4：文档更新
1. 更新API文档
2. 更新策略配置指南
3. 提供参数配置示例

### 6. 兼容性考虑

#### 6.1 向后兼容
- 保持现有API接口不变
- parameters字段为可选，默认使用硬编码参数
- 现有策略配置继续有效

#### 6.2 渐进式迁移
- 新策略使用新的参数配置方式
- 现有策略可选择性升级
- 提供迁移工具协助升级

### 7. 性能优化

#### 7.1 计算缓存
- 对相同参数的MA计算结果进行缓存
- 避免重复计算相同周期的均线

#### 7.2 批量处理
- 支持批量股票的条件计算
- 优化数据库查询，减少I/O操作

## 总结

这个优化方案解决了以下问题：

1. **代码复用**：通过MovingAverageCalculator工具类统一均线计算逻辑
2. **逻辑修复**：修正MA5AngleConsecutiveCondition的计算逻辑，支持真正的连续条件判断
3. **配置灵活性**：通过parameters字段支持复杂参数配置，连续天数N可在数据库中灵活配置
4. **扩展性**：为未来添加更多自定义条件提供了良好的架构基础
5. **兼容性**：保持向后兼容，支持渐进式升级

该方案既解决了当前的技术债务，又为系统的长期发展奠定了良好基础。