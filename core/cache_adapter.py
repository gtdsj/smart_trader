# -*- coding: utf-8 -*-
"""
缓存适配器模块
提供统一的缓存接口，支持本地缓存和Redis
"""

import json
import asyncio
from typing import Any, Optional, Dict, List, Union
from loguru import logger
from .local_cache import get_cache, LocalCache


class CacheAdapter:
    """缓存适配器，提供统一的缓存接口"""
    
    def __init__(self, use_local_cache: bool = True):
        self.use_local_cache = use_local_cache
        self.local_cache = get_cache() if use_local_cache else None
        self.redis = None  # Redis客户端，如果需要的话
        
    async def connect(self):
        """连接缓存服务"""
        if self.use_local_cache:
            logger.info("使用本地缓存")
        else:
            logger.warning("Redis功能已禁用，使用本地缓存作为后备")
            self.local_cache = get_cache()
    
    async def disconnect(self):
        """断开缓存连接"""
        if self.local_cache:
            logger.info("本地缓存连接已关闭")
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            elif not isinstance(value, str):
                value = str(value)
            
            return self.local_cache.set(key, value, expire)
        except Exception as e:
            logger.error(f"缓存设置失败: {key}, 错误: {e}")
            return False
    
    async def get(self, key: str) -> Optional[str]:
        """获取缓存值"""
        try:
            value = self.local_cache.get(key)
            return value
        except Exception as e:
            logger.error(f"缓存获取失败: {key}, 错误: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            return self.local_cache.delete(key)
        except Exception as e:
            logger.error(f"缓存删除失败: {key}, 错误: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            return self.local_cache.exists(key)
        except Exception as e:
            logger.error(f"缓存检查存在失败: {key}, 错误: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        try:
            return self.local_cache.expire(key, seconds)
        except Exception as e:
            logger.error(f"缓存设置过期时间失败: {key}, 错误: {e}")
            return False
    
    async def setex(self, key: str, seconds: int, value: Any) -> bool:
        """设置带过期时间的缓存值"""
        return await self.set(key, value, seconds)
    
    async def hset(self, name: str, mapping: Dict[str, Any]) -> bool:
        """设置哈希表"""
        try:
            # 将哈希表转换为JSON存储
            json_value = json.dumps(mapping, ensure_ascii=False)
            return self.local_cache.set(f"hash:{name}", json_value)
        except Exception as e:
            logger.error(f"哈希设置失败: {name}, 错误: {e}")
            return False
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """获取哈希表字段值"""
        try:
            hash_data = self.local_cache.get(f"hash:{name}")
            if hash_data:
                data = json.loads(hash_data)
                return data.get(key)
            return None
        except Exception as e:
            logger.error(f"哈希获取失败: {name}.{key}, 错误: {e}")
            return None
    
    async def hgetall(self, name: str) -> Dict[str, str]:
        """获取整个哈希表"""
        try:
            hash_data = self.local_cache.get(f"hash:{name}")
            if hash_data:
                return json.loads(hash_data)
            return {}
        except Exception as e:
            logger.error(f"哈希获取全部失败: {name}, 错误: {e}")
            return {}
    
    async def lpush(self, name: str, *values) -> int:
        """向列表左侧推入值"""
        try:
            # 获取现有列表
            list_data = self.local_cache.get(f"list:{name}")
            if list_data:
                current_list = json.loads(list_data)
            else:
                current_list = []
            
            # 添加新值到列表开头
            for value in reversed(values):
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                current_list.insert(0, value)
            
            # 保存更新后的列表
            json_value = json.dumps(current_list, ensure_ascii=False)
            self.local_cache.set(f"list:{name}", json_value)
            return len(current_list)
        except Exception as e:
            logger.error(f"列表推送失败: {name}, 错误: {e}")
            return 0
    
    async def rpop(self, name: str) -> Optional[str]:
        """从列表右侧弹出值"""
        try:
            list_data = self.local_cache.get(f"list:{name}")
            if list_data:
                current_list = json.loads(list_data)
                if current_list:
                    value = current_list.pop()
                    # 更新列表
                    json_value = json.dumps(current_list, ensure_ascii=False)
                    self.local_cache.set(f"list:{name}", json_value)
                    return value
            return None
        except Exception as e:
            logger.error(f"列表弹出失败: {name}, 错误: {e}")
            return None
    
    async def lrange(self, name: str, start: int, end: int) -> List[str]:
        """获取列表范围内的值"""
        try:
            list_data = self.local_cache.get(f"list:{name}")
            if list_data:
                current_list = json.loads(list_data)
                if end == -1:
                    return current_list[start:]
                else:
                    return current_list[start:end+1]
            return []
        except Exception as e:
            logger.error(f"列表范围获取失败: {name}, 错误: {e}")
            return []
    
    async def publish(self, channel: str, message: Any) -> int:
        """发布消息（本地缓存模拟）"""
        try:
            # 本地缓存不支持发布订阅，这里只是记录日志
            logger.info(f"模拟发布消息到频道 {channel}: {message}")
            return 1
        except Exception as e:
            logger.error(f"发布消息失败: {channel}, 错误: {e}")
            return 0
    
    async def ping(self) -> bool:
        """检查连接状态"""
        return self.local_cache is not None
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配模式的所有键"""
        try:
            return self.local_cache.keys(pattern)
        except Exception as e:
            logger.error(f"获取键列表失败: {pattern}, 错误: {e}")
            return []
    
    async def close(self):
        """关闭连接"""
        await self.disconnect()


# 全局缓存适配器实例
cache_adapter = CacheAdapter(use_local_cache=True)


async def init_cache():
    """初始化缓存"""
    await cache_adapter.connect()


async def close_cache():
    """关闭缓存连接"""
    await cache_adapter.disconnect()


def get_cache_client() -> CacheAdapter:
    """获取缓存客户端"""
    return cache_adapter