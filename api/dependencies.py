"""API依赖注入模块"""

from services.data_service import DataService
from services.optimized_backfill_service import OptimizedBackfillService
from services.trading_service import TradingService
from services.strategy_manager import StrategyManager
from services.notification_service import NotificationService
from services.backtest_service import BacktestService
from services.scheduler_service import SchedulerService


def get_data_service() -> DataService:
    """获取数据服务实例（单例模式）"""
    return DataService.get_instance()


def get_optimized_backfill_service() -> OptimizedBackfillService:
    """获取优化补全服务实例"""
    return OptimizedBackfillService()


def get_trading_service() -> TradingService:
    """获取交易服务实例"""
    return TradingService()


def get_strategy_manager() -> StrategyManager:
    """获取策略管理器实例（单例）"""
    return StrategyManager.get_instance()


def get_notification_service() -> NotificationService:
    """获取通知服务实例"""
    return NotificationService()


def get_backtest_service() -> BacktestService:
    """获取回测服务实例"""
    return BacktestService()


def get_scheduler_service() -> SchedulerService:
    """获取调度服务实例"""
    return SchedulerService()