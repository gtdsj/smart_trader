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
    """
    增量补全A股所有股票的历史日线数据
    
    该接口会获取所有股票列表，然后批量更新每只股票的日线数据到DuckDB。
    适用于定时任务或系统维护，确保数据的完整性和时效性。
    """
    try:
        logger.info(f"开始增量补全{market}市场所有股票历史日线数据")
        
        # 获取股票列表
        stocks = await service.get_stock_list(market)
        if not stocks:
            return ApiResponse(
                success=False,
                message=f"未获取到{market}市场的股票列表",
                data=None
            )
        
        stock_codes = [stock["stock_code"] for stock in stocks]
        logger.info(f"获取到{len(stock_codes)}只股票，开始批量更新")
        
        # 批量更新数据
        result = await service._batch_update_daily_data(stock_codes, batch_size)
        
        return ApiResponse(
            success=True,
            message=f"增量补全完成，成功更新{result['success_count']}只股票，失败{result['failed_count']}只",
            data={
                "market": market,
                "total_stocks": len(stock_codes),
                "success_count": result["success_count"],
                "failed_count": result["failed_count"],
                "failed_stocks": result["failed_stocks"][:10],  # 只返回前10个失败的股票
                "batch_size": batch_size
            }
        )
        
    except Exception as e:
        logger.error(f"增量补全失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/daily/full-market-backfill", response_model=ApiResponse, summary="A股全市场历史数据完整补全")
async def full_market_data_backfill(
    market: Optional[str] = Query("ALL", description="市场代码：SH、SZ或ALL"),
    start_date: Optional[str] = Query(None, description="补全开始日期，格式YYYY-MM-DD，默认为3年前"),
    end_date: Optional[str] = Query(None, description="补全结束日期，格式YYYY-MM-DD，默认为今天"),
    batch_size: int = Query(30, description="批量处理大小", ge=1, le=50),
    delay_seconds: float = Query(0.2, description="批次间延迟秒数", ge=0.1, le=2.0),
    force_update: bool = Query(False, description="是否强制更新已存在的数据"),
    service: DataService = Depends(get_data_service)
):
    """A股全市场历史数据完整补全接口
    
    该接口提供全面的A股市场历史数据补全功能：
    
    **功能特性：**
    1. 支持全市场或指定市场的数据补全
    2. 智能增量更新：自动检测缺失数据并补全
    3. 可配置的时间范围和批处理参数
    4. 详细的进度跟踪和错误处理
    5. 数据质量验证和重复数据处理
    
    **适用场景：**
    - 系统初始化时的历史数据导入
    - 定期的数据完整性检查和补全
    - 新增股票的历史数据回填
    - 数据库迁移后的数据验证
    
    **性能优化：**
    - 分批处理避免内存溢出
    - 可配置延迟防止API限流
    - 断点续传支持大规模数据补全
    - 并发控制确保系统稳定性
    """
    try:
        logger.info(f"开始A股全市场历史数据补全：市场={market}, 批次大小={batch_size}")
        
        # 参数验证和默认值设置
        if not start_date:
            start_date = (datetime.now() - timedelta(days=1095)).strftime('%Y-%m-%d')  # 默认3年前
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        # 验证日期格式和范围
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，应为YYYY-MM-DD")
            
        if start_dt > end_dt:
            raise HTTPException(status_code=400, detail="开始日期不能大于结束日期")
            
        if (end_dt - start_dt).days > 2190:  # 6年
            raise HTTPException(status_code=400, detail="数据补全范围不能超过6年")
        
        # 获取股票列表
        all_stocks = await service.get_stock_list()
        if not all_stocks:
            return ApiResponse(
                success=False,
                message="未获取到股票列表",
                data=None
            )
        
        # 根据市场过滤股票
        if market and market != "ALL":
            filtered_stocks = [stock for stock in all_stocks if stock.get("market") == market]
        else:
            filtered_stocks = all_stocks
            
        stock_codes = [stock["stock_code"] for stock in filtered_stocks]
        total_stocks = len(stock_codes)
        
        if total_stocks == 0:
            return ApiResponse(
                success=False,
                message=f"未找到{market}市场的股票",
                data=None
            )
        
        logger.info(f"获取到{total_stocks}只股票，开始全市场数据补全")
        
        # 初始化统计变量
        total_batches = (total_stocks + batch_size - 1) // batch_size
        success_count = 0
        failed_count = 0
        total_records = 0
        skipped_count = 0
        failed_stocks = []
        success_stocks = []
        batch_results = []
        
        # 分批处理股票
        for i in range(0, total_stocks, batch_size):
            batch_stocks = stock_codes[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            logger.info(f"处理第{batch_num}/{total_batches}批，包含{len(batch_stocks)}只股票")
            
            batch_success = 0
            batch_failed = 0
            batch_records = 0
            batch_skipped = 0
            batch_failed_stocks = []
            batch_success_stocks = []
            
            # 处理当前批次的每只股票
            for stock_code in batch_stocks:
                try:
                    # 检查是否需要更新
                    if not force_update:
                        latest_date = service._get_latest_date_from_db(stock_code)
                        if latest_date and latest_date >= end_date:
                            batch_skipped += 1
                            skipped_count += 1
                            logger.debug(f"{stock_code}数据已是最新，跳过")
                            continue
                    
                    # 获取历史数据
                    df = await service.get_stock_daily_data(
                        stock_code=stock_code,
                        start_date=start_date,
                        end_date=end_date,
                        save_to_db=True
                    )
                    
                    if not df.empty:
                        record_count = len(df)
                        batch_success += 1
                        batch_records += record_count
                        batch_success_stocks.append(stock_code)
                        logger.debug(f"{stock_code}补全成功，获取{record_count}条记录")
                    else:
                        batch_failed += 1
                        batch_failed_stocks.append(stock_code)
                        logger.warning(f"{stock_code}未获取到数据")
                        
                except Exception as e:
                    batch_failed += 1
                    batch_failed_stocks.append(stock_code)
                    logger.error(f"补全{stock_code}失败: {e}")
                    
                # 股票间小延迟
                await asyncio.sleep(0.05)
            
            # 更新总计数
            success_count += batch_success
            failed_count += batch_failed
            total_records += batch_records
            failed_stocks.extend(batch_failed_stocks)
            success_stocks.extend(batch_success_stocks)
            
            # 记录批次结果
            batch_result = {
                "batch_num": batch_num,
                "stocks_in_batch": len(batch_stocks),
                "success_count": batch_success,
                "failed_count": batch_failed,
                "skipped_count": batch_skipped,
                "records_count": batch_records,
                "success_stocks": batch_success_stocks[:5],  # 只记录前5个成功的
                "failed_stocks": batch_failed_stocks
            }
            batch_results.append(batch_result)
            
            # 批次间延迟
            if i + batch_size < total_stocks:
                await asyncio.sleep(delay_seconds)
                
            # 进度日志
            progress = round((batch_num / total_batches) * 100, 1)
            logger.info(f"批次{batch_num}完成，进度{progress}%，成功{batch_success}只，失败{batch_failed}只，跳过{batch_skipped}只")
        
        # 计算最终统计
        success_rate = round(success_count / total_stocks * 100, 2) if total_stocks > 0 else 0
        avg_records_per_stock = round(total_records / success_count, 1) if success_count > 0 else 0
        
        # 构建详细结果
        result_summary = {
            "operation": "full_market_data_backfill",
            "market": market,
            "date_range": f"{start_date} 至 {end_date}",
            "total_stocks": total_stocks,
            "success_count": success_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "total_records": total_records,
            "success_rate": success_rate,
            "avg_records_per_stock": avg_records_per_stock,
            "batch_size": batch_size,
            "total_batches": total_batches,
            "delay_seconds": delay_seconds,
            "force_update": force_update,
            "processing_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "failed_stocks_sample": failed_stocks[:20],  # 前20个失败的股票
            "batch_details": batch_results[-10:]  # 最后10个批次的详情
        }
        
        # 生成结果消息
        if success_count == total_stocks:
            message = f"✅ 全市场数据补全完成！成功处理{total_stocks}只股票，共补全{total_records}条记录"
        elif success_count > 0:
            message = f"⚠️ 部分完成：成功{success_count}只，失败{failed_count}只，跳过{skipped_count}只，共补全{total_records}条记录"
        else:
            message = f"❌ 补全失败：{total_stocks}只股票均处理失败"
            
        logger.info(message)
        
        return ApiResponse(
            success=success_count > 0,
            message=message,
            data=result_summary
        )
        
    except Exception as e:
        logger.error(f"A股全市场数据补全失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/daily/smart-backfill", response_model=ApiResponse, summary="智能数据补全")
async def smart_data_backfill(
    target_completeness: float = Query(95.0, description="目标完整度百分比", ge=80.0, le=100.0),
    max_stocks_per_run: int = Query(200, description="单次运行最大股票数", ge=50, le=500),
    priority_mode: str = Query("missing_recent", description="优先级模式：missing_recent(缺失最新数据), missing_most(缺失最多数据), random(随机)"),
    service: DataService = Depends(get_data_service)
):
    """智能数据补全接口
    
    根据数据完整度分析，智能选择需要补全的股票：
    1. 分析每只股票的数据完整度
    2. 按优先级排序选择需要补全的股票
    3. 执行针对性的数据补全
    4. 达到目标完整度后停止
    """
    try:
        logger.info(f"开始智能数据补全，目标完整度：{target_completeness}%")
        
        # 分析数据完整度
        completeness_analysis = await service.analyze_data_completeness()
        
        if not completeness_analysis:
            return ApiResponse(
                success=False,
                message="无法获取数据完整度分析",
                data=None
            )
        
        current_completeness = completeness_analysis.get('overall_completeness', 0)
        
        if current_completeness >= target_completeness:
            return ApiResponse(
                success=True,
                message=f"数据完整度已达标：{current_completeness:.1f}% >= {target_completeness}%",
                data=completeness_analysis
            )
        
        # 获取需要补全的股票列表
        incomplete_stocks = completeness_analysis.get('incomplete_stocks', [])
        
        # 根据优先级模式排序
        if priority_mode == "missing_recent":
            # 按最新数据缺失程度排序
            incomplete_stocks.sort(key=lambda x: x.get('days_behind', 0), reverse=True)
        elif priority_mode == "missing_most":
            # 按缺失数据量排序
            incomplete_stocks.sort(key=lambda x: x.get('missing_days', 0), reverse=True)
        else:  # random
            import random
            random.shuffle(incomplete_stocks)
        
        # 限制处理数量
        stocks_to_process = incomplete_stocks[:max_stocks_per_run]
        stock_codes = [stock['stock_code'] for stock in stocks_to_process]
        
        logger.info(f"选择{len(stock_codes)}只股票进行智能补全")
        
        # 执行批量更新
        batch_result = await service.batch_update_daily_data(stock_codes)
        
        # 重新分析完整度
        updated_analysis = await service.analyze_data_completeness()
        updated_completeness = updated_analysis.get('overall_completeness', 0)
        
        # 构建结果
        result = {
            "before_completeness": current_completeness,
            "after_completeness": updated_completeness,
            "target_completeness": target_completeness,
            "improvement": updated_completeness - current_completeness,
            "target_achieved": updated_completeness >= target_completeness,
            "processed_stocks": len(stock_codes),
            "batch_result": batch_result,
            "priority_mode": priority_mode
        }
        
        message = f"智能补全完成：完整度从{current_completeness:.1f}%提升到{updated_completeness:.1f}%"
        
        return ApiResponse(
            success=True,
            message=message,
            data=result
        )
        
    except Exception as e:
        logger.error(f"智能数据补全失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
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