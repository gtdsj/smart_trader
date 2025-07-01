# -*- coding: utf-8 -*-
"""
XtQuant数据和交易服务模块
提供完整的xtquant功能封装，包括数据获取、实时订阅、交易委托等
"""
import traceback
import asyncio
import time
import threading
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger
from enum import Enum
from core.time_utils import TimeUtils

try:
    from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
    from xtquant.xttype import StockAccount
    from xtquant import xtconstant
    from xtquant import xtdata
except ImportError:
    logger.warning("xtquant模块未安装，相关功能将受限")
    XtQuantTrader = None
    XtQuantTraderCallback = None
    StockAccount = None
    xtconstant = None
    xtdata = None

from config import get_settings
from core.cache_adapter import get_cache_client
from services.notification_service import NotificationService


class Period(Enum):
    """K线周期枚举"""
    TICK = "tick"  # 分笔
    MIN1 = "1m"    # 1分钟
    MIN5 = "5m"    # 5分钟
    MIN15 = "15m"  # 15分钟
    MIN30 = "30m"  # 30分钟
    MIN60 = "1h"   # 1小时
    DAILY = "1d"   # 日线
    WEEKLY = "1w"  # 周线
    MONTHLY = "1M" # 月线


class XtQuantDataCallback:
    """XtQuant数据回调类"""
    
    def __init__(self, xtquant_service):
        self.xtquant_service = xtquant_service
    
    def on_data(self, datas):
        """数据推送回调"""
        try:
            for stock_code, data in datas.items():
                # 处理实时数据推送
                asyncio.create_task(
                    self.xtquant_service._handle_realtime_data(stock_code, data)
                )
        except Exception as e:
            logger.error(f"处理实时数据回调失败: {e}, {traceback.format_exc()}")


if XtQuantTraderCallback is not None:
    class XtQuantTradingCallback(XtQuantTraderCallback):
        """XtQuant交易回调类"""
        
        def __init__(self, xtquant_service):
            super().__init__()
            self.xtquant_service = xtquant_service
else:
    class XtQuantTradingCallback:
        """XtQuant交易回调类（模拟）"""
        
        def __init__(self, xtquant_service):
            self.xtquant_service = xtquant_service
        
        def on_disconnected(self):
            """连接断开回调"""
            logger.warning("XtQuant交易连接断开")
            self.xtquant_service.is_trading_connected = False
            asyncio.create_task(
                self.xtquant_service.notification_service.send_system_error_notification(
                    error_type="交易连接断开",
                    error_message="与XtQuant交易服务器的连接已断开",
                    module="XtQuantService"
                )
            )
        
        def on_stock_order(self, order):
            """委托回报推送"""
            logger.info(f"订单回报: {order.stock_code}, 状态: {order.order_status}, 系统订单号: {order.order_sysid}")
            asyncio.create_task(
                self.xtquant_service._handle_order_callback(order)
            )
        
        def on_stock_trade(self, trade):
            """成交变动推送"""
            logger.info(f"成交回报: {trade.stock_code}, 订单ID: {trade.order_id}")
            asyncio.create_task(
                self.xtquant_service._handle_trade_callback(trade)
            )
        
        def on_order_error(self, order_error):
            """委托失败推送"""
            logger.error(f"订单错误: {order_error.order_id}, 错误码: {order_error.error_id}, 错误信息: {order_error.error_msg}")
            asyncio.create_task(
                self.xtquant_service._handle_order_error(order_error)
            )
        
        def on_cancel_error(self, cancel_error):
            """撤单失败推送"""
            logger.error(f"撤单错误: {cancel_error.order_id}, 错误码: {cancel_error.error_id}, 错误信息: {cancel_error.error_msg}")
        
        def on_order_stock_async_response(self, response):
            """异步下单回报推送"""
            logger.info(f"异步下单回报: 账户: {response.account_id}, 订单ID: {response.order_id}, 序号: {response.seq}")
        
        def on_account_status(self, status):
            """账户状态推送"""
            logger.info(f"账户状态: {status.account_id}, 类型: {status.account_type}, 状态: {status.status}")


class XtQuantService:
    """XtQuant服务类，提供数据获取和交易功能"""
    
    # 类变量用于管理session_id和单例
    _session_counter = 123456
    _session_lock = threading.Lock()
    _instance = None
    _instance_lock = threading.Lock()
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def _get_next_session_id(cls) -> int:
        """获取下一个可用的session_id"""
        with cls._session_lock:
            cls._session_counter += 1
            return cls._session_counter
    
    def __init__(self):
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.settings = get_settings()
        self.cache_client = get_cache_client()
        self.notification_service = NotificationService()
        
        # 为每个实例分配唯一的session_id
        self.session_id = self._get_next_session_id()
        logger.info(f"XtQuantService实例创建，分配session_id: {self.session_id}")
        
        # 线程池执行器
        from concurrent.futures import ThreadPoolExecutor
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # 交易相关
        self.xt_trader = None
        self.account = None
        self.trading_callback = None
        self.is_trading_connected = False
        
        # 数据相关
        self.data_callback = None
        self.is_data_connected = False
        self.subscribed_stocks = set()
        
        # 回调函数注册
        self.realtime_data_callbacks = []
        self.order_callbacks = []
        self.trade_callbacks = []
        
        self.is_running = False
    
    @property
    def is_connected(self) -> bool:
        """检查XtQuant服务连接状态"""
        return self.is_trading_connected and self.is_data_connected
    
    async def start(self):
        """启动XtQuant服务"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("XtQuant服务启动中...")
        
        try:
            if xtdata is None or XtQuantTrader is None:
                raise Exception("xtquant未安装，无法启动真实连接")
            
            # 初始化数据连接
            await self._init_data_connection()
            
            # 初始化交易连接
            await self._init_trading_connection()
            
            logger.info("XtQuant服务启动完成")
            
        except Exception as e:
            logger.error(f"XtQuant服务启动失败: {e}, {traceback.format_exc()}")
            await self.notification_service.send_system_error_notification(
                error_type="XtQuant服务启动失败",
                error_message=f"XtQuant服务启动失败: {str(e)}",
                module="XtQuantService"
            )
            raise
    
    async def stop(self):
        """停止XtQuant服务"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        try:
            # 取消所有订阅
            if self.subscribed_stocks and xtdata:
                for stock_code in self.subscribed_stocks:
                    xtdata.unsubscribe_quote(stock_code, callback=self.data_callback.on_data)
                self.subscribed_stocks.clear()
            
            # 断开交易连接
            if self.xt_trader and self.is_trading_connected:
                # XtQuant可能没有提供显式的断开方法
                pass
            
            logger.info("XtQuant服务已停止")
            
        except Exception as e:
            logger.error(f"停止XtQuant服务失败: {e}, {traceback.format_exc()}")
    
    async def _init_data_connection(self):
        """初始化数据连接"""
        if xtdata is None:
            raise Exception("xtquant数据模块未安装，无法连接数据服务")
        
        # 在线程池中连接数据服务器
        loop = asyncio.get_event_loop()
        connect_result = await loop.run_in_executor(
            self.executor, xtdata.connect
        )
        if not connect_result:
            raise Exception("连接xtdata失败")
        
        # 创建数据回调
        self.data_callback = XtQuantDataCallback(self)
        self.is_data_connected = True
        
        logger.info("XtQuant数据连接成功")
    
    async def _init_trading_connection(self):
        """初始化交易连接"""
        if XtQuantTrader is None:
            raise Exception("xtquant交易模块未安装，无法连接交易服务")
        
        # 创建交易对象，使用实例特有的session_id
        self.xt_trader = XtQuantTrader(
            path=self.settings.xtquant.path,
            session=self.session_id
        )
        
        # 创建账户对象
        self.account = StockAccount(
            account_id=self.settings.xtquant.account_id,
            account_type=self.settings.xtquant.account_type
        )
        
        # 创建交易回调
        self.trading_callback = XtQuantTradingCallback(self)
        self.xt_trader.register_callback(self.trading_callback)
        
        # 在线程池中启动交易线程
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self.xt_trader.start)
        
        # 在线程池中建立连接
        connect_result = await loop.run_in_executor(
            self.executor, self.xt_trader.connect
        )
        if connect_result != 0:
            logger.warning(f"连接交易服务器失败，错误码: {connect_result}，可能QMT客户端未启动")
            self.is_trading_connected = False
            return
        
        # 在线程池中订阅回调
        subscribe_result = await loop.run_in_executor(
            self.executor, self.xt_trader.subscribe, self.account
        )
        if subscribe_result != 0:
            logger.warning(f"订阅交易回调失败，错误码: {subscribe_result}")
            self.is_trading_connected = False
            return
        
        self.is_trading_connected = True
        logger.info("XtQuant交易连接成功, is_trading_connected: " + str(self.is_trading_connected))
    
    # ==================== 数据获取功能 ====================
    
    async def get_stock_list(self, market: str = "ALL") -> List[Dict[str, Any]]:
        """获取股票列表"""
        try:
            if xtdata is None:
                raise Exception("XtQuant数据服务未连接，无法获取股票列表")
            
            # 获取股票列表
            if market == "SH":
                stocks = xtdata.get_stock_list_in_sector("上证A股")
            elif market == "SZ":
                stocks = xtdata.get_stock_list_in_sector("深证A股")
            else:
                sh_stocks = xtdata.get_stock_list_in_sector("上证A股")
                sz_stocks = xtdata.get_stock_list_in_sector("深证A股")
                stocks = sh_stocks + sz_stocks
            stock_list = []
            for stock_code in stocks:
                # 获取股票基本信息
                info = xtdata.get_instrument_detail(stock_code)
                if info:
                    stock_list.append({
                        "stock_code": stock_code,
                        "stock_name": info.get("InstrumentName", ""),
                        "market": "SH" if stock_code.endswith(".SH") else "SZ"
                    })
            
            return stock_list
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}, {traceback.format_exc()}")
            return []
    
    async def get_history_data(self, stock_codes: List[str], period: Period = Period.DAILY,
                              start_date: str = None, end_date: str = None,
                              count: int = 100) -> Dict[str, pd.DataFrame]:
        """获取历史数据"""
        try:
            if xtdata is None:
                raise Exception("XtQuant数据服务未连接，无法获取历史数据")
            
            result = {}
            
            # 转换时间格式：从 '%Y-%m-%d' 转换为 '%Y%m%d'
            xt_start_date = None
            xt_end_date = None
            if start_date:
                # 使用TimeUtils转换日期格式
                xt_start_date = TimeUtils.to_xtquant_date_format(start_date)
            
            if end_date:
                # 使用TimeUtils转换日期格式
                xt_end_date = TimeUtils.to_xtquant_date_format(end_date)
            
            # 转换周期参数
            period_map = {
                Period.TICK: "tick",
                Period.MIN1: "1m",
                Period.MIN5: "5m",
                Period.MIN15: "15m",
                Period.MIN30: "30m",
                Period.MIN60: "1h",
                Period.DAILY: "1d",
                Period.WEEKLY: "1w",
                Period.MONTHLY: "1M"
            }
            
            xt_period = period_map.get(period, "1d")
            
            for stock_code in stock_codes:
                try:
                    # 先下载补充历史数据
                    try:
                        if xt_start_date and xt_end_date:
                            # 使用指定时间范围下载数据
                            xtdata.download_history_data(
                                stock_code=stock_code,
                                period=xt_period,
                                start_time=xt_start_date,
                                end_time=xt_end_date
                            )
                        else:
                            # 增量下载最新数据
                            xtdata.download_history_data(
                                stock_code=stock_code,
                                period=xt_period,
                                incrementally=True
                            )
                    except Exception as download_e:
                        logger.warning(f"下载{stock_code}历史数据失败: {download_e}，继续使用现有数据")
                    
                    # 获取历史数据
                    if xt_start_date and xt_end_date:
                        data = xtdata.get_market_data(
                            stock_list=[stock_code],
                            period=xt_period,
                            start_time=xt_start_date,
                            end_time=xt_end_date
                        )
                    else:
                        data = xtdata.get_market_data(
                            stock_list=[stock_code],
                            period=xt_period,
                            count=count
                        )

                    if data and isinstance(data, dict):
                        # 根据API文档，返回格式为 { field1: DataFrame, field2: DataFrame, ... }
                        # DataFrame的index为stock_list，columns为time_list
                        try:
                            # 构建完整的DataFrame
                            stock_df_data = {}
                            
                            # 获取所有字段的数据
                            for field_name, field_df in data.items():
                                if field_df is not None and not field_df.empty and stock_code in field_df.index:
                                    # 获取该股票在该字段的时间序列数据
                                    stock_series = field_df.loc[stock_code]
                                    if not stock_series.empty:
                                        stock_df_data[field_name] = stock_series
                            
                            if stock_df_data:
                                # 将所有字段合并为一个DataFrame，时间作为索引
                                df = pd.DataFrame(stock_df_data)
                                
                                # 时间已经是索引，直接重命名索引名称
                                df.index.name = 'time'
                                
                                # 标准化列名映射
                                column_mapping = {
                                    'time': 'time',
                                    'open': 'open',
                                    'high': 'high', 
                                    'low': 'low',
                                    'close': 'close',
                                    'volume': 'volume',
                                    'amount': 'amount'
                                }
                                
                                # 重命名存在的列
                                existing_columns = {col: column_mapping.get(col, col) for col in df.columns if col in column_mapping}
                                df.rename(columns=existing_columns, inplace=True)
                                
                                # 确保时间索引格式正确
                                try:
                                    # 检查索引是否有重复值
                                    if df.index.duplicated().any():
                                        logger.warning(f"股票{stock_code}的时间数据存在重复，进行去重处理")
                                        # 保留第一个重复值，删除其他重复值
                                        df = df[~df.index.duplicated(keep='first')]
                                    
                                    # 转换时间格式
                                    # 处理混合格式的时间数据
                                    def convert_mixed_time(time_val):
                                        try:
                                            return TimeUtils.normalize_timestamp(time_val)
                                        except Exception as e:
                                            logger.warning(f"时间转换失败: {time_val}, 错误: {e}")
                                            return pd.NaT
                                    
                                    # 转换索引为时间格式
                                    df.index = df.index.map(convert_mixed_time)
                                    # 删除无效的时间数据
                                    df = df[df.index.notna()]
                                    
                                except Exception as time_error:
                                    logger.warning(f"股票{stock_code}时间转换遇到错误: {time_error}，尝试替代方案")
                                    # 如果时间转换失败，尝试多种备用方案
                                    try:
                                        # 使用TimeUtils工具类转换DataFrame的时间索引
                                        df = TimeUtils.convert_dataframe_time_index(df)
                                        
                                        # 移除无效的时间数据
                                        if df is not None and not df.empty:
                                            df = df[df.index.notna()]
                                        else:
                                            logger.warning(f"时间索引转换后数据为空")
                                            return None
                                        
                                        # 如果转换后没有有效数据，则跳过
                                        if df.empty:
                                            logger.error(f"股票{stock_code}时间转换后无有效数据，跳过该股票")
                                            continue
                                    except Exception as e:
                                        logger.error(f"股票{stock_code}时间转换完全失败: {e}, {traceback.format_exc()}，跳过该股票")
                                        continue
                                
                                result[stock_code] = df
                                logger.info(f"股票{stock_code}数据处理完成，shape: {df.shape}")
                            else:
                                logger.warning(f"股票{stock_code}在返回数据中未找到有效字段")
                                
                        except Exception as parse_e:
                            logger.error(f"解析股票{stock_code}数据失败: {parse_e}, {traceback.format_exc()}")
                            # 尝试备用解析方式（兼容旧格式）
                            logger.warning(f"股票{stock_code}使用标准解析失败，尝试备用解析方式")
                            # 如果标准解析失败，说明数据格式可能不符合预期，跳过该股票
                            continue
                    else:
                        logger.warning(f"股票{stock_code}未获取到有效数据，data类型: {type(data)}，data内容: {data}")
                    
                except Exception as e:
                    logger.error(f"获取{stock_code}历史数据失败: {e}, {traceback.format_exc()}")
                    continue
            
            return result
            
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}, {traceback.format_exc()}")
            return {}
    
    async def get_realtime_data(self, stock_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """获取实时数据"""
        try:
            # 检查是否为模拟模式
            if self.settings.xtquant.mock_mode or xtdata is None or not self.is_data_connected:
                logger.info("使用模拟实时数据")
                return await self._get_mock_realtime_data(stock_codes)
            
            # 在线程池中执行同步调用以避免阻塞
            import asyncio
            import concurrent.futures
            
            def get_tick_data():
                result = {}
                for stock_code in stock_codes:
                    try:
                        # 获取实时行情
                        quote = xtdata.get_full_tick([stock_code])
                        if quote and stock_code in quote:
                            tick_data = quote[stock_code]
                            result[stock_code] = {
                                "stock_code": stock_code,
                                "last_price": tick_data.get("lastPrice", 0),
                                "open": tick_data.get("open", 0),
                                "high": tick_data.get("high", 0),
                                "low": tick_data.get("low", 0),
                                "pre_close": tick_data.get("lastClose", 0),
                                "volume": tick_data.get("volume", 0),
                                "amount": tick_data.get("amount", 0),
                                "bid1": tick_data.get("bidPrice", [0])[0] if tick_data.get("bidPrice") else 0,
                                "ask1": tick_data.get("askPrice", [0])[0] if tick_data.get("askPrice") else 0,
                                "bid1_volume": tick_data.get("bidVol", [0])[0] if tick_data.get("bidVol") else 0,
                                "ask1_volume": tick_data.get("askVol", [0])[0] if tick_data.get("askVol") else 0,
                                "timestamp": datetime.now().isoformat()
                            }
                            
                            # 计算涨跌幅
                            if result[stock_code]["pre_close"] > 0:
                                change = result[stock_code]["last_price"] - result[stock_code]["pre_close"]
                                change_ratio = change / result[stock_code]["pre_close"]
                                result[stock_code]["change"] = change
                                result[stock_code]["change_ratio"] = change_ratio
                            else:
                                result[stock_code]["change"] = 0
                                result[stock_code]["change_ratio"] = 0
                        
                    except Exception as e:
                        logger.error(f"获取{stock_code}实时数据失败: {e}")
                        continue
                return result
            
            # 在线程池中执行
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(executor, get_tick_data)
            
            return result
            
        except Exception as e:
            logger.error(f"获取实时数据失败: {e}, {traceback.format_exc()}")
            return {}
    
    async def _get_mock_realtime_data(self, stock_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """获取模拟实时数据"""
        import random
        result = {}
        
        for stock_code in stock_codes:
            # 生成模拟数据
            base_price = 10.0 + random.uniform(-5, 5)
            change_ratio = random.uniform(-0.05, 0.05)  # -5%到5%的涨跌幅
            current_price = base_price * (1 + change_ratio)
            
            result[stock_code] = {
                "stock_code": stock_code,
                "last_price": round(current_price, 2),
                "open": round(base_price * (1 + random.uniform(-0.02, 0.02)), 2),
                "high": round(current_price * (1 + random.uniform(0, 0.03)), 2),
                "low": round(current_price * (1 - random.uniform(0, 0.03)), 2),
                "pre_close": round(base_price, 2),
                "volume": random.randint(100000, 1000000),
                "amount": random.randint(1000000, 10000000),
                "bid1": round(current_price * 0.999, 2),
                "ask1": round(current_price * 1.001, 2),
                "bid1_volume": random.randint(100, 1000),
                "ask1_volume": random.randint(100, 1000),
                "change": round(current_price - base_price, 2),
                "change_ratio": round(change_ratio, 4),
                "timestamp": datetime.now().isoformat()
            }
        
        return result
    
    async def get_historical_data(self, stock_code: str, start_date: str, 
                                end_date: str, period: str = "1d") -> Dict[str, Any]:
        """获取历史数据"""
        try:
            # 检查是否为模拟模式
            if self.settings.xtquant.mock_mode or xtdata is None or not self.data_connected:
                logger.info("使用模拟历史数据")
                return await self._get_mock_historical_data(stock_code, start_date, end_date, period)
            
            # 在线程池中执行同步调用以避免阻塞
            import asyncio
            import concurrent.futures
            
            def get_history_data():
                try:
                    # 转换周期参数
                    period_map = {
                        "1d": "1d",
                        "1m": "1m",
                        "5m": "5m",
                        "15m": "15m",
                        "30m": "30m",
                        "60m": "1h"
                    }
                    xt_period = period_map.get(period, "1d")
                    
                    # 获取历史数据
                    df = xtdata.get_market_data(
                        stock_list=[stock_code],
                        period=xt_period,
                        start_time=start_date,
                        end_time=end_date
                    )
                    
                    if df is not None and not df.empty:
                        # 转换为标准格式
                        data = []
                        for index, row in df.iterrows():
                            data.append({
                                "trade_date": index.strftime("%Y-%m-%d") if hasattr(index, 'strftime') else str(index),
                                "open_price": float(row.get("open", 0)),
                                "high_price": float(row.get("high", 0)),
                                "low_price": float(row.get("low", 0)),
                                "close_price": float(row.get("close", 0)),
                                "volume": int(row.get("volume", 0)),
                                "amount": float(row.get("amount", 0))
                            })
                        
                        return {"success": True, "data": data}
                    else:
                        return {"success": False, "error": "未获取到数据"}
                        
                except Exception as e:
                    logger.error(f"获取历史数据失败: {e}")
                    return {"success": False, "error": str(e)}
            
            # 在线程池中执行
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(executor, get_history_data)
            
            return result
            
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}, {traceback.format_exc()}")
            return {"success": False, "error": str(e)}
    
    async def _get_mock_historical_data(self, stock_code: str, start_date: str, 
                                      end_date: str, period: str = "1d") -> Dict[str, Any]:
        """获取模拟历史数据"""
        import random
        from datetime import datetime, timedelta
        
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            data = []
            current_dt = start_dt
            base_price = 10.0 + random.uniform(-5, 5)
            
            while current_dt <= end_dt:
                # 跳过周末
                if current_dt.weekday() < 5:
                    # 生成模拟价格数据
                    change_ratio = random.uniform(-0.03, 0.03)
                    open_price = base_price * (1 + random.uniform(-0.01, 0.01))
                    close_price = base_price * (1 + change_ratio)
                    high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.02))
                    low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.02))
                    
                    data.append({
                        "trade_date": current_dt.strftime("%Y-%m-%d"),
                        "open_price": round(open_price, 2),
                        "high_price": round(high_price, 2),
                        "low_price": round(low_price, 2),
                        "close_price": round(close_price, 2),
                        "volume": random.randint(100000, 1000000),
                        "amount": random.randint(1000000, 10000000)
                    })
                    
                    base_price = close_price  # 下一天的基准价格
                
                current_dt += timedelta(days=1)
            
            return {"success": True, "data": data}
            
        except Exception as e:
            logger.error(f"生成模拟历史数据失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def subscribe_realtime_data(self, stock_codes: List[str], 
                                     callback: Optional[Callable] = None):
        """订阅实时数据"""
        try:
            if xtdata is None:
                logger.warning("xtdata未安装，无法订阅实时数据")
                return
            
            # 注册回调函数
            if callback:
                self.realtime_data_callbacks.append(callback)
            
            for stock_code in stock_codes:
                if stock_code not in self.subscribed_stocks:
                    # 订阅实时行情
                    xtdata.subscribe_quote(
                        stock_code, 
                        period="tick", 
                        callback=self.data_callback.on_data
                    )
                    self.subscribed_stocks.add(stock_code)
                    logger.info(f"订阅{stock_code}实时数据成功")
            
        except Exception as e:
            logger.error(f"订阅实时数据失败: {e}, {traceback.format_exc()}")
    
    async def unsubscribe_realtime_data(self, stock_codes: List[str]):
        """取消订阅实时数据"""
        try:
            if xtdata is None:
                return
            
            for stock_code in stock_codes:
                if stock_code in self.subscribed_stocks:
                    xtdata.unsubscribe_quote(
                        stock_code, 
                        callback=self.data_callback.on_data
                    )
                    self.subscribed_stocks.remove(stock_code)
                    logger.info(f"取消订阅{stock_code}实时数据")
            
        except Exception as e:
            logger.error(f"取消订阅实时数据失败: {e}, {traceback.format_exc()}")
    
    # ==================== 交易功能 ====================
    
    async def place_order(self, stock_code: str, order_type: str, volume: int,
                         price: Optional[float] = None, price_type: str = "LIMIT",
                         strategy_name: str = "manual", remark: str = "") -> Optional[str]:
        """下单"""
        try:
            if not self.is_trading_connected or self.xt_trader is None:
                logger.warning("交易连接未建立，使用模拟下单")
                return f"SIM_{int(time.time() * 1000)}"
            
            # 转换订单类型
            xt_order_type = xtconstant.STOCK_BUY if order_type.upper() == "BUY" else xtconstant.STOCK_SELL
            
            # 转换价格类型
            if price_type.upper() == "MARKET":
                xt_price_type = xtconstant.MARKET_PRICE
                if price is None:
                    price = 0  # 市价单价格设为0
            else:
                xt_price_type = xtconstant.FIX_PRICE
                if price is None:
                    # 获取当前价格
                    realtime_data = await self.get_realtime_data([stock_code])
                    if stock_code in realtime_data:
                        price = realtime_data[stock_code]["last_price"]
                    else:
                        raise Exception(f"无法获取{stock_code}当前价格")
            
            # 下单
            order_id = self.xt_trader.order_stock(
                acc=self.account,
                stock_code=stock_code,
                order_type=xt_order_type,
                order_volume=volume,
                price_type=xt_price_type,
                price=price,
                strategy_name=strategy_name,
                order_remark=remark
            )
            
            if order_id <= 0:
                raise Exception(f"下单失败，订单ID: {order_id}")
            
            logger.info(f"下单成功: {order_id}, {stock_code}, {order_type}, {volume}股, 价格: {price}")
            return str(order_id)
            
        except Exception as e:
            logger.error(f"下单失败: {e}, {traceback.format_exc()}")
            return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        try:
            if not self.is_trading_connected or self.xt_trader is None:
                logger.warning("交易连接未建立，使用模拟撤单")
                return True
            
            result = self.xt_trader.cancel_order_stock(self.account, int(order_id))
            if result != 0:
                logger.error(f"撤单失败，错误码: {result}")
                return False
            
            logger.info(f"撤单成功: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"撤单失败: {e}, {traceback.format_exc()}")
            return False
    
    async def get_account_asset(self) -> Optional[Dict[str, Any]]:
        """获取账户资产"""
        try:
            if not self.is_trading_connected or self.xt_trader is None:
                raise Exception("XtQuant交易服务未连接，无法获取账户资产, is_trading_connected: " + str(self.is_trading_connected) + ", self.xt_trader: " + str(self.xt_trader))
            
            asset = self.xt_trader.query_stock_asset(self.account)
            if asset:
                return {
                    "total_asset": getattr(asset, 'total_asset', 0),
                    "cash": getattr(asset, 'cash', 0),
                    "market_value": getattr(asset, 'market_value', 0),
                    "frozen_cash": getattr(asset, 'frozen_cash', 0),
                    "available_cash": getattr(asset, 'available_cash', 0),
                    "profit_loss": getattr(asset, 'profit_loss', 0),
                    "profit_loss_ratio": getattr(asset, 'profit_loss_ratio', 0)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取账户资产失败: {e}, {traceback.format_exc()}")
            return None
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """获取持仓"""
        try:
            if not self.is_trading_connected or self.xt_trader is None:
                raise Exception("XtQuant交易服务未连接，无法获取持仓信息")
            
            positions = []
            xt_positions = self.xt_trader.query_stock_positions(self.account)
            
            for pos in xt_positions:
                # 获取当前价格
                current_price = 0
                try:
                    realtime_data = await self.get_realtime_data([pos.stock_code])
                    if pos.stock_code in realtime_data:
                        current_price = realtime_data[pos.stock_code]["last_price"]
                except:
                    pass
                
                volume = getattr(pos, 'volume', 0)
                avg_price = getattr(pos, 'avg_price', 0)
                market_value = volume * current_price if current_price > 0 else getattr(pos, 'market_value', 0)
                cost_value = volume * avg_price
                profit_loss = market_value - cost_value
                profit_loss_ratio = profit_loss / cost_value if cost_value > 0 else 0
                
                positions.append({
                    "stock_code": pos.stock_code,
                    "stock_name": "",  # 需要从其他地方获取股票名称
                    "volume": volume,
                    "available_volume": getattr(pos, 'available_volume', volume),
                    "avg_price": avg_price,
                    "current_price": current_price,
                    "market_value": market_value,
                    "cost_value": cost_value,
                    "profit_loss": profit_loss,
                    "profit_loss_ratio": profit_loss_ratio
                })
            
            return positions
            
        except Exception as e:
            logger.error(f"获取持仓失败: {e}, {traceback.format_exc()}")
            return []
    
    async def get_orders(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取订单列表"""
        try:
            if not self.is_trading_connected or self.xt_trader is None:
                raise Exception("XtQuant交易服务未连接，无法获取订单信息")
            
            orders = []
            xt_orders = self.xt_trader.query_stock_orders(self.account)
            
            for order in xt_orders[-limit:]:
                orders.append({
                    "order_id": str(getattr(order, 'order_id', '')),
                    "stock_code": getattr(order, 'stock_code', ''),
                    "stock_name": "",  # 需要从其他地方获取股票名称
                    "order_type": "BUY" if getattr(order, 'order_type', 0) == xtconstant.STOCK_BUY else "SELL",
                    "order_price": getattr(order, 'price', 0),
                    "order_volume": getattr(order, 'order_volume', 0),
                    "traded_volume": getattr(order, 'traded_volume', 0),
                    "order_status": self._convert_order_status(getattr(order, 'order_status', 0)),
                    "order_time": getattr(order, 'order_time', datetime.now()).isoformat() if hasattr(getattr(order, 'order_time', None), 'isoformat') else str(getattr(order, 'order_time', ''))
                })
            
            return orders
            
        except Exception as e:
            logger.error(f"获取订单列表失败: {e}, {traceback.format_exc()}")
            return []
    
    async def get_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取成交记录"""
        try:
            if not self.is_trading_connected or self.xt_trader is None:
                raise Exception("XtQuant交易服务未连接，无法获取成交记录")
            
            trades = []
            xt_trades = self.xt_trader.query_stock_trades(self.account)
            
            for trade in xt_trades[-limit:]:
                trades.append({
                    "trade_id": str(getattr(trade, 'trade_id', '')),
                    "order_id": str(getattr(trade, 'order_id', '')),
                    "stock_code": getattr(trade, 'stock_code', ''),
                    "stock_name": "",  # 需要从其他地方获取股票名称
                    "trade_type": "BUY" if getattr(trade, 'order_type', 0) == xtconstant.STOCK_BUY else "SELL",
                    "trade_price": getattr(trade, 'traded_price', 0),
                    "trade_volume": getattr(trade, 'traded_volume', 0),
                    "trade_amount": getattr(trade, 'traded_amount', 0),
                    "trade_time": getattr(trade, 'trade_time', datetime.now()).isoformat() if hasattr(getattr(trade, 'trade_time', None), 'isoformat') else str(getattr(trade, 'trade_time', ''))
                })
            
            return trades
            
        except Exception as e:
            logger.error(f"获取成交记录失败: {e}, {traceback.format_exc()}")
            return []
    
    # ==================== 回调处理 ====================
    
    async def _handle_realtime_data(self, stock_code: str, data: Any):
        """处理实时数据推送"""
        try:
            # 缓存到本地缓存
            cache_key = f"realtime:{stock_code}"
            await self.cache_client.setex(
                cache_key, 
                300,  # 5分钟过期
                str(data)
            )
            
            # 调用注册的回调函数
            for callback in self.realtime_data_callbacks:
                try:
                    await callback(stock_code, data)
                except Exception as e:
                    logger.error(f"实时数据回调函数执行失败: {e}, {traceback.format_exc()}")
            
        except Exception as e:
            logger.error(f"处理实时数据推送失败: {e}, {traceback.format_exc()}")
    
    async def _handle_order_callback(self, order):
        """处理订单回调"""
        try:
            order_data = {
                "order_id": str(getattr(order, 'order_id', '')),
                "stock_code": getattr(order, 'stock_code', ''),
                "order_status": self._convert_order_status(getattr(order, 'order_status', 0)),
                "traded_volume": getattr(order, 'traded_volume', 0),
                "order_sysid": getattr(order, 'order_sysid', '')
            }
            
            # 调用注册的回调函数
            for callback in self.order_callbacks:
                try:
                    await callback(order_data)
                except Exception as e:
                    logger.error(f"订单回调函数执行失败: {e}, {traceback.format_exc()}")
            
        except Exception as e:
            logger.error(f"处理订单回调失败: {e}, {traceback.format_exc()}")
    
    async def _handle_trade_callback(self, trade):
        """处理成交回调"""
        try:
            trade_data = {
                "trade_id": str(getattr(trade, 'trade_id', '')),
                "order_id": str(getattr(trade, 'order_id', '')),
                "stock_code": getattr(trade, 'stock_code', ''),
                "traded_volume": getattr(trade, 'traded_volume', 0),
                "traded_price": getattr(trade, 'traded_price', 0),
                "account_id": getattr(trade, 'account_id', '')
            }
            
            # 调用注册的回调函数
            for callback in self.trade_callbacks:
                try:
                    await callback(trade_data)
                except Exception as e:
                    logger.error(f"成交回调函数执行失败: {e}, {traceback.format_exc()}")
            
        except Exception as e:
            logger.error(f"处理成交回调失败: {e}, {traceback.format_exc()}")
    
    async def _handle_order_error(self, order_error):
        """处理订单错误"""
        try:
            await self.notification_service.send_system_error_notification(
                error_type="订单错误",
                error_message=f"订单{order_error.order_id}错误: {order_error.error_msg} (错误码: {order_error.error_id})",
                module="XtQuantService"
            )
        except Exception as e:
            logger.error(f"处理订单错误失败: {e}, {traceback.format_exc()}")
    
    # ==================== 工具方法 ====================
    
    def _convert_order_status(self, status: int) -> str:
        """转换订单状态"""
        status_map = {
            0: "PENDING",      # 待成交
            1: "PARTIAL_FILLED", # 部分成交
            2: "FILLED",       # 全部成交
            3: "CANCELLED",    # 已撤销
            4: "REJECTED",     # 已拒绝
            5: "ERROR"         # 错误
        }
        return status_map.get(status, "UNKNOWN")
    
    def _generate_mock_history_data(self, stock_codes: List[str], count: int) -> Dict[str, pd.DataFrame]:
        """生成模拟历史数据"""
        result = {}
        
        for stock_code in stock_codes:
            # 生成模拟数据
            dates = pd.date_range(end=datetime.now(), periods=count, freq='D')
            base_price = 10.0
            
            data = []
            for i, date in enumerate(dates):
                price = base_price + (i % 10 - 5) * 0.1
                data.append({
                    'open': price,
                    'high': price * 1.02,
                    'low': price * 0.98,
                    'close': price,
                    'volume': 1000000 + (i % 100) * 10000,
                    'amount': price * (1000000 + (i % 100) * 10000)
                })
            
            df = pd.DataFrame(data, index=dates)
            result[stock_code] = df
        
        return result
    
    def _generate_mock_realtime_data(self, stock_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """生成模拟实时数据"""
        result = {}
        
        for stock_code in stock_codes:
            result[stock_code] = {
                "stock_code": stock_code,
                "last_price": 10.52,
                "open": 10.50,
                "high": 10.68,
                "low": 10.42,
                "pre_close": 10.48,
                "change": 0.04,
                "change_ratio": 0.0038,
                "volume": 12345678,
                "amount": 129876543.21,
                "bid1": 10.51,
                "ask1": 10.53,
                "bid1_volume": 100,
                "ask1_volume": 200,
                "timestamp": datetime.now().isoformat()
            }
        
        return result
    
    # ==================== 回调注册 ====================
    
    def register_realtime_data_callback(self, callback: Callable):
        """注册实时数据回调"""
        if callback not in self.realtime_data_callbacks:
            self.realtime_data_callbacks.append(callback)
    
    def register_order_callback(self, callback: Callable):
        """注册订单回调"""
        if callback not in self.order_callbacks:
            self.order_callbacks.append(callback)
    
    def register_trade_callback(self, callback: Callable):
        """注册成交回调"""
        if callback not in self.trade_callbacks:
            self.trade_callbacks.append(callback)
    
    def unregister_realtime_data_callback(self, callback: Callable):
        """取消注册实时数据回调"""
        if callback in self.realtime_data_callbacks:
            self.realtime_data_callbacks.remove(callback)
    
    def unregister_order_callback(self, callback: Callable):
        """取消注册订单回调"""
        if callback in self.order_callbacks:
            self.order_callbacks.remove(callback)
    
    def unregister_trade_callback(self, callback: Callable):
        """取消注册成交回调"""
        if callback in self.trade_callbacks:
            self.trade_callbacks.remove(callback)