# -*- coding: utf-8 -*-
"""
策略服务API路由
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from loguru import logger

from services.strategy_service import StrategyService, StrategyType, SignalType

# 创建路由器
router = APIRouter(prefix="/api/v1/strategy", tags=["策略服务"])

# 全局服务实例
_strategy_service: StrategyService = None

def set_strategy_service(service: StrategyService):
    """设置策略服务实例"""
    global _strategy_service
    _strategy_service = service

def get_strategy_service() -> StrategyService:
    """获取策略服务实例"""
    if _strategy_service is None:
        raise HTTPException(status_code=500, detail="策略服务未初始化")
    return _strategy_service


# 请求模型
class CreateStrategyRequest(BaseModel):
    """创建策略请求"""
    name: str = Field(..., description="策略名称")
    description: str = Field(..., description="策略描述")
    strategy_type: str = Field(..., description="策略类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="策略参数")


class RunStrategyRequest(BaseModel):
    """运行策略请求"""
    strategy_name: str = Field(..., description="策略名称")
    stock_codes: Optional[List[str]] = Field(None, description="股票代码列表")


class StrategyParametersRequest(BaseModel):
    """策略参数请求"""
    parameters: Dict[str, Any] = Field(..., description="策略参数")


# 响应模型
class StrategyInfo(BaseModel):
    """策略信息"""
    id: int = Field(..., description="策略ID")
    name: str = Field(..., description="策略名称")
    description: str = Field(..., description="策略描述")
    strategy_type: str = Field(..., description="策略类型")
    parameters: Dict[str, Any] = Field(..., description="策略参数")
    is_active: bool = Field(..., description="是否激活")
    created_at: Optional[str] = Field(None, description="创建时间")


class SignalInfo(BaseModel):
    """信号信息"""
    stock_code: str = Field(..., description="股票代码")
    signal: str = Field(..., description="信号类型")
    strategy: str = Field(..., description="策略名称")
    reason: str = Field(..., description="信号原因")
    strength: float = Field(..., description="信号强度")
    price: float = Field(..., description="价格")
    timestamp: str = Field(..., description="时间戳")


class StrategyResult(BaseModel):
    """策略结果"""
    strategy_name: str = Field(..., description="策略名称")
    signals: List[SignalInfo] = Field(..., description="信号列表")
    scan_time: str = Field(..., description="扫描时间")
    total_stocks: int = Field(..., description="扫描股票总数")
    signal_count: int = Field(..., description="信号数量")


class ApiResponse(BaseModel):
    """API响应基类"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Any = Field(None, description="响应数据")


# API路由
@router.get("/types", response_model=ApiResponse, summary="获取策略类型列表")
async def get_strategy_types():
    """获取策略类型列表"""
    try:
        types = [
            {
                "value": strategy_type.value,
                "label": {
                    "technical": "技术分析",
                    "fundamental": "基本面分析",
                    "quantitative": "量化分析",
                    "momentum": "动量策略",
                    "mean_reversion": "均值回归",
                    "breakout": "突破策略"
                }.get(strategy_type.value, strategy_type.value)
            }
            for strategy_type in StrategyType
        ]
        
        return ApiResponse(
            success=True,
            message="获取策略类型成功",
            data=types
        )
    except Exception as e:
        logger.error(f"获取策略类型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/available", response_model=ApiResponse, summary="获取可用策略列表")
async def get_available_strategies(service: StrategyService = Depends(get_strategy_service)):
    """获取可用策略列表"""
    try:
        available_strategies = [
            {
                "name": name,
                "description": {
                    "ma_cross": "均线交叉策略",
                    "rsi_oversold": "RSI超卖策略",
                    "bollinger_bands": "布林带策略",
                    "volume_breakout": "成交量突破策略",
                    "momentum": "动量策略",
                    "mean_reversion": "均值回归策略",
                    "macd_signal": "MACD信号策略",
                    "kdj_signal": "KDJ信号策略"
                }.get(name, name)
            }
            for name in service.strategies.keys()
        ]
        
        return ApiResponse(
            success=True,
            message="获取可用策略成功",
            data=available_strategies
        )
    except Exception as e:
        logger.error(f"获取可用策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create", response_model=ApiResponse, summary="创建策略")
async def create_strategy(
    request: CreateStrategyRequest,
    service: StrategyService = Depends(get_strategy_service)
):
    """创建策略"""
    try:
        # 验证策略类型
        try:
            StrategyType(request.strategy_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的策略类型")
        
        success = await service.create_strategy(
            name=request.name,
            description=request.description,
            strategy_type=request.strategy_type,
            parameters=request.parameters
        )
        
        if success:
            return ApiResponse(
                success=True,
                message="创建策略成功",
                data=None
            )
        else:
            raise HTTPException(status_code=500, detail="创建策略失败")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=ApiResponse, summary="获取策略列表")
async def get_strategies(
    active_only: bool = Query(False, description="仅返回激活的策略"),
    service: StrategyService = Depends(get_strategy_service)
):
    """获取策略列表"""
    try:
        strategies = await service.get_strategies(active_only=active_only)
        return ApiResponse(
            success=True,
            message="获取策略列表成功",
            data=strategies
        )
    except Exception as e:
        logger.error(f"获取策略列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/activate/{strategy_id}", response_model=ApiResponse, summary="激活策略")
async def activate_strategy(
    strategy_id: int,
    service: StrategyService = Depends(get_strategy_service)
):
    """激活策略"""
    try:
        success = await service.activate_strategy(strategy_id)
        if success:
            return ApiResponse(
                success=True,
                message="激活策略成功",
                data=None
            )
        else:
            raise HTTPException(status_code=500, detail="激活策略失败")
    except Exception as e:
        logger.error(f"激活策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deactivate/{strategy_id}", response_model=ApiResponse, summary="停用策略")
async def deactivate_strategy(
    strategy_id: int,
    service: StrategyService = Depends(get_strategy_service)
):
    """停用策略"""
    try:
        success = await service.deactivate_strategy(strategy_id)
        if success:
            return ApiResponse(
                success=True,
                message="停用策略成功",
                data=None
            )
        else:
            raise HTTPException(status_code=500, detail="停用策略失败")
    except Exception as e:
        logger.error(f"停用策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run", response_model=ApiResponse, summary="运行策略扫描")
async def run_strategy_scan(
    request: RunStrategyRequest,
    background_tasks: BackgroundTasks,
    service: StrategyService = Depends(get_strategy_service)
):
    """运行策略扫描"""
    try:
        # 验证策略是否存在
        if request.strategy_name not in service.strategies:
            raise HTTPException(status_code=400, detail="策略不存在")
        
        # 异步运行策略扫描
        background_tasks.add_task(
            _run_strategy_scan_background,
            service,
            request.strategy_name,
            request.stock_codes
        )
        
        return ApiResponse(
            success=True,
            message="策略扫描已启动",
            data={"strategy_name": request.strategy_name}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"运行策略扫描失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _run_strategy_scan_background(
    service: StrategyService,
    strategy_name: str,
    stock_codes: Optional[List[str]]
):
    """后台运行策略扫描"""
    try:
        signals = await service.run_strategy_scan(strategy_name, stock_codes)
        logger.info(f"策略{strategy_name}扫描完成，发现{len(signals)}个信号")
    except Exception as e:
        logger.error(f"后台策略扫描失败: {e}")


@router.post("/run/all", response_model=ApiResponse, summary="运行所有激活策略")
async def run_all_active_strategies(
    background_tasks: BackgroundTasks,
    service: StrategyService = Depends(get_strategy_service)
):
    """运行所有激活策略"""
    try:
        # 异步运行所有激活策略
        background_tasks.add_task(_run_all_strategies_background, service)
        
        return ApiResponse(
            success=True,
            message="所有激活策略扫描已启动",
            data=None
        )
    except Exception as e:
        logger.error(f"运行所有激活策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _run_all_strategies_background(service: StrategyService):
    """后台运行所有策略"""
    try:
        results = await service.run_all_active_strategies()
        total_signals = sum(len(signals) for signals in results.values())
        logger.info(f"所有激活策略扫描完成，共发现{total_signals}个信号")
    except Exception as e:
        logger.error(f"后台运行所有策略失败: {e}")


@router.get("/scan/{strategy_name}", response_model=ApiResponse, summary="获取策略扫描结果")
async def get_strategy_scan_result(
    strategy_name: str,
    stock_codes: Optional[str] = Query(None, description="股票代码，多个用逗号分隔"),
    service: StrategyService = Depends(get_strategy_service)
):
    """获取策略扫描结果（同步）"""
    try:
        # 验证策略是否存在
        if strategy_name not in service.strategies:
            raise HTTPException(status_code=400, detail="策略不存在")
        
        # 解析股票代码
        stock_code_list = None
        if stock_codes:
            stock_code_list = [code.strip() for code in stock_codes.split(',') if code.strip()]
        
        # 运行策略扫描
        signals = await service.run_strategy_scan(strategy_name, stock_code_list)
        
        result = {
            "strategy_name": strategy_name,
            "signals": signals,
            "scan_time": datetime.now().isoformat(),
            "total_stocks": len(stock_code_list) if stock_code_list else 0,
            "signal_count": len(signals)
        }
        
        return ApiResponse(
            success=True,
            message="策略扫描完成",
            data=result
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略扫描结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/latest", response_model=ApiResponse, summary="获取最新信号")
async def get_latest_signals(
    strategy_name: Optional[str] = Query(None, description="策略名称"),
    signal_type: Optional[str] = Query(None, description="信号类型"),
    min_strength: float = Query(0.0, description="最小信号强度", ge=0.0, le=1.0),
    limit: int = Query(50, description="返回数量限制", ge=1, le=200),
    service: StrategyService = Depends(get_strategy_service)
):
    """获取最新信号"""
    try:
        # 从Redis缓存获取最新信号
        cache_key = "latest_signals"
        cached_signals = await service.redis_client.get(cache_key)
        
        if not cached_signals:
            # 如果缓存为空，运行一次快速扫描
            results = await service.run_all_active_strategies()
            signals = []
            for strategy, strategy_signals in results.items():
                signals.extend(strategy_signals)
            
            # 缓存结果
            await service.redis_client.set(cache_key, signals, expire=300)  # 5分钟缓存
        else:
            signals = cached_signals
        
        # 过滤条件
        if strategy_name:
            signals = [s for s in signals if s.get("strategy") == strategy_name]
        
        if signal_type:
            try:
                SignalType(signal_type)
                signals = [s for s in signals if s.get("signal") == signal_type]
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的信号类型")
        
        if min_strength > 0:
            signals = [s for s in signals if s.get("strength", 0) >= min_strength]
        
        # 按强度排序并限制数量
        signals.sort(key=lambda x: x.get("strength", 0), reverse=True)
        signals = signals[:limit]
        
        return ApiResponse(
            success=True,
            message="获取最新信号成功",
            data=signals
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取最新信号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/{strategy_name}", response_model=ApiResponse, summary="获取策略性能")
async def get_strategy_performance(
    strategy_name: str,
    days: int = Query(30, description="统计天数", ge=1, le=365),
    service: StrategyService = Depends(get_strategy_service)
):
    """获取策略性能统计"""
    try:
        # 验证策略是否存在
        if strategy_name not in service.strategies:
            raise HTTPException(status_code=400, detail="策略不存在")
        
        # 从缓存或数据库获取历史信号数据
        # 这里简化处理，实际应该从数据库查询历史信号记录
        performance = {
            "strategy_name": strategy_name,
            "period_days": days,
            "total_signals": 0,
            "buy_signals": 0,
            "sell_signals": 0,
            "avg_strength": 0.0,
            "success_rate": 0.0,  # 需要根据后续价格变化计算
            "last_updated": datetime.now().isoformat()
        }
        
        return ApiResponse(
            success=True,
            message="获取策略性能成功",
            data=performance
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略性能失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parameters/{strategy_name}", response_model=ApiResponse, summary="获取策略参数")
async def get_strategy_parameters(
    strategy_name: str,
    service: StrategyService = Depends(get_strategy_service)
):
    """获取策略参数"""
    try:
        # 验证策略是否存在
        if strategy_name not in service.strategies:
            raise HTTPException(status_code=400, detail="策略不存在")
        
        # 获取策略默认参数
        default_parameters = {
            "ma_cross": {
                "short_period": 5,
                "long_period": 20,
                "min_volume": 1000000
            },
            "rsi_oversold": {
                "period": 14,
                "oversold_threshold": 30,
                "overbought_threshold": 70
            },
            "bollinger_bands": {
                "period": 20,
                "std_multiplier": 2.0
            },
            "volume_breakout": {
                "volume_period": 20,
                "volume_multiplier": 2.0,
                "price_change_threshold": 0.03
            },
            "momentum": {
                "short_period": 5,
                "long_period": 10,
                "momentum_threshold": 0.05
            },
            "mean_reversion": {
                "period": 20,
                "deviation_threshold": 0.1
            },
            "macd_signal": {
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9
            },
            "kdj_signal": {
                "period": 9,
                "oversold_threshold": 20,
                "overbought_threshold": 80
            }
        }
        
        parameters = default_parameters.get(strategy_name, {})
        
        return ApiResponse(
            success=True,
            message="获取策略参数成功",
            data=parameters
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略参数失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/{strategy_name}", response_model=ApiResponse, summary="测试策略")
async def test_strategy(
    strategy_name: str,
    stock_code: str = Query(..., description="测试股票代码"),
    service: StrategyService = Depends(get_strategy_service)
):
    """测试单个股票的策略信号"""
    try:
        # 验证策略是否存在
        if strategy_name not in service.strategies:
            raise HTTPException(status_code=400, detail="策略不存在")
        
        # 运行策略
        strategy_func = service.strategies[strategy_name]
        signal = await strategy_func(stock_code)
        
        if signal:
            return ApiResponse(
                success=True,
                message="策略测试完成",
                data=signal
            )
        else:
            return ApiResponse(
                success=True,
                message="策略测试完成，无信号",
                data=None
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))