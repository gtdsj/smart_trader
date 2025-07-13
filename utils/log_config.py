"""统一日志配置模块

实施方案1：保持现状并优化
- 继续使用 loguru 作为主要日志方案
- 提供统一的日志配置和格式
- 支持不同环境的日志级别管理
"""

import os
import sys
from pathlib import Path
from typing import Optional
from loguru import logger
from config import get_settings


class LogConfig:
    """统一日志配置管理器"""
    
    _initialized = False
    
    @classmethod
    def setup_logger(
        cls,
        log_level: Optional[str] = None,
        log_dir: Optional[str] = None,
        log_file_prefix: Optional[str] = None,
        max_log_files: Optional[int] = None,
        enable_console: bool = True,
        enable_file: bool = True
    ):
        """设置统一的日志配置
        
        Args:
            log_level: 日志级别，默认从配置文件读取
            log_dir: 日志目录，默认从配置文件读取
            log_file_prefix: 日志文件前缀，默认从配置文件读取
            max_log_files: 最大日志文件数，默认从配置文件读取
            enable_console: 是否启用控制台输出
            enable_file: 是否启用文件输出
        """
        if cls._initialized:
            return
        
        # 获取配置
        settings = get_settings()
        log_level = log_level or settings.log_level
        log_dir = log_dir or settings.log_dir
        log_file_prefix = log_file_prefix or settings.log_file_prefix
        max_log_files = max_log_files or settings.max_log_files
        
        # 移除默认处理器
        logger.remove()
        
        # 统一的日志格式
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
        
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} - "
            "{message}"
        )
        
        # 添加控制台输出
        if enable_console:
            logger.add(
                sys.stdout,
                level=log_level,
                format=console_format,
                colorize=True,
                backtrace=True,
                diagnose=True
            )
        
        # 添加文件输出
        if enable_file:
            # 确保日志目录存在
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            
            # 添加文件处理器
            logger.add(
                log_path / f"{log_file_prefix}_{{time:YYYY-MM-DD}}.log",
                level=log_level,
                format=file_format,
                rotation="1 day",
                retention=f"{max_log_files} days",
                compression="zip",
                backtrace=True,
                diagnose=True,
                encoding="utf-8"
            )
            
            # 添加错误日志文件（只记录ERROR及以上级别）
            logger.add(
                log_path / f"{log_file_prefix}_error_{{time:YYYY-MM-DD}}.log",
                level="ERROR",
                format=file_format,
                rotation="1 day",
                retention=f"{max_log_files * 2} days",  # 错误日志保留更久
                compression="zip",
                backtrace=True,
                diagnose=True,
                encoding="utf-8"
            )
        
        cls._initialized = True
        logger.info(f"日志系统初始化完成 - 级别: {log_level}, 目录: {log_dir}")
    
    @classmethod
    def get_logger(cls, name: Optional[str] = None):
        """获取logger实例
        
        Args:
            name: logger名称（可选，主要用于兼容性）
            
        Returns:
            loguru logger实例
        """
        if not cls._initialized:
            cls.setup_logger()
        return logger
    
    @classmethod
    def reset(cls):
        """重置日志配置（主要用于测试）"""
        logger.remove()
        cls._initialized = False


# 提供便捷的导入接口
def setup_logging(**kwargs):
    """设置日志配置的便捷函数"""
    LogConfig.setup_logger(**kwargs)


def get_logger(name: Optional[str] = None):
    """获取logger的便捷函数"""
    return LogConfig.get_logger(name)


# 自动初始化（可选）
# 如果需要在导入时自动初始化，取消下面的注释
# LogConfig.setup_logger()