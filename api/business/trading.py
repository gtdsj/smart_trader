# -*- coding: utf-8 -*-
"""
交易业务API
提供股票交易相关的业务功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any

from config_simple import get_settings

# 创建交易业务路由器
router = APIRouter(prefix="/trading", tags=["交易业务"])

# 获取配置
settings = get_settings()

# 响应模型类
class ApiResponse:
    def __init__(self, success=True, message="", data=None):
        self.success = success
        self.message = message
        self.data = data
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp
        }

# 请求模型
class OrderRequest(BaseModel):
    stock_code: str
    order_type: str  # BUY, SELL
    volume: int
    price_type: str  # MARKET, LIMIT, STOP
    price: Optional[float] = None
    strategy_name: Optional[str] = "manual"
    remark: Optional[str] = ""

class CancelOrderRequest(BaseModel):
    order_id: str
    reason: Optional[str] = "用户取消"

class PositionRequest(BaseModel):
    stock_code: Optional[str] = None
    position_type: Optional[str] = "all"  # all, long, short

@router.get("/", summary="交易概览", description="获取交易系统概览信息")
def get_trading_overview():
    """获取交易概览"""
    try:
        overview = {
            "account": {
                "account_id": getattr(settings.xtquant, 'account_id', ''),
                "account_type": getattr(settings.xtquant, 'account_type', 'STOCK'),
                "status": "active"  # 从XtQuant获取实际状态
            },
            "market": {
                "status": "closed",  # 根据时间判断市场状态
                "trading_day": datetime.now().strftime("%Y-%m-%d"),
                "session": "after_hours"  # morning, afternoon, after_hours
            },
            "statistics": {
                "today_orders": 0,  # 从数据库获取
                "today_trades": 0,  # 从数据库获取
                "today_pnl": 0.0,  # 计算今日盈亏
                "total_positions": 0  # 当前持仓数量
            },
            "risk_control": {
                "status": "normal",  # normal, warning, danger
                "daily_loss_ratio": 0.0,
                "position_ratio": 0.0,
                "available_cash_ratio": 1.0
            }
        }
        
        return ApiResponse(
            message="获取交易概览成功",
            data=overview
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/order", summary="下单", description="提交股票交易订单")
def place_order(order_request: OrderRequest):
    """下单"""
    try:
        # 这里可以实现实际的下单逻辑
        # 1. 验证订单参数
        # 2. 检查风控规则
        # 3. 调用XtQuant下单接口
        # 4. 记录订单到数据库
        
        order_result = {
            "order_id": f"ORDER_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "stock_code": order_request.stock_code,
            "order_type": order_request.order_type,
            "volume": order_request.volume,
            "price_type": order_request.price_type,
            "price": order_request.price,
            "status": "submitted",  # submitted, filled, cancelled, rejected
            "strategy_name": order_request.strategy_name,
            "remark": order_request.remark,
            "submitted_at": datetime.now().isoformat(),
            "estimated_amount": (order_request.price or 0) * order_request.volume
        }
        
        return ApiResponse(
            message="订单提交成功",
            data=order_result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/order/{order_id}", summary="撤单", description="取消指定订单")
def cancel_order(order_id: str, cancel_request: CancelOrderRequest):
    """撤单"""
    try:
        # 这里可以实现实际的撤单逻辑
        # 1. 验证订单存在
        # 2. 检查订单状态
        # 3. 调用XtQuant撤单接口
        # 4. 更新订单状态
        
        cancel_result = {
            "order_id": order_id,
            "original_status": "submitted",
            "new_status": "cancelled",
            "reason": cancel_request.reason,
            "cancelled_at": datetime.now().isoformat(),
            "cancelled_volume": 0,  # 实际撤销数量
            "filled_volume": 0  # 已成交数量
        }
        
        return ApiResponse(
            message="订单撤销成功",
            data=cancel_result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders", summary="订单列表", description="获取订单列表")
def get_orders(date: Optional[str] = None, status: Optional[str] = None, limit: int = 100):
    """获取订单列表"""
    try:
        # 这里可以从数据库或XtQuant获取订单列表
        orders = [
            {
                "order_id": "ORDER_20240101_093000",
                "stock_code": "600000.SH",
                "stock_name": "浦发银行",
                "order_type": "BUY",
                "volume": 1000,
                "price_type": "LIMIT",
                "price": 10.50,
                "status": "filled",
                "filled_volume": 1000,
                "filled_price": 10.48,
                "strategy_name": "manual",
                "submitted_at": "2024-01-01T09:30:00",
                "updated_at": "2024-01-01T09:30:15"
            }
        ]
        
        result = {
            "orders": orders,
            "total": len(orders),
            "filters": {
                "date": date,
                "status": status,
                "limit": limit
            }
        }
        
        return ApiResponse(
            message="获取订单列表成功",
            data=result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/order/{order_id}", summary="订单详情", description="获取指定订单详情")
def get_order_detail(order_id: str):
    """获取订单详情"""
    try:
        # 这里可以从数据库或XtQuant获取订单详情
        order_detail = {
            "order_id": order_id,
            "stock_code": "600000.SH",
            "stock_name": "浦发银行",
            "order_type": "BUY",
            "volume": 1000,
            "price_type": "LIMIT",
            "price": 10.50,
            "status": "filled",
            "filled_volume": 1000,
            "filled_price": 10.48,
            "commission": 5.24,
            "stamp_tax": 0.0,
            "transfer_fee": 1.05,
            "total_fee": 6.29,
            "net_amount": 10486.29,
            "strategy_name": "manual",
            "remark": "",
            "submitted_at": "2024-01-01T09:30:00",
            "filled_at": "2024-01-01T09:30:15",
            "trades": [
                {
                    "trade_id": "TRADE_001",
                    "volume": 1000,
                    "price": 10.48,
                    "amount": 10480.0,
                    "time": "2024-01-01T09:30:15"
                }
            ]
        }
        
        return ApiResponse(
            message="获取订单详情成功",
            data=order_detail
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions", summary="持仓列表", description="获取当前持仓列表")
def get_positions(position_request: PositionRequest = PositionRequest()):
    """获取持仓列表"""
    try:
        # 这里可以从XtQuant获取实际持仓
        positions = [
            {
                "stock_code": "600000.SH",
                "stock_name": "浦发银行",
                "volume": 1000,
                "available_volume": 1000,
                "avg_cost": 10.48,
                "current_price": 10.52,
                "market_value": 10520.0,
                "cost_value": 10480.0,
                "pnl": 40.0,
                "pnl_ratio": 0.0038,
                "position_ratio": 0.105,  # 占总资产比例
                "last_update": datetime.now().isoformat()
            }
        ]
        
        # 计算汇总信息
        summary = {
            "total_positions": len(positions),
            "total_market_value": sum(p["market_value"] for p in positions),
            "total_cost_value": sum(p["cost_value"] for p in positions),
            "total_pnl": sum(p["pnl"] for p in positions),
            "total_pnl_ratio": sum(p["pnl"] for p in positions) / sum(p["cost_value"] for p in positions) if positions else 0
        }
        
        result = {
            "positions": positions,
            "summary": summary,
            "filters": {
                "stock_code": position_request.stock_code,
                "position_type": position_request.position_type
            }
        }
        
        return ApiResponse(
            message="获取持仓列表成功",
            data=result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trades", summary="成交列表", description="获取成交记录列表")
def get_trades(date: Optional[str] = None, stock_code: Optional[str] = None, limit: int = 100):
    """获取成交列表"""
    try:
        # 这里可以从数据库或XtQuant获取成交记录
        trades = [
            {
                "trade_id": "TRADE_001",
                "order_id": "ORDER_20240101_093000",
                "stock_code": "600000.SH",
                "stock_name": "浦发银行",
                "trade_type": "BUY",
                "volume": 1000,
                "price": 10.48,
                "amount": 10480.0,
                "commission": 5.24,
                "stamp_tax": 0.0,
                "transfer_fee": 1.05,
                "total_fee": 6.29,
                "net_amount": 10486.29,
                "strategy_name": "manual",
                "trade_time": "2024-01-01T09:30:15"
            }
        ]
        
        result = {
            "trades": trades,
            "total": len(trades),
            "summary": {
                "total_volume": sum(t["volume"] for t in trades),
                "total_amount": sum(t["amount"] for t in trades),
                "total_fee": sum(t["total_fee"] for t in trades)
            },
            "filters": {
                "date": date,
                "stock_code": stock_code,
                "limit": limit
            }
        }
        
        return ApiResponse(
            message="获取成交列表成功",
            data=result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/account", summary="账户资产", description="获取账户资产信息")
def get_account_asset():
    """获取账户资产"""
    try:
        # 这里可以从XtQuant获取实际账户资产
        asset = {
            "account_id": getattr(settings.xtquant, 'account_id', ''),
            "total_asset": 100000.0,  # 总资产
            "available_cash": 50000.0,  # 可用资金
            "frozen_cash": 0.0,  # 冻结资金
            "market_value": 50000.0,  # 持仓市值
            "today_pnl": 100.0,  # 今日盈亏
            "total_pnl": 1000.0,  # 总盈亏
            "pnl_ratio": 0.01,  # 盈亏比例
            "position_ratio": 0.5,  # 仓位比例
            "risk_level": "low",  # low, medium, high
            "last_update": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="获取账户资产成功",
            data=asset
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))