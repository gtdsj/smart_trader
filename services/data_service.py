# -*- coding: utf-8 -*-
"""
数据服务模块
"""
import traceback
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, and_, desc
from core.time_utils import TimeUtils

from config import get_settings
from core.database import get_db
from core.redis_client import get_redis
from core.duckdb_adapter import DuckDBAdapter
from services.notification_service import NotificationService
from services.xtquant_service import XtQuantService, Period


class DataService:
    """数据服务"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = get_redis()
        self.notification_service = NotificationService()
        self.xtquant_service = XtQuantService()
        self.is_running = False
        self.data_update_task = None
        
        # 初始化DuckDB适配器
        db_path = self.settings.database.path if hasattr(self.settings.database, 'path') else 'data/smart_trader.db'
        self.duckdb = DuckDBAdapter(db_path)
        self._init_daily_data_table()
        
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
        try:
            logger.info("启动数据服务...")
            
            # 启动XtQuant数据服务
            await self.xtquant_service.start()
            
            # 启动数据更新循环
            self.data_update_task = asyncio.create_task(self._data_update_loop())
            
            logger.info("数据服务启动成功")
            
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
                logger.error(f"数据更新循环异常: {e}, {traceback.format_exc()}")
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
    
    async def get_stock_list(self, market: str = None) -> List[Dict[str, Any]]:
        """获取股票列表
        
        Args:
            market: 市场代码，如SH、SZ，None表示获取所有市场
        """
        try:
            # 构建缓存键
            cache_key = f"stock_list:{market or 'ALL'}"
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                logger.debug(f"从缓存获取{market or '全部'}市场股票列表")
                return cached_data
            
            # 从XtQuant获取
            stock_result = self.xtquant_service.get_stock_list()
            if stock_result:
                stocks = stock_result
                
                # 根据市场过滤
                if market and market != "ALL":
                    stocks = [stock for stock in stocks if stock.get("market") == market]
                
                # 缓存30分钟
                await self.redis_client.set(cache_key, stocks, expire=1800)
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
            realtime_result = await self.xtquant_service.get_real_time_data(stock_codes)
            
            if realtime_result["success"]:
                result = realtime_result["data"]
                
                # 缓存数据
                for stock_code, data in result.items():
                    cache_key = f"realtime:{stock_code}"
                    await self.redis_client.set(cache_key, data, expire=30)  # 30秒缓存
                
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
        cached_data = await self.redis_client.get(cache_key)
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
                await self.redis_client.set(cache_key, data, expire=3600)  # 1小时缓存
                
                return df
            else:
                logger.error(f"获取{stock_code}历史数据失败: {historical_result.get('error', '未知错误')}")
                return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"获取{stock_code}历史数据失败: {e}, {traceback.format_exc()}")
            return pd.DataFrame()
    
    def _init_daily_data_table(self):
        """初始化日线数据表"""
        try:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS daily_stock_data (
                stock_code VARCHAR(20) NOT NULL,
                trade_date DATE NOT NULL,
                open_price DECIMAL(10,3),
                high_price DECIMAL(10,3),
                low_price DECIMAL(10,3),
                close_price DECIMAL(10,3),
                volume BIGINT,
                amount DECIMAL(20,2),
                turnover_rate DECIMAL(8,4),
                pe_ratio DECIMAL(8,2),
                pb_ratio DECIMAL(8,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (stock_code, trade_date)
            )
            """
            self.duckdb.execute(create_table_sql)
            
            # 创建索引
            index_sqls = [
                "CREATE INDEX IF NOT EXISTS idx_daily_stock_code ON daily_stock_data(stock_code)",
                "CREATE INDEX IF NOT EXISTS idx_daily_trade_date ON daily_stock_data(trade_date)",
                "CREATE INDEX IF NOT EXISTS idx_daily_code_date ON daily_stock_data(stock_code, trade_date)"
            ]
            
            for sql in index_sqls:
                self.duckdb.execute(sql)
                
            logger.info("日线数据表初始化完成")
            
        except Exception as e:
            logger.error(f"初始化日线数据表失败: {e}, {traceback.format_exc()}")
            raise
    
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
                    start_date = (latest_date + timedelta(days=1)).strftime('%Y-%m-%d')
                    logger.info(f"{stock_code}数据库中最新日期: {latest_date}, 从{start_date}开始增量更新")
                else:
                    # 如果数据库中没有数据，获取最近3年的数据
                    start_date = (datetime.now() - timedelta(days=1095)).strftime('%Y-%m-%d')
                    logger.info(f"{stock_code}数据库中无数据，从{start_date}开始获取历史数据")
            
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
            
            df = history_data[stock_code].copy()
            # 数据预处理
            df = self._preprocess_daily_data(df, stock_code)
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
                    logger.warning(f"股票{stock_code}有{invalid_count}条时间数据超出合理范围，已过滤")
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
        """保存日线数据到数据库"""
        try:
            if df.empty:
                return 0
            
            # 先删除已存在的记录，再插入新记录（DuckDB兼容方式）
            delete_sql = """
            DELETE FROM daily_stock_data 
            WHERE stock_code = ? AND trade_date = ?
            """
            
            insert_sql = """
            INSERT INTO daily_stock_data 
            (stock_code, trade_date, open_price, high_price, low_price, 
             close_price, volume, amount, turnover_rate, pe_ratio, pb_ratio, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """
            
            saved_count = 0
            for _, row in df.iterrows():
                try:
                    # 先删除已存在的记录
                    self.duckdb.execute(delete_sql, (
                        row['stock_code'],
                        row['trade_date']
                    ))
                    
                    # 插入新记录
                    self.duckdb.execute(insert_sql, (
                        row['stock_code'],
                        row['trade_date'],
                        float(row['open_price']) if pd.notna(row['open_price']) else None,
                        float(row['high_price']) if pd.notna(row['high_price']) else None,
                        float(row['low_price']) if pd.notna(row['low_price']) else None,
                        float(row['close_price']) if pd.notna(row['close_price']) else None,
                        int(row['volume']) if pd.notna(row['volume']) else None,
                        float(row['amount']) if pd.notna(row['amount']) else None,
                        float(row['turnover_rate']) if pd.notna(row['turnover_rate']) else None,
                        float(row['pe_ratio']) if pd.notna(row['pe_ratio']) else None,
                        float(row['pb_ratio']) if pd.notna(row['pb_ratio']) else None
                    ))
                    saved_count += 1
                except Exception as e:
                    logger.error(f"保存{stock_code}单条数据失败: {e}, {traceback.format_exc()}")
                    continue
            
            return saved_count
            
        except Exception as e:
            logger.error(f"保存{stock_code}日线数据到数据库失败: {e}, {traceback.format_exc()}")
            return 0
    
    async def _batch_update_daily_data(self, stock_codes: List[str], batch_size: int = 20) -> Dict[str, Any]:
        """
        批量更新日线数据
        
        Args:
            stock_codes: 股票代码列表
            batch_size: 批量大小
            
        Returns:
            Dict: 更新结果统计
        """
        success_count = 0
        failed_count = 0
        failed_stocks = []
        
        for i in range(0, len(stock_codes), batch_size):
            batch = stock_codes[i:i + batch_size]
            
            for stock_code in batch:
                try:
                    result = await self.get_stock_daily_data(stock_code, save_to_db=True)
                    if result is not None and not result.empty:
                        success_count += 1
                        logger.info(f"成功更新 {stock_code} 日线数据")
                    else:
                        failed_count += 1
                        failed_stocks.append(stock_code)
                        logger.warning(f"更新 {stock_code} 日线数据失败：无数据")
                except Exception as e:
                    failed_count += 1
                    failed_stocks.append(stock_code)
                    logger.error(f"更新 {stock_code} 日线数据失败: {e}")
            
            # 批次间延迟
            await asyncio.sleep(0.2)
        
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_stocks": failed_stocks,
            "total_processed": len(stock_codes)
        }
    
    async def batch_update_daily_data(self, stock_codes: List[str], batch_size: int = 30, 
                                    delay_seconds: float = 0.2, force_update: bool = False) -> Dict[str, Any]:
        """
        公开的批量更新日线数据接口
        
        Args:
            stock_codes: 股票代码列表
            batch_size: 批量大小
            delay_seconds: 批次间延迟秒数
            force_update: 是否强制更新
            
        Returns:
            Dict: 更新结果统计
        """
        success_count = 0
        failed_count = 0
        failed_stocks = []
        processed_stocks = []
        
        logger.info(f"开始批量更新{len(stock_codes)}只股票的日线数据")
        
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
                    
                    result = await self.get_stock_daily_data(stock_code, save_to_db=True)
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
            async for db in get_db():
                # 获取最近没有更新的股票
                query = select(StockData.stock_code).distinct().order_by(
                    desc(StockData.updated_at)
                ).limit(100)
                
                result = await db.execute(query)
                stocks = [row[0] for row in result.fetchall()]
                
                return stocks
        except Exception as e:
            logger.error(f"获取需要更新的股票列表失败: {e}, {traceback.format_exc()}")
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
            logger.error(f"添加关注股票失败: {e}, {traceback.format_exc()}")
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
            logger.error(f"移除关注股票失败: {e}, {traceback.format_exc()}")
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
            logger.error(f"获取市场概览失败: {e}, {traceback.format_exc()}")
            return {}