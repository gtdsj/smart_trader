# -*- coding: utf-8 -*-
"""
Redis客户端模块
"""

import json
import traceback
from typing import Any, Optional, Dict, List
import aioredis
from loguru import logger

from config import get_settings


class RedisClient:
    """Redis客户端封装"""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
    
    async def connect(self):
        """连接Redis"""
        settings = get_settings()
        try:
            # 尝试新版本aioredis的连接方式
            if hasattr(aioredis, 'from_url'):
                self.redis = await aioredis.from_url(settings.redis.url, decode_responses=True)
            else:
                # 兼容旧版本aioredis
                self.redis = aioredis.Redis.from_url(settings.redis.url, decode_responses=True)
            
            # 测试连接
            await self.redis.ping()
            logger.info("Redis连接成功")
        except Exception as e:
            logger.warning(f"Redis连接失败: {e}，将使用本地缓存, {traceback.format_exc()}")
            self.redis = None
    
    async def disconnect(self):
        """断开Redis连接"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis连接已关闭")
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """设置键值"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            result = await self.redis.set(key, value, ex=expire)
            return result
        except Exception as e:
            logger.error(f"Redis设置失败: {key}, 错误: {e}, {traceback.format_exc()}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """获取键值"""
        try:
            value = await self.redis.get(key)
            if value is None:
                return None
            
            # 尝试解析JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"Redis获取失败: {key}, 错误: {e}, {traceback.format_exc()}")
            return None
    
    async def delete(self, key: str) -> bool:
        """删除键"""
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis删除失败: {key}, 错误: {e}, {traceback.format_exc()}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            result = await self.redis.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis检查存在失败: {key}, 错误: {e}, {traceback.format_exc()}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """设置键过期时间"""
        try:
            result = await self.redis.expire(key, seconds)
            return result
        except Exception as e:
            logger.error(f"Redis设置过期时间失败: {key}, 错误: {e}, {traceback.format_exc()}")
            return False
    
    async def hset(self, name: str, mapping: Dict[str, Any]) -> int:
        """设置哈希表"""
        try:
            # 序列化复杂对象
            serialized_mapping = {}
            for k, v in mapping.items():
                if isinstance(v, (dict, list)):
                    serialized_mapping[k] = json.dumps(v, ensure_ascii=False)
                else:
                    serialized_mapping[k] = v
            
            result = await self.redis.hset(name, mapping=serialized_mapping)
            return result
        except Exception as e:
            logger.error(f"Redis哈希设置失败: {name}, 错误: {e}, {traceback.format_exc()}")
            return 0
    
    async def hget(self, name: str, key: str) -> Optional[Any]:
        """获取哈希表字段"""
        try:
            value = await self.redis.hget(name, key)
            if value is None:
                return None
            
            # 尝试解析JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"Redis哈希获取失败: {name}.{key}, 错误: {e}, {traceback.format_exc()}")
            return None
    
    async def hgetall(self, name: str) -> Dict[str, Any]:
        """获取哈希表所有字段"""
        try:
            result = await self.redis.hgetall(name)
            
            # 反序列化值
            deserialized_result = {}
            for k, v in result.items():
                try:
                    deserialized_result[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    deserialized_result[k] = v
            
            return deserialized_result
        except Exception as e:
            logger.error(f"Redis哈希获取全部失败: {name}, 错误: {e}, {traceback.format_exc()}")
            return {}
    
    async def lpush(self, name: str, *values) -> int:
        """列表左推"""
        try:
            # 序列化复杂对象
            serialized_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    serialized_values.append(json.dumps(value, ensure_ascii=False))
                else:
                    serialized_values.append(value)
            
            result = await self.redis.lpush(name, *serialized_values)
            return result
        except Exception as e:
            logger.error(f"Redis列表推送失败: {name}, 错误: {e}, {traceback.format_exc()}")
            return 0
    
    async def rpop(self, name: str) -> Optional[Any]:
        """列表右弹"""
        try:
            value = await self.redis.rpop(name)
            if value is None:
                return None
            
            # 尝试解析JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"Redis列表弹出失败: {name}, 错误: {e}, {traceback.format_exc()}")
            return None
    
    async def lrange(self, name: str, start: int, end: int) -> List[Any]:
        """获取列表范围"""
        try:
            values = await self.redis.lrange(name, start, end)
            
            # 反序列化值
            deserialized_values = []
            for value in values:
                try:
                    deserialized_values.append(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    deserialized_values.append(value)
            
            return deserialized_values
        except Exception as e:
            logger.error(f"Redis列表范围获取失败: {name}, 错误: {e}, {traceback.format_exc()}")
            return []
    
    async def publish(self, channel: str, message: Any) -> int:
        """发布消息"""
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message, ensure_ascii=False)
            
            result = await self.redis.publish(channel, message)
            return result
        except Exception as e:
            logger.error(f"Redis发布消息失败: {channel}, 错误: {e}, {traceback.format_exc()}")
            return 0


# 全局Redis客户端实例
redis_client = RedisClient()


async def init_redis():
    """初始化Redis"""
    await redis_client.connect()


async def close_redis():
    """关闭Redis连接"""
    await redis_client.disconnect()


def get_redis() -> RedisClient:
    """获取Redis客户端"""
    return redis_client