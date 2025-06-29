# coding=utf-8
"""
数据补全工具类
提供数据补全相关的工具函数和辅助方法
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, date
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from loguru import logger

from config.data_backfill_config import DataBackfillConfig, DATA_QUALITY_CONFIG


class TaskStatus(Enum):
    """任务状态枚举"""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class BackfillProgress:
    """数据补全进度信息"""
    task_id: str
    total_stocks: int
    processed_stocks: int
    success_count: int
    failed_count: int
    current_stock: Optional[str] = None
    start_time: Optional[datetime] = None
    estimated_end_time: Optional[datetime] = None
    
    @property
    def progress_percentage(self) -> float:
        """进度百分比"""
        if self.total_stocks == 0:
            return 0.0
        return round((self.processed_stocks / self.total_stocks) * 100, 2)
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.processed_stocks == 0:
            return 0.0
        return round((self.success_count / self.processed_stocks) * 100, 2)
    
    @property
    def remaining_stocks(self) -> int:
        """剩余股票数量"""
        return max(0, self.total_stocks - self.processed_stocks)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "total_stocks": self.total_stocks,
            "processed_stocks": self.processed_stocks,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "current_stock": self.current_stock,
            "progress_percentage": self.progress_percentage,
            "success_rate": self.success_rate,
            "remaining_stocks": self.remaining_stocks,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "estimated_end_time": self.estimated_end_time.isoformat() if self.estimated_end_time else None
        }


class DataBackfillUtils:
    """数据补全工具类"""
    
    @staticmethod
    def validate_stock_code(stock_code: str) -> bool:
        """验证股票代码格式"""
        if not stock_code or not isinstance(stock_code, str):
            return False
        
        # 检查格式：6位数字.市场代码
        parts = stock_code.split('.')
        if len(parts) != 2:
            return False
        
        code, market = parts
        if len(code) != 6 or not code.isdigit():
            return False
        
        if market not in ['SH', 'SZ']:
            return False
        
        return True
    
    @staticmethod
    def filter_stock_codes(stock_codes: List[str], market: str = "ALL") -> List[str]:
        """根据市场过滤股票代码"""
        if market == "ALL":
            return [code for code in stock_codes if DataBackfillUtils.validate_stock_code(code)]
        
        filtered_codes = []
        for code in stock_codes:
            if DataBackfillUtils.validate_stock_code(code):
                if code.endswith(f'.{market}'):
                    filtered_codes.append(code)
        
        return filtered_codes
    
    @staticmethod
    def calculate_trading_days(start_date: str, end_date: str) -> int:
        """计算交易日数量（简化版本，不考虑节假日）"""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            # 简化计算：假设每周5个交易日
            total_days = (end - start).days + 1
            weeks = total_days // 7
            remaining_days = total_days % 7
            
            # 估算交易日
            trading_days = weeks * 5
            
            # 处理剩余天数（简化处理）
            if remaining_days > 0:
                # 假设剩余天数中有70%是交易日
                trading_days += int(remaining_days * 0.7)
            
            return max(1, trading_days)
            
        except ValueError:
            return 0
    
    @staticmethod
    def estimate_completion_time(total_stocks: int, batch_size: int, 
                               delay_seconds: float, avg_processing_time: float = 2.0) -> datetime:
        """估算完成时间"""
        # 计算批次数量
        batch_count = (total_stocks + batch_size - 1) // batch_size
        
        # 估算总时间（秒）
        total_time = (
            batch_count * avg_processing_time +  # 处理时间
            (batch_count - 1) * delay_seconds    # 延迟时间
        )
        
        return datetime.now() + timedelta(seconds=total_time)
    
    @staticmethod
    def analyze_stock_completeness(stock_data: Dict[str, Any], 
                                 expected_trading_days: int) -> Dict[str, Any]:
        """分析单只股票的数据完整度"""
        stock_code = stock_data.get("stock_code", "")
        actual_records = stock_data.get("record_count", 0)
        latest_date = stock_data.get("latest_date")
        earliest_date = stock_data.get("earliest_date")
        
        # 计算完整度
        completeness = 0.0
        if expected_trading_days > 0:
            completeness = min(100.0, (actual_records / expected_trading_days) * 100)
        
        # 计算缺失天数
        missing_days = max(0, expected_trading_days - actual_records)
        
        # 计算数据落后天数
        days_behind = 0
        if latest_date:
            try:
                if isinstance(latest_date, str):
                    latest = datetime.strptime(latest_date, "%Y-%m-%d").date()
                else:
                    latest = latest_date
                
                today = datetime.now().date()
                days_behind = (today - latest).days
            except (ValueError, TypeError):
                days_behind = 999  # 无法解析日期
        
        # 数据质量等级
        quality_level = DataBackfillConfig.get_completeness_level(completeness)
        
        return {
            "stock_code": stock_code,
            "completeness": round(completeness, 2),
            "quality_level": quality_level,
            "actual_records": actual_records,
            "expected_records": expected_trading_days,
            "missing_days": missing_days,
            "days_behind": days_behind,
            "latest_date": latest_date,
            "earliest_date": earliest_date,
            "needs_update": completeness < 95 or days_behind > 3
        }
    
    @staticmethod
    def prioritize_stocks(stock_analysis: List[Dict[str, Any]], 
                         priority_mode: str = "completeness") -> List[Dict[str, Any]]:
        """对股票进行优先级排序"""
        if priority_mode == "completeness":
            # 按完整度升序排列（完整度低的优先）
            return sorted(stock_analysis, key=lambda x: x.get("completeness", 0))
        
        elif priority_mode == "days_behind":
            # 按落后天数降序排列（落后多的优先）
            return sorted(stock_analysis, key=lambda x: x.get("days_behind", 0), reverse=True)
        
        elif priority_mode == "missing_records":
            # 按缺失记录数降序排列（缺失多的优先）
            return sorted(stock_analysis, key=lambda x: x.get("missing_days", 0), reverse=True)
        
        elif priority_mode == "balanced":
            # 综合评分：完整度权重0.4，落后天数权重0.3，缺失记录权重0.3
            def calculate_priority_score(stock):
                completeness = stock.get("completeness", 0)
                days_behind = min(stock.get("days_behind", 0), 30)  # 限制最大值
                missing_ratio = stock.get("missing_days", 0) / max(stock.get("expected_records", 1), 1)
                
                # 分数越高优先级越高
                score = (
                    (100 - completeness) * 0.4 +  # 完整度越低分数越高
                    days_behind * 0.3 +           # 落后天数越多分数越高
                    missing_ratio * 100 * 0.3     # 缺失比例越高分数越高
                )
                return score
            
            return sorted(stock_analysis, key=calculate_priority_score, reverse=True)
        
        else:
            # 默认按股票代码排序
            return sorted(stock_analysis, key=lambda x: x.get("stock_code", ""))
    
    @staticmethod
    def validate_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
        """验证数据质量"""
        if df is None or df.empty:
            return {
                "is_valid": False,
                "errors": ["数据为空"],
                "warnings": [],
                "record_count": 0
            }
        
        errors = []
        warnings = []
        
        # 检查必需列
        required_columns = DATA_QUALITY_CONFIG["required_columns"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"缺少必需列: {missing_columns}")
        
        if not errors:  # 只有在有必需列的情况下才进行进一步检查
            # 检查价格范围
            price_columns = ["open", "high", "low", "close"]
            for col in price_columns:
                if col in df.columns:
                    min_price = DATA_QUALITY_CONFIG["min_price"]
                    max_price = DATA_QUALITY_CONFIG["max_price"]
                    
                    invalid_prices = df[(df[col] < min_price) | (df[col] > max_price)]
                    if not invalid_prices.empty:
                        warnings.append(f"{col}列有{len(invalid_prices)}个异常价格")
            
            # 检查成交量
            if "volume" in df.columns:
                min_volume = DATA_QUALITY_CONFIG["min_volume"]
                invalid_volume = df[df["volume"] < min_volume]
                if not invalid_volume.empty:
                    warnings.append(f"成交量列有{len(invalid_volume)}个异常值")
            
            # 检查价格逻辑关系
            if all(col in df.columns for col in ["open", "high", "low", "close"]):
                # 最高价应该 >= 开盘价、收盘价、最低价
                invalid_high = df[
                    (df["high"] < df["open"]) | 
                    (df["high"] < df["close"]) | 
                    (df["high"] < df["low"])
                ]
                if not invalid_high.empty:
                    warnings.append(f"有{len(invalid_high)}条记录的最高价逻辑异常")
                
                # 最低价应该 <= 开盘价、收盘价、最高价
                invalid_low = df[
                    (df["low"] > df["open"]) | 
                    (df["low"] > df["close"]) | 
                    (df["low"] > df["high"])
                ]
                if not invalid_low.empty:
                    warnings.append(f"有{len(invalid_low)}条记录的最低价逻辑异常")
        
        # 检查重复日期
        if "date" in df.columns:
            duplicate_dates = df[df.duplicated(subset=["date"])]
            if not duplicate_dates.empty:
                errors.append(f"有{len(duplicate_dates)}个重复日期")
        
        # 检查空值
        null_counts = df.isnull().sum()
        significant_nulls = null_counts[null_counts > len(df) * 0.1]  # 超过10%的空值
        if not significant_nulls.empty:
            warnings.append(f"以下列有较多空值: {dict(significant_nulls)}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "record_count": len(df),
            "date_range": {
                "start": df["date"].min() if "date" in df.columns else None,
                "end": df["date"].max() if "date" in df.columns else None
            } if "date" in df.columns and not df.empty else None
        }
    
    @staticmethod
    def generate_task_summary(task_info: Dict[str, Any]) -> str:
        """生成任务摘要"""
        task_name = task_info.get("task_name", "未知任务")
        status = task_info.get("status", "unknown")
        success_count = task_info.get("success_count", 0)
        failed_count = task_info.get("failed_count", 0)
        total_stocks = task_info.get("total_stocks", 0)
        
        if status == "completed":
            success_rate = task_info.get("success_rate", 0)
            return f"✅ {task_name} 已完成，成功率 {success_rate}%（{success_count}/{total_stocks}）"
        elif status == "failed":
            error = task_info.get("error", "未知错误")
            return f"❌ {task_name} 执行失败：{error}"
        elif status == "cancelled":
            return f"⏹️ {task_name} 已取消"
        elif status == "running":
            progress = task_info.get("progress", 0)
            return f"🔄 {task_name} 执行中，进度 {progress}%（{success_count + failed_count}/{total_stocks}）"
        else:
            return f"📋 {task_name} 状态：{status}"
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """格式化持续时间"""
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}分钟"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}小时"
    
    @staticmethod
    def calculate_eta(progress: BackfillProgress) -> Optional[datetime]:
        """计算预计完成时间"""
        if not progress.start_time or progress.processed_stocks == 0:
            return None
        
        elapsed_time = datetime.now() - progress.start_time
        elapsed_seconds = elapsed_time.total_seconds()
        
        # 计算平均处理速度（股票/秒）
        processing_rate = progress.processed_stocks / elapsed_seconds
        
        if processing_rate <= 0:
            return None
        
        # 计算剩余时间
        remaining_seconds = progress.remaining_stocks / processing_rate
        
        return datetime.now() + timedelta(seconds=remaining_seconds)
    
    @staticmethod
    def export_task_report(task_info: Dict[str, Any], 
                          detailed_results: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """导出任务报告"""
        report = {
            "task_summary": {
                "task_id": task_info.get("task_id"),
                "task_name": task_info.get("task_name"),
                "status": task_info.get("status"),
                "start_time": task_info.get("start_time"),
                "end_time": task_info.get("end_time"),
                "duration": None
            },
            "statistics": {
                "total_stocks": task_info.get("total_stocks", 0),
                "success_count": task_info.get("success_count", 0),
                "failed_count": task_info.get("failed_count", 0),
                "success_rate": task_info.get("success_rate", 0)
            },
            "configuration": {
                "market": task_info.get("market"),
                "batch_size": task_info.get("batch_size"),
                "delay_seconds": task_info.get("delay_seconds"),
                "force_update": task_info.get("force_update"),
                "priority": task_info.get("priority")
            }
        }
        
        # 计算持续时间
        if task_info.get("start_time") and task_info.get("end_time"):
            try:
                start = datetime.fromisoformat(task_info["start_time"])
                end = datetime.fromisoformat(task_info["end_time"])
                duration = (end - start).total_seconds()
                report["task_summary"]["duration"] = DataBackfillUtils.format_duration(duration)
            except (ValueError, TypeError):
                pass
        
        # 添加详细结果
        if detailed_results:
            report["detailed_results"] = {
                "failed_stocks": task_info.get("failed_stocks", []),
                "success_stocks": task_info.get("processed_stocks", []),
                "error_analysis": DataBackfillUtils._analyze_errors(detailed_results)
            }
        
        return report
    
    @staticmethod
    def _analyze_errors(results: List[Dict]) -> Dict[str, Any]:
        """分析错误模式"""
        error_types = {}
        error_stocks = []
        
        for result in results:
            if result.get("status") == "failed":
                error = result.get("error", "未知错误")
                error_type = error.split(":")[0] if ":" in error else error
                
                if error_type not in error_types:
                    error_types[error_type] = 0
                error_types[error_type] += 1
                
                error_stocks.append({
                    "stock_code": result.get("stock_code"),
                    "error": error
                })
        
        return {
            "error_types": error_types,
            "error_stocks": error_stocks[:10],  # 只返回前10个错误
            "total_errors": len(error_stocks)
        }