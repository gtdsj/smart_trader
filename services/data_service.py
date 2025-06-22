# -*- coding: utf-8 -*-
"""
数据服务模块
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, and_, desc

try:
    import xtdata
except ImportError:
    logger.warning("xtdata模块未安装，数据获取功能将受限")
    xtdata = None

from config import get_settings
from core.database import get_db, StockData
from core.redis_client import get_redis
from services.notification_service import NotificationService


class DataService:
    """数据服务"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = get_redis()
        self.notification_service = NotificationService()
        self.is_running = False
        self.data_update_task = None
        
        # 数据缓存配置
        self.cache_expire_time = 300  # 5分钟缓存过期
        
        # 支持的股票池
        self.stock_pools = {
            "沪深300": "000300.SH",
            "中证500": "000905.SH",
            "创业板指": "399006.SZ",
            "科创50": "000688.SH"
        }
    
    async def start(self):
        """启动数据服务"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("数据服务启动中...")
        
        # 启动数据更新任务
        self.data_update_task = asyncio.create_task(self._data_update_loop())
        
        logger.info("数据服务启动完成")
    
    async def stop(self):
        """停止数据服务"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.data_update_task:
            self.data_update_task.cancel()
            try:
                await self.data_update_task
            except asyncio.CancelledError:
                pass
        
        logger.info("数据服务已停止")
    
    async def _data_update_loop(self):
        """数据更新循环"""
        while self.is_running:
            try:
                # 检查是否为交易时间
                if self._is_trading_time():
                    await self._update_realtime_data()
                else:
                    # 非交易时间，更新历史数据
                    await self._update_historical_data()
                
                # 等待下次更新
                await asyncio.sleep(60)  # 1分钟更新一次
                
            except Exception as e:
                logger.error(f"数据更新循环异常: {e}")
                await self.notification_service.send_system_error_notification(
                    error_type="数据更新异常",
                    error_message=str(e),
                    module="DataService"
                )
                await asyncio.sleep(60)
    
    def _is_trading_time(self) -> bool:
        """检查是否为交易时间"""
        now = datetime.now()
        weekday = now.weekday()
        
        # 周末不交易
        if weekday >= 5:
            return False
        
        # 交易时间：9:30-11:30, 13:00-15:00
        time_str = now.strftime("%H:%M")
        morning_start = "09:30"
        morning_end = "11:30"
        afternoon_start = "13:00"
        afternoon_end = "15:00"
        
        return (morning_start <= time_str <= morning_end) or (afternoon_start <= time_str <= afternoon_end)
    
    async def get_stock_list(self, market: str = "all") -> List[Dict[str, Any]]:
        """获取股票列表"""
        cache_key = f"stock_list:{market}"
        
        # 尝试从缓存获取
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            if xtdata is None:
                # 模拟数据
                stock_list = [
                    {"stock_code": "000001.SZ", "stock_name": "平安银行", "market": "SZ"},
                    {"stock_code": "000002.SZ", "stock_name": "万科A", "market": "SZ"},
                    {"stock_code": "600000.SH", "stock_name": "浦发银行", "market": "SH"},
                    {"stock_code": "600036.SH", "stock_name": "招商银行", "market": "SH"},
                ]
            else:
                # 使用xtdata获取股票列表
                if market == "SH":
                    stock_list = xtdata.get_stock_list_in_sector("沪市A股")
                elif market == "SZ":
                    stock_list = xtdata.get_stock_list_in_sector("深市A股")
                else:
                    sh_stocks = xtdata.get_stock_list_in_sector("沪市A股")
                    sz_stocks = xtdata.get_stock_list_in_sector("深市A股")
                    stock_list = sh_stocks + sz_stocks
            
            # 缓存数据
            await self.redis_client.set(cache_key, stock_list, expire=3600)  # 1小时缓存
            
            return stock_list
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []
    
    async def get_realtime_data(self, stock_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """获取实时行情数据"""
        result = {}
        
        for stock_code in stock_codes:
            cache_key = f"realtime:{stock_code}"
            
            # 尝试从缓存获取
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                result[stock_code] = cached_data
                continue
            
            try:
                if xtdata is None:
                    # 模拟数据
                    data = {
                        "stock_code": stock_code,
                        "current_price": 10.50 + np.random.random() * 2,
                        "open_price": 10.30,
                        "high_price": 10.80,
                        "low_price": 10.20,
                        "volume": int(np.random.random() * 1000000),
                        "amount": np.random.random() * 10000000,
                        "change_ratio": (np.random.random() - 0.5) * 0.1,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    # 使用xtdata获取实时数据
                    tick_data = xtdata.get_full_tick([stock_code])
                    if tick_data and stock_code in tick_data:
                        tick = tick_data[stock_code]
                        data = {
                            "stock_code": stock_code,
                            "current_price": tick.get("lastPrice", 0),
                            "open_price": tick.get("open", 0),
                            "high_price": tick.get("high", 0),
                            "low_price": tick.get("low", 0),
                            "volume": tick.get("volume", 0),
                            "amount": tick.get("amount", 0),
                            "change_ratio": tick.get("pctChg", 0) / 100,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        continue
                
                result[stock_code] = data
                
                # 缓存数据
                await self.redis_client.set(cache_key, data, expire=10)  # 10秒缓存
                
            except Exception as e:
                logger.error(f"获取{stock_code}实时数据失败: {e}")
                continue
        
        return result
    
    async def get_historical_data(self, stock_code: str, start_date: str, 
                                end_date: str, period: str = "1d") -> pd.DataFrame:
        """获取历史行情数据"""
        cache_key = f"historical:{stock_code}:{start_date}:{end_date}:{period}"
        
        # 尝试从缓存获取
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return pd.DataFrame(cached_data)
        
        try:
            if xtdata is None:
                # 模拟数据
                date_range = pd.date_range(start=start_date, end=end_date, freq='D')
                data = []
                base_price = 10.0
                
                for date in date_range:
                    if date.weekday() < 5:  # 工作日
                        change = (np.random.random() - 0.5) * 0.1
                        base_price *= (1 + change)
                        
                        data.append({
                            "trade_date": date,
                            "open_price": base_price * (1 + (np.random.random() - 0.5) * 0.02),
                            "high_price": base_price * (1 + np.random.random() * 0.03),
                            "low_price": base_price * (1 - np.random.random() * 0.03),
                            "close_price": base_price,
                            "volume": int(np.random.random() * 1000000),
                            "amount": base_price * int(np.random.random() * 1000000)
                        })
                
                df = pd.DataFrame(data)
            else:
                # 使用xtdata获取历史数据
                data = xtdata.get_market_data(
                    stock_list=[stock_code],
                    period=period,
                    start_time=start_date,
                    end_time=end_date
                )
                
                if data.empty:
                    return pd.DataFrame()
                
                df = data.reset_index()
                df.columns = [col.lower() for col in df.columns]
            
            # 缓存数据
            await self.redis_client.set(cache_key, df.to_dict('records'), expire=3600)  # 1小时缓存
            
            return df
            
        except Exception as e:
            logger.error(f"获取{stock_code}历史数据失败: {e}")
            return pd.DataFrame()
    
    async def save_stock_data(self, stock_data: Dict[str, Any]):
        """保存股票数据到数据库"""
        try:
            async for db in get_db():
                # 检查数据是否已存在
                existing_query = select(StockData).where(
                    and_(
                        StockData.stock_code == stock_data["stock_code"],
                        StockData.trade_date == stock_data["trade_date"]
                    )
                )
                result = await db.execute(existing_query)
                existing_data = result.scalar_one_or_none()
                
                if existing_data:
                    # 更新现有数据
                    update_stmt = update(StockData).where(
                        StockData.id == existing_data.id
                    ).values(**stock_data)
                    await db.execute(update_stmt)
                else:
                    # 插入新数据
                    insert_stmt = insert(StockData).values(**stock_data)
                    await db.execute(insert_stmt)
                
                await db.commit()
                break
                
        except Exception as e:
            logger.error(f"保存股票数据失败: {e}")
    
    async def _update_realtime_data(self):
        """更新实时数据"""
        try:
            # 获取关注的股票列表
            watched_stocks = await self._get_watched_stocks()
            
            if not watched_stocks:
                return
            
            # 获取实时数据
            realtime_data = await self.get_realtime_data(watched_stocks)
            
            # 保存到数据库
            for stock_code, data in realtime_data.items():
                stock_data = {
                    "stock_code": stock_code,
                    "trade_date": datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
                    "open_price": data.get("open_price"),
                    "high_price": data.get("high_price"),
                    "low_price": data.get("low_price"),
                    "close_price": data.get("current_price"),
                    "volume": data.get("volume"),
                    "amount": data.get("amount")
                }
                await self.save_stock_data(stock_data)
            
            logger.info(f"更新了{len(realtime_data)}只股票的实时数据")
            
        except Exception as e:
            logger.error(f"更新实时数据失败: {e}")
    
    async def _update_historical_data(self):
        """更新历史数据"""
        try:
            # 获取需要更新的股票列表
            stock_list = await self._get_stocks_need_update()
            
            if not stock_list:
                return
            
            # 批量更新历史数据
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            for stock_code in stock_list[:10]:  # 限制每次更新10只股票
                df = await self.get_historical_data(stock_code, start_date, end_date)
                
                if not df.empty:
                    for _, row in df.iterrows():
                        stock_data = {
                            "stock_code": stock_code,
                            "trade_date": row["trade_date"],
                            "open_price": row["open_price"],
                            "high_price": row["high_price"],
                            "low_price": row["low_price"],
                            "close_price": row["close_price"],
                            "volume": row["volume"],
                            "amount": row["amount"]
                        }
                        await self.save_stock_data(stock_data)
            
            logger.info(f"更新了{len(stock_list)}只股票的历史数据")
            
        except Exception as e:
            logger.error(f"更新历史数据失败: {e}")
    
    async def _get_watched_stocks(self) -> List[str]:
        """获取关注的股票列表"""
        # 从Redis获取关注股票列表
        watched_stocks = await self.redis_client.get("watched_stocks")
        if watched_stocks:
            return watched_stocks
        
        # 默认关注一些热门股票
        default_stocks = [
            "000001.SZ", "000002.SZ", "600000.SH", "600036.SH",
            "000858.SZ", "002415.SZ", "600519.SH", "000858.SZ"
        ]
        
        await self.redis_client.set("watched_stocks", default_stocks, expire=3600)
        return default_stocks
    
    async def _get_stocks_need_update(self) -> List[str]:
        """获取需要更新的股票列表"""
        try:
            async for db in get_db():
                # 获取最近没有更新的股票
                query = select(StockData.stock_code).distinct().order_by(
                    desc(StockData.updated_at)
                ).limit(100)
                
                result = await db.execute(query)
                stocks = [row[0] for row in result.fetchall()]
                
                return stocks
        except Exception as e:
            logger.error(f"获取需要更新的股票列表失败: {e}")
            return []
    
    async def add_watched_stock(self, stock_code: str) -> bool:
        """添加关注股票"""
        try:
            watched_stocks = await self._get_watched_stocks()
            if stock_code not in watched_stocks:
                watched_stocks.append(stock_code)
                await self.redis_client.set("watched_stocks", watched_stocks, expire=3600)
                logger.info(f"添加关注股票: {stock_code}")
            return True
        except Exception as e:
            logger.error(f"添加关注股票失败: {e}")
            return False
    
    async def remove_watched_stock(self, stock_code: str) -> bool:
        """移除关注股票"""
        try:
            watched_stocks = await self._get_watched_stocks()
            if stock_code in watched_stocks:
                watched_stocks.remove(stock_code)
                await self.redis_client.set("watched_stocks", watched_stocks, expire=3600)
                logger.info(f"移除关注股票: {stock_code}")
            return True
        except Exception as e:
            logger.error(f"移除关注股票失败: {e}")
            return False
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """获取市场概览"""
        cache_key = "market_overview"
        
        # 尝试从缓存获取
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            overview = {}
            
            # 获取主要指数数据
            for name, code in self.stock_pools.items():
                realtime_data = await self.get_realtime_data([code])
                if code in realtime_data:
                    overview[name] = realtime_data[code]
            
            # 缓存数据
            await self.redis_client.set(cache_key, overview, expire=60)  # 1分钟缓存
            
            return overview
            
        except Exception as e:
            logger.error(f"获取市场概览失败: {e}")
            return {}