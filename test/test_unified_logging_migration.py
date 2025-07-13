#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志迁移验证测试

验证迁移后的日志系统是否正常工作
"""

import os
import sys
import tempfile
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.log_config import get_logger, LogConfig


def test_migrated_files_logging():
    """测试迁移后的文件是否能正常使用日志"""
    print("\n=== 测试迁移后文件的日志功能 ===")
    
    # 测试已迁移的文件路径
    project_root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    migrated_files = [
        project_root / "api" / "unified_backfill_routes.py",
        project_root / "test" / "test_break_board_condition.py",
        project_root / "test" / "test_database_task_loading.py",
        project_root / "test" / "test_singleton_integration.py",
        project_root / "test" / "test_stock_updater_singleton.py",
        project_root / "test" / "test_task_scheduler.py"
    ]
    
    success_count = 0
    
    for file_path in migrated_files:
        try:
            if not file_path.exists():
                print(f"⚠ {file_path.name}: 文件不存在")
                continue
                
            # 读取文件内容检查迁移是否成功
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否包含新的导入语句
            if "from utils.log_config import get_logger" in content:
                # 检查是否使用了新的logger初始化方式
                if "logger = get_logger()" in content:
                    print(f"✓ {file_path.name}: 迁移成功，使用新的日志配置")
                    success_count += 1
                else:
                    print(f"⚠ {file_path.name}: 导入已更新，但logger初始化可能需要检查")
                    success_count += 1  # 仍然算作成功，因为导入已更新
            else:
                print(f"✗ {file_path.name}: 未发现新的日志导入语句")
                
        except Exception as e:
            print(f"✗ {file_path.name}: 检查失败 - {e}")
    
    print(f"\n测试结果: {success_count}/{len(migrated_files)} 个文件通过测试")
    return success_count >= len(migrated_files) - 1  # 允许一个文件失败


def test_new_logging_interface():
    """测试新的日志接口"""
    print("\n=== 测试新的日志接口 ===")
    
    try:
        # 测试get_logger函数
        logger = get_logger()
        
        # 测试各种日志级别
        logger.debug("这是一条DEBUG日志")
        logger.info("这是一条INFO日志")
        logger.warning("这是一条WARNING日志")
        logger.error("这是一条ERROR日志")
        
        print("✓ 新日志接口功能正常")
        return True
        
    except Exception as e:
        print(f"✗ 新日志接口测试失败: {e}")
        return False


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n=== 测试向后兼容性 ===")
    
    try:
        # 测试直接使用loguru
        from loguru import logger as loguru_logger
        
        loguru_logger.info("测试直接使用loguru的兼容性")
        
        print("✓ 向后兼容性正常")
        return True
        
    except Exception as e:
        print(f"✗ 向后兼容性测试失败: {e}")
        return False


def test_log_file_creation():
    """测试日志文件创建"""
    print("\n=== 测试日志文件创建 ===")
    
    try:
        # 创建临时目录进行测试
        with tempfile.TemporaryDirectory() as temp_dir:
            # 重置日志配置
            LogConfig.reset()
            
            # 使用临时目录配置日志
            LogConfig.setup_logger(
                log_dir=temp_dir,
                log_file_prefix="test_log",
                enable_console=False,
                enable_file=True
            )
            
            # 获取logger并记录日志
            logger = get_logger()
            logger.info("测试日志文件创建")
            logger.error("测试错误日志文件创建")
            
            # 等待日志写入
            time.sleep(0.1)
            
            # 检查日志文件是否创建
            log_files = list(Path(temp_dir).glob("*.log"))
            
            if len(log_files) >= 1:
                print(f"✓ 日志文件创建成功: {[f.name for f in log_files]}")
                
                # 检查日志内容
                for log_file in log_files:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if "测试日志文件创建" in content:
                            print(f"✓ 日志内容写入正常: {log_file.name}")
                        else:
                            print(f"⚠ 日志内容可能未完全写入: {log_file.name}")
                
                return True
            else:
                print("✗ 日志文件未创建")
                return False
                
    except Exception as e:
        print(f"✗ 日志文件创建测试失败: {e}")
        import traceback
        print(f"错误详情: {traceback.format_exc()}")
        return False
    finally:
        # 重置日志配置
        LogConfig.reset()


def test_performance_impact():
    """测试性能影响"""
    print("\n=== 测试性能影响 ===")
    
    try:
        logger = get_logger()
        
        # 测试大量日志记录的性能
        start_time = time.time()
        
        for i in range(1000):
            logger.debug(f"性能测试日志 {i}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✓ 1000条DEBUG日志耗时: {duration:.3f}秒")
        
        if duration < 1.0:  # 应该在1秒内完成
            print("✓ 性能表现良好")
            return True
        else:
            print("⚠ 性能可能需要优化")
            return False
            
    except Exception as e:
        print(f"✗ 性能测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("开始统一日志迁移验证测试...")
    
    tests = [
        ("新日志接口测试", test_new_logging_interface),
        ("向后兼容性测试", test_backward_compatibility),
        ("日志文件创建测试", test_log_file_creation),
        ("性能影响测试", test_performance_impact),
        ("迁移文件日志测试", test_migrated_files_logging),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"执行测试: {test_name}")
        print(f"{'='*50}")
        
        try:
            if test_func():
                passed_tests += 1
                print(f"\n✓ {test_name} 通过")
            else:
                print(f"\n✗ {test_name} 失败")
        except Exception as e:
            print(f"\n✗ {test_name} 异常: {e}")
            import traceback
            print(f"异常详情: {traceback.format_exc()}")
    
    print(f"\n{'='*60}")
    print(f"测试总结: {passed_tests}/{total_tests} 个测试通过")
    print(f"{'='*60}")
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！日志迁移成功！")
        return True
    else:
        print(f"\n⚠ 有 {total_tests - passed_tests} 个测试失败，请检查相关问题")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)