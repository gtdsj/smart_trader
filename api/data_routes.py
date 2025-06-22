# -*- coding: utf-8 -*-
"""
数据服务API路由
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from loguru import logger

from services.data_service import DataService

# 创建路由器
router = APIRouter(prefix="/api/v1/data", tags=["数据服务"])

# 全局服务实例
_data_service: DataService = None

def set_data_service(service: DataService):
    """设置数据服务实例"""
    global _data_service
    _data_service = service

def get_data_service() -> DataService:
    """获取数据服务实例"""
    if _data_service is None:
        raise HTTPException(status_code=500, detail="数据服务未初始化")
    return _data_service


# 请求模型
class StockListRequest(BaseModel):
    """股票列表请求"""
    market: Optional[str] = Field(None, description="市场代码，如SH、SZ")
    limit: int = Field(100, description="返回数量限制", ge=1, le=1000)


class HistoricalDataRequest(BaseModel):
    """历史数据请求"""
    stock_code: str = Field(..., description="股票代码")
    start_date: str = Field(..., description="开始日期，格式YYYY-MM-DD")
    end_date: str = Field(..., description="结束日期，格式YYYY-MM-DD")
    period: str = Field("1d", description="数据周期：1d, 1w, 1m")


class RealtimeDataRequest(BaseModel):
    """实时数据请求"""
    stock_codes: List[str] = Field(..., description="股票代码列表")


class WatchlistRequest(BaseModel):
    """监控列表请求"""
    stock_codes: List[str] = Field(..., description="股票代码列表")


# 响应模型
class StockInfo(BaseModel):
    """股票信息"""
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    market: str = Field(..., description="市场")
    industry: Optional[str] = Field(None, description="行业")
    list_date: Optional[str] = Field(None, description="上市日期")


class StockData(BaseModel):
    """股票数据"""
    stock_code: str = Field(..., description="股票代码")
    trade_date: str = Field(..., description="交易日期")
    open_price: float = Field(..., description="开盘价")
    high_price: float = Field(..., description="最高价")
    low_price: float = Field(..., description="最低价")
    close_price: float = Field(..., description="收盘价")
    volume: int = Field(..., description="成交量")
    amount: Optional[float] = Field(None, description="成交额")
    change_rate: Optional[float] = Field(None, description="涨跌幅")


class RealtimeData(BaseModel):
    """实时数据"""
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    current_price: float = Field(..., description="当前价格")
    change_amount: float = Field(..., description="涨跌额")
    change_rate: float = Field(..., description="涨跌幅")
    volume: int = Field(..., description="成交量")
    amount: float = Field(..., description="成交额")
    high_price: float = Field(..., description="最高价")
    low_price: float = Field(..., description="最低价")
    open_price: float = Field(..., description="开盘价")
    prev_close: float = Field(..., description="昨收价")
    timestamp: str = Field(..., description="时间戳")


class ApiResponse(BaseModel):
    """API响应基类"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Any = Field(None, description="响应数据")


# API路由
@router.get("/status", response_model=ApiResponse, summary="获取数据服务状态")
async def get_data_service_status(service: DataService = Depends(get_data_service)):
    """获取数据服务状态"""
    try:
        status = {
            "is_running": service.is_running,
            "last_update": service.last_update_time.isoformat() if service.last_update_time else None,
            "watched_stocks_count": len(service.watched_stocks),
            "cache_status": "connected" if service.redis_client else "disconnected"
        }
        
        return ApiResponse(
            success=True,
            message="获取数据服务状态成功",
            data=status
        )
    except Exception as e:
        logger.error(f"获取数据服务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start", response_model=ApiResponse, summary="启动数据服务")
async def start_data_service(service: DataService = Depends(get_data_service)):
    """启动数据服务"""
    try:
        success = await service.start()
        if success:
            return ApiResponse(
                success=True,
                message="数据服务启动成功",
                data=None
            )
        else:
            raise HTTPException(status_code=500, detail="数据服务启动失败")
    except Exception as e:
        logger.error(f"启动数据服务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=ApiResponse, summary="停止数据服务")
async def stop_data_service(service: DataService = Depends(get_data_service)):
    """停止数据服务"""
    try:
        await service.stop()
        return ApiResponse(
            success=True,
            message="数据服务停止成功",
            data=None
        )
    except Exception as e:
        logger.error(f"停止数据服务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks", response_model=ApiResponse, summary="获取股票列表")
async def get_stock_list(
    market: Optional[str] = Query(None, description="市场代码"),
    limit: int = Query(100, description="返回数量限制", ge=1, le=1000),
    service: DataService = Depends(get_data_service)
):
    """获取股票列表"""
    try:
        stocks = await service.get_stock_list()
        
        # 过滤市场
        if market:
            stocks = [stock for stock in stocks if stock.get("market") == market]
        
        # 限制数量
        stocks = stocks[:limit]
        
        return ApiResponse(
            success=True,
            message="获取股票列表成功",
            data=stocks
        )
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/realtime", response_model=ApiResponse, summary="获取实时数据")
async def get_realtime_data(
    request: RealtimeDataRequest,
    service: DataService = Depends(get_data_service)
):
    """获取实时数据"""
    try:
        if len(request.stock_codes) > 50:
            raise HTTPException(status_code=400, detail="股票代码数量不能超过50个")
        
        realtime_data = []
        for stock_code in request.stock_codes:
            data = await service.get_realtime_data(stock_code)
            if data:
                realtime_data.append(data)
        
        return ApiResponse(
            success=True,
            message="获取实时数据成功",
            data=realtime_data
        )
    except Exception as e:
        logger.error(f"获取实时数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/historical", response_model=ApiResponse, summary="获取历史数据")
async def get_historical_data(
    request: HistoricalDataRequest,
    service: DataService = Depends(get_data_service)
):
    """获取历史数据"""
    try:
        # 验证日期格式
        try:
            start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(request.end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，应为YYYY-MM-DD")
        
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="开始日期不能大于结束日期")
        
        if (end_date - start_date).days > 365:
            raise HTTPException(status_code=400, detail="日期范围不能超过365天")
        
        df = await service.get_historical_data(
            request.stock_code, 
            request.start_date, 
            request.end_date,
            request.period
        )
        
        if df.empty:
            return ApiResponse(
                success=True,
                message="未找到历史数据",
                data=[]
            )
        
        # 转换为字典列表
        data = df.to_dict('records')
        
        # 格式化日期
        for record in data:
            if 'trade_date' in record and hasattr(record['trade_date'], 'strftime'):
                record['trade_date'] = record['trade_date'].strftime('%Y-%m-%d')
        
        return ApiResponse(
            success=True,
            message="获取历史数据成功",
            data=data
        )
    except Exception as e:
        logger.error(f"获取历史数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/watchlist", response_model=ApiResponse, summary="获取监控列表")
async def get_watchlist(service: DataService = Depends(get_data_service)):
    """获取监控列表"""
    try:
        watchlist = list(service.watched_stocks)
        return ApiResponse(
            success=True,
            message="获取监控列表成功",
            data=watchlist
        )
    except Exception as e:
        logger.error(f"获取监控列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchlist/add", response_model=ApiResponse, summary="添加监控股票")
async def add_to_watchlist(
    request: WatchlistRequest,
    service: DataService = Depends(get_data_service)
):
    """添加监控股票"""
    try:
        if len(request.stock_codes) > 100:
            raise HTTPException(status_code=400, detail="一次最多添加100只股票")
        
        added_count = 0
        for stock_code in request.stock_codes:
            if await service.add_watched_stock(stock_code):
                added_count += 1
        
        return ApiResponse(
            success=True,
            message=f"成功添加{added_count}只股票到监控列表",
            data={"added_count": added_count}
        )
    except Exception as e:
        logger.error(f"添加监控股票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchlist/remove", response_model=ApiResponse, summary="移除监控股票")
async def remove_from_watchlist(
    request: WatchlistRequest,
    service: DataService = Depends(get_data_service)
):
    """移除监控股票"""
    try:
        removed_count = 0
        for stock_code in request.stock_codes:
            if await service.remove_watched_stock(stock_code):
                removed_count += 1
        
        return ApiResponse(
            success=True,
            message=f"成功移除{removed_count}只股票",
            data={"removed_count": removed_count}
        )
    except Exception as e:
        logger.error(f"移除监控股票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/status", response_model=ApiResponse, summary="获取市场状态")
async def get_market_status(service: DataService = Depends(get_data_service)):
    """获取市场状态"""
    try:
        is_trading_time = service.is_trading_time()
        current_time = datetime.now()
        
        status = {
            "is_trading_time": is_trading_time,
            "current_time": current_time.isoformat(),
            "market_status": "开市" if is_trading_time else "闭市"
        }
        
        return ApiResponse(
            success=True,
            message="获取市场状态成功",
            data=status
        )
    except Exception as e:
        logger.error(f"获取市场状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats", response_model=ApiResponse, summary="获取缓存统计")
async def get_cache_stats(service: DataService = Depends(get_data_service)):
    """获取缓存统计"""
    try:
        if not service.redis_client:
            raise HTTPException(status_code=500, detail="Redis客户端未连接")
        
        # 获取缓存键统计
        keys = await service.redis_client.redis.keys("stock_data:*")
        realtime_keys = await service.redis_client.redis.keys("realtime:*")
        
        stats = {
            "total_cached_stocks": len(keys),
            "realtime_cached_stocks": len(realtime_keys),
            "cache_hit_rate": "N/A",  # 需要实现缓存命中率统计
            "memory_usage": "N/A"     # 需要实现内存使用统计
        }
        
        return ApiResponse(
            success=True,
            message="获取缓存统计成功",
            data=stats
        )
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache/clear", response_model=ApiResponse, summary="清空缓存")
async def clear_cache(
    pattern: str = Query("stock_data:*", description="缓存键模式"),
    service: DataService = Depends(get_data_service)
):
    """清空缓存"""
    try:
        if not service.redis_client:
            raise HTTPException(status_code=500, detail="Redis客户端未连接")
        
        # 获取匹配的键
        keys = await service.redis_client.redis.keys(pattern)
        
        if keys:
            # 删除键
            await service.redis_client.redis.delete(*keys)
            cleared_count = len(keys)
        else:
            cleared_count = 0
        
        return ApiResponse(
            success=True,
            message=f"成功清空{cleared_count}个缓存项",
            data={"cleared_count": cleared_count}
        )
    except Exception as e:
        logger.error(f"清空缓存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))