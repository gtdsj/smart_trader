#coding=utf-8
"""
优化的A股全量数据补全配置
针对大批量数据插入进行性能优化
"""

from typing import Dict, Any
from datetime import datetime, timedelta


class OptimizedBackfillConfig:
    """
    优化的数据补全配置类
    专门针对A股全量数据补全场景进行性能优化
    """
    
    # ==================== 核心性能优化配置 ====================
    
    # 批量获取配置 - 大幅提升数据获取效率
    STOCK_BATCH_SIZE = 100          # 一次性获取100只股票数据（原30只）
    DATA_BATCH_INSERT_SIZE = 5000   # 数据库批量插入5000条（原1000条）
    
    # 并发配置 - 提升处理速度
    MAX_CONCURRENT_BATCHES = 3      # 最大并发批次数
    ENABLE_PARALLEL_PROCESSING = True  # 启用并行处理
    
    # 内存优化配置
    MEMORY_LIMIT_MB = 2048          # 增加内存限制到2GB
    ENABLE_MEMORY_OPTIMIZATION = True
    
    # 网络优化配置
    REQUEST_TIMEOUT = 30            # 请求超时时间（秒）
    MAX_RETRIES = 5                 # 最大重试次数
    RETRY_DELAY = 1.0              # 重试延迟（秒）
    
    # ==================== 数据库优化配置 ====================
    
    # DuckDB优化参数
    DUCKDB_OPTIMIZATION_SETTINGS = {
        'enable_progress_bar': False,
        'memory_limit': '2GB',
        'threads': 4,
        'max_memory': '2GB',
        'temp_directory': './temp',
        'enable_object_cache': True,
        'enable_http_metadata_cache': True,
        'force_compression': 'zstd'  # 修复：使用支持的压缩格式
    }
    
    # 批量插入策略配置
    BATCH_INSERT_STRATEGY = {
        'small_batch_threshold': 1000,     # 小批量阈值
        'large_batch_threshold': 5000,     # 大批量阈值
        'use_copy_method': True,           # 启用COPY方法
        'use_transaction': True,           # 使用事务
        'commit_interval': 10000           # 提交间隔
    }
    
    # ==================== 任务配置模板 ====================
    
    # 全量数据补全任务配置
    FULL_MARKET_TASK_CONFIG = {
        'task_name': '优化全量数据补全',
        'market': 'ALL',
        'batch_size': STOCK_BATCH_SIZE,
        'delay_seconds': 0.05,              # 减少延迟提升速度
        'force_update': False,
        'priority': 'high',
        'auto_retry': True,
        'max_retries': MAX_RETRIES,
        'enable_parallel': ENABLE_PARALLEL_PROCESSING,
        'memory_optimization': ENABLE_MEMORY_OPTIMIZATION
    }
    
    # 增量更新任务配置
    INCREMENTAL_TASK_CONFIG = {
        'task_name': '优化增量更新',
        'market': 'ALL',
        'batch_size': STOCK_BATCH_SIZE,
        'delay_seconds': 0.02,
        'force_update': False,
        'priority': 'high',
        'auto_retry': True,
        'max_retries': 3,
        'enable_parallel': True,
        'memory_optimization': True
    }
    
    # ==================== 数据质量配置 ====================
    
    # 数据完整性检查
    DATA_QUALITY_CONFIG = {
        'min_records_per_year': 200,
        'max_missing_days_ratio': 0.1,
        'enable_data_validation': True,
        'enable_duplicate_check': True,
        'enable_price_validation': True
    }
    
    # ==================== 监控和日志配置 ====================
    
    # 性能监控配置
    PERFORMANCE_MONITORING = {
        'enable_performance_log': True,
        'log_interval_seconds': 30,
        'enable_memory_monitoring': True,
        'enable_speed_monitoring': True,
        'performance_threshold': {
            'min_insert_speed': 1000,       # 最小插入速度（条/秒）
            'max_memory_usage': 1.5,        # 最大内存使用（GB）
            'max_batch_time': 60            # 最大批次处理时间（秒）
        }
    }
    
    # 日志配置
    LOGGING_CONFIG = {
        'log_level': 'INFO',
        'enable_detailed_log': True,
        'log_file_path': './logs/optimized_backfill.log',
        'max_log_size_mb': 100,
        'backup_count': 5
    }
    
    # ==================== 时间范围配置 ====================
    
    @staticmethod
    def get_default_date_range() -> tuple:
        """
        获取默认的数据补全日期范围
        
        Returns:
            tuple: (start_date, end_date)
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        # 默认获取最近5年的数据
        start_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
        return start_date, end_date
    
    @staticmethod
    def get_full_history_range() -> tuple:
        """
        获取全历史数据范围
        
        Returns:
            tuple: (start_date, end_date)
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = '1990-01-01'  # A股市场开始时间
        return start_date, end_date
    
    # ==================== 优化建议配置 ====================
    
    OPTIMIZATION_RECOMMENDATIONS = {
        'database': [
            '使用COPY方法进行大批量插入，性能提升90%+',
            '启用DuckDB内存优化和并行处理',
            '使用事务批量提交，减少I/O开销',
            '优化临时文件存储路径，使用SSD存储'
        ],
        'network': [
            '增加批量获取股票数量，减少网络请求次数',
            '启用请求重试机制，提高数据获取成功率',
            '优化请求间隔，平衡速度和稳定性'
        ],
        'memory': [
            '增加内存限制，支持更大批量处理',
            '启用内存监控，防止内存溢出',
            '优化数据结构，减少内存占用'
        ],
        'parallel': [
            '启用并行处理，充分利用多核CPU',
            '合理设置并发数，避免资源竞争',
            '使用异步处理，提升整体效率'
        ]
    }
    
    @classmethod
    def get_optimized_config(cls, scenario: str = 'full_market') -> Dict[str, Any]:
        """
        获取针对特定场景的优化配置
        
        Args:
            scenario: 场景类型 ('full_market', 'incremental', 'custom')
            
        Returns:
            Dict: 优化配置字典
        """
        base_config = {
            'duckdb_settings': cls.DUCKDB_OPTIMIZATION_SETTINGS,
            'batch_strategy': cls.BATCH_INSERT_STRATEGY,
            'performance_monitoring': cls.PERFORMANCE_MONITORING,
            'data_quality': cls.DATA_QUALITY_CONFIG
        }
        
        if scenario == 'full_market':
            base_config.update(cls.FULL_MARKET_TASK_CONFIG)
        elif scenario == 'incremental':
            base_config.update(cls.INCREMENTAL_TASK_CONFIG)
        
        return base_config