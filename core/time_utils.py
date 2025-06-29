# -*- coding: utf-8 -*-
"""
时间处理工具类
统一管理项目中的时间转换逻辑
"""

import traceback
import pandas as pd
from datetime import datetime, date
from typing import Union, Any
import logging

logger = logging.getLogger(__name__)

class TimeUtils:
    """时间处理工具类"""
    
    @staticmethod
    def normalize_timestamp(timestamp: Any) -> pd.Timestamp:
        """
        统一时间戳标准化处理
        
        Args:
            timestamp: 时间戳，支持多种格式
            
        Returns:
            pd.Timestamp: 标准化后的时间戳
        """
        try:
            # 如果已经是datetime类型，直接转换
            if isinstance(timestamp, (datetime, pd.Timestamp)):
                return pd.Timestamp(timestamp)
            
            # 如果是字符串
            if isinstance(timestamp, str):
                timestamp_str = timestamp.strip()
                
                # 如果是纯数字字符串
                if timestamp_str.isdigit():
                    timestamp_int = int(timestamp_str)
                    return TimeUtils._convert_numeric_timestamp(timestamp_int)
                else:
                    # 尝试直接解析字符串，如果包含时区信息则转换为本地时区
                    parsed_dt = pd.to_datetime(timestamp_str)
                    if parsed_dt.tz is not None:
                        return parsed_dt.tz_convert('Asia/Shanghai').tz_localize(None)
                    return parsed_dt
            
            # 如果是数字类型
            if isinstance(timestamp, (int, float)):
                return TimeUtils._convert_numeric_timestamp(timestamp)
            
            # 其他情况直接转换，处理可能的时区问题
            parsed_dt = pd.to_datetime(timestamp)
            if hasattr(parsed_dt, 'tz') and parsed_dt.tz is not None:
                return parsed_dt.tz_convert('Asia/Shanghai').tz_localize(None)
            return parsed_dt
            
        except Exception as e:
            logger.warning(f"时间戳转换失败: {timestamp}, 错误: {e}")
            return pd.NaT
    
    @staticmethod
    def _convert_numeric_timestamp(timestamp: Union[int, float]) -> pd.Timestamp:
        """
        转换数字时间戳
        
        Args:
            timestamp: 数字时间戳
            
        Returns:
            pd.Timestamp: 转换后的时间戳
        """
        timestamp_str = str(int(timestamp))
        
        # 根据数字长度判断时间戳类型
        if len(timestamp_str) == 8:
            # YYYYMMDD格式
            return pd.to_datetime(timestamp_str, format='%Y%m%d')
        elif len(timestamp_str) == 10:
            # 秒时间戳，转换为本地时区
            return pd.to_datetime(timestamp, unit='s', utc=True).tz_convert('Asia/Shanghai').tz_localize(None)
        elif len(timestamp_str) == 13:
            # 毫秒时间戳，转换为本地时区
            return pd.to_datetime(timestamp, unit='ms', utc=True).tz_convert('Asia/Shanghai').tz_localize(None)
        elif len(timestamp_str) > 13:
            # 纳秒时间戳，转换为本地时区
            return pd.to_datetime(timestamp, unit='ns', utc=True).tz_convert('Asia/Shanghai').tz_localize(None)
        else:
            # 其他情况，尝试直接转换
            return pd.to_datetime(timestamp)
    
    @staticmethod
    def to_trade_date(dt: Any) -> date:
        """
        转换为交易日期格式
        
        Args:
            dt: 时间对象
            
        Returns:
            date: 日期对象
        """
        try:
            if isinstance(dt, date) and not isinstance(dt, datetime):
                return dt
            
            normalized_dt = TimeUtils.normalize_timestamp(dt)
            if pd.isna(normalized_dt):
                raise ValueError(f"无法转换时间: {dt}")
            
            return normalized_dt.date()
            
        except Exception as e:
            logger.error(f"转换交易日期失败: {dt}, 错误: {e}, {traceback.format_exc()}")
            raise
    
    @staticmethod
    def validate_time_range(dt: Any, min_date: datetime = None, max_date: datetime = None) -> bool:
        """
        验证时间范围的有效性
        
        Args:
            dt: 时间对象
            min_date: 最小日期，默认为1990-01-01
            max_date: 最大日期，默认为当前时间+1天
            
        Returns:
            bool: 是否在有效范围内
        """
        try:
            if min_date is None:
                min_date = datetime(1990, 1, 1)
            if max_date is None:
                max_date = datetime.now().replace(hour=23, minute=59, second=59)
            
            normalized_dt = TimeUtils.normalize_timestamp(dt)
            if pd.isna(normalized_dt):
                return False
            
            return min_date <= normalized_dt <= max_date
            
        except Exception:
            return False
    
    @staticmethod
    def convert_dataframe_time_column(df: pd.DataFrame, time_column: str = 'time', 
                                    target_column: str = 'trade_date', 
                                    to_date: bool = True) -> pd.DataFrame:
        """
        转换DataFrame中的时间列
        
        Args:
            df: DataFrame
            time_column: 源时间列名
            target_column: 目标列名
            to_date: 是否转换为date格式
            
        Returns:
            pd.DataFrame: 处理后的DataFrame
        """
        try:
            if time_column not in df.columns:
                logger.warning(f"列 {time_column} 不存在于DataFrame中")
                return df
            
            df = df.copy()
            
            # 批量转换时间
            if to_date:
                df[target_column] = df[time_column].apply(
                    lambda x: TimeUtils.to_trade_date(x) if pd.notna(x) else None
                )
            else:
                df[target_column] = df[time_column].apply(
                    lambda x: TimeUtils.normalize_timestamp(x) if pd.notna(x) else pd.NaT
                )
            
            # 移除无效的时间数据
            df = df.dropna(subset=[target_column])
            
            return df
            
        except Exception as e:
            logger.error(f"DataFrame时间列转换失败: {e}, {traceback.format_exc()}")
            return df
    
    @staticmethod
    def convert_dataframe_time_index(df: pd.DataFrame, to_date: bool = False) -> pd.DataFrame:
        """
        转换DataFrame的时间索引
        
        Args:
            df: DataFrame
            to_date: 是否转换为date格式
            
        Returns:
            pd.DataFrame: 处理后的DataFrame
        """
        try:
            df = df.copy()
            
            # 转换索引
            if to_date:
                df.index = df.index.map(
                    lambda x: TimeUtils.to_trade_date(x) if pd.notna(x) else None
                )
            else:
                df.index = df.index.map(
                    lambda x: TimeUtils.normalize_timestamp(x) if pd.notna(x) else pd.NaT
                )
            
            # 移除无效的时间数据
            df = df[df.index.notna()]
            
            return df
            
        except Exception as e:
            logger.error(f"DataFrame时间索引转换失败: {e}, {traceback.format_exc()}")
            return df
    
    @staticmethod
    def convert_date_format(date_str: str, from_format: str = None, to_format: str = '%Y%m%d') -> str:
        """
        转换日期格式
        
        Args:
            date_str: 日期字符串
            from_format: 源格式，如果为None则自动检测
            to_format: 目标格式，默认为'%Y%m%d'
            
        Returns:
            str: 转换后的日期字符串
        """
        try:
            if not date_str:
                return date_str
            
            # 如果已经是目标格式，直接返回
            if to_format == '%Y%m%d' and len(date_str) == 8 and date_str.isdigit():
                return date_str
            
            # 自动检测源格式
            if from_format is None:
                if len(date_str) == 8 and date_str.isdigit():
                    from_format = '%Y%m%d'
                elif len(date_str) == 10 and '-' in date_str:
                    from_format = '%Y-%m-%d'
                elif len(date_str) == 10 and '/' in date_str:
                    from_format = '%Y/%m/%d'
                else:
                    # 尝试使用pandas解析
                    dt = pd.to_datetime(date_str)
                    return dt.strftime(to_format)
            
            # 转换格式
            dt = datetime.strptime(date_str, from_format)
            return dt.strftime(to_format)
            
        except Exception as e:
            logger.warning(f"日期格式转换失败: {date_str}, 错误: {e}，返回原值")
            return date_str
    
    @staticmethod
    def to_xtquant_date_format(date_str: str) -> str:
        """
        转换为XtQuant所需的日期格式(%Y%m%d)
        
        Args:
            date_str: 日期字符串
            
        Returns:
            str: XtQuant格式的日期字符串
        """
        return TimeUtils.convert_date_format(date_str, to_format='%Y%m%d')