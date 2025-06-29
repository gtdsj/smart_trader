# -*- coding: utf-8 -*-
"""
数据业务API
提供股票数据获取和管理功能
"""
import traceback
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from config import get_settings
from services.data_service import DataService
from services.xtquant_service import XtQuantService

# 创建数据业务路由器
router = APIRouter(prefix="/data", tags=["数据业务"])

# 获取配置和服务
settings = get_settings()
data_service = DataService()
xtquant_service = XtQuantService()

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
class StockListRequest(BaseModel):
    market: Optional[str] = "all"  # SH, SZ, all
    stock_type: Optional[str] = "stock"  # stock, index, etf
    status: Optional[str] = "active"  # active, suspended, delisted
    limit: Optional[int] = 1000

class HistoryDataRequest(BaseModel):
    stock_codes: List[str]
    start_date: str
    end_date: str
    period: Optional[str] = "1d"  # 1m, 5m, 15m, 30m, 1h, 1d
    adjust: Optional[str] = "qfq"  # qfq, hfq, none

class RealtimeDataRequest(BaseModel):
    stock_codes: List[str]
    fields: Optional[List[str]] = ["last_price", "volume", "amount", "bid1", "ask1"]

@router.get("/", summary="数据概览", description="获取数据服务概览信息")
async def get_data_overview():
    """获取数据概览"""
    try:
        # 检查XtQuant连接状态
        xtquant_connected = xtquant_service.is_connected
        
        # 检查市场状态
        is_trading_time = data_service._is_trading_time()
        
        overview = {
            "data_source": {
                "provider": "XtQuant",
                "status": "connected" if xtquant_connected else "disconnected",
                "last_update": datetime.now().isoformat()
            },
            "market_status": {
                "is_trading_time": is_trading_time,
                "trading_day": datetime.now().strftime("%Y-%m-%d"),
                "current_time": datetime.now().strftime("%H:%M:%S")
            },
            "service_status": {
                "data_service": "running",
                "xtquant_service": "connected" if xtquant_connected else "disconnected",
                "cache_status": "active"
            }
        }
        
        return ApiResponse(
            message="获取数据概览成功",
            data=overview
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{str(e)}, {traceback.format_exc()}")

@router.get("/stocks", summary="股票列表", description="获取股票列表")
async def get_stock_list(
    market: str = Query("all", description="市场代码：SH, SZ, all"),
    stock_type: str = Query("stock", description="股票类型：stock, index, etf"),
    status: str = Query("active", description="状态：active, suspended, delisted"),
    limit: int = Query(1000, description="返回数量限制")
):
    """获取股票列表"""
    try:
        # 使用DataService获取股票列表
        stock_list = await data_service.get_stock_list(market)
        
        if not stock_list:
            stocks = []
        else:
            # 转换为API响应格式
            stocks = []
            for stock in stock_list:
                stock_info = {
                    "stock_code": stock.get("code", ""),
                    "stock_name": stock.get("name", ""),
                    "market": stock.get("market", ""),
                    "stock_type": stock_type,
                    "status": status
                }
                stocks.append(stock_info)
        
        # 根据参数过滤
        if market != "all":
            stocks = [s for s in stocks if s["market"] == market.upper()]
        if stock_type != "all":
            stocks = [s for s in stocks if s["stock_type"] == stock_type]
        if status != "all":
            stocks = [s for s in stocks if s["status"] == status]
        
        # 限制返回数量
        stocks = stocks[:limit]
        
        result = {
            "stocks": stocks,
            "total": len(stocks),
            "filters": {
                "market": market,
                "stock_type": stock_type,
                "status": status,
                "limit": limit
            }
        }
        
        return ApiResponse(
            message="获取股票列表成功",
            data=result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/history", summary="历史数据", description="获取股票历史数据")
async def get_history_data(request: HistoryDataRequest):
    """获取历史数据"""
    try:
        # 使用DataService获取历史数据
        history_data = {}
        
        for stock_code in request.stock_codes:
            # 获取历史数据
            data = await data_service.get_historical_data(
                stock_code=stock_code,
                start_date=request.start_date,
                end_date=request.end_date,
                period=request.period
            )
            
            if data:
                # 转换为API响应格式
                data_points = []
                for item in data:
                    data_point = {
                        "date": item.get("date", ""),
                        "open": item.get("open", 0.0),
                        "high": item.get("high", 0.0),
                        "low": item.get("low", 0.0),
                        "close": item.get("close", 0.0),
                        "volume": item.get("volume", 0),
                        "amount": item.get("amount", 0.0)
                    }
                    data_points.append(data_point)
                
                history_data[stock_code] = {
                    "stock_code": stock_code,
                    "period": request.period,
                    "adjust": request.adjust,
                    "start_date": request.start_date,
                    "end_date": request.end_date,
                    "data": data_points,
                    "count": len(data_points)
                }
            else:
                # 如果没有数据，返回空数据
                history_data[stock_code] = {
                    "stock_code": stock_code,
                    "period": request.period,
                    "adjust": request.adjust,
                    "start_date": request.start_date,
                    "end_date": request.end_date,
                    "data": [],
                    "count": 0
                }
        
        result = {
            "request_info": {
                "stock_codes": request.stock_codes,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "period": request.period,
                "adjust": request.adjust
            },
            "data": history_data,
            "total_stocks": len(request.stock_codes),
            "total_records": sum(len(data["data"]) for data in history_data.values())
        }
        
        return ApiResponse(
            message="获取历史数据成功",
            data=result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/realtime", summary="实时数据", description="获取股票实时数据")
async def get_realtime_data(request: RealtimeDataRequest):
    """获取实时数据"""
    try:
        # 使用DataService获取实时数据
        realtime_data = {}
        
        for stock_code in request.stock_codes:
            # 获取实时数据
            data = await data_service.get_realtime_data(request.stock_codes)
            
            if data and stock_code in data:
                stock_data = data[stock_code]
                # 转换为API响应格式
                formatted_data = {
                    "stock_code": stock_code,
                    "last_price": stock_data.get("last_price", 0.0),
                    "open": stock_data.get("open", 0.0),
                    "high": stock_data.get("high", 0.0),
                    "low": stock_data.get("low", 0.0),
                    "pre_close": stock_data.get("pre_close", 0.0),
                    "change": stock_data.get("change", 0.0),
                    "change_ratio": stock_data.get("change_ratio", 0.0),
                    "volume": stock_data.get("volume", 0),
                    "amount": stock_data.get("amount", 0.0),
                    "bid1": stock_data.get("bid1", 0.0),
                    "ask1": stock_data.get("ask1", 0.0),
                    "timestamp": datetime.now().isoformat()
                }
                
                # 根据请求字段过滤数据
                if request.fields:
                    filtered_data = {"stock_code": stock_code}
                    for field in request.fields:
                        if field in formatted_data:
                            filtered_data[field] = formatted_data[field]
                    realtime_data[stock_code] = filtered_data
                else:
                    realtime_data[stock_code] = formatted_data
            else:
                # 如果没有数据，返回基本信息
                realtime_data[stock_code] = {
                    "stock_code": stock_code,
                    "error": "数据获取失败"
                }
        
        result = {
            "request_info": {
                "stock_codes": request.stock_codes,
                "fields": request.fields
            },
            "data": realtime_data,
            "total_stocks": len(request.stock_codes),
            "update_time": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="获取实时数据成功",
            data=result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market-status", summary="市场状态", description="获取市场开盘状态")
def get_market_status():
    """获取市场状态"""
    try:
        # 这里可以根据时间或从数据源获取实际市场状态
        current_time = datetime.now()
        
        market_status = {
            "trading_day": current_time.strftime("%Y-%m-%d"),
            "current_time": current_time.isoformat(),
            "markets": {
                "SH": {
                    "status": "closed",  # open, closed, auction, break
                    "session": "after_hours",  # pre_market, morning, break, afternoon, after_hours
                    "next_open": "2024-01-02T09:30:00",
                    "next_close": "2024-01-02T15:00:00"
                },
                "SZ": {
                    "status": "closed",
                    "session": "after_hours",
                    "next_open": "2024-01-02T09:30:00",
                    "next_close": "2024-01-02T15:00:00"
                }
            },
            "trading_calendar": {
                "is_trading_day": False,  # 可以根据交易日历判断
                "next_trading_day": "2024-01-02",
                "prev_trading_day": "2023-12-29"
            }
        }
        
        return ApiResponse(
            message="获取市场状态成功",
            data=market_status
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stock/{stock_code}", summary="股票详情", description="获取指定股票详细信息")
def get_stock_detail(stock_code: str):
    """获取股票详情"""
    try:
        # 这里可以从数据库或XtQuant获取股票详细信息
        stock_detail = {
            "basic_info": {
                "stock_code": stock_code,
                "stock_name": "浦发银行",
                "market": "SH",
                "stock_type": "stock",
                "industry": "银行",
                "sector": "金融",
                "list_date": "1999-11-10",
                "status": "active",
                "total_shares": 29376543210,
                "float_shares": 29376543210,
                "market_cap": 3087654321.0,
                "float_market_cap": 3087654321.0
            },
            "price_info": {
                "last_price": 10.52,
                "open": 10.50,
                "high": 10.68,
                "low": 10.42,
                "pre_close": 10.48,
                "change": 0.04,
                "change_ratio": 0.0038,
                "volume": 12345678,
                "amount": 129876543.21,
                "turnover_rate": 0.0234
            },
            "financial_info": {
                "pe_ratio": 5.23,
                "pb_ratio": 0.65,
                "ps_ratio": 1.23,
                "roe": 0.125,
                "roa": 0.089,
                "debt_ratio": 0.876,
                "eps": 2.01,
                "bps": 16.18,
                "dividend_yield": 0.045
            },
            "technical_info": {
                "ma5": 10.45,
                "ma10": 10.38,
                "ma20": 10.32,
                "ma60": 10.28,
                "volume_ma5": 15678901,
                "volume_ma10": 14567890,
                "rsi": 52.34,
                "macd": 0.012,
                "kdj_k": 45.67,
                "kdj_d": 43.21
            },
            "last_update": datetime.now().isoformat()
        }
        
        return ApiResponse(
            message="获取股票详情成功",
            data=stock_detail
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search", summary="股票搜索", description="搜索股票")
def search_stocks(
    keyword: str = Query(..., description="搜索关键词（股票代码或名称）"),
    limit: int = Query(20, description="返回数量限制")
):
    """搜索股票"""
    try:
        # 这里可以实现实际的股票搜索逻辑
        # 模拟搜索结果
        search_results = [
            {
                "stock_code": "600000.SH",
                "stock_name": "浦发银行",
                "market": "SH",
                "industry": "银行",
                "last_price": 10.52,
                "change_ratio": 0.0038,
                "match_type": "name"  # code, name, pinyin
            }
        ]
        
        result = {
            "keyword": keyword,
            "results": search_results[:limit],
            "total": len(search_results),
            "limit": limit
        }
        
        return ApiResponse(
            message="股票搜索完成",
            data=result
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))