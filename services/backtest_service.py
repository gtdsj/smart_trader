# -*- coding: utf-8 -*-
"""
回测服务模块
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import pandas as pd
import numpy as np
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, and_, desc

from config import get_settings
from core.database import get_db, BacktestResult, Strategy
from core.redis_client import get_redis
from services.notification_service import NotificationService
from services.data_service import DataService
from services.strategy_service import StrategyService, SignalType


class BacktestStatus(Enum):
    """回测状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Position:
    """持仓类"""
    
    def __init__(self, stock_code: str, quantity: int, avg_price: float, 
                 entry_time: datetime, entry_reason: str = ""):
        self.stock_code = stock_code
        self.quantity = quantity
        self.avg_price = avg_price
        self.entry_time = entry_time
        self.entry_reason = entry_reason
        self.unrealized_pnl = 0.0
        self.market_value = 0.0
    
    def update_market_value(self, current_price: float):
        """更新市值和未实现盈亏"""
        self.market_value = self.quantity * current_price
        self.unrealized_pnl = (current_price - self.avg_price) * self.quantity
    
    def get_return_rate(self, current_price: float) -> float:
        """获取收益率"""
        return (current_price - self.avg_price) / self.avg_price


class Trade:
    """交易记录类"""
    
    def __init__(self, stock_code: str, action: str, quantity: int, 
                 price: float, timestamp: datetime, reason: str = ""):
        self.stock_code = stock_code
        self.action = action  # BUY, SELL
        self.quantity = quantity
        self.price = price
        self.timestamp = timestamp
        self.reason = reason
        self.amount = quantity * price
        self.commission = self.amount * 0.0003  # 手续费0.03%
        self.net_amount = self.amount + self.commission if action == "BUY" else self.amount - self.commission


class Portfolio:
    """投资组合类"""
    
    def __init__(self, initial_capital: float = 1000000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.daily_values: List[Dict[str, Any]] = []
        
        # 统计指标
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_commission = 0.0
        self.max_drawdown = 0.0
        self.max_portfolio_value = initial_capital
    
    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        """获取总资产价值"""
        total_value = self.cash
        
        for stock_code, position in self.positions.items():
            if stock_code in current_prices:
                position.update_market_value(current_prices[stock_code])
                total_value += position.market_value
        
        return total_value
    
    def get_positions_value(self, current_prices: Dict[str, float]) -> float:
        """获取持仓总价值"""
        total_value = 0.0
        
        for stock_code, position in self.positions.items():
            if stock_code in current_prices:
                position.update_market_value(current_prices[stock_code])
                total_value += position.market_value
        
        return total_value
    
    def buy_stock(self, stock_code: str, quantity: int, price: float, 
                  timestamp: datetime, reason: str = "") -> bool:
        """买入股票"""
        trade = Trade(stock_code, "BUY", quantity, price, timestamp, reason)
        
        if self.cash < trade.net_amount:
            return False  # 资金不足
        
        # 更新现金
        self.cash -= trade.net_amount
        self.total_commission += trade.commission
        
        # 更新持仓
        if stock_code in self.positions:
            # 已有持仓，计算平均成本
            old_position = self.positions[stock_code]
            total_quantity = old_position.quantity + quantity
            total_cost = old_position.quantity * old_position.avg_price + quantity * price
            avg_price = total_cost / total_quantity
            
            self.positions[stock_code] = Position(
                stock_code, total_quantity, avg_price, old_position.entry_time, reason
            )
        else:
            # 新建持仓
            self.positions[stock_code] = Position(
                stock_code, quantity, price, timestamp, reason
            )
        
        # 记录交易
        self.trades.append(trade)
        self.total_trades += 1
        
        return True
    
    def sell_stock(self, stock_code: str, quantity: int, price: float, 
                   timestamp: datetime, reason: str = "") -> bool:
        """卖出股票"""
        if stock_code not in self.positions:
            return False  # 无持仓
        
        position = self.positions[stock_code]
        if position.quantity < quantity:
            return False  # 持仓不足
        
        trade = Trade(stock_code, "SELL", quantity, price, timestamp, reason)
        
        # 更新现金
        self.cash += trade.net_amount
        self.total_commission += trade.commission
        
        # 更新持仓
        position.quantity -= quantity
        if position.quantity == 0:
            del self.positions[stock_code]
        
        # 计算盈亏
        pnl = (price - position.avg_price) * quantity - trade.commission
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # 记录交易
        self.trades.append(trade)
        self.total_trades += 1
        
        return True
    
    def update_daily_value(self, date: datetime, current_prices: Dict[str, float]):
        """更新每日价值"""
        total_value = self.get_total_value(current_prices)
        positions_value = self.get_positions_value(current_prices)
        
        # 更新最大回撤
        if total_value > self.max_portfolio_value:
            self.max_portfolio_value = total_value
        
        drawdown = (self.max_portfolio_value - total_value) / self.max_portfolio_value
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        
        daily_record = {
            "date": date,
            "total_value": total_value,
            "cash": self.cash,
            "positions_value": positions_value,
            "daily_return": 0.0,
            "cumulative_return": (total_value - self.initial_capital) / self.initial_capital,
            "drawdown": drawdown
        }
        
        # 计算日收益率
        if self.daily_values:
            prev_value = self.daily_values[-1]["total_value"]
            daily_record["daily_return"] = (total_value - prev_value) / prev_value
        
        self.daily_values.append(daily_record)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取绩效指标"""
        if not self.daily_values:
            return {}
        
        # 计算收益率序列
        returns = [record["daily_return"] for record in self.daily_values[1:]]
        
        if not returns:
            return {}
        
        returns_array = np.array(returns)
        
        # 基本指标
        total_return = self.daily_values[-1]["cumulative_return"]
        annual_return = (1 + total_return) ** (252 / len(self.daily_values)) - 1
        volatility = np.std(returns_array) * np.sqrt(252)
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0
        
        # 胜率
        win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        
        # 最大连续亏损
        max_consecutive_losses = 0
        consecutive_losses = 0
        for ret in returns:
            if ret < 0:
                consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            else:
                consecutive_losses = 0
        
        return {
            "total_return": total_return,
            "annual_return": annual_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": win_rate,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "total_commission": self.total_commission,
            "max_consecutive_losses": max_consecutive_losses,
            "final_value": self.daily_values[-1]["total_value"],
            "initial_capital": self.initial_capital
        }


class BacktestService:
    """回测服务"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = get_redis()
        self.notification_service = NotificationService()
        self.data_service = None  # 延迟初始化
        self.strategy_service = None  # 延迟初始化
        
        # 回测任务队列
        self.running_backtests: Dict[str, Dict[str, Any]] = {}
    
    def set_data_service(self, data_service: DataService):
        """设置数据服务"""
        self.data_service = data_service
    
    def set_strategy_service(self, strategy_service: StrategyService):
        """设置策略服务"""
        self.strategy_service = strategy_service
    
    async def create_backtest(self, name: str, description: str, 
                            strategy_name: str, start_date: str, end_date: str,
                            initial_capital: float = 1000000.0,
                            stock_pool: Optional[List[str]] = None,
                            parameters: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """创建回测任务"""
        try:
            backtest_id = f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backtest_config = {
                "id": backtest_id,
                "name": name,
                "description": description,
                "strategy_name": strategy_name,
                "start_date": start_date,
                "end_date": end_date,
                "initial_capital": initial_capital,
                "stock_pool": stock_pool or [],
                "parameters": parameters or {},
                "status": BacktestStatus.PENDING.value,
                "created_at": datetime.now().isoformat()
            }
            
            # 保存到数据库
            async for db in get_db():
                backtest_data = {
                    "backtest_id": backtest_id,
                    "name": name,
                    "description": description,
                    "strategy_name": strategy_name,
                    "start_date": datetime.strptime(start_date, "%Y-%m-%d"),
                    "end_date": datetime.strptime(end_date, "%Y-%m-%d"),
                    "initial_capital": initial_capital,
                    "parameters": parameters or {},
                    "status": BacktestStatus.PENDING.value,
                    "created_at": datetime.now()
                }
                
                stmt = insert(BacktestResult).values(**backtest_data)
                await db.execute(stmt)
                await db.commit()
            
            # 缓存配置
            await self.redis_client.set(f"backtest_config:{backtest_id}", backtest_config, expire=86400)
            
            logger.info(f"创建回测任务: {backtest_id}")
            return backtest_id
            
        except Exception as e:
            logger.error(f"创建回测任务失败: {e}")
            return None
    
    async def start_backtest(self, backtest_id: str) -> bool:
        """启动回测"""
        try:
            # 获取回测配置
            config = await self.redis_client.get(f"backtest_config:{backtest_id}")
            if not config:
                logger.error(f"回测配置不存在: {backtest_id}")
                return False
            
            # 更新状态
            await self._update_backtest_status(backtest_id, BacktestStatus.RUNNING)
            
            # 异步执行回测
            asyncio.create_task(self._run_backtest(backtest_id, config))
            
            logger.info(f"启动回测: {backtest_id}")
            return True
            
        except Exception as e:
            logger.error(f"启动回测失败: {e}")
            await self._update_backtest_status(backtest_id, BacktestStatus.FAILED)
            return False
    
    async def get_backtest_list(self) -> List[Dict[str, Any]]:
        """获取回测列表"""
        try:
            async for db in get_db():
                query = select(BacktestResult).order_by(desc(BacktestResult.created_at))
                result = await db.execute(query)
                backtests = result.scalars().all()
                
                return [
                    {
                        "id": bt.id,
                        "backtest_id": bt.backtest_id,
                        "name": bt.name,
                        "description": bt.description,
                        "strategy_name": bt.strategy_name,
                        "start_date": bt.start_date.strftime("%Y-%m-%d") if bt.start_date else None,
                        "end_date": bt.end_date.strftime("%Y-%m-%d") if bt.end_date else None,
                        "initial_capital": bt.initial_capital,
                        "status": bt.status,
                        "total_return": bt.total_return,
                        "annual_return": bt.annual_return,
                        "max_drawdown": bt.max_drawdown,
                        "sharpe_ratio": bt.sharpe_ratio,
                        "created_at": bt.created_at.isoformat() if bt.created_at else None,
                        "completed_at": bt.completed_at.isoformat() if bt.completed_at else None
                    }
                    for bt in backtests
                ]
                
        except Exception as e:
            logger.error(f"获取回测列表失败: {e}")
            return []
    
    async def get_backtest_result(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """获取回测结果"""
        try:
            async for db in get_db():
                query = select(BacktestResult).where(BacktestResult.backtest_id == backtest_id)
                result = await db.execute(query)
                backtest = result.scalar_one_or_none()
                
                if not backtest:
                    return None
                
                # 获取详细结果
                detailed_result = await self.redis_client.get(f"backtest_result:{backtest_id}")
                
                base_result = {
                    "id": backtest.id,
                    "backtest_id": backtest.backtest_id,
                    "name": backtest.name,
                    "description": backtest.description,
                    "strategy_name": backtest.strategy_name,
                    "start_date": backtest.start_date.strftime("%Y-%m-%d") if backtest.start_date else None,
                    "end_date": backtest.end_date.strftime("%Y-%m-%d") if backtest.end_date else None,
                    "initial_capital": backtest.initial_capital,
                    "status": backtest.status,
                    "total_return": backtest.total_return,
                    "annual_return": backtest.annual_return,
                    "volatility": backtest.volatility,
                    "sharpe_ratio": backtest.sharpe_ratio,
                    "max_drawdown": backtest.max_drawdown,
                    "win_rate": backtest.win_rate,
                    "total_trades": backtest.total_trades,
                    "created_at": backtest.created_at.isoformat() if backtest.created_at else None,
                    "completed_at": backtest.completed_at.isoformat() if backtest.completed_at else None
                }
                
                if detailed_result:
                    base_result.update(detailed_result)
                
                return base_result
                
        except Exception as e:
            logger.error(f"获取回测结果失败: {e}")
            return None
    
    async def stop_backtest(self, backtest_id: str) -> bool:
        """停止回测"""
        try:
            if backtest_id in self.running_backtests:
                self.running_backtests[backtest_id]["stop_flag"] = True
                await self._update_backtest_status(backtest_id, BacktestStatus.FAILED)
                logger.info(f"停止回测: {backtest_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"停止回测失败: {e}")
            return False
    
    async def _run_backtest(self, backtest_id: str, config: Dict[str, Any]):
        """执行回测"""
        try:
            self.running_backtests[backtest_id] = {"stop_flag": False}
            
            # 初始化投资组合
            portfolio = Portfolio(config["initial_capital"])
            
            # 获取股票池
            stock_pool = config.get("stock_pool", [])
            if not stock_pool:
                # 使用默认股票池
                stock_pool = ["000001.SZ", "000002.SZ", "600000.SH", "600036.SH", "000858.SZ"]
            
            # 获取回测日期范围
            start_date = datetime.strptime(config["start_date"], "%Y-%m-%d")
            end_date = datetime.strptime(config["end_date"], "%Y-%m-%d")
            
            # 生成交易日列表
            trading_days = self._generate_trading_days(start_date, end_date)
            
            logger.info(f"开始回测 {backtest_id}: {len(trading_days)} 个交易日, {len(stock_pool)} 只股票")
            
            # 逐日回测
            for i, current_date in enumerate(trading_days):
                if self.running_backtests[backtest_id]["stop_flag"]:
                    break
                
                # 获取当日股价数据
                current_prices = await self._get_daily_prices(stock_pool, current_date)
                
                # 运行策略信号
                if self.strategy_service:
                    signals = await self._get_strategy_signals(
                        config["strategy_name"], stock_pool, current_date
                    )
                    
                    # 执行交易信号
                    await self._execute_signals(portfolio, signals, current_prices, current_date)
                
                # 更新每日价值
                portfolio.update_daily_value(current_date, current_prices)
                
                # 更新进度
                progress = (i + 1) / len(trading_days) * 100
                await self.redis_client.set(
                    f"backtest_progress:{backtest_id}", 
                    {"progress": progress, "current_date": current_date.strftime("%Y-%m-%d")},
                    expire=3600
                )
            
            # 计算最终结果
            performance = portfolio.get_performance_metrics()
            
            # 保存结果
            await self._save_backtest_result(backtest_id, portfolio, performance)
            
            # 更新状态
            await self._update_backtest_status(backtest_id, BacktestStatus.COMPLETED)
            
            # 发送完成通知
            await self.notification_service.send_backtest_notification(
                backtest_id=backtest_id,
                status="completed",
                result_summary=f"总收益: {performance.get('total_return', 0):.2%}, "
                              f"年化收益: {performance.get('annual_return', 0):.2%}, "
                              f"最大回撤: {performance.get('max_drawdown', 0):.2%}"
            )
            
            logger.info(f"回测完成: {backtest_id}")
            
        except Exception as e:
            logger.error(f"回测执行失败 {backtest_id}: {e}")
            await self._update_backtest_status(backtest_id, BacktestStatus.FAILED)
            
            await self.notification_service.send_backtest_notification(
                backtest_id=backtest_id,
                status="failed",
                result_summary=f"回测失败: {str(e)}"
            )
        
        finally:
            # 清理运行状态
            if backtest_id in self.running_backtests:
                del self.running_backtests[backtest_id]
    
    def _generate_trading_days(self, start_date: datetime, end_date: datetime) -> List[datetime]:
        """生成交易日列表"""
        trading_days = []
        current_date = start_date
        
        while current_date <= end_date:
            # 排除周末
            if current_date.weekday() < 5:
                trading_days.append(current_date)
            current_date += timedelta(days=1)
        
        return trading_days
    
    async def _get_daily_prices(self, stock_codes: List[str], date: datetime) -> Dict[str, float]:
        """获取指定日期的股价数据"""
        prices = {}
        
        for stock_code in stock_codes:
            try:
                if self.data_service:
                    # 尝试从数据服务获取
                    date_str = date.strftime("%Y-%m-%d")
                    df = await self.data_service.get_historical_data(stock_code, date_str, date_str)
                    if not df.empty:
                        prices[stock_code] = df.iloc[0]['close_price']
                        continue
                
                # 模拟价格数据
                base_price = 10.0 + hash(stock_code) % 50
                days_from_start = (date - datetime(2024, 1, 1)).days
                trend = np.sin(days_from_start * 0.01) * 0.1
                noise = (hash(f"{stock_code}_{date.strftime('%Y%m%d')}") % 1000 - 500) / 10000
                prices[stock_code] = base_price * (1 + trend + noise)
                
            except Exception as e:
                logger.error(f"获取{stock_code}在{date}的价格失败: {e}")
                prices[stock_code] = 10.0  # 默认价格
        
        return prices
    
    async def _get_strategy_signals(self, strategy_name: str, stock_codes: List[str], 
                                  date: datetime) -> List[Dict[str, Any]]:
        """获取策略信号"""
        signals = []
        
        try:
            if not self.strategy_service:
                return signals
            
            # 为每只股票运行策略
            for stock_code in stock_codes:
                try:
                    # 这里简化处理，实际应该传入历史数据到指定日期
                    if strategy_name in self.strategy_service.strategies:
                        signal = await self.strategy_service.strategies[strategy_name](stock_code)
                        if signal and signal["signal"] != SignalType.HOLD:
                            signals.append(signal)
                except Exception as e:
                    logger.error(f"获取{stock_code}策略信号失败: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"获取策略信号失败: {e}")
        
        return signals
    
    async def _execute_signals(self, portfolio: Portfolio, signals: List[Dict[str, Any]], 
                             current_prices: Dict[str, float], date: datetime):
        """执行交易信号"""
        try:
            for signal in signals:
                stock_code = signal["stock_code"]
                signal_type = signal["signal"]
                strength = signal.get("strength", 0.5)
                reason = signal.get("reason", "")
                
                if stock_code not in current_prices:
                    continue
                
                current_price = current_prices[stock_code]
                
                if signal_type == SignalType.BUY:
                    # 买入信号
                    # 根据信号强度和可用资金计算买入金额
                    max_position_value = portfolio.cash * 0.1  # 单只股票最大仓位10%
                    buy_value = max_position_value * strength
                    quantity = int(buy_value / current_price / 100) * 100  # 整手买入
                    
                    if quantity > 0:
                        success = portfolio.buy_stock(
                            stock_code, quantity, current_price, date, reason
                        )
                        if success:
                            logger.debug(f"买入 {stock_code}: {quantity}股 @ {current_price:.2f}")
                
                elif signal_type == SignalType.SELL:
                    # 卖出信号
                    if stock_code in portfolio.positions:
                        position = portfolio.positions[stock_code]
                        # 根据信号强度决定卖出比例
                        sell_quantity = int(position.quantity * strength)
                        
                        if sell_quantity > 0:
                            success = portfolio.sell_stock(
                                stock_code, sell_quantity, current_price, date, reason
                            )
                            if success:
                                logger.debug(f"卖出 {stock_code}: {sell_quantity}股 @ {current_price:.2f}")
        
        except Exception as e:
            logger.error(f"执行交易信号失败: {e}")
    
    async def _save_backtest_result(self, backtest_id: str, portfolio: Portfolio, 
                                  performance: Dict[str, Any]):
        """保存回测结果"""
        try:
            # 保存详细结果到Redis
            detailed_result = {
                "daily_values": portfolio.daily_values,
                "trades": [
                    {
                        "stock_code": trade.stock_code,
                        "action": trade.action,
                        "quantity": trade.quantity,
                        "price": trade.price,
                        "timestamp": trade.timestamp.isoformat(),
                        "reason": trade.reason,
                        "amount": trade.amount,
                        "commission": trade.commission
                    }
                    for trade in portfolio.trades
                ],
                "final_positions": [
                    {
                        "stock_code": pos.stock_code,
                        "quantity": pos.quantity,
                        "avg_price": pos.avg_price,
                        "market_value": pos.market_value,
                        "unrealized_pnl": pos.unrealized_pnl
                    }
                    for pos in portfolio.positions.values()
                ],
                "performance": performance
            }
            
            await self.redis_client.set(
                f"backtest_result:{backtest_id}", 
                detailed_result, 
                expire=86400 * 30  # 保存30天
            )
            
            # 更新数据库记录
            async for db in get_db():
                stmt = update(BacktestResult).where(
                    BacktestResult.backtest_id == backtest_id
                ).values(
                    total_return=performance.get("total_return"),
                    annual_return=performance.get("annual_return"),
                    volatility=performance.get("volatility"),
                    sharpe_ratio=performance.get("sharpe_ratio"),
                    max_drawdown=performance.get("max_drawdown"),
                    win_rate=performance.get("win_rate"),
                    total_trades=performance.get("total_trades"),
                    final_value=performance.get("final_value"),
                    completed_at=datetime.now()
                )
                
                await db.execute(stmt)
                await db.commit()
            
            logger.info(f"保存回测结果: {backtest_id}")
            
        except Exception as e:
            logger.error(f"保存回测结果失败: {e}")
    
    async def _update_backtest_status(self, backtest_id: str, status: BacktestStatus):
        """更新回测状态"""
        try:
            async for db in get_db():
                stmt = update(BacktestResult).where(
                    BacktestResult.backtest_id == backtest_id
                ).values(
                    status=status.value,
                    updated_at=datetime.now()
                )
                
                await db.execute(stmt)
                await db.commit()
            
            # 更新缓存
            config = await self.redis_client.get(f"backtest_config:{backtest_id}")
            if config:
                config["status"] = status.value
                await self.redis_client.set(f"backtest_config:{backtest_id}", config, expire=86400)
            
        except Exception as e:
            logger.error(f"更新回测状态失败: {e}")
    
    async def get_backtest_progress(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """获取回测进度"""
        try:
            progress = await self.redis_client.get(f"backtest_progress:{backtest_id}")
            return progress
        except Exception as e:
            logger.error(f"获取回测进度失败: {e}")
            return None