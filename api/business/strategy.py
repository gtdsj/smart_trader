# -*- coding: utf-8 -*-
"""
策略业务API
提供量化策略管理和执行功能
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any

from config_simple import get_settings

# 创建策略业务路由器
router = APIRouter(prefix="/strategy", tags=["策略业务"])

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
class StrategyCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    strategy_type: str  # trend, mean_reversion, arbitrage, grid, etc.
    parameters: Dict[str, Any]
    stock_pool: List[str]
    risk_control: Optional[Dict[str, Any]] = None
    schedule: Optional[Dict[str, Any]] = None

class StrategyUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    stock_pool: Optional[List[str]] = None
    risk_control: Optional[Dict[str, Any]] = None
    schedule: Optional[Dict[str, Any]] = None
    status: Optional[str] = None  # active, inactive, paused

class StrategyExecuteRequest(BaseModel):
    strategy_id: str
    execution_mode: Optional[str] = "auto"  # auto, manual, simulation
    force_execute: Optional[bool] = False

@router.get("/", summary="策略概览", description="获取策略系统概览信息")
def get_strategy_overview():
    """获取策略概览"""
    try:
        overview = {
            "strategy_engine": {
                "status": "running",
                "version": "1.0.0",
                "last_update": datetime.now().isoformat()
            },
            "statistics": {
                "total_strategies": 5,
                "active_strategies": 3,
                "paused_strategies": 1,
                "inactive_strategies": 1,
                "running_strategies": 2
            },
            "performance": {
                "today_signals": 12,
                "today_trades": 8,
                "success_rate": 0.75,
                "avg_return": 0.0234
            },
            "risk_status": {
                "overall_risk": "low",
                "max_drawdown": 0.05,
                "position_concentration": 0.3,
                "leverage_ratio": 1.0
            }
        }
        
        return ApiResponse(
            message="获取策略概览成功",
            data=overview
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list", summary="策略列表", description="获取策略列表")
def get_strategy_list(
    status: Optional[str] = Query(None, description="策略状态过滤"),
    strategy_type: Optional[str] = Query(None, description="策略类型过滤"),
    limit: int = Query(100, description="返回数量限制")
):
    """获取策略列表"""
    try:
        # 这里可以从数据库获取实际策略列表
        strategies = [
            {
                "strategy_id": "STRATEGY_001",
                "name": "均线突破策略",
                "description": "基于双均线交叉的趋势跟踪策略",
                "strategy_type": "trend",
                "status": "active",
                "created_by": "admin",
                "created_at": "2024-01-01T10:00:00",
                "updated_at": "2024-01-01T15:30:00",
                "last_execution": "2024-01-01T15:00:00",
                "performance": {
                    "total_return": 0.125,
                    "sharpe_ratio": 1.85,
                    "max_drawdown": 0.08,
                    "win_rate": 0.68
                },
                "risk_metrics": {
                    "var_95": 0.02,
                    "beta": 0.95,
                    "volatility": 0.15
                }
            },
            {
                "strategy_id": "STRATEGY_002",
                "name": "网格交易策略",
                "description": "基于价格区间的网格交易策略",
                "strategy_type": "grid",
                "status": "paused",
                "created_by": "admin",
                "created_at": "2024-01-01T11:00:00",
                "updated_at": "2024-01-01T14:20:00",
                "last_execution": "2024-01-01T14:00:00",
                "performance": {
                    "total_return": 0.089,
                    "sharpe_ratio": 1.42,
                    "max_drawdown": 0.05,
                    "win_rate": 0.72
                },
                "risk_metrics": {
                    "var_95": 0.015,
                    "beta": 0.88,
                    "volatility": 0.12
                }
            }
        ]
        
        # 根据参数过滤
        if status:
            strategies = [s for s in strategies if s["status"] == status]
        if strategy_type:
            strategies = [s for s in strategies if s["strategy_type"] == strategy_type]
        
        # 限制返回数量
        strategies = strategies[:limit]
        
        result = {
            "strategies": strategies,
            "total": len(strategies),
            "filters": {
                "status": status,
                "strategy_type": strategy_type,
                "limit": limit
            }
        }
        
        return ApiResponse(
            message="获取策略列表成功",
            data=result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create", summary="创建策略", description="创建新的量化策略")
def create_strategy(request: StrategyCreateRequest):
    """创建策略"""
    try:
        # 这里可以实现实际的策略创建逻辑
        strategy_id = f"STRATEGY_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        new_strategy = {
            "strategy_id": strategy_id,
            "name": request.name,
            "description": request.description,
            "strategy_type": request.strategy_type,
            "parameters": request.parameters,
            "stock_pool": request.stock_pool,
            "risk_control": request.risk_control or {
                "max_position_ratio": 0.1,
                "stop_loss_ratio": 0.05,
                "take_profit_ratio": 0.1
            },
            "schedule": request.schedule or {
                "enabled": True,
                "frequency": "daily",
                "time": "09:30:00"
            },
            "status": "inactive",
            "created_by": "admin",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="策略创建成功",
            data=new_strategy
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{strategy_id}", summary="策略详情", description="获取指定策略详细信息")
def get_strategy_detail(strategy_id: str):
    """获取策略详情"""
    try:
        # 这里可以从数据库获取实际策略详情
        strategy_detail = {
            "strategy_id": strategy_id,
            "name": "均线突破策略",
            "description": "基于双均线交叉的趋势跟踪策略",
            "strategy_type": "trend",
            "status": "active",
            "parameters": {
                "short_period": 5,
                "long_period": 20,
                "signal_threshold": 0.02,
                "position_size": 0.1
            },
            "stock_pool": ["600000.SH", "000001.SZ", "000002.SZ"],
            "risk_control": {
                "max_position_ratio": 0.1,
                "stop_loss_ratio": 0.05,
                "take_profit_ratio": 0.1,
                "max_drawdown": 0.15
            },
            "schedule": {
                "enabled": True,
                "frequency": "daily",
                "time": "09:30:00",
                "weekdays_only": True
            },
            "performance": {
                "total_return": 0.125,
                "annual_return": 0.156,
                "sharpe_ratio": 1.85,
                "max_drawdown": 0.08,
                "win_rate": 0.68,
                "profit_factor": 2.34,
                "total_trades": 156,
                "winning_trades": 106,
                "losing_trades": 50
            },
            "recent_signals": [
                {
                    "signal_id": "SIG_001",
                    "stock_code": "600000.SH",
                    "signal_type": "BUY",
                    "signal_strength": 0.85,
                    "price": 10.52,
                    "volume": 1000,
                    "generated_at": "2024-01-01T09:30:00",
                    "executed": True,
                    "execution_price": 10.53
                }
            ],
            "created_by": "admin",
            "created_at": "2024-01-01T10:00:00",
            "updated_at": "2024-01-01T15:30:00",
            "last_execution": "2024-01-01T15:00:00"
        }
        
        return ApiResponse(
            message="获取策略详情成功",
            data=strategy_detail
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{strategy_id}", summary="更新策略", description="更新指定策略配置")
def update_strategy(strategy_id: str, request: StrategyUpdateRequest):
    """更新策略"""
    try:
        # 这里可以实现实际的策略更新逻辑
        updated_fields = {}
        
        if request.name is not None:
            updated_fields["name"] = request.name
        if request.description is not None:
            updated_fields["description"] = request.description
        if request.parameters is not None:
            updated_fields["parameters"] = request.parameters
        if request.stock_pool is not None:
            updated_fields["stock_pool"] = request.stock_pool
        if request.risk_control is not None:
            updated_fields["risk_control"] = request.risk_control
        if request.schedule is not None:
            updated_fields["schedule"] = request.schedule
        if request.status is not None:
            updated_fields["status"] = request.status
        
        updated_fields["updated_at"] = datetime.now().isoformat()
        
        result = {
            "strategy_id": strategy_id,
            "updated_fields": updated_fields,
            "update_count": len(updated_fields) - 1  # 减去updated_at字段
        }
        
        return ApiResponse(
            message="策略更新成功",
            data=result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{strategy_id}", summary="删除策略", description="删除指定策略")
def delete_strategy(strategy_id: str):
    """删除策略"""
    try:
        # 这里可以实现实际的策略删除逻辑
        # 需要检查策略是否正在运行
        
        delete_result = {
            "strategy_id": strategy_id,
            "deleted_at": datetime.now().isoformat(),
            "cleanup_completed": True
        }
        
        return ApiResponse(
            message="策略删除成功",
            data=delete_result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{strategy_id}/start", summary="启动策略", description="启动指定策略")
def start_strategy(strategy_id: str):
    """启动策略"""
    try:
        # 这里可以实现实际的策略启动逻辑
        start_result = {
            "strategy_id": strategy_id,
            "status": "active",
            "started_at": datetime.now().isoformat(),
            "next_execution": "2024-01-02T09:30:00"
        }
        
        return ApiResponse(
            message="策略启动成功",
            data=start_result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{strategy_id}/stop", summary="停止策略", description="停止指定策略")
def stop_strategy(strategy_id: str):
    """停止策略"""
    try:
        # 这里可以实现实际的策略停止逻辑
        stop_result = {
            "strategy_id": strategy_id,
            "status": "inactive",
            "stopped_at": datetime.now().isoformat(),
            "final_positions": []  # 可以返回最终持仓信息
        }
        
        return ApiResponse(
            message="策略停止成功",
            data=stop_result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{strategy_id}/execute", summary="执行策略", description="手动执行指定策略")
def execute_strategy(strategy_id: str, request: StrategyExecuteRequest):
    """执行策略"""
    try:
        # 这里可以实现实际的策略执行逻辑
        execution_result = {
            "strategy_id": strategy_id,
            "execution_id": f"EXEC_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "execution_mode": request.execution_mode,
            "executed_at": datetime.now().isoformat(),
            "signals_generated": 3,
            "orders_placed": 2,
            "execution_time": "0.5s",
            "signals": [
                {
                    "stock_code": "600000.SH",
                    "signal_type": "BUY",
                    "signal_strength": 0.85,
                    "recommended_price": 10.52,
                    "recommended_volume": 1000
                }
            ]
        }
        
        return ApiResponse(
            message="策略执行成功",
            data=execution_result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{strategy_id}/performance", summary="策略绩效", description="获取策略绩效分析")
def get_strategy_performance(strategy_id: str, period: str = Query("1M", description="分析周期")):
    """获取策略绩效"""
    try:
        # 这里可以实现实际的绩效分析
        performance = {
            "strategy_id": strategy_id,
            "period": period,
            "basic_metrics": {
                "total_return": 0.125,
                "annual_return": 0.156,
                "volatility": 0.18,
                "sharpe_ratio": 1.85,
                "max_drawdown": 0.08,
                "calmar_ratio": 1.95
            },
            "trade_metrics": {
                "total_trades": 156,
                "winning_trades": 106,
                "losing_trades": 50,
                "win_rate": 0.68,
                "profit_factor": 2.34,
                "avg_win": 0.025,
                "avg_loss": -0.012
            },
            "risk_metrics": {
                "var_95": 0.02,
                "cvar_95": 0.035,
                "beta": 0.95,
                "alpha": 0.02,
                "information_ratio": 0.85
            },
            "monthly_returns": [
                {"month": "2024-01", "return": 0.025},
                {"month": "2024-02", "return": 0.018},
                {"month": "2024-03", "return": -0.008}
            ],
            "drawdown_periods": [
                {
                    "start_date": "2024-02-15",
                    "end_date": "2024-02-28",
                    "max_drawdown": 0.05,
                    "duration_days": 13
                }
            ]
        }
        
        return ApiResponse(
            message="获取策略绩效成功",
            data=performance
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{strategy_id}/signals", summary="策略信号", description="获取策略生成的交易信号")
def get_strategy_signals(
    strategy_id: str,
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    signal_type: Optional[str] = Query(None, description="信号类型"),
    limit: int = Query(100, description="返回数量限制")
):
    """获取策略信号"""
    try:
        # 这里可以从数据库获取实际信号记录
        signals = [
            {
                "signal_id": "SIG_001",
                "strategy_id": strategy_id,
                "stock_code": "600000.SH",
                "stock_name": "浦发银行",
                "signal_type": "BUY",
                "signal_strength": 0.85,
                "price": 10.52,
                "volume": 1000,
                "generated_at": "2024-01-01T09:30:00",
                "executed": True,
                "execution_price": 10.53,
                "execution_time": "2024-01-01T09:30:15",
                "pnl": 10.0,
                "pnl_ratio": 0.001
            }
        ]
        
        result = {
            "strategy_id": strategy_id,
            "signals": signals,
            "total": len(signals),
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "signal_type": signal_type,
                "limit": limit
            },
            "summary": {
                "total_signals": len(signals),
                "buy_signals": len([s for s in signals if s["signal_type"] == "BUY"]),
                "sell_signals": len([s for s in signals if s["signal_type"] == "SELL"]),
                "executed_signals": len([s for s in signals if s["executed"]])
            }
        }
        
        return ApiResponse(
            message="获取策略信号成功",
            data=result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))