#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票基础信息缓存服务

提供全局内存缓存，在系统启动时加载所有股票基础信息，
并提供快速查询接口。
"""

import traceback
import threading
import asyncio
from datetime import datetime
from typing import Dict, Optional, List, Any
from loguru import logger

from core.database import get_db, StockBasicInfo


class StockInfoCacheService:
    """
    股票基础信息缓存服务
    
    功能：
    1. 系统启动时加载所有股票基础信息到内存
    2. 提供快速的股票信息查询接口
    3. 支持缓存更新和刷新
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化缓存服务"""
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self._stock_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.RLock()
        self._last_update_time = None
        self._is_initialized = False
        
        logger.info("股票信息缓存服务初始化")
    
    async def initialize(self) -> bool:
        """
        初始化缓存服务
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            if self._is_initialized:
                logger.info("股票信息缓存已初始化")
                return True
                
            logger.info("初始化股票信息缓存服务...")
            
            # 加载初始数据
            if not await self._load_stock_data():
                logger.error("加载股票数据失败")
                return False
            
            self._is_initialized = True
            logger.info(f"✓ 股票信息缓存初始化成功，已缓存 {len(self._stock_cache)} 只股票")
            return True
            
        except Exception as e:
            logger.error(f"初始化股票信息缓存失败: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return False
    
    def clear_cache(self):
        """
        清空缓存
        """
        try:
            with self._cache_lock:
                self._stock_cache.clear()
                self._is_initialized = False
                self._last_update_time = None
            
            logger.info("股票信息缓存已清空")
            
        except Exception as e:
            logger.error(f"清空股票信息缓存失败: {e}")
    
    async def _load_stock_data(self) -> bool:
        """
        从数据库加载股票数据到内存
        
        Returns:
            bool: 加载是否成功
        """
        try:
            logger.info("开始从数据库加载股票基础信息...")
            
            # 从数据库加载所有股票信息
            db = next(get_db())
            try:
                stocks = db.query(StockBasicInfo).all()
                
                with self._cache_lock:
                    self._stock_cache.clear()
                    
                    for stock in stocks:
                        # 解析市场信息
                        market = 'SZ' if stock.stock_code.endswith('.SZ') else 'SH'
                        
                        stock_info = {
                            'stock_code': stock.stock_code,
                            'stock_name': stock.stock_name,
                            'market': market,
                            'exchange': stock.exchange,
                            'listing_date': stock.listing_date,
                            'is_st': stock.is_st,
                            'is_trading': stock.is_trading,
                            'price_tick': stock.price_tick,
                            'updated_at': stock.updated_at
                        }
                        self._stock_cache[stock.stock_code] = stock_info
                
                self._last_update_time = datetime.now()
                logger.info(f"✓ 成功加载 {len(self._stock_cache)} 只股票到内存缓存")
                
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"从数据库加载股票数据失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return False
    
    async def refresh_cache(self) -> bool:
        """
        刷新缓存（重新从数据库加载）
        
        Returns:
            bool: 刷新是否成功
        """
        try:
            logger.info("刷新股票信息缓存...")
            return await self._load_stock_data()
            
        except Exception as e:
            logger.error(f"刷新股票信息缓存失败: {traceback.format_exc()}")
            return False
    
    def get_stock_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取单只股票基础信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            股票信息字典，如果不存在返回None
        """
        try:
            with self._cache_lock:
                return self._stock_cache.get(stock_code)
                
        except Exception as e:
            logger.error(f"get_stock_info失败 {stock_code}: {traceback.format_exc()}")
            return None
    
    def get_stocks_info(self, stock_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        批量获取股票信息
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            股票信息字典
        """
        try:
            result = {}
            with self._cache_lock:
                for code in stock_codes:
                    if code in self._stock_cache:
                        result[code] = self._stock_cache[code]
            return result
                
        except Exception as e:
            logger.error(f"批量获取股票信息失败: {e}")
            return {}
    
    def get_all_stocks(self) -> List[Dict[str, Any]]:
        """
        获取所有股票信息
        
        Returns:
            所有股票信息列表
        """
        try:
            with self._cache_lock:
                return list(self._stock_cache.values())
                
        except Exception as e:
            logger.error(f"获取所有股票信息失败: {e}")
            return []
    
    def get_stocks_by_condition(self, **conditions) -> List[Dict[str, Any]]:
        """
        按条件获取股票信息
        
        Args:
            **conditions: 查询条件，如 market='SZ', is_st=True, is_trading=False
            
        Returns:
            符合条件的股票信息列表
        """
        try:
            result = []
            with self._cache_lock:
                for stock_info in self._stock_cache.values():
                    match = True
                    for key, value in conditions.items():
                        if stock_info.get(key) != value:
                            match = False
                            break
                    if match:
                        result.append(stock_info)
            return result
                
        except Exception as e:
            logger.error(f"按条件获取股票信息失败: {e}")
            return []
    
    def search_stocks(self, keyword: str) -> List[Dict[str, Any]]:
        """
        按关键词搜索股票
        
        Args:
            keyword: 搜索关键词（在股票名称中搜索）
            
        Returns:
            包含关键词的股票信息列表
        """
        try:
            result = []
            keyword = keyword.lower()
            with self._cache_lock:
                for stock_info in self._stock_cache.values():
                    stock_name = stock_info.get('stock_name', '').lower()
                    if keyword in stock_name:
                        result.append(stock_info)
            return result
                
        except Exception as e:
            logger.error(f"搜索股票失败: {e}")
            return []
    
    def update_stock_info(self, stock_code: str, stock_info: Dict[str, Any]):
        """
        更新单只股票信息（同步更新内存缓存）
        
        Args:
            stock_code: 股票代码
            stock_info: 股票信息
        """
        try:
            with self._cache_lock:
                self._stock_cache[stock_code] = stock_info
            
            logger.debug(f"更新股票缓存: {stock_code}")
            
        except Exception as e:
            logger.error(f"更新股票缓存失败 {stock_code}: {e}")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """
        获取缓存状态信息
        
        Returns:
            缓存状态信息
        """
        try:
            with self._cache_lock:
                total_count = len(self._stock_cache)
                sz_count = len([s for s in self._stock_cache.values() if s.get('market') == 'SZ'])
                sh_count = len([s for s in self._stock_cache.values() if s.get('market') == 'SH'])
                st_count = len([s for s in self._stock_cache.values() if s.get('is_st', False)])
                trading_count = len([s for s in self._stock_cache.values() if s.get('is_trading', True)])
                
                return {
                    'stock_count': total_count,
                    'sz_count': sz_count,
                    'sh_count': sh_count,
                    'st_count': st_count,
                    'trading_count': trading_count,
                    'last_update_time': self._last_update_time.strftime('%Y-%m-%d %H:%M:%S') if self._last_update_time else None,
                    'is_initialized': self._is_initialized
                }
                
        except Exception as e:
            logger.error(f"获取缓存状态失败: {e}")
            return {
                'stock_count': 0,
                'is_initialized': self._is_initialized,
                'error': str(e)
            }

def get_stock_cache_service():
    """
    获取股票信息缓存服务实例
    """
    return StockInfoCacheService()