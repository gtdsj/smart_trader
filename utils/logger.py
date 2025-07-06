"""日志工具模块"""

import os
import logging
import sys
from config import get_settings
from pathlib import Path
from typing import Optional
from loguru import logger as loguru_logger


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """获取标准logger实例"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # 获取设置
        settings = get_settings()
        
        # 创建日志目录
        log_dir = Path(settings.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建格式器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        
        # 创建文件处理器
        from datetime import datetime
        log_filename = f"{settings.log_file_prefix}_{datetime.now().strftime('%Y-%m-%d')}.log"
        log_file_path = log_dir / log_filename
        
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        
        # 添加处理器到logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.setLevel(getattr(logging, level.upper()))
    
    return logger


def setup_loguru_logger(
    log_file: Optional[str] = None,
    level: str = "INFO",
    rotation: str = "10 MB",
    retention: str = "7 days"
):
    """配置loguru日志器"""
    # 移除默认处理器
    loguru_logger.remove()
    
    # 添加控制台输出
    loguru_logger.add(
        sys.stdout,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # 如果指定了日志文件，添加文件输出
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        loguru_logger.add(
            log_file,
            level=level,
            rotation=rotation,
            retention=retention,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )
    
    return loguru_logger


# 默认设置
settings = get_settings()
setup_loguru_logger(
    log_file= os.path.join(settings.log_dir, f"{settings.log_file_prefix}_{{time:YYYY-MM-DD}}.log"),
    level="INFO"
)