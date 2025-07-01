#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
废弃代码清理脚本
自动清理项目中的废弃API引用和相关代码
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Set
from datetime import datetime

# 需要清理的文件模式
DEPRECATED_FILES = {
    "routes": [
        "**/data_routes.py",
        "**/data_backfill_routes.py", 
        "**/optimized_backfill_routes.py"
    ],
    "services": [
        "**/deprecated_*",
        "**/legacy_*"
    ],
    "tests": [
        "**/test_data_routes.py",
        "**/test_data_backfill.py",
        "**/test_optimized_backfill.py"
    ]
}

# 需要清理的导入语句模式
DEPRECATED_IMPORTS = [
    r"from\s+.*data_routes\s+import",
    r"from\s+.*data_backfill_routes\s+import",
    r"from\s+.*optimized_backfill_routes\s+import",
    r"import\s+.*data_routes",
    r"import\s+.*data_backfill_routes",
    r"import\s+.*optimized_backfill_routes"
]

# 需要清理的函数调用模式
DEPRECATED_CALLS = [
    r"set_data_service\s*\(",
    r"create_backfill_task\s*\(",
    r"optimized_full_market_backfill\s*\(",
    r"incremental_update_all_stocks\s*\("
]

# 需要清理的路由注册模式
DEPRECATED_ROUTES = [
    r"app\.include_router\s*\(\s*data_router\s*\)",
    r"app\.include_router\s*\(\s*data_backfill_router\s*\)",
    r"app\.include_router\s*\(\s*optimized_backfill_router\s*\)",
    r"router\.include_router\s*\(\s*data_routes\s*\)",
    r"router\.include_router\s*\(\s*data_backfill_routes\s*\)"
]

# 排除的目录和文件
EXCLUDED_DIRS = {
    ".git", ".vscode", "__pycache__", ".pytest_cache",
    "node_modules", "venv", "env", ".env", "logs", "temp", "data",
    "docs", "examples"  # 保留文档和示例
}

EXCLUDED_FILES = {
    "check_deprecated_apis.py",
    "cleanup_deprecated_code.py",
    "unified_backfill_migration_guide.md",
    "api_deprecation_notice.md"
}

class DeprecatedCodeCleaner:
    """废弃代码清理器"""
    
    def __init__(self, project_root: str, dry_run: bool = True):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.cleaned_files = []
        self.deleted_files = []
        self.backup_dir = None
        
        if not dry_run:
            # 创建备份目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.backup_dir = self.project_root / "temp" / f"cleanup_backup_{timestamp}"
            self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def cleanup_project(self) -> Dict[str, any]:
        """清理整个项目"""
        print(f"🧹 开始清理项目: {self.project_root}")
        print(f"🔧 模式: {'预览模式' if self.dry_run else '执行模式'}")
        
        if not self.dry_run:
            print(f"💾 备份目录: {self.backup_dir}")
        
        print("-" * 60)
        
        # 1. 删除废弃文件
        self._delete_deprecated_files()
        
        # 2. 清理代码引用
        self._cleanup_code_references()
        
        # 3. 清理配置文件
        self._cleanup_config_files()
        
        # 4. 生成清理报告
        return self._generate_cleanup_report()
    
    def _delete_deprecated_files(self):
        """删除废弃文件"""
        print("📁 扫描废弃文件...")
        
        for category, patterns in DEPRECATED_FILES.items():
            for pattern in patterns:
                files = list(self.project_root.glob(pattern))
                
                for file_path in files:
                    if file_path.name in EXCLUDED_FILES:
                        continue
                    
                    if self._should_exclude_path(file_path):
                        continue
                    
                    if file_path.exists():
                        if self.dry_run:
                            print(f"   [预览] 将删除: {file_path.relative_to(self.project_root)}")
                        else:
                            # 备份文件
                            backup_path = self.backup_dir / file_path.relative_to(self.project_root)
                            backup_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(file_path, backup_path)
                            
                            # 删除文件
                            file_path.unlink()
                            print(f"   ✅ 已删除: {file_path.relative_to(self.project_root)}")
                        
                        self.deleted_files.append(str(file_path.relative_to(self.project_root)))
    
    def _cleanup_code_references(self):
        """清理代码引用"""
        print("\n🔍 清理代码引用...")
        
        python_files = list(self.project_root.glob("**/*.py"))
        
        for file_path in python_files:
            if self._should_exclude_path(file_path):
                continue
            
            if file_path.name in EXCLUDED_FILES:
                continue
            
            self._cleanup_file_references(file_path)
    
    def _cleanup_file_references(self, file_path: Path):
        """清理单个文件的引用"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            modified = False
            
            # 清理导入语句
            for pattern in DEPRECATED_IMPORTS:
                if re.search(pattern, content, re.IGNORECASE):
                    content = re.sub(pattern + r".*\n", "", content, flags=re.IGNORECASE)
                    modified = True
            
            # 清理函数调用
            for pattern in DEPRECATED_CALLS:
                if re.search(pattern, content, re.IGNORECASE):
                    # 注释掉而不是删除，保留上下文
                    content = re.sub(
                        f"({pattern}.*)", 
                        r"# DEPRECATED: \1", 
                        content, 
                        flags=re.IGNORECASE
                    )
                    modified = True
            
            # 清理路由注册
            for pattern in DEPRECATED_ROUTES:
                if re.search(pattern, content, re.IGNORECASE):
                    content = re.sub(pattern + r".*\n", "", content, flags=re.IGNORECASE)
                    modified = True
            
            if modified:
                if self.dry_run:
                    print(f"   [预览] 将清理: {file_path.relative_to(self.project_root)}")
                else:
                    # 备份原文件
                    backup_path = self.backup_dir / file_path.relative_to(self.project_root)
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(original_content)
                    
                    # 写入清理后的内容
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print(f"   ✅ 已清理: {file_path.relative_to(self.project_root)}")
                
                self.cleaned_files.append(str(file_path.relative_to(self.project_root)))
        
        except Exception as e:
            print(f"   ❌ 清理失败 {file_path}: {e}")
    
    def _cleanup_config_files(self):
        """清理配置文件"""
        print("\n⚙️ 清理配置文件...")
        
        # 清理requirements.txt中可能的废弃依赖
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            self._cleanup_requirements(requirements_file)
        
        # 清理其他配置文件
        config_files = [
            "pyproject.toml",
            "setup.py",
            "setup.cfg"
        ]
        
        for config_file in config_files:
            config_path = self.project_root / config_file
            if config_path.exists():
                self._cleanup_config_file(config_path)
    
    def _cleanup_requirements(self, requirements_file: Path):
        """清理requirements.txt"""
        try:
            with open(requirements_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 移除可能的废弃依赖注释
            cleaned_lines = []
            for line in lines:
                if not any(dep in line.lower() for dep in ["deprecated", "legacy", "old"]):
                    cleaned_lines.append(line)
            
            if len(cleaned_lines) != len(lines):
                if self.dry_run:
                    print(f"   [预览] 将清理: {requirements_file.name}")
                else:
                    with open(requirements_file, 'w', encoding='utf-8') as f:
                        f.writelines(cleaned_lines)
                    print(f"   ✅ 已清理: {requirements_file.name}")
        
        except Exception as e:
            print(f"   ❌ 清理失败 {requirements_file}: {e}")
    
    def _cleanup_config_file(self, config_file: Path):
        """清理配置文件"""
        # 这里可以添加特定配置文件的清理逻辑
        pass
    
    def _should_exclude_path(self, path: Path) -> bool:
        """检查路径是否应该被排除"""
        # 检查是否在排除目录中
        for part in path.parts:
            if part in EXCLUDED_DIRS:
                return True
        
        # 检查是否是排除文件
        if path.name in EXCLUDED_FILES:
            return True
        
        return False
    
    def _generate_cleanup_report(self) -> Dict[str, any]:
        """生成清理报告"""
        return {
            "cleanup_info": {
                "project_root": str(self.project_root),
                "cleanup_time": datetime.now().isoformat(),
                "dry_run": self.dry_run,
                "backup_dir": str(self.backup_dir) if self.backup_dir else None
            },
            "statistics": {
                "deleted_files_count": len(self.deleted_files),
                "cleaned_files_count": len(self.cleaned_files),
                "total_changes": len(self.deleted_files) + len(self.cleaned_files)
            },
            "deleted_files": self.deleted_files,
            "cleaned_files": self.cleaned_files,
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """生成清理后的建议"""
        recommendations = []
        
        if not self.dry_run:
            recommendations.extend([
                "运行测试套件确保系统正常工作",
                "检查应用启动是否正常",
                "验证API接口是否可访问",
                "更新部署脚本和文档"
            ])
        else:
            recommendations.extend([
                "使用 --execute 参数执行实际清理",
                "在执行前确保代码已提交到版本控制",
                "准备回滚计划以防出现问题"
            ])
        
        recommendations.extend([
            "运行废弃API检查脚本验证清理效果",
            "更新CI/CD流水线配置",
            "通知团队成员API变更"
        ])
        
        return recommendations

def print_cleanup_report(report: Dict[str, any]):
    """打印清理报告"""
    print("\n" + "=" * 80)
    print("🧹 废弃代码清理报告")
    print("=" * 80)
    
    # 基本信息
    info = report["cleanup_info"]
    print(f"\n📋 清理信息:")
    print(f"   项目路径: {info['project_root']}")
    print(f"   清理时间: {info['cleanup_time']}")
    print(f"   执行模式: {'预览模式' if info['dry_run'] else '执行模式'}")
    
    if info['backup_dir']:
        print(f"   备份目录: {info['backup_dir']}")
    
    # 统计信息
    stats = report["statistics"]
    print(f"\n📊 清理统计:")
    print(f"   删除文件数: {stats['deleted_files_count']}")
    print(f"   清理文件数: {stats['cleaned_files_count']}")
    print(f"   总变更数: {stats['total_changes']}")
    
    # 详细信息
    if report["deleted_files"]:
        print(f"\n🗑️ 删除的文件:")
        for file_path in report["deleted_files"]:
            print(f"   - {file_path}")
    
    if report["cleaned_files"]:
        print(f"\n🔧 清理的文件:")
        for file_path in report["cleaned_files"]:
            print(f"   - {file_path}")
    
    # 建议
    print(f"\n💡 后续建议:")
    for i, recommendation in enumerate(report["recommendations"], 1):
        print(f"   {i}. {recommendation}")
    
    print("\n" + "=" * 80)
    if stats['total_changes'] == 0:
        print("✅ 项目已经很干净，无需清理")
    else:
        mode = "预览完成" if info['dry_run'] else "清理完成"
        print(f"🎉 {mode}！共处理 {stats['total_changes']} 项变更")
    print("=" * 80)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="废弃代码清理工具")
    parser.add_argument(
        "--project-root",
        default=".",
        help="项目根目录路径 (默认: 当前目录)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="执行实际清理 (默认: 预览模式)"
    )
    parser.add_argument(
        "--output",
        default="cleanup_report.json",
        help="输出报告文件路径"
    )
    
    args = parser.parse_args()
    
    # 检查项目根目录
    project_root = Path(args.project_root).resolve()
    if not project_root.exists():
        print(f"❌ 项目目录不存在: {project_root}")
        return 1
    
    # 安全检查
    if args.execute:
        response = input("⚠️  您确定要执行实际清理吗？这将删除和修改文件！(y/N): ")
        if response.lower() != 'y':
            print("❌ 清理已取消")
            return 0
    
    # 执行清理
    cleaner = DeprecatedCodeCleaner(str(project_root), dry_run=not args.execute)
    report = cleaner.cleanup_project()
    
    # 输出报告
    print_cleanup_report(report)
    
    # 保存报告
    import json
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n💾 报告已保存到: {args.output}")
    except Exception as e:
        print(f"❌ 保存报告失败: {e}")
    
    return 0

if __name__ == "__main__":
    exit(main())