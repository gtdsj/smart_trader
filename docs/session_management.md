# XtQuantService Session管理说明

## 问题背景

根据讯投(XtQuant)官方文档，`XtQuantTrader`的`session_id`参数不能重复。在原有的项目架构中，多个地方创建了`XtQuantService`实例，但都使用相同的`session_id`（123456），这会导致连接冲突。

## 解决方案

### 自动Session分配机制

修改了`XtQuantService`类，实现了自动的session_id分配机制：

1. **类级别计数器**：使用类变量`_session_counter`维护全局session计数
2. **线程安全**：使用`threading.Lock()`确保多线程环境下的安全性
3. **自动递增**：每创建一个新实例，session_id自动递增
4. **日志记录**：记录每个实例分配的session_id，便于调试

### 代码实现

```python
class XtQuantService:
    # 类级别的session计数器和锁
    _session_counter = 123456
    _session_lock = threading.Lock()
    
    @classmethod
    def _get_next_session_id(cls) -> int:
        """获取下一个可用的session_id"""
        with cls._session_lock:
            cls._session_counter += 1
            return cls._session_counter
    
    def __init__(self):
        # 为每个实例分配唯一的session_id
        self.session_id = self._get_next_session_id()
        logger.info(f"XtQuantService实例创建，分配session_id: {self.session_id}")
        # ... 其他初始化代码
```

## 影响的文件和模块

### 创建XtQuantService实例的位置

1. `main_fastapi.py` - 主应用启动时创建
2. `services/data_service.py` - 数据服务中创建
3. `services/trading_service.py` - 交易服务中创建
4. `api/business/data.py` - 数据API业务逻辑中创建
5. `api/business/trading.py` - 交易API业务逻辑中创建

### Session分配示例

当系统启动时，各个实例将获得如下session_id：
- 第1个实例：123457
- 第2个实例：123458
- 第3个实例：123459
- 第4个实例：123460
- 第5个实例：123461

## 使用建议

### 1. 避免不必要的实例创建

虽然现在支持多实例，但建议评估是否真的需要创建多个`XtQuantService`实例：

- **数据获取**：可以共享同一个实例
- **交易操作**：通常一个账户只需要一个连接
- **实时订阅**：可以在一个实例中管理所有订阅

### 2. 考虑单例模式

如果确定只需要一个XtQuant连接，可以考虑实现单例模式：

```python
class XtQuantService:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
```

### 3. 资源管理

多个实例意味着多个连接，需要注意：
- **内存使用**：每个实例都会占用内存
- **连接数限制**：XtQuant可能有连接数限制
- **性能影响**：多个连接可能影响性能

## 测试验证

运行`test_session_uniqueness.py`可以验证session_id的唯一性：

```bash
python test_session_uniqueness.py
```

预期输出：
```
✅ 测试通过：所有session_id都是唯一的
```

## 配置说明

原有的配置文件中的`session_id`设置现在主要用作起始值，实际使用的session_id会在此基础上递增分配。

如需修改起始session_id，可以调整`XtQuantService._session_counter`的初始值。