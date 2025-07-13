# -*- coding: utf-8 -*-
"""
选股筛选API路由
提供股票筛选相关的API接口
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from loguru import logger

from services.stock_screener import StockScreener
from services.data_service import DataService
from api.strategy_manager_routes import ApiResponse


router = APIRouter(prefix="/api/screener", tags=["股票筛选"])


# 依赖注入
def get_stock_screener() -> StockScreener:
    """获取选股筛选器实例"""
    data_service = DataService.get_instance()
    return StockScreener(data_service)


# 请求模型
class ScreenByStrategyRequest(BaseModel):
    """策略筛选请求模型"""
    strategy_id: int = Field(..., description="策略ID")
    stock_list: Optional[List[str]] = Field(None, description="股票列表，为空则筛选全部股票")
    date: Optional[str] = Field(None, description="筛选日期，格式YYYY-MM-DD，为空则使用当前日期")


class ScreenByExpressionRequest(BaseModel):
    """表达式筛选请求模型"""
    expression: str = Field(..., description="筛选表达式")
    stock_list: Optional[List[str]] = Field(None, description="股票列表，为空则筛选全部股票")
    date: Optional[str] = Field(None, description="筛选日期，格式YYYY-MM-DD，为空则使用当前日期")


# 响应模型
class MatchedStock(BaseModel):
    """匹配的股票模型"""
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    price: float = Field(..., description="当前价格")
    reason: str = Field(..., description="匹配原因")
    indicators: Optional[Dict[str, Any]] = Field(None, description="相关指标值")


class ScreeningResult(BaseModel):
    """筛选结果模型"""
    success: bool = Field(..., description="筛选是否成功")
    message: str = Field(..., description="结果消息")
    matched_stocks: List[MatchedStock] = Field(..., description="匹配的股票列表")
    total_checked: int = Field(..., description="总检查股票数")
    execution_time: float = Field(..., description="执行时间（秒）")
    expression_description: Optional[str] = Field(None, description="表达式描述")


class ScreeningHistoryItem(BaseModel):
    """筛选历史项模型"""
    id: int = Field(..., description="执行ID")
    strategy_id: Optional[int] = Field(None, description="策略ID")
    execution_date: str = Field(..., description="执行日期")
    status: str = Field(..., description="执行状态")
    matched_count: int = Field(..., description="匹配股票数")
    total_checked: int = Field(..., description="总检查股票数")
    execution_time: float = Field(..., description="执行时间（秒）")
    error_message: Optional[str] = Field(None, description="错误消息")


class ScreeningResultDetail(BaseModel):
    """筛选结果详情模型"""
    execution_id: int = Field(..., description="执行ID")
    strategy_id: Optional[int] = Field(None, description="策略ID")
    execution_date: str = Field(..., description="执行日期")
    status: str = Field(..., description="执行状态")
    matched_stocks: List[MatchedStock] = Field(..., description="匹配的股票列表")
    total_checked: int = Field(..., description="总检查股票数")
    execution_time: float = Field(..., description="执行时间（秒）")
    error_message: Optional[str] = Field(None, description="错误消息")


# API路由
@router.post("/screen-by-strategy", response_model=ApiResponse[ScreeningResult], summary="根据策略筛选股票")
async def screen_stocks_by_strategy(
    request: ScreenByStrategyRequest,
    screener: StockScreener = Depends(get_stock_screener)
):
    """根据策略筛选股票"""
    try:
        result = await screener.screen_stocks_by_strategy(
            strategy_id=request.strategy_id,
            stock_list=request.stock_list,
            date=request.date
        )
        
        # 检查筛选结果是否成功
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        # 转换匹配的股票格式
        matched_stocks = []
        for stock in result["matched_stocks"]:
            matched_stocks.append(MatchedStock(
                symbol=stock["symbol"],
                name=stock.get("name", ""),
                price=stock.get("price", 0.0),
                reason=stock.get("reason", ""),
                indicators=stock.get("indicators", {})
            ))
        
        screening_result = ScreeningResult(
            success=result["success"],
            message=result["message"],
            matched_stocks=matched_stocks,
            total_checked=result["total_checked"],
            execution_time=result["execution_time"]
        )
        
        return {
            "success": True,
            "message": "策略筛选完成",
            "data": screening_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"策略筛选API错误: {e}")
        raise HTTPException(status_code=500, detail=f"策略筛选失败: {str(e)}")


@router.post("/screen-by-expression", response_model=ApiResponse[ScreeningResult], summary="根据表达式筛选股票")
async def screen_stocks_by_expression(
    request: ScreenByExpressionRequest,
    screener: StockScreener = Depends(get_stock_screener)
):
    """根据表达式筛选股票"""
    try:
        result = await screener.screen_stocks_by_expression(
            expression=request.expression,
            stock_list=request.stock_list,
            date=request.date
        )
        
        # 转换匹配的股票格式
        matched_stocks = []
        for stock in result["matched_stocks"]:
            matched_stocks.append(MatchedStock(
                symbol=stock["symbol"],
                name=stock.get("name", ""),
                price=stock.get("price", 0.0),
                reason=stock.get("reason", ""),
                indicators=stock.get("indicators", {})
            ))
        
        screening_result = ScreeningResult(
            success=result["success"],
            message=result["message"],
            matched_stocks=matched_stocks,
            total_checked=result["total_checked"],
            execution_time=result["execution_time"],
            expression_description=result.get("expression_description")
        )
        
        return {
            "success": True,
            "message": "表达式筛选完成",
            "data": screening_result
        }
        
    except Exception as e:
        logger.error(f"表达式筛选API错误: {e}")
        raise HTTPException(status_code=500, detail=f"表达式筛选失败: {str(e)}")


@router.get("/history", response_model=ApiResponse[List[ScreeningHistoryItem]], summary="获取筛选历史")
async def get_screening_history(
    strategy_id: Optional[int] = Query(None, description="策略ID，为空则获取所有策略的历史"),
    limit: int = Query(100, description="返回记录数限制"),
    screener: StockScreener = Depends(get_stock_screener)
):
    """获取筛选历史"""
    try:
        result = await screener.get_screening_history(strategy_id=strategy_id, limit=limit)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])
        
        # 转换历史记录格式
        history_items = []
        for item in result["data"]:
            history_items.append(ScreeningHistoryItem(
                id=item["id"],
                strategy_id=item.get("strategy_id"),
                execution_date=item["execution_date"],
                status=item["status"],
                matched_count=item["matched_count"],
                total_checked=item["total_checked"],
                execution_time=item["execution_time"],
                error_message=item.get("error_message")
            ))
        
        return {
            "success": True,
            "message": "获取筛选历史成功",
            "data": history_items
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取筛选历史API错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取筛选历史失败: {str(e)}")


@router.get("/result/{execution_id}", response_model=ApiResponse[ScreeningResultDetail], summary="获取筛选结果详情")
async def get_screening_result(
    execution_id: int,
    screener: StockScreener = Depends(get_stock_screener)
):
    """获取筛选结果详情"""
    try:
        result = await screener.get_screening_result(execution_id)
        
        if not result["success"]:
            if "不存在" in result["message"]:
                raise HTTPException(status_code=404, detail=result["message"])
            else:
                raise HTTPException(status_code=500, detail=result["message"])
        
        data = result["data"]
        
        # 转换匹配的股票格式
        matched_stocks = []
        for stock in data["matched_stocks"]:
            matched_stocks.append(MatchedStock(
                symbol=stock["symbol"],
                name=stock.get("name", ""),
                price=stock.get("price", 0.0),
                reason=stock.get("reason", ""),
                indicators=stock.get("indicators", {})
            ))
        
        result_detail = ScreeningResultDetail(
            execution_id=data["execution_id"],
            strategy_id=data.get("strategy_id"),
            execution_date=data["execution_date"],
            status=data["status"],
            matched_stocks=matched_stocks,
            total_checked=data["total_checked"],
            execution_time=data["execution_time"],
            error_message=data.get("error_message")
        )
        
        return {
            "success": True,
            "message": "获取筛选结果成功",
            "data": result_detail
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取筛选结果API错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取筛选结果失败: {str(e)}")


@router.get("/stock-list", response_model=ApiResponse[List[str]], summary="获取可筛选的股票列表")
async def get_available_stock_list(
    screener: StockScreener = Depends(get_stock_screener)
):
    """获取可筛选的股票列表"""
    try:
        # 获取股票列表
        stock_list = await screener._get_all_stock_list()
        
        return {
            "success": True,
            "message": "获取股票列表成功",
            "data": stock_list
        }
        
    except Exception as e:
        logger.error(f"获取股票列表API错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取股票列表失败: {str(e)}")


@router.get("/statistics", response_model=ApiResponse[Dict[str, Any]], summary="获取筛选统计信息")
async def get_screening_statistics(
    days: int = Query(30, description="统计天数"),
    screener: StockScreener = Depends(get_stock_screener)
):
    """获取筛选统计信息"""
    try:
        # 获取最近的筛选历史
        result = await screener.get_screening_history(limit=1000)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])
        
        history = result["data"]
        
        # 计算统计信息
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_history = [
            item for item in history 
            if datetime.strptime(item["execution_date"], '%Y-%m-%d %H:%M:%S') >= cutoff_date
        ]
        
        total_executions = len(recent_history)
        successful_executions = len([item for item in recent_history if item["status"] == "completed"])
        total_stocks_checked = sum(item["total_checked"] for item in recent_history)
        total_stocks_matched = sum(item["matched_count"] for item in recent_history)
        avg_execution_time = sum(item["execution_time"] for item in recent_history) / max(total_executions, 1)
        
        # 按策略统计
        strategy_stats = {}
        for item in recent_history:
            strategy_id = item.get("strategy_id")
            if strategy_id:
                if strategy_id not in strategy_stats:
                    strategy_stats[strategy_id] = {
                        "executions": 0,
                        "matched_stocks": 0,
                        "total_checked": 0
                    }
                strategy_stats[strategy_id]["executions"] += 1
                strategy_stats[strategy_id]["matched_stocks"] += item["matched_count"]
                strategy_stats[strategy_id]["total_checked"] += item["total_checked"]
        
        statistics = {
            "period_days": days,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": successful_executions / max(total_executions, 1),
            "total_stocks_checked": total_stocks_checked,
            "total_stocks_matched": total_stocks_matched,
            "match_rate": total_stocks_matched / max(total_stocks_checked, 1),
            "avg_execution_time": avg_execution_time,
            "strategy_statistics": strategy_stats
        }
        
        return {
            "success": True,
            "message": "获取筛选统计成功",
            "data": statistics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取筛选统计API错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取筛选统计失败: {str(e)}")