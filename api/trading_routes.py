# -*- coding: utf-8 -*-
"""
交易服务API路由
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from loguru import logger

from services.trading_service import TradingService, OrderType, PriceType

# 创建路由器
router = APIRouter(prefix="/api/v1/trading", tags=["交易服务"])

# 全局服务实例
_trading_service: TradingService = None

def set_trading_service(service: TradingService):
    """设置交易服务实例"""
    global _trading_service
    _trading_service = service

def get_trading_service() -> TradingService:
    """获取交易服务实例"""
    if _trading_service is None:
        raise HTTPException(status_code=500, detail="交易服务未初始化")
    return _trading_service


# 请求模型
class PlaceOrderRequest(BaseModel):
    """下单请求"""
    stock_code: str = Field(..., description="股票代码")
    order_type: str = Field(..., description="订单类型：BUY, SELL")
    quantity: int = Field(..., description="数量", gt=0)
    price_type: str = Field(..., description="价格类型：MARKET, LIMIT")
    price: Optional[float] = Field(None, description="价格（限价单必填）")
    strategy_name: Optional[str] = Field(None, description="策略名称")
    remark: Optional[str] = Field(None, description="备注")


class CancelOrderRequest(BaseModel):
    """撤单请求"""
    order_id: str = Field(..., description="订单ID")


class QueryOrdersRequest(BaseModel):
    """查询订单请求"""
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    stock_code: Optional[str] = Field(None, description="股票代码")
    status: Optional[str] = Field(None, description="订单状态")
    limit: int = Field(100, description="返回数量限制", ge=1, le=1000)


# 响应模型
class OrderInfo(BaseModel):
    """订单信息"""
    order_id: str = Field(..., description="订单ID")
    stock_code: str = Field(..., description="股票代码")
    order_type: str = Field(..., description="订单类型")
    quantity: int = Field(..., description="数量")
    price: float = Field(..., description="价格")
    filled_quantity: int = Field(..., description="已成交数量")
    avg_price: float = Field(..., description="平均成交价")
    status: str = Field(..., description="订单状态")
    order_time: str = Field(..., description="下单时间")
    strategy_name: Optional[str] = Field(None, description="策略名称")
    remark: Optional[str] = Field(None, description="备注")


class TradeInfo(BaseModel):
    """成交信息"""
    trade_id: str = Field(..., description="成交ID")
    order_id: str = Field(..., description="订单ID")
    stock_code: str = Field(..., description="股票代码")
    quantity: int = Field(..., description="成交数量")
    price: float = Field(..., description="成交价格")
    amount: float = Field(..., description="成交金额")
    trade_time: str = Field(..., description="成交时间")
    commission: float = Field(..., description="手续费")


class PositionInfo(BaseModel):
    """持仓信息"""
    stock_code: str = Field(..., description="股票代码")
    stock_name: Optional[str] = Field(None, description="股票名称")
    quantity: int = Field(..., description="持仓数量")
    available_quantity: int = Field(..., description="可用数量")
    avg_price: float = Field(..., description="平均成本")
    current_price: float = Field(..., description="当前价格")
    market_value: float = Field(..., description="市值")
    unrealized_pnl: float = Field(..., description="浮动盈亏")
    unrealized_pnl_rate: float = Field(..., description="浮动盈亏率")


class AssetInfo(BaseModel):
    """资产信息"""
    account_id: str = Field(..., description="账户ID")
    total_asset: float = Field(..., description="总资产")
    cash: float = Field(..., description="可用资金")
    market_value: float = Field(..., description="持仓市值")
    frozen_cash: float = Field(..., description="冻结资金")
    profit_loss: float = Field(..., description="盈亏")
    profit_loss_rate: float = Field(..., description="盈亏率")


class ApiResponse(BaseModel):
    """API响应基类"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Any = Field(None, description="响应数据")


# API路由
@router.get("/status", response_model=ApiResponse, summary="获取交易服务状态")
async def get_trading_service_status(service: TradingService = Depends(get_trading_service)):
    """获取交易服务状态"""
    try:
        status = {
            "is_connected": service.connected,
            "account_id": service.xtquant_service.account.account_id if service.xtquant_service.account else None,
            # "last_heartbeat": service.last_heartbeat.isoformat() if service.last_heartbeat else None,
            "total_orders": len(service.orders),
            "simulation_mode": not service.xt_trader
        }
        
        return ApiResponse(
            success=True,
            message="获取交易服务状态成功",
            data=status
        )
    except Exception as e:
        logger.error(f"获取交易服务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start", response_model=ApiResponse, summary="启动交易服务")
async def start_trading_service(service: TradingService = Depends(get_trading_service)):
    """启动交易服务"""
    try:
        success = await service.start()
        if success:
            return ApiResponse(
                success=True,
                message="交易服务启动成功",
                data=None
            )
        else:
            raise HTTPException(status_code=500, detail="交易服务启动失败")
    except Exception as e:
        logger.error(f"启动交易服务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=ApiResponse, summary="停止交易服务")
async def stop_trading_service(service: TradingService = Depends(get_trading_service)):
    """停止交易服务"""
    try:
        await service.stop()
        return ApiResponse(
            success=True,
            message="交易服务停止成功",
            data=None
        )
    except Exception as e:
        logger.error(f"停止交易服务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/place", response_model=ApiResponse, summary="下单")
async def place_order(
    request: PlaceOrderRequest,
    service: TradingService = Depends(get_trading_service)
):
    """下单"""
    try:
        # 验证订单类型
        try:
            order_type = OrderType(request.order_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的订单类型")
        
        # 验证价格类型
        try:
            price_type = PriceType(request.price_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的价格类型")
        
        # 限价单必须提供价格
        if price_type == PriceType.LIMIT and request.price is None:
            raise HTTPException(status_code=400, detail="限价单必须提供价格")
        
        # 市价单不需要价格
        price = request.price if price_type == PriceType.LIMIT else 0.0
        
        order_id = await service.place_order(
            stock_code=request.stock_code,
            order_type=order_type,
            quantity=request.quantity,
            price_type=price_type,
            price=price,
            strategy_name=request.strategy_name or "",
            remark=request.remark or ""
        )
        
        if order_id:
            return ApiResponse(
                success=True,
                message="下单成功",
                data={"order_id": order_id}
            )
        else:
            raise HTTPException(status_code=500, detail="下单失败")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/cancel", response_model=ApiResponse, summary="撤单")
async def cancel_order(
    request: CancelOrderRequest,
    service: TradingService = Depends(get_trading_service)
):
    """撤单"""
    try:
        success = await service.cancel_order(request.order_id)
        if success:
            return ApiResponse(
                success=True,
                message="撤单成功",
                data=None
            )
        else:
            raise HTTPException(status_code=500, detail="撤单失败")
    except Exception as e:
        logger.error(f"撤单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders", response_model=ApiResponse, summary="查询订单")
async def get_orders(
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    stock_code: Optional[str] = Query(None, description="股票代码"),
    status: Optional[str] = Query(None, description="订单状态"),
    limit: int = Query(100, description="返回数量限制", ge=1, le=1000),
    service: TradingService = Depends(get_trading_service)
):
    """查询订单"""
    try:
        orders = await service.get_orders()
        
        # 过滤条件
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                orders = [order for order in orders if order.get("order_time", "") >= start_date]
            except ValueError:
                raise HTTPException(status_code=400, detail="开始日期格式错误")
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                orders = [order for order in orders if order.get("order_time", "") <= end_date]
            except ValueError:
                raise HTTPException(status_code=400, detail="结束日期格式错误")
        
        if stock_code:
            orders = [order for order in orders if order.get("stock_code") == stock_code]
        
        if status:
            orders = [order for order in orders if order.get("status") == status]
        
        # 限制数量
        orders = orders[:limit]
        
        return ApiResponse(
            success=True,
            message="查询订单成功",
            data=orders
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询订单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}", response_model=ApiResponse, summary="查询单个订单")
async def get_order(
    order_id: str,
    service: TradingService = Depends(get_trading_service)
):
    """查询单个订单"""
    try:
        order = await service.get_order(order_id)
        if order:
            return ApiResponse(
                success=True,
                message="查询订单成功",
                data=order
            )
        else:
            raise HTTPException(status_code=404, detail="订单不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询订单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades", response_model=ApiResponse, summary="查询成交记录")
async def get_trades(
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    stock_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(100, description="返回数量限制", ge=1, le=1000),
    service: TradingService = Depends(get_trading_service)
):
    """查询成交记录"""
    try:
        trades = await service.get_trades()
        
        # 过滤条件
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                trades = [trade for trade in trades if trade.get("trade_time", "") >= start_date]
            except ValueError:
                raise HTTPException(status_code=400, detail="开始日期格式错误")
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                trades = [trade for trade in trades if trade.get("trade_time", "") <= end_date]
            except ValueError:
                raise HTTPException(status_code=400, detail="结束日期格式错误")
        
        if stock_code:
            trades = [trade for trade in trades if trade.get("stock_code") == stock_code]
        
        # 限制数量
        trades = trades[:limit]
        
        return ApiResponse(
            success=True,
            message="查询成交记录成功",
            data=trades
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询成交记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions", response_model=ApiResponse, summary="查询持仓")
async def get_positions(service: TradingService = Depends(get_trading_service)):
    """查询持仓"""
    try:
        positions = await service.get_positions()
        
        # 检查是否成功获取到持仓数据
        if positions is not None:
            return ApiResponse(
                success=True,
                message="查询持仓成功" if positions else "当前无持仓",
                data=positions
            )
        else:
            return ApiResponse(
                success=False,
                message="查询持仓失败，请检查交易服务连接状态",
                data=[]
            )
    except Exception as e:
        logger.error(f"查询持仓失败: {e}")
        # 返回友好的错误信息而不是抛出异常
        return ApiResponse(
            success=False,
            message=f"查询持仓失败: {str(e)}",
            data=[]
        )


@router.get("/positions/{stock_code}", response_model=ApiResponse, summary="查询指定股票持仓")
async def get_position(stock_code: str, service: TradingService = Depends(get_trading_service)):
    """查询指定股票持仓"""
    try:
        position = await service.get_position(stock_code)
        
        if position is not None:
            return ApiResponse(
                success=True,
                message="查询持仓成功",
                data=position
            )
        else:
            return ApiResponse(
                success=False,
                message=f"未找到股票 {stock_code} 的持仓信息",
                data=None
            )
    except Exception as e:
        logger.error(f"查询持仓失败: {e}")
        # 返回友好的错误信息而不是抛出异常
        return ApiResponse(
            success=False,
            message=f"查询持仓失败: {str(e)}",
            data=None
        )


@router.get("/asset", response_model=ApiResponse, summary="查询资产")
async def get_asset(service: TradingService = Depends(get_trading_service)):
    """查询资产"""
    try:
        asset = await service.get_account_asset()
        if asset:
            return ApiResponse(
                success=True,
                message="查询资产成功",
                data=asset
            )
        else:
            raise HTTPException(status_code=500, detail="查询资产失败")
    except Exception as e:
        logger.error(f"查询资产失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk/check", response_model=ApiResponse, summary="风险检查")
async def risk_check(
    stock_code: str = Query(..., description="股票代码"),
    order_type: str = Query(..., description="订单类型"),
    quantity: int = Query(..., description="数量"),
    price: float = Query(..., description="价格"),
    service: TradingService = Depends(get_trading_service)
):
    """风险检查"""
    try:
        # 验证订单类型
        try:
            order_type_enum = OrderType(order_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的订单类型")
        
        risk_result = await service.check_risk(
            stock_code=stock_code,
            order_type=order_type_enum,
            quantity=quantity,
            price=price
        )
        
        return ApiResponse(
            success=True,
            message="风险检查完成",
            data=risk_result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"风险检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=ApiResponse, summary="交易统计")
async def get_trading_statistics(
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    service: TradingService = Depends(get_trading_service)
):
    """获取交易统计"""
    try:
        # 获取订单和成交数据
        orders = await service.get_orders()
        trades = await service.get_trades()
        
        # 日期过滤
        if start_date:
            orders = [order for order in orders if order.get("order_time", "") >= start_date]
            trades = [trade for trade in trades if trade.get("trade_time", "") >= start_date]
        
        if end_date:
            orders = [order for order in orders if order.get("order_time", "") <= end_date]
            trades = [trade for trade in trades if trade.get("trade_time", "") <= end_date]
        
        # 计算统计指标
        total_orders = len(orders)
        total_trades = len(trades)
        filled_orders = len([order for order in orders if order.get("status") == "FILLED"])
        cancelled_orders = len([order for order in orders if order.get("status") == "CANCELLED"])
        
        total_buy_amount = sum(trade.get("amount", 0) for trade in trades if trade.get("order_type") == "BUY")
        total_sell_amount = sum(trade.get("amount", 0) for trade in trades if trade.get("order_type") == "SELL")
        total_commission = sum(trade.get("commission", 0) for trade in trades)
        
        fill_rate = filled_orders / total_orders if total_orders > 0 else 0
        cancel_rate = cancelled_orders / total_orders if total_orders > 0 else 0
        
        statistics = {
            "total_orders": total_orders,
            "total_trades": total_trades,
            "filled_orders": filled_orders,
            "cancelled_orders": cancelled_orders,
            "fill_rate": fill_rate,
            "cancel_rate": cancel_rate,
            "total_buy_amount": total_buy_amount,
            "total_sell_amount": total_sell_amount,
            "total_commission": total_commission,
            "net_amount": total_sell_amount - total_buy_amount
        }
        
        return ApiResponse(
            success=True,
            message="获取交易统计成功",
            data=statistics
        )
    except Exception as e:
        logger.error(f"获取交易统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))