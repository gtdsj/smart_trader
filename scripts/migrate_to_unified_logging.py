#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志系统迁移脚本

自动将使用 utils.logger 的文件迁移到新的统一日志配置
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.log_config import get_logger

logger = get_logger()


class LoggingMigrator:
    """日志系统迁移器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.migration_stats = {
            "total_files": 0,
            "migrated_files": 0,
            "skipped_files": 0,
            "error_files": 0,
            "backup_created": 0
        }
        
        # 需要迁移的文件模式
        self.target_patterns = [
            r"from utils\.logger import get_logger",
            r"from utils import logger",
            r"import utils\.logger"
        ]
        
        # 替换规则
        self.replacement_rules = [
            {
                "pattern": r"from utils\.logger import get_logger",
                "replacement": "from utils.log_config import get_logger"
            },
            {
                "pattern": r"logger = get_logger\(__name__\)",
                "replacement": "logger = get_logger()"
            },
            {
                "pattern": r"logger = get_logger\(['\"].*?['\"]\)",
                "replacement": "logger = get_logger()"
            }
        ]
    
    def find_target_files(self) -> List[Path]:
        """查找需要迁移的文件"""
        target_files = []
        
        # 搜索所有Python文件
        for py_file in self.project_root.rglob("*.py"):
            # 跳过特定目录
            if any(part in str(py_file) for part in [".git", "__pycache__", ".pytest_cache"]):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查是否包含目标模式
                for pattern in self.target_patterns:
                    if re.search(pattern, content):
                        target_files.append(py_file)
                        break
                        
            except Exception as e:
                logger.warning(f"读取文件失败 {py_file}: {e}")
        
        return target_files
    
    def analyze_file(self, file_path: Path) -> Dict:
        """分析文件的迁移需求"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            analysis = {
                "file_path": file_path,
                "needs_migration": False,
                "patterns_found": [],
                "estimated_changes": 0,
                "content": content
            }
            
            # 检查每个模式
            for pattern in self.target_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    analysis["needs_migration"] = True
                    analysis["patterns_found"].extend(matches)
            
            # 估算需要的更改数量
            for rule in self.replacement_rules:
                matches = re.findall(rule["pattern"], content)
                analysis["estimated_changes"] += len(matches)
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析文件失败 {file_path}: {e}")
            return {"file_path": file_path, "error": str(e)}
    
    def create_backup(self, file_path: Path) -> Path:
        """创建文件备份"""
        backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
        
        try:
            import shutil
            shutil.copy2(file_path, backup_path)
            self.migration_stats["backup_created"] += 1
            logger.debug(f"创建备份: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"创建备份失败 {file_path}: {e}")
            raise
    
    def migrate_file(self, file_path: Path, create_backup: bool = True) -> bool:
        """迁移单个文件"""
        try:
            # 分析文件
            analysis = self.analyze_file(file_path)
            
            if "error" in analysis:
                logger.error(f"文件分析失败: {analysis['error']}")
                self.migration_stats["error_files"] += 1
                return False
            
            if not analysis["needs_migration"]:
                logger.info(f"文件无需迁移: {file_path}")
                self.migration_stats["skipped_files"] += 1
                return True
            
            # 创建备份
            if create_backup:
                self.create_backup(file_path)
            
            # 应用替换规则
            content = analysis["content"]
            changes_made = 0
            
            for rule in self.replacement_rules:
                new_content, count = re.subn(rule["pattern"], rule["replacement"], content)
                if count > 0:
                    content = new_content
                    changes_made += count
                    logger.debug(f"应用规则 '{rule['pattern']}': {count} 次替换")
            
            # 写入修改后的内容
            if changes_made > 0:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"迁移完成: {file_path} ({changes_made} 处修改)")
                self.migration_stats["migrated_files"] += 1
                return True
            else:
                logger.warning(f"未发现需要替换的内容: {file_path}")
                self.migration_stats["skipped_files"] += 1
                return True
                
        except Exception as e:
            logger.error(f"迁移文件失败 {file_path}: {e}")
            self.migration_stats["error_files"] += 1
            return False
    
    def migrate_all(self, dry_run: bool = False, create_backup: bool = True) -> Dict:
        """迁移所有目标文件"""
        logger.info("开始日志系统迁移...")
        
        # 查找目标文件
        target_files = self.find_target_files()
        self.migration_stats["total_files"] = len(target_files)
        
        logger.info(f"找到 {len(target_files)} 个需要检查的文件")
        
        if dry_run:
            logger.info("=== 干运行模式 - 仅分析，不修改文件 ===")
        
        # 处理每个文件
        for file_path in target_files:
            logger.info(f"处理文件: {file_path}")
            
            if dry_run:
                # 干运行：仅分析
                analysis = self.analyze_file(file_path)
                if "error" not in analysis and analysis["needs_migration"]:
                    logger.info(f"  需要迁移: {analysis['estimated_changes']} 处修改")
                    logger.info(f"  发现模式: {analysis['patterns_found']}")
                else:
                    logger.info("  无需迁移")
            else:
                # 实际迁移
                self.migrate_file(file_path, create_backup)
        
        # 输出统计信息
        self.print_migration_stats()
        
        return self.migration_stats
    
    def print_migration_stats(self):
        """打印迁移统计信息"""
        stats = self.migration_stats
        
        logger.info("\n=== 迁移统计 ===")
        logger.info(f"总文件数: {stats['total_files']}")
        logger.info(f"成功迁移: {stats['migrated_files']}")
        logger.info(f"跳过文件: {stats['skipped_files']}")
        logger.info(f"错误文件: {stats['error_files']}")
        logger.info(f"创建备份: {stats['backup_created']}")
        
        if stats['total_files'] > 0:
            success_rate = (stats['migrated_files'] + stats['skipped_files']) / stats['total_files'] * 100
            logger.info(f"成功率: {success_rate:.1f}%")
    
    def cleanup_backups(self):
        """清理备份文件"""
        logger.info("清理备份文件...")
        
        backup_files = list(self.project_root.rglob("*.backup"))
        
        for backup_file in backup_files:
            try:
                backup_file.unlink()
                logger.debug(f"删除备份: {backup_file}")
            except Exception as e:
                logger.error(f"删除备份失败 {backup_file}: {e}")
        
        logger.info(f"清理完成，删除了 {len(backup_files)} 个备份文件")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="日志系统迁移工具")
    parser.add_argument("--dry-run", action="store_true", help="干运行模式，仅分析不修改")
    parser.add_argument("--no-backup", action="store_true", help="不创建备份文件")
    parser.add_argument("--cleanup", action="store_true", help="清理备份文件")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    
    args = parser.parse_args()
    
    # 获取项目根目录
    project_root = os.path.abspath(args.project_root)
    
    logger.info(f"项目根目录: {project_root}")
    
    # 创建迁移器
    migrator = LoggingMigrator(project_root)
    
    if args.cleanup:
        migrator.cleanup_backups()
        return
    
    # 执行迁移
    try:
        stats = migrator.migrate_all(
            dry_run=args.dry_run,
            create_backup=not args.no_backup
        )
        
        if stats["error_files"] > 0:
            logger.warning(f"迁移完成，但有 {stats['error_files']} 个文件出现错误")
            sys.exit(1)
        else:
            logger.info("迁移成功完成！")
            
    except Exception as e:
        logger.error(f"迁移过程出现错误: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()