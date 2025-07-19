# -*- coding: utf-8 -*-
"""
数据服务模块
"""
import json
import traceback
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, and_, desc
from core.time_utils import TimeUtils

from config import get_settings
from core.database import get_db, StockData
from core.cache_adapter import get_cache_client
from core.duckdb_adapter import DuckDBAdapter
from services.notification_service import NotificationService
from services.xtquant_service import XtQuantService, Period


class DataService:
    """数据服务 - 单例模式"""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        # 防止重复初始化
        if self._initialized:
            return
            
        self.settings = get_settings()
        self.cache_client = get_cache_client()
        self.notification_service = NotificationService()
        self.xtquant_service = XtQuantService()
        self.is_running = False
        self.data_update_task = None
        
        # 初始化DuckDB适配器（延迟到start方法中异步执行）
        self.duckdb = None
        self.db_initialized = False
        
        # 数据缓存配置
        self.cache_expire_time = 300  # 5分钟缓存过期
        
        # 支持的股票池
        self.stock_pools = {
            "沪深300": "000300.SH",
            "中证500": "000905.SH",
            "创业板指": "399006.SZ",
            "科创50": "000688.SH"
        }
        
        # 标记为已初始化
        self._initialized = True
    
    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置单例实例（主要用于测试）"""
        if cls._instance is not None:
            cls._instance = None
    
    async def _init_database(self):
        """异步初始化数据库"""
        if self.db_initialized:
            return
            
        try:
            # 在模拟模式下跳过数据库初始化
            if self.settings.simulation_mode:
                logger.info("模拟模式：跳过数据库初始化")
                self.duckdb = None
                self.db_initialized = True
                return
            
            loop = asyncio.get_event_loop()
            
            # 在线程池中执行数据库初始化
            def init_db():
                # 初始化SQLAlchemy数据库表
                from core.database import init_database, get_duckdb_connection
                from core.duckdb_adapter import init_duckdb
                init_database()
                
                # 使用SQLAlchemy的数据库连接
                try:
                    duckdb_conn = get_duckdb_connection()
                    self.duckdb = DuckDBAdapter(connection=duckdb_conn)
                except Exception as e:
                    logger.warning(f"无法获取SQLAlchemy连接，使用独立连接: {e}")
                    # 备选方案：使用独立的DuckDB连接
                    if self.settings.database.memory:
                        self.duckdb = DuckDBAdapter(':memory:')
                    else:
                        db_path = self.settings.database.path
                        self.duckdb = DuckDBAdapter(db_path)
                
                # DuckDB表创建已移至统一的 core.database 模块
                logger.info("DuckDB表创建已由统一数据库模块处理")
                
                return True
            
            await loop.run_in_executor(None, init_db)
            
            # 初始化日线数据表（在主线程中执行）
            if self.duckdb:
                try:
                    self._init_daily_data_table()
                    logger.info("日线数据表初始化完成")
                except Exception as e:
                    logger.warning(f"日线数据表初始化失败: {e}")
            
            self.db_initialized = True
            logger.info("DuckDB数据库异步初始化成功")
            
        except Exception as e:
            logger.warning(f"DuckDB初始化失败: {e}，将使用模拟模式")
            self.duckdb = None
            self.db_initialized = False
    
    async def start(self):
        """启动数据服务"""
        if self.is_running:
            return
        
        logger.info("启动数据服务...")
        
        try:
            # 异步初始化数据库
            await self._init_database()
            logger.info("数据库初始化完成")
            
            # 检查是否为模拟模式
            if not self.settings.simulation_mode:
                # 启动XtQuant数据服务（带超时）
                try:
                    await asyncio.wait_for(self.xtquant_service.start(), timeout=30.0)
                    logger.info("XtQuant数据服务启动成功")
                except asyncio.TimeoutError:
                    logger.error("XtQuant数据服务启动超时")
                    raise
                except Exception as e:
                    logger.error(f"XtQuant数据服务启动失败: {e}")
                    raise
            else:
                logger.info("模拟模式：跳过XtQuant数据服务启动")
            
            self.is_running = True
            logger.info("数据服务启动成功")
            
            # 延迟启动数据更新循环
            async def delayed_start_loop():
                await asyncio.sleep(2)  # 等待2秒后启动
                logger.info("准备启动数据更新循环...")
                self.data_update_task = asyncio.create_task(self._data_update_loop())
                logger.info("数据更新循环任务已创建")
            
            asyncio.create_task(delayed_start_loop())
            
        except Exception as e:
            logger.error(f"启动数据服务失败: {e}, {traceback.format_exc()}")
            await self.notification_service.send_system_error_notification(
                error_type="数据服务启动失败",
                error_message=str(e),
                module="DataService"
            )
            raise
    
    async def stop(self):
        """停止数据服务"""
        try:
            logger.info("停止数据服务...")
            
            # 停止数据更新任务
            if self.data_update_task:
                self.data_update_task.cancel()
                try:
                    await self.data_update_task
                except asyncio.CancelledError:
                    pass
            
            # 停止XtQuant数据服务
            await self.xtquant_service.stop()
            
            logger.info("数据服务已停止")
            
        except Exception as e:
            logger.error(f"停止数据服务失败: {e}, {traceback.format_exc()}")
    
    async def _data_update_loop(self):
        """数据更新循环"""
        logger.info("数据更新循环开始运行")
        while self.is_running:
            try:
                logger.debug("数据更新循环：开始新的循环")
                
                # 检查是否为模拟模式
                if self.settings.simulation_mode:
                    logger.debug("模拟模式：跳过数据更新")
                    await asyncio.sleep(60)  # 1分钟等待一次
                    continue
                
                # 检查是否为交易时间
                if self._is_trading_time():
                    logger.debug("当前为交易时间，更新实时数据")
                    await self._update_realtime_data()
                else:
                    # 非交易时间，更新历史数据
                    logger.debug("当前为非交易时间，更新历史数据")
                    await self._update_historical_data()
                
                # 等待下次更新
                logger.debug("数据更新完成，等待下次更新")
                await asyncio.sleep(60)  # 1分钟更新一次
                
            except Exception as e:
                logger.error(f"数据更新循环异常: {e}, {traceback.format_exc()}")
                await self.notification_service.send_system_error_notification(
                    error_type="数据更新异常",
                    error_message=str(e),
                    module="DataService"
                )
                await asyncio.sleep(60)
        logger.info("数据更新循环已停止")
    
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
    
    async def get_stock_list(self, market: str = None) -> List[Dict[str, Any]]:
        """获取股票列表
        
        Args:
            market: 市场代码，如SH、SZ，None表示获取所有市场
        """
        try:
            # 构建缓存键
            cache_key = f"stock_list:{market or 'ALL'}"
            cached_data = await self.cache_client.get(cache_key)
            if cached_data:
                logger.debug(f"从缓存获取{market or '全部'}市场股票列表,{type(cached_data)}")
                try:
                    return json.loads(cached_data)
                except:
                    logger.error(f"从缓存获取{market or '全部'}市场股票列表,解析失败:{traceback.format_exc()}")
                    return cached_data
            
            # 从XtQuant获取
            stock_result = await self.xtquant_service.get_stock_list()
            if stock_result:
                stocks = stock_result
                
                # 根据市场过滤
                if market and market != "ALL":
                    stocks = [stock for stock in stocks if stock.get("market") == market]
                
                # 缓存30分钟
                await self.cache_client.set(cache_key, stocks, expire=1800)
                logger.info(f"获取{market or '全部'}市场股票列表成功，共{len(stocks)}只股票")
                return stocks
            else:
                logger.error("获取股票列表失败")
                return []
                
        except Exception as e:
            logger.error(f"获取股票列表异常: {e}, {traceback.format_exc()}")
            return []
    
    async def get_realtime_data(self, stock_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """获取实时行情数据"""
        try:
            # 使用XtQuantService获取实时数据
            realtime_result = await self.xtquant_service.get_realtime_data(stock_codes)
            
            if realtime_result["success"]:
                result = realtime_result["data"]
                
                # 缓存数据
                for stock_code, data in result.items():
                    cache_key = f"realtime:{stock_code}"
                    await self.cache_client.set(cache_key, data, expire=30)  # 30秒缓存
                
                return result
            else:
                logger.error(f"获取实时数据失败: {realtime_result.get('error', '未知错误')}")
                return {}
                
        except Exception as e:
            logger.error(f"获取实时数据失败: {e}, {traceback.format_exc()}")
            return {}

    
    async def get_historical_data(self, stock_code: str, start_date: str, 
                                end_date: str, period: str = "1d") -> pd.DataFrame:
        """获取历史行情数据"""
        cache_key = f"historical:{stock_code}:{start_date}:{end_date}:{period}"
        
        # 尝试从缓存获取
        cached_data = await self.cache_client.get(cache_key)
        if cached_data:
            return pd.DataFrame(cached_data)
        
        try:
            # 使用XtQuantService获取历史数据
            historical_result = await self.xtquant_service.get_historical_data(
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date,
                period=period
            )
            
            if historical_result["success"]:
                data = historical_result["data"]
                df = pd.DataFrame(data)
                
                # 缓存数据
                await self.cache_client.set(cache_key, data, expire=3600)  # 1小时缓存
                
                return df
            else:
                logger.error(f"获取{stock_code}历史数据失败: {historical_result.get('error', '未知错误')}")
                return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"获取{stock_code}历史数据失败: {e}, {traceback.format_exc()}")
            return pd.DataFrame()
    
    def _init_daily_data_table(self):
        """初始化日线数据表 - 已移除，使用统一的 core.database 模块"""
        # 表创建逻辑已移至 core.database.create_tables_manually()
        # 这里不再重复创建表，避免冲突
        logger.info("数据服务：跳过表创建，使用统一数据库模块")
    
    async def get_stock_daily_data(self, stock_code: str, start_date: str = None, 
                                 end_date: str = None, save_to_db: bool = True) -> pd.DataFrame:
        """获取指定股票的全部日线数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式YYYY-MM-DD，默认为None（获取全部数据）
            end_date: 结束日期，格式YYYY-MM-DD，默认为今天
            save_to_db: 是否保存到数据库，默认True
            
        Returns:
            pandas.DataFrame: 日线数据
        """
        try:
            logger.info(f"开始获取{stock_code}的日线数据")
            
            # 如果没有指定结束日期，使用今天
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            # 如果没有指定开始日期，尝试从数据库获取最新日期
            if start_date is None:
                latest_date = self._get_latest_date_from_db(stock_code)
                if latest_date:
                    # 从最新日期的下一天开始获取（增量更新）
                    try:
                        start_date = (latest_date + timedelta(days=1)).strftime('%Y-%m-%d')
                        logger.info(f"{stock_code}数据库中最新日期: {latest_date}, 从{start_date}开始增量更新")
                    except:
                        logger.error(f"{stock_code}数据库中最新日期: {latest_date} 转换失败")
                else:
                    # 如果数据库中没有数据，从XtQuant获取全部数据
                    start_date = '1990-01-01'
                    logger.info(f"{stock_code}数据库中没有数据，从{start_date}开始获取全部数据")
            
            # 检查日期范围
            if start_date >= end_date:
                logger.info(f"{stock_code}无需更新，数据已是最新")
                return self._get_data_from_db(stock_code, start_date, end_date)
            
            # 从XtQuant获取数据
            history_data = await self.xtquant_service.get_history_data(
                stock_codes=[stock_code],
                period=Period.DAILY,
                start_date=start_date,
                end_date=end_date
            )
            
            if stock_code not in history_data or history_data[stock_code].empty:
                logger.warning(f"未获取到{stock_code}的数据")
                return pd.DataFrame()
            
            logger.info(f"before copy, 获取到{stock_code}的{len(history_data[stock_code])}条数据")
            df = history_data[stock_code].copy()
            # 数据预处理
            logger.info(f"before preprocess, {stock_code}获取到{len(df)}条数据")
            df = self._preprocess_daily_data(df, stock_code)
            logger.info(f"after preprocess, {stock_code}获取到{len(df)}条数据")
            # 保存到数据库
            if save_to_db and not df.empty:
                saved_count = await self._save_daily_data_to_db(df, stock_code)
                logger.info(f"成功保存{stock_code}的{saved_count}条日线数据")
            
            return df
            
        except Exception as e:
            logger.error(f"获取{stock_code}日线数据失败: {e}, {traceback.format_exc()}")
            return pd.DataFrame()
    
    def _get_latest_date_from_db(self, stock_code: str) -> Optional[datetime]:
        """从数据库获取指定股票的最新日期"""
        try:
            sql = """
            SELECT MAX(trade_date) as latest_date 
            FROM daily_stock_data 
            WHERE stock_code = ?
            """
            result = self.duckdb.fetchone(sql, (stock_code,))
            
            if result and result[0]:
                return datetime.strptime(str(result[0]), '%Y-%m-%d')
            return None
            
        except Exception as e:
            logger.error(f"获取{stock_code}最新日期失败: {e}, {traceback.format_exc()}")
            return None
    
    def _get_data_from_db(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """从数据库获取数据"""
        try:
            sql = """
            SELECT stock_code, trade_date, open_price, high_price, low_price, 
                   close_price, volume, amount, turnover_rate, pe_ratio, pb_ratio
            FROM daily_stock_data 
            WHERE stock_code = ? AND trade_date BETWEEN ? AND ?
            ORDER BY trade_date
            """
            return self.duckdb.fetchdf(sql, (stock_code, start_date, end_date))
            
        except Exception as e:
            logger.error(f"从数据库获取{stock_code}数据失败: {e}, {traceback.format_exc()}")
            return pd.DataFrame()
    
    def _preprocess_daily_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """预处理日线数据"""
        try:
            # 检查是否需要重置索引，避免重复插入time列
            if 'time' not in df.columns and df.index.name == 'time':
                # 重置索引，将时间列转为普通列
                df = df.reset_index()
            elif df.index.name == 'time':
                # 如果已经有time列但索引仍是time，只重置索引不插入新列
                df = df.reset_index(drop=True)
            
            # 添加股票代码
            df['stock_code'] = stock_code
            
            # 重命名列
            column_mapping = {
                'time': 'trade_date',
                'open': 'open_price',
                'high': 'high_price', 
                'low': 'low_price',
                'close': 'close_price'
            }
            df = df.rename(columns=column_mapping)
            
            
            # 使用TimeUtils工具类处理时间格式
            try:
                # 转换trade_date列为标准日期格式
                df['trade_date'] = df['trade_date'].apply(TimeUtils.to_trade_date)
                
                # 移除转换失败的行
                df = df.dropna(subset=['trade_date'])
                
                if df.empty:
                    logger.error(f"股票{stock_code}时间转换后无有效数据")
                    return pd.DataFrame()
                    
                # 验证时间范围的合理性
                valid_dates = df['trade_date'].apply(lambda x: TimeUtils.validate_time_range(x))
                if not valid_dates.all():
                    invalid_count = (~valid_dates).sum()
                    # logger.warning(f"股票{stock_code}有{invalid_count}条时间数据超出合理范围，已过滤")
                    df = df[valid_dates]
            except Exception as e:
                logger.error(f"股票{stock_code}时间转换失败: {e}, {traceback.format_exc()}")
                return pd.DataFrame()
            
            # 添加默认值
            if 'turnover_rate' not in df.columns:
                df['turnover_rate'] = None
            if 'pe_ratio' not in df.columns:
                df['pe_ratio'] = None
            if 'pb_ratio' not in df.columns:
                df['pb_ratio'] = None
            
            # 选择需要的列
            columns = ['stock_code', 'trade_date', 'open_price', 'high_price', 
                      'low_price', 'close_price', 'volume', 'amount', 
                      'turnover_rate', 'pe_ratio', 'pb_ratio']
            
            df = df[columns]
            # 去除重复数据
            df = df.drop_duplicates(subset=['stock_code', 'trade_date'])
            return df
            
        except Exception as e:
            logger.error(f"预处理{stock_code}数据失败: {e}, {traceback.format_exc()}")
            return pd.DataFrame()
    
    async def _save_daily_data_to_db(self, df: pd.DataFrame, stock_code: str) -> int:
        """保存日线数据到数据库（批量优化版本）"""
        try:
            if df.empty:
                return 0
            
            # 开始事务
            self.duckdb.execute("BEGIN TRANSACTION")
            
            try:
                # 批量删除已存在的记录
                if len(df) > 0:
                    # 构建删除条件
                    delete_conditions = []
                    delete_params = []
                    for _, row in df.iterrows():
                        delete_conditions.append("(stock_code = ? AND trade_date = ?)")
                        delete_params.extend([row['stock_code'], row['trade_date']])
                    
                    if delete_conditions:
                        delete_sql = f"""
                        DELETE FROM daily_stock_data 
                        WHERE {' OR '.join(delete_conditions)}
                        """
                        self.duckdb.execute(delete_sql, delete_params)
                
                # 批量插入新记录
                insert_sql = """
                INSERT INTO daily_stock_data 
                (stock_code, trade_date, open_price, high_price, low_price, 
                 close_price, volume, amount, turnover_rate, pe_ratio, pb_ratio, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW())
                """
                
                # 准备批量插入数据
                insert_data = []
                for _, row in df.iterrows():
                    insert_data.append((
                        row['stock_code'],
                        row['trade_date'],
                        # A股价格数据：保持原始精度，让数据库DECIMAL(8,2)自动处理
                        float(row['open_price']) if pd.notna(row['open_price']) else None,
                        float(row['high_price']) if pd.notna(row['high_price']) else None,
                        float(row['low_price']) if pd.notna(row['low_price']) else None,
                        float(row['close_price']) if pd.notna(row['close_price']) else None,
                        # 成交量：整数类型
                        int(row['volume']) if pd.notna(row['volume']) else None,
                        # 成交金额：保持原始精度
                        float(row['amount']) if pd.notna(row['amount']) else None,
                        # 换手率：保持更高精度用于精确计算
                        float(row['turnover_rate']) if pd.notna(row['turnover_rate']) else None,
                        # 估值指标：保持原始精度
                        float(row['pe_ratio']) if pd.notna(row['pe_ratio']) else None,
                        float(row['pb_ratio']) if pd.notna(row['pb_ratio']) else None
                    ))
                
                # 执行批量插入
                self.duckdb.executemany(insert_sql, insert_data)
                
                # 提交事务
                self.duckdb.execute("COMMIT")
                
                return len(insert_data)
                
            except Exception as e:
                # 回滚事务
                self.duckdb.execute("ROLLBACK")
                raise e
            
        except Exception as e:
            logger.error(f"保存{stock_code}日线数据到数据库失败: {e}, {traceback.format_exc()}")
            return 0
    
    async def _batch_insert_daily_data(self, batch_data: List[Dict]) -> int:
        """
        智能批量插入日线数据到DuckDB
        根据数据量自动选择最优插入策略，基于性能测试结果优化
        
        性能基准（基于测试结果）：
        - 小批量（<1000条）：executemany方法，性能提升30-35%
        - 大批量（>=1000条）：COPY方法，性能提升90-97%
        
        Args:
            batch_data: 批量数据列表，每个元素包含股票数据字典
            
        Returns:
            int: 成功插入的记录数
        """
        if not batch_data:
            return 0
            
        data_count = len(batch_data)
        start_time = time.time()
        
        try:
            # 智能选择插入策略（基于性能测试优化）
            if data_count >= 1000:
                # 大批量数据使用COPY方法，性能提升90%+
                logger.info(f"使用COPY方法处理{data_count}条大批量数据")
                result = await self._batch_insert_with_copy(batch_data)
                method = "COPY"
            else:
                # 中小批量数据使用executemany方法，性能提升30%+
                logger.info(f"使用executemany方法处理{data_count}条中小批量数据")
                result = await self._batch_insert_with_executemany(batch_data)
                method = "executemany"
            
            # 性能监控和日志
            duration = time.time() - start_time
            speed = result / duration if duration > 0 else 0
            logger.info(f"{method}方法插入{result}条数据完成，耗时{duration:.3f}秒，速度{speed:.0f}条/秒")
            
            return result
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"批量插入{data_count}条日线数据失败，耗时{duration:.3f}秒: {e}, {traceback.format_exc()}")
            return 0
    
    async def _batch_insert_with_copy(self, batch_data: List[Dict]) -> int:
        """
        使用COPY语句进行大批量高效插入
        适用于1000条以上的大批量数据
        """
        import tempfile
        import csv
        import os
        
        temp_file = None
        try:
            # 优化：设置DuckDB批量插入优化参数
            self.duckdb.execute("SET enable_progress_bar=false")       # 禁用进度条
            
            # 创建临时CSV文件，使用更快的写入方式
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, 
                                                  encoding='utf-8', newline='', buffering=8192)
            
            # 优化：使用csv.writer直接写入，避免DictWriter的开销
            writer = csv.writer(temp_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            
            # 预处理数据并批量写入
            rows = []
            for data in batch_data:
                row = [
                    str(data['stock_code']),
                    str(data['trade_date']),
                    data['open_price'] if data['open_price'] is not None else '',
                    data['high_price'] if data['high_price'] is not None else '',
                    data['low_price'] if data['low_price'] is not None else '',
                    data['close_price'] if data['close_price'] is not None else '',
                    data['volume'] if data['volume'] is not None else '',
                    data['amount'] if data['amount'] is not None else '',
                    data['turnover_rate'] if data['turnover_rate'] is not None else '',
                    data['pe_ratio'] if data['pe_ratio'] is not None else '',
                    data['pb_ratio'] if data['pb_ratio'] is not None else ''
                ]
                rows.append(row)
            
            # 批量写入所有行
            writer.writerows(rows)
            temp_file.close()
            
            # 优化：使用更高效的事务模式
            self.duckdb.execute("BEGIN TRANSACTION")
            
            # 优化：创建临时表进行UPSERT操作
            # 先删除可能存在的临时表
            self.duckdb.execute("DROP TABLE IF EXISTS temp_daily_data")
            
            temp_table_sql = """
            CREATE TEMPORARY TABLE temp_daily_data AS 
            SELECT * FROM daily_stock_data WHERE 1=0
            """
            self.duckdb.execute(temp_table_sql)
            
            # 使用优化的COPY语句导入到临时表
            copy_sql = f"""
            COPY temp_daily_data 
            (stock_code, trade_date, open_price, high_price, low_price, close_price, 
             volume, amount, turnover_rate, pe_ratio, pb_ratio)
            FROM '{temp_file.name}' 
            (FORMAT CSV, HEADER false, DELIMITER ',', NULL_PADDING true, IGNORE_ERRORS false)
            """
            
            self.duckdb.execute(copy_sql)
            
            # 优化：使用MERGE语句进行高效UPSERT
            merge_sql = """
            INSERT INTO daily_stock_data 
            SELECT stock_code, trade_date, open_price, high_price, low_price, close_price,
                   volume, amount, turnover_rate, pe_ratio, pb_ratio, NOW() as created_at, NOW() as updated_at
            FROM temp_daily_data
            ON CONFLICT (stock_code, trade_date) DO UPDATE SET
                open_price = EXCLUDED.open_price,
                high_price = EXCLUDED.high_price,
                low_price = EXCLUDED.low_price,
                close_price = EXCLUDED.close_price,
                volume = EXCLUDED.volume,
                amount = EXCLUDED.amount,
                turnover_rate = EXCLUDED.turnover_rate,
                pe_ratio = EXCLUDED.pe_ratio,
                pb_ratio = EXCLUDED.pb_ratio,
                updated_at = NOW()
            """
            
            self.duckdb.execute(merge_sql)
            
            # 提交事务
            self.duckdb.execute("COMMIT")
            
            logger.info(f"使用优化COPY语句批量插入{len(batch_data)}条日线数据成功")
            return len(batch_data)
            
        except Exception as e:
            # 回滚事务
            try:
                self.duckdb.execute("ROLLBACK")
            except:
                pass
            raise e
        finally:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
    
    async def _batch_insert_with_executemany(self, batch_data: List[Dict]) -> int:
        """
        使用优化的executemany进行中小批量插入
        适用于1000条以下的数据
        """
        try:
            # 优化：设置DuckDB性能参数
            self.duckdb.execute("SET enable_progress_bar=false")
            
            # 优化：使用WAL模式和延迟事务提交
            self.duckdb.execute("BEGIN TRANSACTION")
            
            # 优化：预编译SQL语句，使用更高效的UPSERT
            insert_sql = """
            INSERT INTO daily_stock_data 
            (stock_code, trade_date, open_price, high_price, low_price, close_price, 
             volume, amount, turnover_rate, pe_ratio, pb_ratio, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW())
            ON CONFLICT (stock_code, trade_date) DO UPDATE SET
                open_price = EXCLUDED.open_price,
                high_price = EXCLUDED.high_price,
                low_price = EXCLUDED.low_price,
                close_price = EXCLUDED.close_price,
                volume = EXCLUDED.volume,
                amount = EXCLUDED.amount,
                turnover_rate = EXCLUDED.turnover_rate,
                pe_ratio = EXCLUDED.pe_ratio,
                pb_ratio = EXCLUDED.pb_ratio,
                updated_at = NOW()
            """
            
            # 优化：批量预处理数据，减少循环开销
            insert_values = [
                (
                    str(data['stock_code']),
                    str(data['trade_date']),
                    float(data['open_price']) if data['open_price'] is not None else None,
                    float(data['high_price']) if data['high_price'] is not None else None,
                    float(data['low_price']) if data['low_price'] is not None else None,
                    float(data['close_price']) if data['close_price'] is not None else None,
                    int(data['volume']) if data['volume'] is not None else None,
                    float(data['amount']) if data['amount'] is not None else None,
                    float(data['turnover_rate']) if data['turnover_rate'] is not None else None,
                    float(data['pe_ratio']) if data['pe_ratio'] is not None else None,
                    float(data['pb_ratio']) if data['pb_ratio'] is not None else None
                )
                for data in batch_data
            ]
            
            # 优化：根据数据量动态调整批次大小
            if len(insert_values) <= 100:
                batch_size = len(insert_values)  # 小数据量一次性插入
            elif len(insert_values) <= 500:
                batch_size = 250  # 中等数据量分2批
            else:
                batch_size = 333  # 大数据量分3批
            
            total_inserted = 0
            
            # 优化：使用预编译语句和批量执行
            for i in range(0, len(insert_values), batch_size):
                batch = insert_values[i:i + batch_size]
                
                # 使用executemany进行批量插入
                self.duckdb.executemany(insert_sql, batch)
                total_inserted += len(batch)
                
                # 优化：中间检查点，防止长事务
                if total_inserted % 500 == 0 and total_inserted < len(insert_values):
                    self.duckdb.execute("SAVEPOINT batch_checkpoint")
            
            # 提交事务
            self.duckdb.execute("COMMIT")
            
            logger.info(f"使用优化executemany批量插入{total_inserted}条日线数据成功")
            return total_inserted
            
        except Exception as e:
            # 回滚事务
            try:
                self.duckdb.execute("ROLLBACK")
            except:
                pass
            raise e
    
    async def _batch_update_daily_data_optimized(self, stock_codes: List[str], batch_size: int = 20, 
                                               start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        优化的批量更新日线数据 - 一次获取多个股票数据并批量插入
        
        Args:
            stock_codes: 股票代码列表
            batch_size: 批量大小
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict: 更新结果统计
        """
        success_count = 0
        failed_count = 0
        failed_stocks = []
        
        for i in range(0, len(stock_codes), batch_size):
            batch = stock_codes[i:i + batch_size]
            
            try:
                # 批量获取多个股票的数据
                actual_start_date = start_date if start_date else "1990-01-01"
                actual_end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')
                
                logger.info(f"批量获取 {len(batch)} 只股票数据: {batch}")
                
                # 使用XtQuant批量获取数据
                history_data = await self.xtquant_service.get_history_data(
                    stock_codes=batch,
                    period=Period.DAILY,
                    start_date=actual_start_date,
                    end_date=actual_end_date
                )
                
                # 批量处理和插入数据
                batch_insert_data = []
                
                for stock_code in batch:
                    try:
                        if stock_code not in history_data or history_data[stock_code].empty:
                            failed_count += 1
                            failed_stocks.append(stock_code)
                            logger.warning(f"未获取到{stock_code}的数据")
                            continue
                        
                        df = history_data[stock_code].copy()
                        df = self._preprocess_daily_data(df, stock_code)
                        
                        if not df.empty:
                            # 转换为插入数据格式
                            for _, row in df.iterrows():
                                batch_insert_data.append({
                                    'stock_code': row['stock_code'],
                                    'trade_date': row['trade_date'],
                                    'open_price': float(row['open_price']),
                                    'high_price': float(row['high_price']),
                                    'low_price': float(row['low_price']),
                                    'close_price': float(row['close_price']),
                                    'volume': int(row['volume']) if pd.notna(row['volume']) else 0,
                                    'amount': float(row['amount']) if pd.notna(row['amount']) else 0.0,
                                    'turnover_rate': float(row.get('turnover_rate', 0.0)) if pd.notna(row.get('turnover_rate')) else 0.0,
                                    'pe_ratio': float(row.get('pe_ratio', 0.0)) if pd.notna(row.get('pe_ratio')) else 0.0,
                                    'pb_ratio': float(row.get('pb_ratio', 0.0)) if pd.notna(row.get('pb_ratio')) else 0.0
                                })
                            success_count += 1
                            logger.debug(f"成功处理 {stock_code} 数据，共{len(df)}条记录")
                        else:
                            failed_count += 1
                            failed_stocks.append(stock_code)
                            logger.warning(f"{stock_code} 预处理后无数据")
                            
                    except Exception as e:
                        failed_count += 1
                        failed_stocks.append(stock_code)
                        logger.error(f"处理 {stock_code} 数据失败: {e}")
                
                # 批量插入数据库
                if batch_insert_data:
                    inserted_count = await self._batch_insert_daily_data(batch_insert_data)
                    logger.info(f"批量插入 {inserted_count} 条数据到数据库")
                
            except Exception as e:
                # 批量处理失败，标记整个批次失败
                failed_count += len(batch)
                failed_stocks.extend(batch)
                logger.error(f"批量处理失败: {e}")
            
            # 批次间延迟
            await asyncio.sleep(0.2)
        
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_stocks": failed_stocks,
            "total_processed": len(stock_codes)
        }
    
    async def batch_update_daily_data(self, stock_codes: List[str], batch_size: int = 30, 
                                    delay_seconds: float = 0.2, force_update: bool = False,
                                    start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        公开的批量更新日线数据接口
        
        Args:
            stock_codes: 股票代码列表
            batch_size: 批量大小
            delay_seconds: 批次间延迟秒数
            force_update: 是否强制更新
            start_date: 开始日期，格式YYYY-MM-DD，为None时获取所有历史数据
            end_date: 结束日期，格式YYYY-MM-DD
            
        Returns:
            Dict: 更新结果统计
        """
        success_count = 0
        failed_count = 0
        failed_stocks = []
        processed_stocks = []
        
        logger.info(f"开始批量更新{len(stock_codes)}只股票的日线数据")
        
        # 使用优化的批量处理方法
        if len(stock_codes) > batch_size:
            # 大批量数据使用优化方法
            result = await self._batch_update_daily_data_optimized(
                stock_codes, batch_size, start_date, end_date
            )
            return result
        
        # 小批量数据使用原有逻辑
        for i in range(0, len(stock_codes), batch_size):
            batch = stock_codes[i:i + batch_size]
            
            for stock_code in batch:
                try:
                    # 如果不是强制更新，先检查是否需要更新
                    if not force_update:
                        latest_date = self._get_latest_date_from_db(stock_code)
                        if latest_date:
                            # 如果最新数据是今天或昨天（考虑周末），可能不需要更新
                            from datetime import datetime, timedelta
                            today = datetime.now().date()
                            if isinstance(latest_date, str):
                                latest_date = datetime.strptime(latest_date, '%Y-%m-%d').date()
                            elif isinstance(latest_date, datetime):
                                latest_date = latest_date.date()
                            
                            if latest_date >= today - timedelta(days=3):
                                logger.debug(f"{stock_code} 数据较新，跳过更新")
                                continue
                    
                    result = await self.get_stock_daily_data(stock_code, start_date=start_date, end_date=end_date, save_to_db=True)
                    if result is not None and not result.empty:
                        success_count += 1
                        processed_stocks.append(stock_code)
                        logger.debug(f"成功更新 {stock_code} 日线数据，共{len(result)}条记录")
                    else:
                        failed_count += 1
                        failed_stocks.append(stock_code)
                        logger.warning(f"更新 {stock_code} 日线数据失败：无数据")
                        
                except Exception as e:
                    failed_count += 1
                    failed_stocks.append(stock_code)
                    logger.error(f"更新 {stock_code} 日线数据失败: {e}")
            
            # 批次间延迟
            if i + batch_size < len(stock_codes) and delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
        
        result = {
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_stocks": failed_stocks,
            "processed_stocks": processed_stocks,
            "total_requested": len(stock_codes),
            "total_processed": success_count + failed_count,
            "success_rate": round(success_count / len(stock_codes) * 100, 2) if stock_codes else 0
        }
        
        logger.info(f"批量更新完成：成功{success_count}只，失败{failed_count}只，成功率{result['success_rate']}%")
        return result
    
    async def save_stock_data(self, stock_data: Dict[str, Any]):
        """保存股票数据到数据库"""
        try:
            db_gen = get_db()
            db = next(db_gen)
            try:
                # 检查数据是否已存在
                existing_query = select(StockData).where(
                    and_(
                        StockData.stock_code == stock_data["stock_code"],
                        StockData.trade_date == stock_data["trade_date"]
                    )
                )
                result = db.execute(existing_query)
                existing_data = result.scalar_one_or_none()
                
                if existing_data:
                    # 更新现有数据
                    update_stmt = update(StockData).where(
                        StockData.id == existing_data.id
                    ).values(**stock_data)
                    db.execute(update_stmt)
                else:
                    # 插入新数据
                    insert_stmt = insert(StockData).values(**stock_data)
                    db.execute(insert_stmt)
                
                db.commit()
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"保存股票数据失败: {e}, {traceback.format_exc()}")
    
    async def analyze_data_completeness(self) -> Dict[str, Any]:
        """分析数据完整度
        
        Returns:
            包含完整度分析结果的字典
        """
        try:
            logger.info("开始分析数据完整度")
            
            # 获取所有股票列表
            all_stocks = await self.get_stock_list()
            if not all_stocks:
                return {}
            
            total_stocks = len(all_stocks)
            stock_codes = [stock["stock_code"] for stock in all_stocks]
            
            # 分析每只股票的数据完整度
            incomplete_stocks = []
            complete_stocks = []
            total_expected_days = 0
            total_actual_days = 0
            
            # 计算预期的交易日数量（最近3年）
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1095)  # 3年
            expected_trading_days = self._calculate_trading_days(start_date, end_date)
            
            for stock_code in stock_codes:
                try:
                    # 获取该股票的数据统计
                    stats_sql = """
                    SELECT 
                        COUNT(*) as record_count,
                        MIN(trade_date) as earliest_date,
                        MAX(trade_date) as latest_date
                    FROM daily_stock_data 
                    WHERE stock_code = ?
                    """
                    
                    result = self.duckdb.fetchone(stats_sql, (stock_code,))
                    
                    if result and result[0] > 0:
                        record_count, earliest_date, latest_date = result
                        
                        # 计算数据完整度
                        actual_days = record_count
                        completeness = min(actual_days / expected_trading_days * 100, 100)
                        
                        # 计算距离最新交易日的天数
                        if latest_date:
                            days_behind = (datetime.now().date() - latest_date).days
                        else:
                            days_behind = 999
                        
                        stock_analysis = {
                            "stock_code": stock_code,
                            "record_count": actual_days,
                            "expected_days": expected_trading_days,
                            "completeness": round(completeness, 2),
                            "earliest_date": str(earliest_date) if earliest_date else None,
                            "latest_date": str(latest_date) if latest_date else None,
                            "days_behind": days_behind,
                            "missing_days": max(expected_trading_days - actual_days, 0)
                        }
                        
                        if completeness < 90 or days_behind > 5:
                            incomplete_stocks.append(stock_analysis)
                        else:
                            complete_stocks.append(stock_analysis)
                        
                        total_actual_days += actual_days
                    else:
                        # 没有数据的股票
                        stock_analysis = {
                            "stock_code": stock_code,
                            "record_count": 0,
                            "expected_days": expected_trading_days,
                            "completeness": 0.0,
                            "earliest_date": None,
                            "latest_date": None,
                            "days_behind": 999,
                            "missing_days": expected_trading_days
                        }
                        incomplete_stocks.append(stock_analysis)
                    
                    total_expected_days += expected_trading_days
                    
                except Exception as e:
                    logger.warning(f"分析{stock_code}数据完整度失败: {e}")
                    continue
            
            # 计算总体完整度
            overall_completeness = (total_actual_days / total_expected_days * 100) if total_expected_days > 0 else 0
            
            # 按完整度排序
            incomplete_stocks.sort(key=lambda x: x['completeness'])
            
            analysis_result = {
                "analysis_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "total_stocks": total_stocks,
                "complete_stocks_count": len(complete_stocks),
                "incomplete_stocks_count": len(incomplete_stocks),
                "overall_completeness": round(overall_completeness, 2),
                "expected_trading_days": expected_trading_days,
                "total_expected_records": total_expected_days,
                "total_actual_records": total_actual_days,
                "missing_records": total_expected_days - total_actual_days,
                "incomplete_stocks": incomplete_stocks[:100],  # 返回前100个需要补全的
                "completeness_distribution": self._get_completeness_distribution(incomplete_stocks + complete_stocks)
            }
            
            logger.info(f"数据完整度分析完成：总体完整度{overall_completeness:.1f}%，{len(incomplete_stocks)}只股票需要补全")
            return analysis_result
            
        except Exception as e:
            logger.error(f"分析数据完整度失败: {e}, {traceback.format_exc()}")
            return {}
    
    def _calculate_trading_days(self, start_date: datetime, end_date: datetime) -> int:
        """计算交易日数量（简化版本，实际应考虑节假日）"""
        total_days = (end_date - start_date).days
        # 简化计算：去除周末，约为总天数的5/7
        # 实际应该使用交易日历
        trading_days = int(total_days * 5 / 7 * 0.95)  # 0.95考虑节假日
        return max(trading_days, 1)
    
    def _get_completeness_distribution(self, stocks_analysis: List[Dict]) -> Dict[str, int]:
        """获取完整度分布统计"""
        distribution = {
            "0-20%": 0,
            "20-40%": 0,
            "40-60%": 0,
            "60-80%": 0,
            "80-90%": 0,
            "90-100%": 0
        }
        
        for stock in stocks_analysis:
            completeness = stock.get('completeness', 0)
            if completeness < 20:
                distribution["0-20%"] += 1
            elif completeness < 40:
                distribution["20-40%"] += 1
            elif completeness < 60:
                distribution["40-60%"] += 1
            elif completeness < 80:
                distribution["60-80%"] += 1
            elif completeness < 90:
                distribution["80-90%"] += 1
            else:
                distribution["90-100%"] += 1
        
        return distribution
    
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
            logger.error(f"更新实时数据失败: {e}, {traceback.format_exc()}")
    
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
            logger.error(f"更新历史数据失败: {e}, {traceback.format_exc()}")
    
    async def _get_watched_stocks(self) -> List[str]:
        """获取关注的股票列表"""
        # 从缓存获取关注股票列表
        watched_stocks = await self.cache_client.get("watched_stocks")
        if watched_stocks:
            return watched_stocks
        
        # 默认关注一些热门股票
        default_stocks = [
            "000001.SZ", "000002.SZ", "600000.SH", "600036.SH",
            "000858.SZ", "002415.SZ", "600519.SH", "000858.SZ"
        ]
        
        await self.cache_client.set("watched_stocks", default_stocks, expire=3600)
        return default_stocks
    
    def _get_latest_date_from_db(self, stock_code: str) -> str:
        """获取数据库中指定股票的最新日期"""
        try:
            sql = "SELECT MAX(trade_date) FROM daily_stock_data WHERE stock_code = ?"
            result = self.duckdb.fetchone(sql, (stock_code,))
            if result and result[0]:
                return str(result[0])
            return None
        except Exception as e:
            logger.warning(f"获取{stock_code}最新日期失败: {e}")
            return None
    
    async def _get_stocks_need_update(self) -> List[str]:
        """获取需要更新的股票列表"""
        try:
            # 使用DuckDB直接查询
            sql = """
            SELECT DISTINCT stock_code 
            FROM stock_data 
            ORDER BY updated_at DESC 
            LIMIT 100
            """
            
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.duckdb.fetchall, sql
            )
            
            stocks = [row[0] for row in result] if result else []
            return stocks
            
        except Exception as e:
            logger.error(f"获取需要更新的股票列表失败: {e}, {traceback.format_exc()}")
            # 返回默认股票列表
            return [
                "000001.SZ", "000002.SZ", "600000.SH", "600036.SH",
                "000858.SZ", "002415.SZ", "600519.SH", "300750.SZ"
            ]
    
    async def add_watched_stock(self, stock_code: str) -> bool:
        """添加关注股票"""
        try:
            watched_stocks = await self._get_watched_stocks()
            if stock_code not in watched_stocks:
                watched_stocks.append(stock_code)
                await self.cache_client.set("watched_stocks", watched_stocks, expire=3600)
                logger.info(f"添加关注股票: {stock_code}")
            return True
        except Exception as e:
            logger.error(f"添加关注股票失败: {e}, {traceback.format_exc()}")
            return False
    
    async def remove_watched_stock(self, stock_code: str) -> bool:
        """移除关注股票"""
        try:
            watched_stocks = await self._get_watched_stocks()
            if stock_code in watched_stocks:
                watched_stocks.remove(stock_code)
                await self.cache_client.set("watched_stocks", watched_stocks, expire=3600)
                logger.info(f"移除关注股票: {stock_code}")
            return True
        except Exception as e:
            logger.error(f"移除关注股票失败: {e}, {traceback.format_exc()}")
            return False
    
    async def get_stock_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取股票数据（为兼容性提供的方法）
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式YYYY-MM-DD
            end_date: 结束日期，格式YYYY-MM-DD
            
        Returns:
            股票数据DataFrame
        """
        try:
            return await self.get_historical_data(stock_code, start_date, end_date)
        except Exception as e:
            logger.error(f"获取股票数据失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    async def get_batch_historical_data(self, stock_codes: List[str], start_date: str, 
                                      end_date: str, period: str = "1d") -> Dict[str, pd.DataFrame]:
        """批量获取多个股票的历史数据
        优先从本地数据库获取，本地没有时从xtquant获取
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期，格式YYYY-MM-DD
            end_date: 结束日期，格式YYYY-MM-DD
            period: 数据周期，默认为日线
            
        Returns:
            Dict[str, pd.DataFrame]: 股票代码到DataFrame的映射
        """
        try:
            result = {}
            stocks_need_fetch = []  # 需要从xtquant获取的股票
            
            # 首先尝试从本地数据库获取数据
            for stock_code in stock_codes:
                try:
                    db_data = self._get_data_from_db(stock_code, start_date, end_date)
                    if not db_data.empty:
                        # 转换为标准格式
                        processed_df = db_data.copy()
                        
                        # 设置时间索引
                        if 'trade_date' in processed_df.columns:
                            processed_df['trade_date'] = pd.to_datetime(processed_df['trade_date'])
                            processed_df = processed_df.set_index('trade_date')
                        
                        result[stock_code] = processed_df
                        logger.debug(f"从本地数据库获取{stock_code}数据: {len(processed_df)}条")
                    else:
                        stocks_need_fetch.append(stock_code)
                        logger.debug(f"本地数据库无{stock_code}数据，需要从xtquant获取")
                except Exception as e:
                    logger.warning(f"从数据库获取{stock_code}数据失败: {e}")
                    stocks_need_fetch.append(stock_code)
            
            # 如果有股票需要从xtquant获取，则批量获取
            if stocks_need_fetch:
                logger.info(f"从xtquant批量获取{len(stocks_need_fetch)}只股票数据")
                history_data = await self.xtquant_service.get_history_data(
                    stock_codes=stocks_need_fetch,
                    period=Period.DAILY,
                    start_date=start_date,
                    end_date=end_date
                )
                
                # 处理从xtquant获取的数据
                for stock_code in stocks_need_fetch:
                    df = history_data.get(stock_code)
                    if df is not None and not df.empty:
                        # 标准化列名
                        df_processed = df.copy()
                        
                        # 确保必要的列存在
                        required_columns = ['open', 'high', 'low', 'close', 'volume']
                        for col in required_columns:
                            if col not in df_processed.columns:
                                logger.warning(f"股票{stock_code}缺少{col}列")
                                df_processed[col] = 0
                        
                        # 重命名列以保持一致性
                        column_mapping = {
                            'open': 'open_price',
                            'high': 'high_price', 
                            'low': 'low_price',
                            'close': 'close_price'
                        }
                        
                        for old_col, new_col in column_mapping.items():
                            if old_col in df_processed.columns:
                                df_processed[new_col] = df_processed[old_col]
                        
                        # 添加股票代码列
                        df_processed['stock_code'] = stock_code
                        
                        # 确保时间索引
                        if 'time' in df_processed.columns:
                            df_processed['trade_date'] = pd.to_datetime(df_processed['time']).dt.strftime('%Y-%m-%d')
                        elif df_processed.index.name == 'time' or isinstance(df_processed.index, pd.DatetimeIndex):
                            df_processed['trade_date'] = pd.to_datetime(df_processed.index).strftime('%Y-%m-%d')
                        
                        result[stock_code] = df_processed
                        
                        # 异步保存到数据库（不等待完成，避免阻塞）
                        try:
                            # 预处理数据用于保存
                            save_df = self._preprocess_daily_data(df.copy(), stock_code)
                            if not save_df.empty:
                                asyncio.create_task(self._save_daily_data_to_db(save_df, stock_code))
                        except Exception as save_e:
                            logger.warning(f"保存{stock_code}数据到数据库失败: {save_e}")
                    else:
                        logger.warning(f"股票{stock_code}无历史数据")
                        result[stock_code] = pd.DataFrame()
            
            # 确保所有股票都有结果
            for stock_code in stock_codes:
                if stock_code not in result:
                    result[stock_code] = pd.DataFrame()
            
            logger.info(f"批量获取完成: 本地{len(result) - len(stocks_need_fetch)}只, xtquant{len(stocks_need_fetch)}只")
            return result
            
        except Exception as e:
            logger.error(f"批量获取历史数据失败: {e}, {traceback.format_exc()}")
            return {stock_code: pd.DataFrame() for stock_code in stock_codes}
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """获取市场概览"""
        cache_key = "market_overview"
        
        # 尝试从缓存获取
        cached_data = await self.cache_client.get(cache_key)
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
            await self.cache_client.set(cache_key, overview, expire=60)  # 1分钟缓存
            
            return overview
            
        except Exception as e:
            logger.error(f"获取市场概览失败: {e}, {traceback.format_exc()}")
            return {}