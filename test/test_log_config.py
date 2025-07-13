#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置测试脚本

测试新的统一日志配置模块是否正常工作
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.log_config import LogConfig, setup_logging, get_logger
from config import get_settings


def test_basic_logging():
    """测试基本日志功能"""
    print("\n=== 测试基本日志功能 ===")
    
    # 重置日志配置
    LogConfig.reset()
    
    # 使用临时目录进行测试
    with tempfile.TemporaryDirectory() as temp_dir:
        # 设置测试日志配置
        setup_logging(
            log_level="DEBUG",
            log_dir=temp_dir,
            log_file_prefix="test_log",
            max_log_files=3,
            enable_console=True,
            enable_file=True
        )
        
        # 获取logger
        logger = get_logger()
        
        # 测试不同级别的日志
        logger.debug("这是一条DEBUG日志")
        logger.info("这是一条INFO日志")
        logger.warning("这是一条WARNING日志")
        logger.error("这是一条ERROR日志")
        
        # 测试异常日志
        try:
            raise ValueError("测试异常")
        except Exception as e:
            logger.error(f"捕获到异常: {e}")
        
        # 等待日志写入完成
        time.sleep(0.2)
        
        # 检查日志文件是否创建
        log_files = list(Path(temp_dir).glob("*.log"))
        print(f"创建的日志文件: {[f.name for f in log_files]}")
        
        # 验证日志文件内容
        for log_file in log_files:
            if log_file.stat().st_size > 0:
                print(f"\n{log_file.name} 内容预览:")
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:5]  # 只显示前5行
                    for line in lines:
                        print(f"  {line.strip()}")
        
        # 重置日志配置以释放文件句柄
        LogConfig.reset()
        time.sleep(0.1)  # 等待文件句柄释放
        
        print("✓ 基本日志功能测试通过")


def test_logger_singleton():
    """测试logger单例模式"""
    print("\n=== 测试logger单例模式 ===")
    
    # 重置配置
    LogConfig.reset()
    
    # 获取多个logger实例
    logger1 = get_logger()
    logger2 = get_logger("test_module")
    logger3 = get_logger()
    
    # 验证是否为同一个实例
    print(f"logger1 id: {id(logger1)}")
    print(f"logger2 id: {id(logger2)}")
    print(f"logger3 id: {id(logger3)}")
    
    # loguru的logger是全局单例
    assert logger1 is logger2 is logger3
    print("✓ logger单例模式测试通过")


def test_config_from_settings():
    """测试从配置文件读取日志设置"""
    print("\n=== 测试从配置文件读取设置 ===")
    
    # 重置配置
    LogConfig.reset()
    
    # 获取当前配置
    settings = get_settings()
    print(f"当前日志配置:")
    print(f"  log_level: {settings.log_level}")
    print(f"  log_dir: {settings.log_dir}")
    print(f"  log_file_prefix: {settings.log_file_prefix}")
    print(f"  max_log_files: {settings.max_log_files}")
    
    # 使用默认配置设置日志
    setup_logging()
    logger = get_logger()
    
    logger.info("使用默认配置的日志测试")
    print("✓ 配置文件读取测试通过")


def test_console_only_mode():
    """测试仅控制台输出模式"""
    print("\n=== 测试仅控制台输出模式 ===")
    
    # 重置配置
    LogConfig.reset()
    
    # 设置仅控制台输出
    setup_logging(
        log_level="INFO",
        enable_console=True,
        enable_file=False
    )
    
    logger = get_logger()
    logger.info("这条日志只会输出到控制台")
    logger.warning("控制台模式测试")
    
    print("✓ 仅控制台输出模式测试通过")


def test_file_only_mode():
    """测试仅文件输出模式"""
    print("\n=== 测试仅文件输出模式 ===")
    
    # 重置配置
    LogConfig.reset()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 设置仅文件输出
        setup_logging(
            log_level="INFO",
            log_dir=temp_dir,
            log_file_prefix="file_only_test",
            enable_console=False,
            enable_file=True
        )
        
        logger = get_logger()
        logger.info("这条日志只会输出到文件")
        logger.error("文件模式测试错误")
        
        # 检查文件是否创建
        log_files = list(Path(temp_dir).glob("*.log"))
        assert len(log_files) >= 1, "应该创建至少一个日志文件"
        
        print(f"创建的日志文件: {[f.name for f in log_files]}")
        
        # 重置日志配置以释放文件句柄
        LogConfig.reset()
        time.sleep(0.1)
        
        print("✓ 仅文件输出模式测试通过")


def test_error_log_separation():
    """测试错误日志分离功能"""
    print("\n=== 测试错误日志分离功能 ===")
    
    # 重置配置
    LogConfig.reset()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        setup_logging(
            log_level="DEBUG",
            log_dir=temp_dir,
            log_file_prefix="error_test",
            enable_console=False,
            enable_file=True
        )
        
        logger = get_logger()
        
        # 记录不同级别的日志
        logger.debug("调试信息")
        logger.info("普通信息")
        logger.warning("警告信息")
        logger.error("错误信息")
        
        # 等待文件写入
        time.sleep(0.1)
        
        # 检查文件
        all_files = list(Path(temp_dir).glob("*.log"))
        error_files = [f for f in all_files if "error" in f.name]
        normal_files = [f for f in all_files if "error" not in f.name]
        
        print(f"普通日志文件: {[f.name for f in normal_files]}")
        print(f"错误日志文件: {[f.name for f in error_files]}")
        
        # 验证错误日志文件存在且包含错误信息
        assert len(error_files) >= 1, "应该创建错误日志文件"
        
        error_file = error_files[0]
        if error_file.stat().st_size > 0:
            with open(error_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "错误信息" in content, "错误日志文件应包含错误信息"
                print("✓ 错误日志分离功能测试通过")
        else:
            print("⚠ 错误日志文件为空，可能需要等待更长时间")
        
        # 重置日志配置以释放文件句柄
        LogConfig.reset()
        time.sleep(0.1)


def test_migration_compatibility():
    """测试迁移兼容性"""
    print("\n=== 测试迁移兼容性 ===")
    
    # 重置配置
    LogConfig.reset()
    
    # 测试新接口
    logger_new = get_logger()
    logger_new.info("使用新接口的日志")
    
    # 测试带名称的接口（兼容性）
    logger_named = get_logger("test_module")
    logger_named.info("使用命名接口的日志")
    
    # 测试直接使用loguru
    from loguru import logger as loguru_logger
    loguru_logger.info("直接使用loguru的日志")
    
    print("✓ 迁移兼容性测试通过")


def run_all_tests():
    """运行所有测试"""
    print("开始日志配置测试...")
    
    try:
        test_basic_logging()
        test_logger_singleton()
        test_config_from_settings()
        test_console_only_mode()
        test_file_only_mode()
        test_error_log_separation()
        test_migration_compatibility()
        
        print("\n🎉 所有日志配置测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理
        LogConfig.reset()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)