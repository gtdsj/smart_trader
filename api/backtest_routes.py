# -*- coding: utf-8 -*-
"""
回测服务API路由
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field, validator
from loguru import logger
import json

from services.backtest_service import BacktestService, BacktestStatus

# 创建路由器
router = APIRouter(prefix="/api/v1/backtest", tags=["回测服务"])

# 全局服务实例
_backtest_service: BacktestService = None

def set_backtest_service(service: BacktestService):
    """设置回测服务实例"""
    global _backtest_service
    _backtest_service = service

def get_backtest_service() -> BacktestService:
    """获取回测服务实例"""
    if _backtest_service is None:
        raise HTTPException(status_code=500, detail="回测服务未初始化")
    return _backtest_service


# 请求模型
class CreateBacktestRequest(BaseModel):
    """创建回测请求"""
    name: str = Field(..., description="回测名称")
    strategy_name: str = Field(..., description="策略名称")
    stock_codes: List[str] = Field(..., description="股票代码列表")
    start_date: str = Field(..., description="开始日期 (YYYY-MM-DD)")
    end_date: str = Field(..., description="结束日期 (YYYY-MM-DD)")
    initial_capital: float = Field(1000000.0, description="初始资金", gt=0)
    commission_rate: float = Field(0.0003, description="手续费率", ge=0, le=0.01)
    slippage: float = Field(0.001, description="滑点", ge=0, le=0.01)
    max_position_size: float = Field(0.1, description="最大持仓比例", gt=0, le=1)
    
    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('日期格式必须为 YYYY-MM-DD')
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if 'start_date' in values:
            start = datetime.strptime(values['start_date'], '%Y-%m-%d')
            end = datetime.strptime(v, '%Y-%m-%d')
            if end <= start:
                raise ValueError('结束日期必须晚于开始日期')
        return v


class BacktestParametersRequest(BaseModel):
    """回测参数请求"""
    initial_capital: Optional[float] = Field(None, description="初始资金", gt=0)
    commission_rate: Optional[float] = Field(None, description="手续费率", ge=0, le=0.01)
    slippage: Optional[float] = Field(None, description="滑点", ge=0, le=0.01)
    max_position_size: Optional[float] = Field(None, description="最大持仓比例", gt=0, le=1)


# 响应模型
class BacktestInfo(BaseModel):
    """回测信息"""
    id: str = Field(..., description="回测ID")
    name: str = Field(..., description="回测名称")
    strategy_name: str = Field(..., description="策略名称")
    stock_codes: List[str] = Field(..., description="股票代码列表")
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
    status: str = Field(..., description="回测状态")
    initial_capital: float = Field(..., description="初始资金")
    commission_rate: float = Field(..., description="手续费率")
    slippage: float = Field(..., description="滑点")
    max_position_size: float = Field(..., description="最大持仓比例")
    created_at: str = Field(..., description="创建时间")
    started_at: Optional[str] = Field(None, description="开始时间")
    completed_at: Optional[str] = Field(None, description="完成时间")
    progress: float = Field(0.0, description="进度百分比")


class BacktestResult(BaseModel):
    """回测结果"""
    backtest_id: str = Field(..., description="回测ID")
    total_return: float = Field(..., description="总收益率")
    annual_return: float = Field(..., description="年化收益率")
    sharpe_ratio: float = Field(..., description="夏普比率")
    max_drawdown: float = Field(..., description="最大回撤")
    win_rate: float = Field(..., description="胜率")
    total_trades: int = Field(..., description="总交易次数")
    final_value: float = Field(..., description="最终资产价值")
    benchmark_return: Optional[float] = Field(None, description="基准收益率")
    alpha: Optional[float] = Field(None, description="阿尔法")
    beta: Optional[float] = Field(None, description="贝塔")
    volatility: float = Field(..., description="波动率")
    calmar_ratio: float = Field(..., description="卡玛比率")
    sortino_ratio: float = Field(..., description="索提诺比率")


class TradeRecord(BaseModel):
    """交易记录"""
    date: str = Field(..., description="交易日期")
    stock_code: str = Field(..., description="股票代码")
    action: str = Field(..., description="交易动作")
    quantity: int = Field(..., description="交易数量")
    price: float = Field(..., description="交易价格")
    amount: float = Field(..., description="交易金额")
    commission: float = Field(..., description="手续费")
    reason: str = Field(..., description="交易原因")


class PositionRecord(BaseModel):
    """持仓记录"""
    date: str = Field(..., description="日期")
    stock_code: str = Field(..., description="股票代码")
    quantity: int = Field(..., description="持仓数量")
    avg_cost: float = Field(..., description="平均成本")
    market_value: float = Field(..., description="市值")
    unrealized_pnl: float = Field(..., description="浮动盈亏")
    weight: float = Field(..., description="持仓权重")


class PerformanceMetrics(BaseModel):
    """性能指标"""
    date: str = Field(..., description="日期")
    portfolio_value: float = Field(..., description="组合价值")
    cash: float = Field(..., description="现金")
    daily_return: float = Field(..., description="日收益率")
    cumulative_return: float = Field(..., description="累计收益率")
    drawdown: float = Field(..., description="回撤")
    benchmark_value: Optional[float] = Field(None, description="基准价值")


class ApiResponse(BaseModel):
    """API响应基类"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Any = Field(None, description="响应数据")


# API路由
@router.post("/create", response_model=ApiResponse, summary="创建回测任务")
async def create_backtest(
    request: CreateBacktestRequest,
    service: BacktestService = Depends(get_backtest_service)
):
    """创建回测任务"""
    try:
        backtest_id = await service.create_backtest(
            name=request.name,
            strategy_name=request.strategy_name,
            stock_codes=request.stock_codes,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            commission_rate=request.commission_rate,
            slippage=request.slippage,
            max_position_size=request.max_position_size
        )
        
        return ApiResponse(
            success=True,
            message="创建回测任务成功",
            data={"backtest_id": backtest_id}
        )
    
    except Exception as e:
        logger.error(f"创建回测任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start/{backtest_id}", response_model=ApiResponse, summary="启动回测")
async def start_backtest(
    backtest_id: str,
    background_tasks: BackgroundTasks,
    service: BacktestService = Depends(get_backtest_service)
):
    """启动回测"""
    try:
        # 异步启动回测
        background_tasks.add_task(_run_backtest_background, service, backtest_id)
        
        return ApiResponse(
            success=True,
            message="回测已启动",
            data={"backtest_id": backtest_id}
        )
    
    except Exception as e:
        logger.error(f"启动回测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _run_backtest_background(service: BacktestService, backtest_id: str):
    """后台运行回测"""
    try:
        await service.start_backtest(backtest_id)
        logger.info(f"回测{backtest_id}完成")
    except Exception as e:
        logger.error(f"后台回测失败: {e}")


@router.get("/list", response_model=ApiResponse, summary="获取回测列表")
async def get_backtests(
    status: Optional[str] = Query(None, description="回测状态过滤"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=200),
    offset: int = Query(0, description="偏移量", ge=0),
    service: BacktestService = Depends(get_backtest_service)
):
    """获取回测列表"""
    try:
        # 验证状态参数
        if status:
            try:
                BacktestStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的回测状态")
        
        backtests = await service.get_backtests(
            status=status,
            limit=limit,
            offset=offset
        )
        
        return ApiResponse(
            success=True,
            message="获取回测列表成功",
            data=backtests
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取回测列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{backtest_id}", response_model=ApiResponse, summary="获取回测状态")
async def get_backtest_status(
    backtest_id: str,
    service: BacktestService = Depends(get_backtest_service)
):
    """获取回测状态"""
    try:
        status_info = await service.get_backtest_status(backtest_id)
        if not status_info:
            raise HTTPException(status_code=404, detail="回测任务不存在")
        
        return ApiResponse(
            success=True,
            message="获取回测状态成功",
            data=status_info
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取回测状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/{backtest_id}", response_model=ApiResponse, summary="获取回测结果")
async def get_backtest_result(
    backtest_id: str,
    service: BacktestService = Depends(get_backtest_service)
):
    """获取回测结果"""
    try:
        result = await service.get_backtest_result(backtest_id)
        if not result:
            raise HTTPException(status_code=404, detail="回测结果不存在")
        
        return ApiResponse(
            success=True,
            message="获取回测结果成功",
            data=result
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取回测结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades/{backtest_id}", response_model=ApiResponse, summary="获取交易记录")
async def get_backtest_trades(
    backtest_id: str,
    stock_code: Optional[str] = Query(None, description="股票代码过滤"),
    action: Optional[str] = Query(None, description="交易动作过滤 (buy/sell)"),
    limit: int = Query(100, description="返回数量限制", ge=1, le=1000),
    service: BacktestService = Depends(get_backtest_service)
):
    """获取交易记录"""
    try:
        # 从缓存获取详细回测数据
        backtest_data_str = await service.cache_client.get(f"backtest_detail:{backtest_id}")
        backtest_data = json.loads(backtest_data_str) if backtest_data_str else None
        if not backtest_data:
            raise HTTPException(status_code=404, detail="回测数据不存在")
        
        trades = backtest_data.get("trades", [])
        
        # 应用过滤条件
        if stock_code:
            trades = [t for t in trades if t.get("stock_code") == stock_code]
        
        if action:
            if action not in ["buy", "sell"]:
                raise HTTPException(status_code=400, detail="无效的交易动作")
            trades = [t for t in trades if t.get("action") == action]
        
        # 限制返回数量
        trades = trades[:limit]
        
        return ApiResponse(
            success=True,
            message="获取交易记录成功",
            data=trades
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取交易记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions/{backtest_id}", response_model=ApiResponse, summary="获取持仓记录")
async def get_backtest_positions(
    backtest_id: str,
    date: Optional[str] = Query(None, description="指定日期 (YYYY-MM-DD)"),
    stock_code: Optional[str] = Query(None, description="股票代码过滤"),
    service: BacktestService = Depends(get_backtest_service)
):
    """获取持仓记录"""
    try:
        # 验证日期格式
        if date:
            try:
                datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="日期格式必须为 YYYY-MM-DD")
        
        # 从缓存获取详细回测数据
        backtest_data_str = await service.cache_client.get(f"backtest_detail:{backtest_id}")
        backtest_data = json.loads(backtest_data_str) if backtest_data_str else None
        if not backtest_data:
            raise HTTPException(status_code=404, detail="回测数据不存在")
        
        positions = backtest_data.get("positions", [])
        
        # 应用过滤条件
        if date:
            positions = [p for p in positions if p.get("date") == date]
        
        if stock_code:
            positions = [p for p in positions if p.get("stock_code") == stock_code]
        
        return ApiResponse(
            success=True,
            message="获取持仓记录成功",
            data=positions
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取持仓记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/{backtest_id}", response_model=ApiResponse, summary="获取性能指标")
async def get_backtest_performance(
    backtest_id: str,
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    service: BacktestService = Depends(get_backtest_service)
):
    """获取性能指标时间序列"""
    try:
        # 验证日期格式
        if start_date:
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="开始日期格式必须为 YYYY-MM-DD")
        
        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="结束日期格式必须为 YYYY-MM-DD")
        
        # 从缓存获取详细回测数据
        backtest_data_str = await service.cache_client.get(f"backtest_detail:{backtest_id}")
        backtest_data = json.loads(backtest_data_str) if backtest_data_str else None
        if not backtest_data:
            raise HTTPException(status_code=404, detail="回测数据不存在")
        
        performance = backtest_data.get("performance", [])
        
        # 应用日期过滤
        if start_date:
            performance = [p for p in performance if p.get("date") >= start_date]
        
        if end_date:
            performance = [p for p in performance if p.get("date") <= end_date]
        
        return ApiResponse(
            success=True,
            message="获取性能指标成功",
            data=performance
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取性能指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop/{backtest_id}", response_model=ApiResponse, summary="停止回测")
async def stop_backtest(
    backtest_id: str,
    service: BacktestService = Depends(get_backtest_service)
):
    """停止回测"""
    try:
        success = await service.stop_backtest(backtest_id)
        if success:
            return ApiResponse(
                success=True,
                message="停止回测成功",
                data={"backtest_id": backtest_id}
            )
        else:
            raise HTTPException(status_code=500, detail="停止回测失败")
    
    except Exception as e:
        logger.error(f"停止回测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{backtest_id}", response_model=ApiResponse, summary="删除回测")
async def delete_backtest(
    backtest_id: str,
    service: BacktestService = Depends(get_backtest_service)
):
    """删除回测任务和结果"""
    try:
        # 删除缓存中的详细数据
        await service.cache_client.delete(f"backtest_detail:{backtest_id}")
        await service.cache_client.delete(f"backtest_status:{backtest_id}")
        
        # 删除数据库中的记录
        # 这里需要实现数据库删除逻辑
        
        return ApiResponse(
            success=True,
            message="删除回测成功",
            data={"backtest_id": backtest_id}
        )
    
    except Exception as e:
        logger.error(f"删除回测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare", response_model=ApiResponse, summary="比较回测结果")
async def compare_backtests(
    backtest_ids: str = Query(..., description="回测ID列表，用逗号分隔"),
    service: BacktestService = Depends(get_backtest_service)
):
    """比较多个回测结果"""
    try:
        # 解析回测ID列表
        ids = [id.strip() for id in backtest_ids.split(',') if id.strip()]
        if len(ids) < 2:
            raise HTTPException(status_code=400, detail="至少需要两个回测ID进行比较")
        
        if len(ids) > 5:
            raise HTTPException(status_code=400, detail="最多只能比较5个回测")
        
        # 获取各个回测的结果
        comparison_data = []
        for backtest_id in ids:
            result = await service.get_backtest_result(backtest_id)
            if result:
                comparison_data.append({
                    "backtest_id": backtest_id,
                    "name": result.get("name", backtest_id),
                    "strategy_name": result.get("strategy_name"),
                    "total_return": result.get("total_return"),
                    "annual_return": result.get("annual_return"),
                    "sharpe_ratio": result.get("sharpe_ratio"),
                    "max_drawdown": result.get("max_drawdown"),
                    "win_rate": result.get("win_rate"),
                    "total_trades": result.get("total_trades"),
                    "volatility": result.get("volatility")
                })
        
        if not comparison_data:
            raise HTTPException(status_code=404, detail="未找到有效的回测结果")
        
        return ApiResponse(
            success=True,
            message="回测比较成功",
            data=comparison_data
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"回测比较失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=ApiResponse, summary="获取回测统计")
async def get_backtest_statistics(
    service: BacktestService = Depends(get_backtest_service)
):
    """获取回测统计信息"""
    try:
        # 从数据库获取统计信息
        # 这里简化处理，实际应该查询数据库
        statistics = {
            "total_backtests": 0,
            "running_backtests": 0,
            "completed_backtests": 0,
            "failed_backtests": 0,
            "avg_completion_time": 0.0,
            "most_used_strategies": [],
            "best_performing_backtest": None,
            "last_updated": datetime.now().isoformat()
        }
        
        return ApiResponse(
            success=True,
            message="获取回测统计成功",
            data=statistics
        )
    
    except Exception as e:
        logger.error(f"获取回测统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))