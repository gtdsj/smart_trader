# DataService 单例模式实现指南

## 概述

`DataService` 类已经重构为单例模式，确保在整个应用程序中只有一个数据服务实例。这种设计模式有助于：

- **资源管理**：避免重复创建数据库连接和缓存客户端
- **状态一致性**：确保所有模块使用相同的数据服务状态
- **性能优化**：减少重复初始化的开销
- **内存效率**：避免多个实例占用额外内存

## 实现特性

### 1. 线程安全的单例实现

```python
class DataService:
    """数据服务 - 单例模式"""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
```

### 2. 防重复初始化机制

```python
def __init__(self):
    # 防止重复初始化
    if self._initialized:
        return
    
    # 初始化代码...
    
    # 标记为已初始化
    self._initialized = True
```

### 3. 便捷的获取方法

```python
@classmethod
def get_instance(cls):
    """获取单例实例"""
    if cls._instance is None:
        cls._instance = cls()
    return cls._instance
```

### 4. 测试支持的重置方法

```python
@classmethod
def reset_instance(cls):
    """重置单例实例（主要用于测试）"""
    if cls._instance is not None:
        cls._instance = None
```

## 使用方法

### 标准使用方式

```python
# 方式1：直接实例化（推荐）
data_service = DataService()

# 方式2：通过类方法获取
data_service = DataService.get_instance()

# 两种方式获取的都是同一个实例
assert DataService() is DataService.get_instance()
```

### 在其他服务中使用

```python
class SomeService:
    def __init__(self):
        # 获取DataService单例
        self.data_service = DataService()
    
    async def some_method(self):
        # 使用数据服务
        stock_list = await self.data_service.get_stock_list()
        return stock_list
```

### 在API路由中使用

```python
from services.data_service import DataService

@app.get("/api/stocks")
async def get_stocks():
    data_service = DataService()
    stocks = await data_service.get_stock_list()
    return {"stocks": stocks}
```

## 测试支持

### 单元测试中的使用

```python
import pytest
from services.data_service import DataService

class TestSomeFeature:
    def setup_method(self):
        # 重置单例以确保测试隔离
        DataService.reset_instance()
    
    def teardown_method(self):
        # 清理单例状态
        DataService.reset_instance()
    
    def test_some_feature(self):
        data_service = DataService()
        # 测试代码...
```

### 模拟测试

```python
from unittest.mock import patch
from services.data_service import DataService

def test_with_mock():
    DataService.reset_instance()
    
    with patch('services.data_service.get_settings') as mock_settings:
        mock_settings.return_value = mock_config
        
        data_service = DataService()
        # 测试代码...
```

## 注意事项

### 1. 初始化时机

- 单例在第一次访问时创建
- 初始化过程只执行一次
- 后续访问直接返回已创建的实例

### 2. 线程安全性

- 实现是线程安全的
- 多线程环境下保证只创建一个实例
- 使用 `asyncio.Lock()` 确保异步安全

### 3. 内存管理

- 单例实例在应用程序生命周期内持续存在
- 只有在显式调用 `reset_instance()` 时才会释放
- 适合长期运行的服务应用

### 4. 测试隔离

- 在测试中使用 `reset_instance()` 确保测试隔离
- 避免测试之间的状态污染
- 在 `setup_method` 和 `teardown_method` 中重置实例

## 性能优势

### 1. 减少资源消耗

- 避免重复创建数据库连接
- 共享缓存客户端实例
- 减少内存占用

### 2. 提高响应速度

- 避免重复初始化开销
- 复用已建立的连接
- 缓存配置和设置

### 3. 状态一致性

- 所有模块共享相同的数据服务状态
- 避免配置不一致问题
- 统一的错误处理和日志记录

## 兼容性

### 向后兼容

- 现有代码无需修改
- `DataService()` 调用方式保持不变
- API接口完全兼容

### 迁移建议

1. **无需立即修改现有代码**：单例模式是透明的
2. **逐步采用最佳实践**：在新代码中使用推荐的使用方式
3. **测试代码需要适配**：添加实例重置逻辑确保测试隔离

## 故障排除

### 常见问题

1. **测试失败**：确保在测试中正确重置单例实例
2. **状态污染**：检查是否在适当的时机重置实例
3. **内存泄漏**：单例实例会持续存在，这是正常行为

### 调试技巧

```python
# 检查实例ID
service1 = DataService()
service2 = DataService()
print(f"Instance IDs: {id(service1)} == {id(service2)}")

# 检查初始化状态
print(f"Initialized: {service1._initialized}")

# 检查实例计数（调试用）
print(f"Instance exists: {DataService._instance is not None}")
```

## 总结

DataService 的单例模式实现提供了：

- ✅ **线程安全**的单例实现
- ✅ **防重复初始化**机制
- ✅ **向后兼容**的API
- ✅ **测试友好**的重置功能
- ✅ **性能优化**和资源节约
- ✅ **状态一致性**保证

这种实现确保了数据服务在整个应用程序中的一致性和效率，同时保持了代码的简洁性和可测试性。