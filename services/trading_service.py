# -*- coding: utf-8 -*-
"""
交易服务模块
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, and_, desc

try:
    from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
    from xtquant.xttype import StockAccount
    from xtquant import xtconstant
except ImportError:
    logger.warning("xtquant模块未安装，交易功能将受限")
    XtQuantTrader = None
    XtQuantTraderCallback = None
    StockAccount = None
    xtconstant = None

from config import get_settings
from core.database import get_db, TradingOrder, Position
from core.redis_client import get_redis
from services.notification_service import NotificationService
from services.data_service import DataService


class OrderType(Enum):
    """订单类型枚举"""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """订单状态枚举"""
    PENDING = "PENDING"  # 待成交
    PARTIAL_FILLED = "PARTIAL_FILLED"  # 部分成交
    FILLED = "FILLED"  # 全部成交
    CANCELLED = "CANCELLED"  # 已撤销
    REJECTED = "REJECTED"  # 已拒绝
    ERROR = "ERROR"  # 错误


class PriceType(Enum):
    """价格类型枚举"""
    MARKET = "MARKET"  # 市价
    LIMIT = "LIMIT"  # 限价
    STOP = "STOP"  # 止损
    STOP_LIMIT = "STOP_LIMIT"  # 止损限价


class TradingCallback(XtQuantTraderCallback):
    """交易回调类"""
    
    def __init__(self, trading_service):
        super().__init__()
        self.trading_service = trading_service
    
    def on_disconnected(self):
        """连接断开回调"""
        logger.warning("交易连接断开")
        asyncio.create_task(
            self.trading_service.notification_service.send_system_error_notification(
                error_type="交易连接断开",
                error_message="与交易服务器的连接已断开",
                module="TradingService"
            )
        )
    
    def on_stock_order(self, order):
        """委托回报推送"""
        logger.info(f"订单回报: {order.stock_code}, 状态: {order.order_status}, 系统订单号: {order.order_sysid}")
        
        # 异步更新订单状态
        asyncio.create_task(
            self.trading_service._update_order_status(
                order_id=str(order.order_id),
                status=order.order_status,
                traded_volume=getattr(order, 'traded_volume', 0)
            )
        )
    
    def on_stock_trade(self, trade):
        """成交变动推送"""
        logger.info(f"成交回报: {trade.stock_code}, 订单ID: {trade.order_id}")
        
        # 异步处理成交回报
        asyncio.create_task(
            self.trading_service._handle_trade_callback(
                account_id=trade.account_id,
                stock_code=trade.stock_code,
                order_id=str(trade.order_id),
                traded_volume=getattr(trade, 'traded_volume', 0),
                traded_price=getattr(trade, 'traded_price', 0)
            )
        )
    
    def on_order_error(self, order_error):
        """委托失败推送"""
        logger.error(f"订单错误: {order_error.order_id}, 错误码: {order_error.error_id}, 错误信息: {order_error.error_msg}")
        
        # 异步处理订单错误
        asyncio.create_task(
            self.trading_service._handle_order_error(
                order_id=str(order_error.order_id),
                error_id=order_error.error_id,
                error_msg=order_error.error_msg
            )
        )
    
    def on_cancel_error(self, cancel_error):
        """撤单失败推送"""
        logger.error(f"撤单错误: {cancel_error.order_id}, 错误码: {cancel_error.error_id}, 错误信息: {cancel_error.error_msg}")
    
    def on_order_stock_async_response(self, response):
        """异步下单回报推送"""
        logger.info(f"异步下单回报: 账户: {response.account_id}, 订单ID: {response.order_id}, 序号: {response.seq}")
    
    def on_account_status(self, status):
        """账户状态推送"""
        logger.info(f"账户状态: {status.account_id}, 类型: {status.account_type}, 状态: {status.status}")


class TradingService:
    """交易服务"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = get_redis()
        self.notification_service = NotificationService()
        self.data_service = None  # 延迟初始化
        
        self.xt_trader = None
        self.account = None
        self.callback = None
        self.is_connected = False
        self.is_running = False
        
        # 风控参数
        self.max_position_ratio = self.settings.trading.max_position_ratio
        self.max_single_stock_ratio = self.settings.trading.max_single_stock_ratio
        self.stop_loss_ratio = self.settings.trading.stop_loss_ratio
        self.take_profit_ratio = self.settings.trading.take_profit_ratio
        self.min_trade_amount = self.settings.trading.min_trade_amount
    
    async def start(self):
        """启动交易服务"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("交易服务启动中...")
        
        try:
            if XtQuantTrader is None:
                logger.warning("xtquant未安装，使用模拟交易模式")
                self.is_connected = True
            else:
                await self._connect_xtquant()
            
            logger.info("交易服务启动完成")
            
        except Exception as e:
            logger.error(f"交易服务启动失败: {e}")
            await self.notification_service.send_system_error_notification(
                error_type="交易服务启动失败",
                error_message=str(e),
                module="TradingService"
            )
    
    async def stop(self):
        """停止交易服务"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.xt_trader and self.is_connected:
            try:
                # 这里应该有断开连接的方法，但xtquant可能没有提供异步版本
                pass
            except Exception as e:
                logger.error(f"断开交易连接失败: {e}")
        
        logger.info("交易服务已停止")
    
    async def _connect_xtquant(self):
        """连接XtQuant"""
        try:
            # 创建交易对象
            self.xt_trader = XtQuantTrader(
                path=self.settings.xtquant.path,
                session_id=self.settings.xtquant.session_id
            )
            
            # 创建账户对象
            self.account = StockAccount(
                account_id=self.settings.xtquant.account_id,
                account_type=self.settings.xtquant.account_type
            )
            
            # 创建回调对象
            self.callback = TradingCallback(self)
            self.xt_trader.register_callback(self.callback)
            
            # 启动交易线程
            self.xt_trader.start()
            
            # 建立连接
            connect_result = self.xt_trader.connect()
            if connect_result != 0:
                raise Exception(f"连接失败，错误码: {connect_result}")
            
            # 订阅回调
            subscribe_result = self.xt_trader.subscribe(self.account)
            if subscribe_result != 0:
                raise Exception(f"订阅失败，错误码: {subscribe_result}")
            
            self.is_connected = True
            logger.info("XtQuant连接成功")
            
        except Exception as e:
            logger.error(f"XtQuant连接失败: {e}")
            raise
    
    async def place_order(self, stock_code: str, order_type: OrderType, 
                         volume: int, price: Optional[float] = None,
                         price_type: PriceType = PriceType.LIMIT,
                         strategy_name: str = "manual",
                         remark: str = "") -> Optional[str]:
        """下单"""
        try:
            # 风控检查
            risk_check_result = await self._risk_check(
                stock_code=stock_code,
                order_type=order_type,
                volume=volume,
                price=price
            )
            
            if not risk_check_result["passed"]:
                logger.warning(f"风控检查未通过: {risk_check_result['reason']}")
                return None
            
            # 获取当前价格（如果未指定价格）
            if price is None and self.data_service:
                realtime_data = await self.data_service.get_realtime_data([stock_code])
                if stock_code in realtime_data:
                    price = realtime_data[stock_code]["current_price"]
                else:
                    logger.error(f"无法获取{stock_code}的当前价格")
                    return None
            
            if price is None:
                price = 10.0  # 默认价格
            
            # 执行下单
            if self.xt_trader and self.is_connected:
                # 转换订单类型
                xt_order_type = xtconstant.STOCK_BUY if order_type == OrderType.BUY else xtconstant.STOCK_SELL
                
                # 转换价格类型
                if price_type == PriceType.MARKET:
                    xt_price_type = xtconstant.MARKET_PRICE
                else:
                    xt_price_type = xtconstant.FIX_PRICE
                
                # 下单
                order_id = self.xt_trader.order_stock(
                    acc=self.account,
                    stock_code=stock_code,
                    order_type=xt_order_type,
                    order_volume=volume,
                    price_type=xt_price_type,
                    price=price,
                    strategy_name=strategy_name,
                    order_remark=remark
                )
                
                if order_id <= 0:
                    logger.error(f"下单失败，订单ID: {order_id}")
                    return None
                
                order_id_str = str(order_id)
            else:
                # 模拟下单
                import time
                order_id_str = f"SIM_{int(time.time() * 1000)}"
                logger.info(f"模拟下单: {stock_code}, {order_type.value}, {volume}股, 价格: {price}")
            
            # 保存订单到数据库
            await self._save_order(
                order_id=order_id_str,
                stock_code=stock_code,
                order_type=order_type.value,
                price_type=price_type.value,
                order_price=price,
                order_volume=volume,
                strategy_name=strategy_name,
                remark=remark
            )
            
            # 发送通知
            await self.notification_service.send_trade_signal_notification(
                stock_code=stock_code,
                signal_type=f"{order_type.value}订单",
                price=price,
                reason=f"下单{volume}股",
                strategy_name=strategy_name
            )
            
            logger.info(f"下单成功: {order_id_str}")
            return order_id_str
            
        except Exception as e:
            logger.error(f"下单失败: {e}")
            await self.notification_service.send_system_error_notification(
                error_type="下单失败",
                error_message=str(e),
                module="TradingService"
            )
            return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        try:
            if self.xt_trader and self.is_connected:
                result = self.xt_trader.cancel_order_stock(self.account, int(order_id))
                if result != 0:
                    logger.error(f"撤单失败，错误码: {result}")
                    return False
            else:
                logger.info(f"模拟撤单: {order_id}")
            
            # 更新订单状态
            await self._update_order_status(order_id, OrderStatus.CANCELLED.value)
            
            logger.info(f"撤单成功: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False
    
    async def get_account_asset(self) -> Optional[Dict[str, Any]]:
        """获取账户资产"""
        try:
            if self.xt_trader and self.is_connected:
                asset = self.xt_trader.query_stock_asset(self.account)
                if asset:
                    return {
                        "total_asset": getattr(asset, 'total_asset', 0),
                        "cash": getattr(asset, 'cash', 0),
                        "market_value": getattr(asset, 'market_value', 0),
                        "frozen_cash": getattr(asset, 'frozen_cash', 0),
                        "available_cash": getattr(asset, 'available_cash', 0)
                    }
            else:
                # 模拟资产数据
                return {
                    "total_asset": 1000000.0,
                    "cash": 500000.0,
                    "market_value": 500000.0,
                    "frozen_cash": 0.0,
                    "available_cash": 500000.0
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取账户资产失败: {e}")
            return None
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """获取持仓"""
        try:
            positions = []
            
            if self.xt_trader and self.is_connected:
                xt_positions = self.xt_trader.query_stock_positions(self.account)
                for pos in xt_positions:
                    positions.append({
                        "stock_code": pos.stock_code,
                        "volume": getattr(pos, 'volume', 0),
                        "available_volume": getattr(pos, 'available_volume', 0),
                        "avg_price": getattr(pos, 'avg_price', 0),
                        "market_value": getattr(pos, 'market_value', 0),
                        "profit_loss": getattr(pos, 'profit_loss', 0)
                    })
            else:
                # 从数据库获取持仓
                async for db in get_db():
                    query = select(Position).where(
                        Position.account_id == self.settings.xtquant.account_id
                    )
                    result = await db.execute(query)
                    db_positions = result.scalars().all()
                    
                    for pos in db_positions:
                        positions.append({
                            "stock_code": pos.stock_code,
                            "volume": pos.volume,
                            "available_volume": pos.available_volume,
                            "avg_price": pos.avg_price,
                            "market_value": pos.market_value,
                            "profit_loss": pos.profit_loss
                        })
                    break
            
            return positions
            
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return []
    
    async def get_orders(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取订单列表"""
        try:
            orders = []
            
            # 从数据库获取订单
            async for db in get_db():
                query = select(TradingOrder).order_by(
                    desc(TradingOrder.created_at)
                ).limit(limit)
                
                result = await db.execute(query)
                db_orders = result.scalars().all()
                
                for order in db_orders:
                    orders.append({
                        "order_id": order.order_id,
                        "stock_code": order.stock_code,
                        "order_type": order.order_type,
                        "price_type": order.price_type,
                        "order_price": order.order_price,
                        "order_volume": order.order_volume,
                        "traded_volume": order.traded_volume,
                        "order_status": order.order_status,
                        "strategy_name": order.strategy_name,
                        "remark": order.remark,
                        "created_at": order.created_at.isoformat() if order.created_at else None
                    })
                break
            
            return orders
            
        except Exception as e:
            logger.error(f"获取订单列表失败: {e}")
            return []
    
    async def _risk_check(self, stock_code: str, order_type: OrderType, 
                         volume: int, price: Optional[float]) -> Dict[str, Any]:
        """风控检查"""
        try:
            # 获取账户资产
            asset = await self.get_account_asset()
            if not asset:
                return {"passed": False, "reason": "无法获取账户资产"}
            
            # 检查最小交易金额
            if price and price * volume < self.min_trade_amount:
                return {
                    "passed": False, 
                    "reason": f"交易金额{price * volume:.2f}小于最小交易金额{self.min_trade_amount}"
                }
            
            # 买入检查
            if order_type == OrderType.BUY:
                # 检查可用资金
                required_cash = price * volume if price else 0
                if required_cash > asset["available_cash"]:
                    return {
                        "passed": False,
                        "reason": f"可用资金{asset['available_cash']:.2f}不足，需要{required_cash:.2f}"
                    }
                
                # 检查总仓位比例
                total_position_value = asset["market_value"] + required_cash
                if total_position_value > asset["total_asset"] * self.max_position_ratio:
                    return {
                        "passed": False,
                        "reason": f"总仓位比例将超过{self.max_position_ratio:.1%}"
                    }
                
                # 检查单只股票仓位比例
                positions = await self.get_positions()
                current_position = next((p for p in positions if p["stock_code"] == stock_code), None)
                current_value = current_position["market_value"] if current_position else 0
                new_value = current_value + required_cash
                
                if new_value > asset["total_asset"] * self.max_single_stock_ratio:
                    return {
                        "passed": False,
                        "reason": f"单只股票{stock_code}仓位比例将超过{self.max_single_stock_ratio:.1%}"
                    }
            
            # 卖出检查
            elif order_type == OrderType.SELL:
                positions = await self.get_positions()
                position = next((p for p in positions if p["stock_code"] == stock_code), None)
                
                if not position:
                    return {"passed": False, "reason": f"没有{stock_code}的持仓"}
                
                if volume > position["available_volume"]:
                    return {
                        "passed": False,
                        "reason": f"可用数量{position['available_volume']}不足，需要{volume}"
                    }
            
            return {"passed": True, "reason": "风控检查通过"}
            
        except Exception as e:
            logger.error(f"风控检查失败: {e}")
            return {"passed": False, "reason": f"风控检查异常: {e}"}
    
    async def _save_order(self, order_id: str, stock_code: str, order_type: str,
                         price_type: str, order_price: float, order_volume: int,
                         strategy_name: str, remark: str):
        """保存订单到数据库"""
        try:
            async for db in get_db():
                order_data = {
                    "order_id": order_id,
                    "stock_code": stock_code,
                    "order_type": order_type,
                    "price_type": price_type,
                    "order_price": order_price,
                    "order_volume": order_volume,
                    "traded_volume": 0,
                    "order_status": OrderStatus.PENDING.value,
                    "strategy_name": strategy_name,
                    "remark": remark,
                    "created_at": datetime.now()
                }
                
                stmt = insert(TradingOrder).values(**order_data)
                await db.execute(stmt)
                await db.commit()
                break
                
        except Exception as e:
            logger.error(f"保存订单失败: {e}")
    
    async def _update_order_status(self, order_id: str, status: str, 
                                  traded_volume: int = 0):
        """更新订单状态"""
        try:
            async for db in get_db():
                stmt = update(TradingOrder).where(
                    TradingOrder.order_id == order_id
                ).values(
                    order_status=status,
                    traded_volume=traded_volume,
                    updated_at=datetime.now()
                )
                
                await db.execute(stmt)
                await db.commit()
                break
                
        except Exception as e:
            logger.error(f"更新订单状态失败: {e}")
    
    async def _handle_trade_callback(self, account_id: str, stock_code: str,
                                   order_id: str, traded_volume: int, 
                                   traded_price: float):
        """处理成交回报"""
        try:
            # 发送成交通知
            await self.notification_service.send_order_filled_notification(
                order_id=order_id,
                stock_code=stock_code,
                order_type="交易",
                volume=traded_volume,
                price=traded_price
            )
            
            # 更新持仓（这里需要更复杂的逻辑来计算持仓）
            # ...
            
        except Exception as e:
            logger.error(f"处理成交回报失败: {e}")
    
    async def _handle_order_error(self, order_id: str, error_id: int, error_msg: str):
        """处理订单错误"""
        try:
            # 更新订单状态为错误
            await self._update_order_status(order_id, OrderStatus.ERROR.value)
            
            # 发送错误通知
            await self.notification_service.send_system_error_notification(
                error_type="订单错误",
                error_message=f"订单{order_id}错误: {error_msg} (错误码: {error_id})",
                module="TradingService"
            )
            
        except Exception as e:
            logger.error(f"处理订单错误失败: {e}")