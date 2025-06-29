# coding=utf-8
"""
数据补全配置文件
定义数据补全相关的参数和设置
"""

from typing import Dict, Any
from datetime import datetime, timedelta


class DataBackfillConfig:
    """数据补全配置类"""
    
    # 默认配置参数
    DEFAULT_BATCH_SIZE = 30
    DEFAULT_DELAY_SECONDS = 0.2
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_TIMEOUT_SECONDS = 300
    
    # 市场配置
    SUPPORTED_MARKETS = ["SH", "SZ", "ALL"]
    
    # 数据完整度阈值
    COMPLETENESS_THRESHOLDS = {
        "excellent": 95,
        "good": 80,
        "fair": 50,
        "poor": 0
    }
    
    # 优先级配置
    PRIORITY_LEVELS = {
        "high": {
            "batch_size": 20,
            "delay_seconds": 0.1,
            "max_concurrent": 5
        },
        "normal": {
            "batch_size": 30,
            "delay_seconds": 0.2,
            "max_concurrent": 3
        },
        "low": {
            "batch_size": 50,
            "delay_seconds": 0.5,
            "max_concurrent": 2
        }
    }
    
    # 任务限制
    MAX_CONCURRENT_TASKS = 3
    MAX_TASK_HISTORY = 100
    TASK_CLEANUP_DAYS = 7
    
    # 数据范围配置
    DEFAULT_HISTORY_YEARS = 3
    MAX_HISTORY_YEARS = 10
    MIN_DATE = "2010-01-01"
    
    # 重试配置
    RETRY_DELAYS = [1, 3, 5]  # 重试间隔（秒）
    RETRY_BACKOFF_FACTOR = 2
    
    # 监控配置
    PROGRESS_UPDATE_INTERVAL = 10  # 进度更新间隔（股票数量）
    LOG_LEVEL = "INFO"
    
    # 性能配置
    DB_BATCH_INSERT_SIZE = 1000
    MEMORY_LIMIT_MB = 512
    
    # 数据质量配置
    MIN_RECORDS_PER_YEAR = 200  # 每年最少交易日数
    MAX_MISSING_DAYS_RATIO = 0.1  # 最大缺失天数比例
    
    @classmethod
    def get_priority_config(cls, priority: str) -> Dict[str, Any]:
        """获取优先级配置"""
        return cls.PRIORITY_LEVELS.get(priority, cls.PRIORITY_LEVELS["normal"])
    
    @classmethod
    def get_completeness_level(cls, completeness: float) -> str:
        """根据完整度获取等级"""
        if completeness >= cls.COMPLETENESS_THRESHOLDS["excellent"]:
            return "excellent"
        elif completeness >= cls.COMPLETENESS_THRESHOLDS["good"]:
            return "good"
        elif completeness >= cls.COMPLETENESS_THRESHOLDS["fair"]:
            return "fair"
        else:
            return "poor"
    
    @classmethod
    def get_default_date_range(cls) -> tuple:
        """获取默认日期范围"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=cls.DEFAULT_HISTORY_YEARS * 365)
        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
    
    @classmethod
    def validate_date_range(cls, start_date: str, end_date: str) -> bool:
        """验证日期范围"""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            min_date = datetime.strptime(cls.MIN_DATE, "%Y-%m-%d")
            
            # 检查日期范围
            if start < min_date:
                return False
            if end < start:
                return False
            if (end - start).days > cls.MAX_HISTORY_YEARS * 365:
                return False
                
            return True
        except ValueError:
            return False
    
    @classmethod
    def get_retry_delay(cls, attempt: int) -> float:
        """获取重试延迟时间"""
        if attempt <= len(cls.RETRY_DELAYS):
            return cls.RETRY_DELAYS[attempt - 1]
        else:
            # 指数退避
            base_delay = cls.RETRY_DELAYS[-1]
            return base_delay * (cls.RETRY_BACKOFF_FACTOR ** (attempt - len(cls.RETRY_DELAYS)))


# 预定义的任务模板
TASK_TEMPLATES = {
    "full_market_backfill": {
        "task_name": "全市场数据补全",
        "market": "ALL",
        "batch_size": 30,
        "delay_seconds": 0.2,
        "force_update": False,
        "priority": "normal",
        "auto_retry": True,
        "max_retries": 3
    },
    "sh_market_backfill": {
        "task_name": "沪市数据补全",
        "market": "SH",
        "batch_size": 40,
        "delay_seconds": 0.15,
        "force_update": False,
        "priority": "normal",
        "auto_retry": True,
        "max_retries": 3
    },
    "sz_market_backfill": {
        "task_name": "深市数据补全",
        "market": "SZ",
        "batch_size": 40,
        "delay_seconds": 0.15,
        "force_update": False,
        "priority": "normal",
        "auto_retry": True,
        "max_retries": 3
    },
    "incremental_update": {
        "task_name": "增量数据更新",
        "market": "ALL",
        "batch_size": 50,
        "delay_seconds": 0.1,
        "force_update": False,
        "priority": "high",
        "auto_retry": True,
        "max_retries": 2
    },
    "priority_stocks_update": {
        "task_name": "重点股票更新",
        "batch_size": 20,
        "delay_seconds": 0.1,
        "force_update": True,
        "priority": "high",
        "auto_retry": True,
        "max_retries": 5
    }
}


# 数据质量检查配置
DATA_QUALITY_CONFIG = {
    "min_price": 0.01,  # 最小价格
    "max_price": 10000,  # 最大价格
    "min_volume": 0,  # 最小成交量
    "max_volume_ratio": 100,  # 最大成交量比例（相对于平均值）
    "price_change_limit": 0.2,  # 单日最大涨跌幅
    "required_columns": ["open", "high", "low", "close", "volume"],
    "date_format": "%Y-%m-%d",
    "timezone": "Asia/Shanghai"
}


# 监控和告警配置
MONITORING_CONFIG = {
    "enable_alerts": True,
    "alert_thresholds": {
        "task_failure_rate": 0.1,  # 任务失败率阈值
        "data_missing_rate": 0.05,  # 数据缺失率阈值
        "processing_time_minutes": 60,  # 处理时间阈值（分钟）
    },
    "notification_channels": ["log", "email"],  # 通知渠道
    "health_check_interval": 300,  # 健康检查间隔（秒）
}


# 缓存配置
CACHE_CONFIG = {
    "enable_cache": True,
    "cache_ttl_seconds": 3600,  # 缓存过期时间
    "max_cache_size": 1000,  # 最大缓存条目数
    "cache_key_prefix": "data_backfill:",
    "cache_compression": True
}