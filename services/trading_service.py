# -*- coding: utf-8 -*-
"""
交易服务模块
"""

import traceback
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, and_, desc

from config import get_settings
from core.database import get_db, TradingOrder, Position
from core.redis_client import get_redis
from services.notification_service import NotificationService
from services.xtquant_service import XtQuantService


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


# TradingCallback已移至XtQuantService中


class TradingService:
    """交易服务"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = get_redis()
        self.notification_service = NotificationService()
        self.xtquant_service = XtQuantService()
        
        # 连接状态
        self.connected = False
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
            # 启动XtQuant服务
            await self.xtquant_service.start()
            self.connected = self.xtquant_service.is_connected
            
            logger.info("交易服务启动完成")
            
        except Exception as e:
            logger.error(f"交易服务启动失败: {e}, {traceback.format_exc()}")
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
        
        try:
            logger.info("停止交易服务...")
            
            # 停止XtQuant服务
            await self.xtquant_service.stop()
            self.connected = False
            
            logger.info("交易服务已停止")
            
        except Exception as e:
            logger.error(f"停止交易服务失败: {e}, {traceback.format_exc()}")
    
    # _connect_xtquant方法已移至XtQuantService
    
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
            if price is None:
                real_time_data = await self.xtquant_service.get_real_time_data([stock_code])
                if real_time_data and stock_code in real_time_data:
                    price = real_time_data[stock_code].get('lastPrice', 10.0)
                else:
                    price = 10.0  # 默认价格
            
            # 使用XtQuantService下单
            order_result = await self.xtquant_service.place_order(
                stock_code=stock_code,
                order_type=order_type.value,
                volume=volume,
                price=price,
                price_type=price_type.value,
                strategy_name=strategy_name,
                remark=remark
            )
            
            if not order_result["success"]:
                logger.error(f"下单失败: {order_result.get('error', '未知错误')}")
                return None
            
            order_id_str = order_result["order_id"]
            
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
            logger.error(f"下单失败: {e}, {traceback.format_exc()}")
            await self.notification_service.send_system_error_notification(
                error_type="下单失败",
                error_message=str(e),
                module="TradingService"
            )
            return None
    
    async def cancel_order(self, order_id: str) -> dict:
        """撤单"""
        try:
            # 使用XtQuantService撤单
            cancel_result = await self.xtquant_service.cancel_order(order_id)
            
            if not cancel_result["success"]:
                return cancel_result
            
            # 更新订单状态
            await self._update_order_status(order_id, OrderStatus.CANCELLED.value)
            
            return {
                "success": True,
                "message": "撤单成功"
            }
            
        except Exception as e:
            logger.error(f"撤单失败: {e}, {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_account_asset(self) -> Optional[Dict[str, Any]]:
        """获取账户资产"""
        try:
            # 使用XtQuantService获取账户资产
            asset_result = await self.xtquant_service.get_account_asset()
            
            if asset_result["success"]:
                return asset_result["data"]
            else:
                logger.error(f"获取账户资产失败: {asset_result.get('error', '未知错误')}")
                return None
            
        except Exception as e:
            logger.error(f"获取账户资产失败: {e}, {traceback.format_exc()}")
            return None
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """获取持仓"""
        try:
            # 使用XtQuantService获取持仓
            positions_result = await self.xtquant_service.get_positions()
            
            # xtquant_service.get_positions() 直接返回列表，不是字典格式
            if isinstance(positions_result, list):
                return positions_result
            else:
                logger.error(f"获取持仓失败: 返回数据格式错误")
                # 从数据库查询持仓作为备选
                return await self._get_positions_from_db()
            
        except Exception as e:
            # 如果是XtQuant未连接的错误，尝试从数据库获取
            if "XtQuant交易服务未连接" in str(e):
                logger.warning(f"XtQuant服务未连接，尝试从数据库获取持仓: {e}")
                return await self._get_positions_from_db()
            else:
                logger.error(f"获取持仓失败: {e}")
                return []
    
    async def _get_positions_from_db(self) -> List[Dict[str, Any]]:
        """从数据库获取持仓信息"""
        try:
            async for db in get_db():
                query = select(Position).where(
                    Position.account_id == self.settings.xtquant.account_id
                )
                result = await db.execute(query)
                db_positions = result.scalars().all()
                
                positions = []
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
        except Exception as db_e:
            logger.error(f"从数据库获取持仓失败: {db_e}, {traceback.format_exc()}")
            return []
    
    async def get_position(self, stock_code: str) -> Dict[str, Any]:
        """获取指定股票的持仓信息"""
        try:
            # 获取所有持仓
            positions = await self.get_positions()
            
            # 查找指定股票的持仓
            for position in positions:
                if position.get("stock_code") == stock_code:
                    return position
            
            # 如果没有找到持仓，返回None
            return None
            
        except Exception as e:
            logger.error(f"获取股票 {stock_code} 持仓失败: {e}, {traceback.format_exc()}")
            return None
    
    async def get_orders(self, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """获取订单"""
        try:
            # 优先使用XtQuantService获取当日订单
            orders_result = await self.xtquant_service.get_orders()
            xt_orders = orders_result["data"] if orders_result["success"] else []
            
            # 从数据库查询历史订单
            db_orders = []
            async for db in get_db():
                query = select(TradingOrder)
                
                if start_date:
                    query = query.where(TradingOrder.created_at >= start_date)
                if end_date:
                    query = query.where(TradingOrder.created_at <= end_date)
                
                query = query.order_by(desc(TradingOrder.created_at))
                
                result = await db.execute(query)
                db_order_records = result.scalars().all()
                
                for order in db_order_records:
                    db_orders.append({
                        "order_id": order.order_id,
                        "stock_code": order.stock_code,
                        "order_type": order.order_type,
                        "volume": order.order_volume,
                        "price": order.order_price,
                        "status": order.order_status,
                        "traded_volume": order.traded_volume,
                        "strategy_name": order.strategy_name,
                        "remark": order.remark,
                        "created_at": order.created_at.isoformat() if order.created_at else None,
                        "updated_at": order.updated_at.isoformat() if order.updated_at else None
                    })
                break
            
            # 合并XtQuant订单和数据库订单，去重
            all_orders = xt_orders + db_orders
            seen_order_ids = set()
            unique_orders = []
            
            for order in all_orders:
                order_id = order.get("order_id")
                if order_id and order_id not in seen_order_ids:
                    seen_order_ids.add(order_id)
                    unique_orders.append(order)
            
            return unique_orders
            
        except Exception as e:
            logger.error(f"获取持仓失败: {e}, {traceback.format_exc()}")
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
            logger.error(f"风控检查失败: {e}, {traceback.format_exc()}")
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
            logger.error(f"处理成交回报失败: {e}, {traceback.format_exc()}")
    
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
            logger.error(f"更新订单状态失败: {e}, {traceback.format_exc()}")
    
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
            logger.error(f"处理成交回报失败: {e}, {traceback.format_exc()}")
    
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
            logger.error(f"处理订单错误失败: {e}, {traceback.format_exc()}")