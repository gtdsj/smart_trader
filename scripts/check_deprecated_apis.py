#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
废弃API检查脚本
扫描项目中对废弃API的使用情况，生成迁移报告
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# 废弃API模式定义
DEPRECATED_APIS = {
    "data_backfill": {
        "patterns": [
            r"/api/v1/data-backfill/task/create",
            r"/api/v1/data-backfill/task/[^/]+",
            r"/api/v1/data-backfill/tasks",
            r"/api/v1/data-backfill/status",
            r"/api/v1/data-backfill/analyze",
            r"data-backfill/task/create",
            r"data_backfill_routes",
            r"BackfillTaskRequest",
            r"create_backfill_task",
            r"get_backfill_status"
        ],
        "replacement": "/api/v1/data/unified-backfill/full-market (mode: 'traditional')",
        "category": "传统数据补全"
    },
    "incremental_update": {
        "patterns": [
            r"/api/v1/data/daily/incremental-update-all",
            r"daily/incremental-update-all",
            r"incremental_update_all_stocks",
            r"incremental-update-all"
        ],
        "replacement": "/api/v1/data/unified-backfill/quick (mode: 'incremental')",
        "category": "增量更新"
    },
    "optimized_backfill": {
        "patterns": [
            r"/api/v1/optimized-backfill/full-market",
            r"/api/v1/optimized-backfill/quick-backfill",
            r"/api/v1/optimized-backfill/config",
            r"/api/v1/optimized-backfill/task/[^/]+",
            r"/api/v1/optimized-backfill/tasks",
            r"/api/v1/optimized-backfill/performance/stats",
            r"optimized-backfill",
            r"optimized_backfill_routes",
            r"OptimizedBackfillRequest",
            r"optimized_full_market_backfill"
        ],
        "replacement": "/api/v1/data/unified-backfill/full-market (mode: 'optimized')",
        "category": "优化补全"
    }
}

# 文件扩展名过滤
SCANNED_EXTENSIONS = {".py", ".js", ".ts", ".md", ".json", ".yaml", ".yml", ".sh", ".bat"}

# 排除目录
EXCLUDED_DIRS = {
    ".git", ".vscode", "__pycache__", ".pytest_cache", 
    "node_modules", "venv", "env", ".env", "logs", "temp", "data"
}

class DeprecatedAPIChecker:
    """废弃API检查器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.findings = []
        self.stats = {
            "total_files_scanned": 0,
            "files_with_deprecated_apis": 0,
            "total_deprecated_usages": 0,
            "by_category": {}
        }
    
    def scan_project(self) -> Dict[str, Any]:
        """扫描整个项目"""
        print(f"🔍 开始扫描项目: {self.project_root}")
        print(f"📁 扫描文件类型: {', '.join(SCANNED_EXTENSIONS)}")
        print(f"🚫 排除目录: {', '.join(EXCLUDED_DIRS)}")
        print("-" * 60)
        
        for file_path in self._get_files_to_scan():
            self._scan_file(file_path)
        
        self._generate_stats()
        return self._generate_report()
    
    def _get_files_to_scan(self) -> List[Path]:
        """获取需要扫描的文件列表"""
        files = []
        
        for root, dirs, filenames in os.walk(self.project_root):
            # 排除指定目录
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            
            for filename in filenames:
                file_path = Path(root) / filename
                if file_path.suffix in SCANNED_EXTENSIONS:
                    files.append(file_path)
        
        return files
    
    def _scan_file(self, file_path: Path):
        """扫描单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            self.stats["total_files_scanned"] += 1
            file_findings = []
            
            for api_type, api_info in DEPRECATED_APIS.items():
                for pattern in api_info["patterns"]:
                    matches = list(re.finditer(pattern, content, re.IGNORECASE))
                    
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = content.split('\n')[line_num - 1].strip()
                        
                        finding = {
                            "file": str(file_path.relative_to(self.project_root)),
                            "line": line_num,
                            "line_content": line_content,
                            "matched_pattern": pattern,
                            "matched_text": match.group(),
                            "api_type": api_type,
                            "category": api_info["category"],
                            "replacement": api_info["replacement"]
                        }
                        
                        file_findings.append(finding)
                        self.findings.append(finding)
            
            if file_findings:
                self.stats["files_with_deprecated_apis"] += 1
                print(f"⚠️  {file_path.relative_to(self.project_root)}: 发现 {len(file_findings)} 个废弃API使用")
        
        except Exception as e:
            print(f"❌ 扫描文件失败 {file_path}: {e}")
    
    def _generate_stats(self):
        """生成统计信息"""
        self.stats["total_deprecated_usages"] = len(self.findings)
        
        # 按类别统计
        for finding in self.findings:
            category = finding["category"]
            if category not in self.stats["by_category"]:
                self.stats["by_category"][category] = {
                    "count": 0,
                    "files": set()
                }
            
            self.stats["by_category"][category]["count"] += 1
            self.stats["by_category"][category]["files"].add(finding["file"])
        
        # 转换set为list以便JSON序列化
        for category in self.stats["by_category"]:
            self.stats["by_category"][category]["files"] = list(
                self.stats["by_category"][category]["files"]
            )
    
    def _generate_report(self) -> Dict[str, Any]:
        """生成检查报告"""
        return {
            "scan_info": {
                "project_root": str(self.project_root),
                "scan_time": datetime.now().isoformat(),
                "scanned_extensions": list(SCANNED_EXTENSIONS),
                "excluded_dirs": list(EXCLUDED_DIRS)
            },
            "statistics": self.stats,
            "findings": self.findings,
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """生成迁移建议"""
        recommendations = []
        
        # 按文件分组建议
        files_by_category = {}
        for finding in self.findings:
            category = finding["category"]
            file_path = finding["file"]
            
            if category not in files_by_category:
                files_by_category[category] = {}
            
            if file_path not in files_by_category[category]:
                files_by_category[category][file_path] = []
            
            files_by_category[category][file_path].append(finding)
        
        # 生成具体建议
        for category, files in files_by_category.items():
            for file_path, file_findings in files.items():
                recommendation = {
                    "priority": self._get_priority(category, len(file_findings)),
                    "category": category,
                    "file": file_path,
                    "issues_count": len(file_findings),
                    "action": self._get_action_for_category(category),
                    "replacement_api": file_findings[0]["replacement"],
                    "estimated_effort": self._estimate_effort(len(file_findings)),
                    "details": file_findings
                }
                recommendations.append(recommendation)
        
        # 按优先级排序
        priority_order = {"高": 1, "中": 2, "低": 3}
        recommendations.sort(key=lambda x: (priority_order.get(x["priority"], 4), -x["issues_count"]))
        
        return recommendations
    
    def _get_priority(self, category: str, count: int) -> str:
        """获取优先级"""
        if count >= 5:
            return "高"
        elif count >= 2:
            return "中"
        else:
            return "低"
    
    def _get_action_for_category(self, category: str) -> str:
        """获取类别对应的行动建议"""
        actions = {
            "传统数据补全": "迁移到统一接口，使用 mode: 'traditional'",
            "增量更新": "迁移到快速补全接口，使用 mode: 'incremental'",
            "优化补全": "迁移到统一接口，使用 mode: 'optimized'"
        }
        return actions.get(category, "请查看迁移指南")
    
    def _estimate_effort(self, count: int) -> str:
        """估算工作量"""
        if count >= 10:
            return "大（2-4小时）"
        elif count >= 5:
            return "中（1-2小时）"
        else:
            return "小（30分钟内）"

def print_report(report: Dict[str, Any]):
    """打印检查报告"""
    print("\n" + "=" * 80)
    print("📊 废弃API检查报告")
    print("=" * 80)
    
    # 基本统计
    stats = report["statistics"]
    print(f"\n📈 扫描统计:")
    print(f"   总文件数: {stats['total_files_scanned']}")
    print(f"   包含废弃API的文件: {stats['files_with_deprecated_apis']}")
    print(f"   废弃API使用总数: {stats['total_deprecated_usages']}")
    
    # 按类别统计
    if stats["by_category"]:
        print(f"\n📋 按类别统计:")
        for category, info in stats["by_category"].items():
            print(f"   {category}: {info['count']} 次使用，涉及 {len(info['files'])} 个文件")
    
    # 迁移建议
    recommendations = report["recommendations"]
    if recommendations:
        print(f"\n🎯 迁移建议 (按优先级排序):")
        print("-" * 80)
        
        for i, rec in enumerate(recommendations, 1):
            priority_emoji = {"高": "🔴", "中": "🟡", "低": "🟢"}
            emoji = priority_emoji.get(rec["priority"], "⚪")
            
            print(f"\n{i}. {emoji} {rec['file']} (优先级: {rec['priority']})")
            print(f"   类别: {rec['category']}")
            print(f"   问题数: {rec['issues_count']}")
            print(f"   预估工作量: {rec['estimated_effort']}")
            print(f"   行动建议: {rec['action']}")
            print(f"   替代接口: {rec['replacement_api']}")
    
    # 总结
    print(f"\n" + "=" * 80)
    if stats["total_deprecated_usages"] == 0:
        print("🎉 恭喜！未发现废弃API的使用")
    else:
        print(f"⚠️  发现 {stats['total_deprecated_usages']} 处废弃API使用，建议尽快迁移")
        print(f"📚 迁移指南: docs/unified_backfill_migration_guide.md")
        print(f"📋 废弃通知: docs/api_deprecation_notice.md")
    print("=" * 80)

def save_report(report: Dict[str, Any], output_file: str):
    """保存报告到文件"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n💾 报告已保存到: {output_file}")
    except Exception as e:
        print(f"❌ 保存报告失败: {e}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="废弃API检查工具")
    parser.add_argument(
        "--project-root", 
        default=".", 
        help="项目根目录路径 (默认: 当前目录)"
    )
    parser.add_argument(
        "--output", 
        default="deprecated_api_report.json", 
        help="输出报告文件路径 (默认: deprecated_api_report.json)"
    )
    parser.add_argument(
        "--quiet", 
        action="store_true", 
        help="静默模式，只输出结果"
    )
    
    args = parser.parse_args()
    
    # 检查项目根目录
    project_root = Path(args.project_root).resolve()
    if not project_root.exists():
        print(f"❌ 项目目录不存在: {project_root}")
        return 1
    
    # 执行检查
    checker = DeprecatedAPIChecker(str(project_root))
    report = checker.scan_project()
    
    # 输出报告
    if not args.quiet:
        print_report(report)
    
    # 保存报告
    save_report(report, args.output)
    
    # 返回退出码
    return 1 if report["statistics"]["total_deprecated_usages"] > 0 else 0

if __name__ == "__main__":
    exit(main())