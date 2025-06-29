# -*- coding: utf-8 -*-
"""
数据服务API路由
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
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


class DailyDataRequest(BaseModel):
    """日线数据请求"""
    stock_code: str = Field(..., description="股票代码")
    start_date: Optional[str] = Field(None, description="开始日期，格式YYYY-MM-DD，默认为增量更新")
    end_date: Optional[str] = Field(None, description="结束日期，格式YYYY-MM-DD，默认为今天")
    save_to_db: bool = Field(True, description="是否保存到数据库")


class BatchDailyDataRequest(BaseModel):
    """批量日线数据请求"""
    stock_codes: List[str] = Field(..., description="股票代码列表")
    start_date: Optional[str] = Field(None, description="开始日期，格式YYYY-MM-DD，默认为增量更新")
    end_date: Optional[str] = Field(None, description="结束日期，格式YYYY-MM-DD，默认为今天")


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


@router.post("/daily", response_model=ApiResponse, summary="获取股票日线数据")
async def get_stock_daily_data(
    request: DailyDataRequest,
    service: DataService = Depends(get_data_service)
):
    """获取指定股票的日线数据并保存到DuckDB
    
    支持增量更新：
    - 如果不指定start_date，会自动从数据库最新日期开始增量更新
    - 如果数据库中没有该股票数据，会获取最近3年的历史数据
    - 支持指定日期范围获取特定时间段的数据
    """
    try:
        # 验证日期格式
        if request.start_date:
            try:
                datetime.strptime(request.start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="开始日期格式错误，应为YYYY-MM-DD")
        
        if request.end_date:
            try:
                datetime.strptime(request.end_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="结束日期格式错误，应为YYYY-MM-DD")
        
        if request.start_date and request.end_date:
            start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(request.end_date, "%Y-%m-%d")
            if start_date > end_date:
                raise HTTPException(status_code=400, detail="开始日期不能大于结束日期")
        
        # 获取日线数据
        df = await service.get_stock_daily_data(
            stock_code=request.stock_code,
            start_date=request.start_date,
            end_date=request.end_date,
            save_to_db=request.save_to_db
        )
        
        if df.empty:
            return ApiResponse(
                success=True,
                message=f"未获取到{request.stock_code}的日线数据",
                data=[]
            )
        
        # 转换为字典列表
        data = df.to_dict('records')
        
        # 格式化日期和数值
        for record in data:
            if 'trade_date' in record:
                if hasattr(record['trade_date'], 'strftime'):
                    record['trade_date'] = record['trade_date'].strftime('%Y-%m-%d')
                else:
                    record['trade_date'] = str(record['trade_date'])
            
            # 格式化数值字段
            for field in ['open_price', 'high_price', 'low_price', 'close_price', 'amount', 'turnover_rate', 'pe_ratio', 'pb_ratio']:
                if field in record and record[field] is not None:
                    record[field] = round(float(record[field]), 3)
        
        return ApiResponse(
            success=True,
            message=f"成功获取{request.stock_code}的{len(data)}条日线数据",
            data={
                "stock_code": request.stock_code,
                "total_records": len(data),
                "data": data
            }
        )
        
    except Exception as e:
        logger.error(f"获取{request.stock_code}日线数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/daily/batch", response_model=ApiResponse, summary="批量获取股票日线数据")
async def batch_get_daily_data(
    request: BatchDailyDataRequest,
    service: DataService = Depends(get_data_service)
):
    """批量获取多只股票的日线数据
    
    支持批量增量更新，适用于定时任务或大量股票数据更新
    """
    try:
        # 验证股票代码数量
        if len(request.stock_codes) > 100:
            raise HTTPException(status_code=400, detail="单次批量请求股票数量不能超过100只")
        
        # 验证日期格式
        if request.start_date:
            try:
                datetime.strptime(request.start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="开始日期格式错误，应为YYYY-MM-DD")
        
        if request.end_date:
            try:
                datetime.strptime(request.end_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="结束日期格式错误，应为YYYY-MM-DD")
        
        # 批量更新数据
        results = await service.batch_update_daily_data(request.stock_codes)
        
        return ApiResponse(
            success=True,
            message=f"批量更新完成：成功{results['success_count']}只，失败{results['failed_count']}只",
            data=results
        )
        
    except Exception as e:
        logger.error(f"批量获取日线数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/daily/incremental-update-all", response_model=ApiResponse, summary="增量补全A股所有股票历史日线数据")
async def incremental_update_all_stocks(
    market: Optional[str] = Query("ALL", description="市场代码：SH、SZ或ALL"),
    batch_size: int = Query(50, description="批量处理大小", ge=1, le=100),
    service: DataService = Depends(get_data_service)
):
    """增量补全A股所有股票的历史日线数据
    
    该接口将：
    1. 获取指定市场的所有股票列表
    2. 分批次进行增量更新（从数据库最新日期开始补全到今天）
    3. 返回详细的更新统计信息
    
    适用于定时任务或系统初始化时的数据补全
    """
    try:
        logger.info(f"开始增量补全{market}市场所有股票的历史日线数据")
        
        # 获取股票列表
        all_stocks = await service.get_stock_list(market)
        if not all_stocks:
            return ApiResponse(
                success=False,
                message="未获取到股票列表",
                data=None
            )
        
        stock_codes = [stock["stock_code"] for stock in all_stocks]
        total_stocks = len(stock_codes)
        
        logger.info(f"获取到{total_stocks}只股票，开始分批增量更新")
        
        # 分批处理
        batch_results = []
        success_count = 0
        failed_count = 0
        total_records = 0
        failed_stocks = []
        success_stocks = []
        
        for i in range(0, total_stocks, batch_size):
            batch_stocks = stock_codes[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_stocks + batch_size - 1) // batch_size
            
            logger.info(f"处理第{batch_num}/{total_batches}批，包含{len(batch_stocks)}只股票")
            
            # 批量更新当前批次
            batch_result = await service.batch_update_daily_data(batch_stocks)
            batch_results.append({
                "batch_num": batch_num,
                "stocks_in_batch": len(batch_stocks),
                "result": batch_result
            })
            
            # 累计统计
            success_count += batch_result.get('success_count', 0)
            failed_count += batch_result.get('failed_count', 0)
            total_records += batch_result.get('total_records', 0)
            failed_stocks.extend(batch_result.get('failed_stocks', []))
            success_stocks.extend(batch_result.get('success_stocks', []))
            
            # 批次间延迟，避免过载
            if i + batch_size < total_stocks:
                await asyncio.sleep(1)
        
        # 汇总结果
        summary = {
            "market": market,
            "total_stocks": total_stocks,
            "success_count": success_count,
            "failed_count": failed_count,
            "total_records": total_records,
            "success_rate": round(success_count / total_stocks * 100, 2) if total_stocks > 0 else 0,
            "batch_size": batch_size,
            "total_batches": len(batch_results),
            "failed_stocks": failed_stocks[:10],  # 只返回前10个失败的股票
            "batch_details": batch_results
        }
        
        message = f"增量更新完成：处理{total_stocks}只股票，成功{success_count}只，失败{failed_count}只，共更新{total_records}条记录"
        logger.info(message)
        
        return ApiResponse(
            success=True,
            message=message,
            data=summary
        )
        
    except Exception as e:
        logger.error(f"增量补全A股历史数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily/statistics", response_model=ApiResponse, summary="获取数据库日线数据统计信息")
async def get_daily_data_statistics(
    service: DataService = Depends(get_data_service)
):
    """获取数据库中日线数据的统计信息
    
    返回：
    - 总股票数量
    - 总记录数量
    - 数据日期范围
    - 各股票最新数据日期
    - 需要更新的股票列表
    """
    try:
        # 获取统计信息
        stats_sql = """
        SELECT 
            COUNT(DISTINCT stock_code) as total_stocks,
            COUNT(*) as total_records,
            MIN(trade_date) as earliest_date,
            MAX(trade_date) as latest_date
        FROM daily_stock_data
        """
        
        stats_result = service.duckdb.fetchone(stats_sql)
        
        if not stats_result or stats_result[0] == 0:
            return ApiResponse(
                success=True,
                message="数据库中暂无日线数据",
                data={
                    "total_stocks": 0,
                    "total_records": 0,
                    "earliest_date": None,
                    "latest_date": None,
                    "stocks_need_update": [],
                    "latest_data_by_stock": []
                }
            )
        
        total_stocks, total_records, earliest_date, latest_date = stats_result
        
        # 获取各股票最新数据日期
        latest_by_stock_sql = """
        SELECT 
            stock_code,
            MAX(trade_date) as latest_date,
            COUNT(*) as record_count
        FROM daily_stock_data 
        GROUP BY stock_code 
        ORDER BY latest_date DESC
        LIMIT 20
        """
        
        latest_by_stock = service.duckdb.fetchall(latest_by_stock_sql)
        
        # 查找需要更新的股票（最新数据超过3天的）
        today = datetime.now().strftime('%Y-%m-%d')
        outdated_sql = """
        SELECT 
            stock_code,
            MAX(trade_date) as latest_date,
            DATEDIFF('day', MAX(trade_date), CURRENT_DATE) as days_behind
        FROM daily_stock_data 
        GROUP BY stock_code 
        HAVING DATEDIFF('day', MAX(trade_date), CURRENT_DATE) > 3
        ORDER BY days_behind DESC
        LIMIT 50
        """
        
        outdated_stocks = service.duckdb.fetchall(outdated_sql)
        
        # 格式化结果
        latest_data_by_stock = [
            {
                "stock_code": row[0],
                "latest_date": str(row[1]),
                "record_count": row[2]
            }
            for row in latest_by_stock
        ]
        
        stocks_need_update = [
            {
                "stock_code": row[0],
                "latest_date": str(row[1]),
                "days_behind": row[2]
            }
            for row in outdated_stocks
        ]
        
        statistics = {
            "total_stocks": total_stocks,
            "total_records": total_records,
            "earliest_date": str(earliest_date) if earliest_date else None,
            "latest_date": str(latest_date) if latest_date else None,
            "data_span_days": (datetime.strptime(str(latest_date), '%Y-%m-%d') - 
                              datetime.strptime(str(earliest_date), '%Y-%m-%d')).days if earliest_date and latest_date else 0,
            "stocks_need_update_count": len(stocks_need_update),
            "stocks_need_update": stocks_need_update,
            "latest_data_by_stock": latest_data_by_stock,
            "query_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return ApiResponse(
            success=True,
            message=f"数据库统计信息：{total_stocks}只股票，{total_records}条记录",
            data=statistics
        )
        
    except Exception as e:
        logger.error(f"获取数据库统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily/query", response_model=ApiResponse, summary="查询数据库中的日线数据")
async def query_daily_data_from_db(
    stock_code: str = Query(..., description="股票代码"),
    start_date: str = Query(..., description="开始日期，格式YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期，格式YYYY-MM-DD"),
    service: DataService = Depends(get_data_service)
):
    """从数据库查询已存储的日线数据
    
    直接从DuckDB数据库查询数据，不会触发新的数据获取
    """
    try:
        # 验证日期格式
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，应为YYYY-MM-DD")
        
        if start_dt > end_dt:
            raise HTTPException(status_code=400, detail="开始日期不能大于结束日期")
        
        if (end_dt - start_dt).days > 1095:  # 3年
            raise HTTPException(status_code=400, detail="查询日期范围不能超过3年")
        
        # 从数据库查询数据
        df = service._get_data_from_db(stock_code, start_date, end_date)
        
        if df.empty:
            return ApiResponse(
                success=True,
                message=f"数据库中未找到{stock_code}在{start_date}至{end_date}期间的数据",
                data=[]
            )
        
        # 转换为字典列表
        data = df.to_dict('records')
        
        # 格式化数据
        for record in data:
            if 'trade_date' in record:
                record['trade_date'] = str(record['trade_date'])
            
            # 格式化数值字段
            for field in ['open_price', 'high_price', 'low_price', 'close_price', 'amount', 'turnover_rate', 'pe_ratio', 'pb_ratio']:
                if field in record and record[field] is not None:
                    record[field] = round(float(record[field]), 3)
        
        return ApiResponse(
            success=True,
            message=f"从数据库查询到{stock_code}的{len(data)}条日线数据",
            data={
                "stock_code": stock_code,
                "date_range": f"{start_date} 至 {end_date}",
                "total_records": len(data),
                "data": data
            }
        )
        
    except Exception as e:
        logger.error(f"查询{stock_code}数据库数据失败: {e}")
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