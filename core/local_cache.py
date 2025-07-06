#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地缓存模块
替代Redis，提供内存缓存功能
"""

import json
import time
from typing import Any, Optional, Dict, List
from threading import Lock
# 移除loguru以避免Python 3.6兼容性问题
from loguru import logger


class LocalCache:
    """本地内存缓存"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
    
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            expire: 过期时间（秒），None表示永不过期
        
        Returns:
            bool: 是否设置成功
        """
        try:
            with self._lock:
                expire_time = None
                if expire is not None:
                    expire_time = time.time() + expire
                
                self._cache[key] = {
                    'value': value,
                    'expire_time': expire_time,
                    'created_at': time.time()
                }
            return True
        except Exception as e:
            logger.error(f"设置缓存失败: {key}, 错误: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            缓存值，如果不存在或已过期则返回None
        """
        try:
            with self._lock:
                if key not in self._cache:
                    return None
                
                cache_item = self._cache[key]
                
                # 检查是否过期
                if cache_item['expire_time'] is not None:
                    if time.time() > cache_item['expire_time']:
                        del self._cache[key]
                        return None
                
                return cache_item['value']
        except Exception as e:
            logger.error(f"获取缓存失败: {key}, 错误: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """删除缓存
        
        Args:
            key: 缓存键
        
        Returns:
            bool: 是否删除成功
        """
        try:
            with self._lock:
                if key in self._cache:
                    del self._cache[key]
                    return True
                return False
        except Exception as e:
            logger.error(f"删除缓存失败: {key}, 错误: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在
        
        Args:
            key: 缓存键
        
        Returns:
            bool: 是否存在
        """
        return self.get(key) is not None
    
    def clear(self) -> bool:
        """清空所有缓存
        
        Returns:
            bool: 是否清空成功
        """
        try:
            with self._lock:
                self._cache.clear()
            return True
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            return False
    
    def keys(self, pattern: str = "*") -> List[str]:
        """获取所有键
        
        Args:
            pattern: 匹配模式（简单支持*通配符）
        
        Returns:
            List[str]: 键列表
        """
        try:
            with self._lock:
                if pattern == "*":
                    return list(self._cache.keys())
                
                # 简单的通配符匹配
                keys = []
                for key in self._cache.keys():
                    if pattern.replace("*", "") in key:
                        keys.append(key)
                return keys
        except Exception as e:
            logger.error(f"获取键列表失败: {e}")
            return []
    
    def expire(self, key: str, seconds: int) -> bool:
        """设置键的过期时间
        
        Args:
            key: 缓存键
            seconds: 过期时间（秒）
        
        Returns:
            bool: 是否设置成功
        """
        try:
            with self._lock:
                if key in self._cache:
                    self._cache[key]['expire_time'] = time.time() + seconds
                    return True
                return False
        except Exception as e:
            logger.error(f"设置过期时间失败: {key}, 错误: {e}")
            return False
    
    def ttl(self, key: str) -> Optional[int]:
        """获取键的剩余生存时间
        
        Args:
            key: 缓存键
        
        Returns:
            剩余秒数，-1表示永不过期，None表示键不存在
        """
        try:
            with self._lock:
                if key not in self._cache:
                    return None
                
                cache_item = self._cache[key]
                if cache_item['expire_time'] is None:
                    return -1
                
                remaining = cache_item['expire_time'] - time.time()
                return max(0, int(remaining))
        except Exception as e:
            logger.error(f"获取TTL失败: {key}, 错误: {e}")
            return None
    
    def cleanup_expired(self) -> int:
        """清理过期的缓存项
        
        Returns:
            int: 清理的项目数量
        """
        try:
            with self._lock:
                current_time = time.time()
                expired_keys = []
                
                for key, cache_item in self._cache.items():
                    if (cache_item['expire_time'] is not None and 
                        current_time > cache_item['expire_time']):
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self._cache[key]
                
                if expired_keys:
                    logger.info(f"清理了 {len(expired_keys)} 个过期缓存项")
                
                return len(expired_keys)
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")
            return 0
    
    def info(self) -> Dict[str, Any]:
        """获取缓存信息
        
        Returns:
            Dict: 缓存统计信息
        """
        try:
            with self._lock:
                total_keys = len(self._cache)
                expired_count = 0
                current_time = time.time()
                
                for cache_item in self._cache.values():
                    if (cache_item['expire_time'] is not None and 
                        current_time > cache_item['expire_time']):
                        expired_count += 1
                
                return {
                    'total_keys': total_keys,
                    'expired_keys': expired_count,
                    'active_keys': total_keys - expired_count,
                    'memory_usage': len(str(self._cache))  # 简单的内存使用估算
                }
        except Exception as e:
            logger.error(f"获取缓存信息失败: {e}")
            return {}
    
    def set_json(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """设置JSON格式的缓存值
        
        Args:
            key: 缓存键
            value: 要序列化为JSON的值
            expire: 过期时间（秒）
        
        Returns:
            bool: 是否设置成功
        """
        try:
            json_value = json.dumps(value, ensure_ascii=False)
            return self.set(key, json_value, expire)
        except Exception as e:
            logger.error(f"设置JSON缓存失败: {key}, 错误: {e}")
            return False
    
    def get_json(self, key: str) -> Optional[Any]:
        """获取JSON格式的缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            反序列化后的值，如果不存在或解析失败则返回None
        """
        try:
            json_value = self.get(key)
            if json_value is None:
                return None
            return json.loads(json_value)
        except Exception as e:
            logger.error(f"获取JSON缓存失败: {key}, 错误: {e}")
            return None


# 全局缓存实例
_cache_instance = None


def get_cache() -> LocalCache:
    """获取全局缓存实例"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LocalCache()
        logger.info("本地缓存初始化完成")
    return _cache_instance


def init_cache():
    """初始化缓存"""
    get_cache()
    logger.info("本地缓存服务启动")


def close_cache():
    """关闭缓存"""
    global _cache_instance
    if _cache_instance:
        _cache_instance.clear()
        _cache_instance = None
        logger.info("本地缓存服务关闭")