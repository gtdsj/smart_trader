# -*- coding: utf-8 -*-
"""
选股策略执行器
用于执行选股策略，对全网股票进行筛选
"""

import traceback
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from loguru import logger
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.database import get_db, Strategy, StrategyCondition, StrategyExecution, StrategySignal
from services.data_service import DataService
from services.strategy_manager import StrategyManager
from services.strategy_expression_parser import StrategyExpressionParser
from services.indicator_manager import IndicatorManager
from services.operator_manager import OperatorManager


class StockScreener:
    """选股策略执行器"""
    
    def __init__(self, data_service: DataService = None):
        self.data_service = data_service or DataService()
        self.strategy_manager = StrategyManager()
        self.expression_parser = StrategyExpressionParser()
        self.indicator_manager = IndicatorManager()
        self.operator_manager = OperatorManager()
        
        # 设置数据服务
        self.strategy_manager.set_data_service(self.data_service)
        
        # 并发配置
        self.max_workers = 10  # 最大并发数
        self.batch_size = 50   # 批处理大小
    
    async def screen_stocks_by_strategy(self, strategy_id: int, stock_list: List[str] = None, 
                                      date: str = None) -> Dict[str, Any]:
        """根据策略筛选股票"""
        try:
            # 获取策略详情
            strategy_detail = await self.strategy_manager.get_strategy_detail(strategy_id)
            if not strategy_detail["success"]:
                return {
                    "success": False,
                    "message": f"获取策略失败: {strategy_detail['message']}",
                    "matched_stocks": [],
                    "total_checked": 0,
                    "execution_time": 0
                }
            
            strategy = strategy_detail["data"]
            
            # 验证策略类型
            if strategy["category"] != "stock_selection":
                return {
                    "success": False,
                    "message": "只支持选股策略",
                    "matched_stocks": [],
                    "total_checked": 0,
                    "execution_time": 0
                }
            
            start_time = datetime.now()
            
            # 获取股票列表
            if stock_list is None:
                stock_list = await self._get_all_stock_list()
            
            # 设置筛选日期
            screen_date = date or datetime.now().strftime('%Y-%m-%d')
            
            # 执行筛选
            matched_stocks = await self._execute_screening(
                strategy=strategy,
                stock_list=stock_list,
                screen_date=screen_date
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 保存筛选结果
            await self._save_screening_result(
                strategy_id=strategy_id,
                matched_stocks=matched_stocks,
                total_checked=len(stock_list),
                execution_time=execution_time,
                screen_date=screen_date
            )
            
            return {
                "success": True,
                "message": "股票筛选完成",
                "matched_stocks": matched_stocks,
                "total_checked": len(stock_list),
                "execution_time": execution_time
            }
            
        except Exception as e:
            logger.error(f"股票筛选失败: {e}, {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"股票筛选失败: {str(e)}",
                "matched_stocks": [],
                "total_checked": 0,
                "execution_time": 0
            }
    
    async def screen_stocks_by_expression(self, expression: str, stock_list: List[str] = None, 
                                        date: str = None) -> Dict[str, Any]:
        """根据表达式筛选股票"""
        try:
            start_time = datetime.now()
            
            # 解析表达式
            parse_result = await self.strategy_manager.parse_strategy_expression(expression)
            if not parse_result["success"]:
                return {
                    "success": False,
                    "message": f"表达式解析失败: {parse_result['message']}",
                    "matched_stocks": [],
                    "total_checked": 0,
                    "execution_time": 0
                }
            
            # 获取股票列表
            if stock_list is None:
                stock_list = await self._get_all_stock_list()
            
            # 设置筛选日期
            screen_date = date or datetime.now().strftime('%Y-%m-%d')
            
            # 执行筛选
            matched_stocks = await self._execute_expression_screening(
                expression=expression,
                stock_list=stock_list,
                screen_date=screen_date
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "message": "股票筛选完成",
                "matched_stocks": matched_stocks,
                "total_checked": len(stock_list),
                "execution_time": execution_time,
                "expression_description": parse_result["description"]
            }
            
        except Exception as e:
            logger.error(f"表达式筛选失败: {e}, {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"表达式筛选失败: {str(e)}",
                "matched_stocks": [],
                "total_checked": 0,
                "execution_time": 0
            }
    
    async def get_screening_history(self, strategy_id: int = None, limit: int = 100) -> Dict[str, Any]:
        """获取筛选历史"""
        try:
            db_gen = get_db()
            session = next(db_gen)
            try:
                query = session.query(StrategyExecution)
                
                if strategy_id:
                    query = query.filter(StrategyExecution.strategy_id == strategy_id)
                
                executions = query.order_by(StrategyExecution.created_at.desc()).limit(limit).all()
                
                history = []
                for execution in executions:
                    # 获取匹配的股票数量
                    matched_count = session.query(StrategySignal).filter(
                        StrategySignal.execution_id == execution.id,
                        StrategySignal.signal_type == "BUY"
                    ).count()
                    
                    history.append({
                        "id": execution.id,
                        "strategy_id": execution.strategy_id,
                        "execution_date": execution.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        "status": execution.status,
                        "matched_count": matched_count,
                        "total_checked": execution.total_stocks or 0,
                        "execution_time": execution.execution_time or 0,
                        "error_message": execution.error_message
                    })
                
                return {
                    "success": True,
                    "data": history,
                    "message": "获取筛选历史成功"
                }
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"获取筛选历史失败: {e}")
            return {
                "success": False,
                "data": [],
                "message": f"获取筛选历史失败: {str(e)}"
            }
    
    async def get_screening_result(self, execution_id: int) -> Dict[str, Any]:
        """获取筛选结果详情"""
        try:
            db_gen = get_db()
            session = next(db_gen)
            try:
                # 获取执行记录
                execution = session.query(StrategyExecution).filter(
                    StrategyExecution.id == execution_id
                ).first()
                
                if not execution:
                    return {
                        "success": False,
                        "data": None,
                        "message": "筛选记录不存在"
                    }
                
                # 获取匹配的股票信号
                signals = session.query(StrategySignal).filter(
                    StrategySignal.execution_id == execution_id,
                    StrategySignal.signal_type == "BUY"
                ).all()
                
                matched_stocks = []
                for signal in signals:
                    matched_stocks.append({
                        "symbol": signal.stock_code,
                        "signal_time": signal.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        "price": signal.trigger_price or 0.0,
                        "confidence": signal.confidence or 0.0,
                        "reason": signal.reason or ""
                    })
                
                return {
                    "success": True,
                    "data": {
                        "execution_id": execution.id,
                        "strategy_id": execution.strategy_id,
                        "execution_date": execution.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        "status": execution.status,
                        "matched_stocks": matched_stocks,
                        "total_checked": execution.total_stocks or 0,
                        "execution_time": execution.execution_time or 0,
                        "error_message": execution.error_message
                    },
                    "message": "获取筛选结果成功"
                }
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"获取筛选结果失败: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"获取筛选结果失败: {str(e)}"
            }
    
    async def _get_all_stock_list(self) -> List[str]:
        """获取全部股票列表"""
        try:
            # 这里应该从数据源获取所有股票代码
            # 暂时返回一些示例股票代码
            stock_list = [
                "000001.SZ", "000002.SZ", "000858.SZ", "000876.SZ", "002415.SZ",
                "600000.SH", "600036.SH", "600519.SH", "600887.SH", "601318.SH",
                "601398.SH", "601857.SH", "601988.SH", "603259.SH", "603993.SH"
            ]
            
            # TODO: 实际实现中应该调用数据服务获取完整的股票列表
            # stock_list = await self.data_service.get_all_stock_symbols()
            
            return stock_list
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []
    
    async def _execute_screening(self, strategy: Dict[str, Any], stock_list: List[str], 
                               screen_date: str) -> List[Dict[str, Any]]:
        """执行策略筛选"""
        matched_stocks = []
        
        # 分批处理股票
        batches = [stock_list[i:i + self.batch_size] for i in range(0, len(stock_list), self.batch_size)]
        
        for batch in batches:
            batch_results = await self._process_stock_batch_strategy(batch, strategy, screen_date)
            matched_stocks.extend(batch_results)
        
        return matched_stocks
    
    async def _execute_expression_screening(self, expression: str, stock_list: List[str], 
                                          screen_date: str) -> List[Dict[str, Any]]:
        """执行表达式筛选"""
        matched_stocks = []
        
        # 分批处理股票
        batches = [stock_list[i:i + self.batch_size] for i in range(0, len(stock_list), self.batch_size)]
        
        for batch in batches:
            batch_results = await self._process_stock_batch_expression(batch, expression, screen_date)
            matched_stocks.extend(batch_results)
        
        return matched_stocks
    
    async def _process_stock_batch_strategy(self, stock_batch: List[str], strategy: Dict[str, Any], 
                                          screen_date: str) -> List[Dict[str, Any]]:
        """处理股票批次（策略模式）"""
        matched_stocks = []
        
        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交任务
            future_to_symbol = {
                executor.submit(self._check_single_stock_strategy, symbol, strategy, screen_date): symbol
                for symbol in stock_batch
            }
            
            # 收集结果
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    if result["matched"]:
                        matched_stocks.append(result)
                except Exception as e:
                    logger.error(f"检查股票 {symbol} 失败: {e}")
        
        return matched_stocks
    
    async def _process_stock_batch_expression(self, stock_batch: List[str], expression: str, 
                                            screen_date: str) -> List[Dict[str, Any]]:
        """处理股票批次（表达式模式）"""
        matched_stocks = []
        
        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交任务
            future_to_symbol = {
                executor.submit(self._check_single_stock_expression, symbol, expression, screen_date): symbol
                for symbol in stock_batch
            }
            
            # 收集结果
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    if result["matched"]:
                        matched_stocks.append(result)
                except Exception as e:
                    logger.error(f"检查股票 {symbol} 失败: {e}")
        
        return matched_stocks
    
    def _check_single_stock_strategy(self, symbol: str, strategy: Dict[str, Any], 
                                   screen_date: str) -> Dict[str, Any]:
        """检查单个股票是否符合策略条件"""
        try:
            # 获取股票数据
            end_date = screen_date
            start_date = (datetime.strptime(screen_date, '%Y-%m-%d') - timedelta(days=365)).strftime('%Y-%m-%d')
            
            # 同步获取数据（在线程池中运行）
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                stock_data = loop.run_until_complete(
                    self.data_service.get_stock_data(symbol, start_date, end_date)
                )
            finally:
                loop.close()
            
            if stock_data.empty:
                return {"matched": False, "symbol": symbol, "reason": "无数据"}
            
            # 评估策略条件
            conditions = strategy.get("conditions", [])
            if not conditions:
                return {"matched": False, "symbol": symbol, "reason": "无策略条件"}
            
            # 计算指标
            indicators = self._calculate_indicators_for_conditions(stock_data, conditions)
            
            # 评估所有条件
            condition_results = []
            for condition in conditions:
                result = self._evaluate_condition(condition, stock_data, indicators)
                condition_results.append(result)
            
            # 根据逻辑操作符组合结果
            final_result = self._combine_condition_results(condition_results, conditions)
            
            if final_result:
                current_price = stock_data['close'].iloc[-1] if 'close' in stock_data.columns else 0
                return {
                    "matched": True,
                    "symbol": symbol,
                    "price": float(current_price),
                    "reason": "符合策略条件",
                    "indicators": {k: float(v) if isinstance(v, (int, float, np.number)) else str(v) 
                                 for k, v in indicators.items()}
                }
            else:
                return {"matched": False, "symbol": symbol, "reason": "不符合策略条件"}
            
        except Exception as e:
            logger.error(f"检查股票 {symbol} 策略失败: {e}")
            return {"matched": False, "symbol": symbol, "reason": f"检查失败: {str(e)}"}
    
    def _check_single_stock_expression(self, symbol: str, expression: str, 
                                     screen_date: str) -> Dict[str, Any]:
        """检查单个股票是否符合表达式条件"""
        try:
            # 获取股票数据
            end_date = screen_date
            start_date = (datetime.strptime(screen_date, '%Y-%m-%d') - timedelta(days=365)).strftime('%Y-%m-%d')
            
            # 同步获取数据（在线程池中运行）
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                stock_data = loop.run_until_complete(
                    self.data_service.get_stock_data(symbol, start_date, end_date)
                )
                
                # 评估表达式
                evaluation_result = loop.run_until_complete(
                    self.strategy_manager.evaluate_strategy_expression(expression, stock_data, symbol)
                )
            finally:
                loop.close()
            
            if stock_data.empty:
                return {"matched": False, "symbol": symbol, "reason": "无数据"}
            
            if not evaluation_result["success"]:
                return {"matched": False, "symbol": symbol, "reason": f"表达式评估失败: {evaluation_result['message']}"}
            
            if evaluation_result["result"]:
                current_price = stock_data['close'].iloc[-1] if 'close' in stock_data.columns else 0
                return {
                    "matched": True,
                    "symbol": symbol,
                    "price": float(current_price),
                    "reason": "符合表达式条件",
                    "indicators": {k: float(v) if isinstance(v, (int, float, np.number)) else str(v) 
                                 for k, v in evaluation_result["indicators"].items()}
                }
            else:
                return {"matched": False, "symbol": symbol, "reason": "不符合表达式条件"}
            
        except Exception as e:
            logger.error(f"检查股票 {symbol} 表达式失败: {e}")
            return {"matched": False, "symbol": symbol, "reason": f"检查失败: {str(e)}"}
    
    def _calculate_indicators_for_conditions(self, stock_data: pd.DataFrame, 
                                           conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """为条件计算所需指标"""
        indicators = {}
        
        # 收集需要计算的技术指标
        technical_indicators = set()
        for condition in conditions:
            if condition.get("condition_type") == "technical":
                technical_indicators.add(condition["indicator"])
        
        # 计算技术指标
        for indicator in technical_indicators:
            try:
                result = self.indicator_manager.calculate_indicator(indicator, stock_data)
                if result["success"]:
                    indicators[indicator] = result["value"]
            except Exception as e:
                logger.error(f"计算指标 {indicator} 失败: {e}")
                indicators[indicator] = None
        
        return indicators
    
    def _evaluate_condition(self, condition: Dict[str, Any], stock_data: pd.DataFrame, 
                          indicators: Dict[str, Any]) -> bool:
        """评估单个条件"""
        try:
            condition_type = condition.get("condition_type")
            indicator = condition.get("indicator")
            operator = condition.get("operator")
            value = condition.get("value")
            
            # 获取指标值
            if condition_type == "technical":
                if indicator not in indicators:
                    return False
                indicator_value = indicators[indicator]
            elif condition_type == "fundamental":
                if indicator not in stock_data.columns:
                    return False
                indicator_value = stock_data[indicator].iloc[-1]
            else:
                return False
            
            # 如果指标值是Series，取最后一个值
            if hasattr(indicator_value, 'iloc'):
                indicator_value = indicator_value.iloc[-1]
            
            # 评估条件
            return self.operator_manager.evaluate_condition(indicator_value, operator, value)
            
        except Exception as e:
            logger.error(f"评估条件失败: {e}")
            return False
    
    def _combine_condition_results(self, condition_results: List[bool], 
                                 conditions: List[Dict[str, Any]]) -> bool:
        """组合条件结果"""
        if not condition_results:
            return False
        
        if len(condition_results) == 1:
            return condition_results[0]
        
        # 简单的AND逻辑组合（可以根据需要扩展）
        # TODO: 支持更复杂的逻辑组合
        return all(condition_results)
    
    async def _save_screening_result(self, strategy_id: int, matched_stocks: List[Dict[str, Any]], 
                                   total_checked: int, execution_time: float, screen_date: str):
        """保存筛选结果"""
        try:
            db_gen = get_db()
            session = next(db_gen)
            try:
                # 创建执行记录
                execution = StrategyExecution(
                    strategy_id=strategy_id,
                    execution_type="screening",
                    status="completed",
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    execution_time=execution_time,
                    total_stocks=total_checked,
                    signal_count=len(matched_stocks),
                    created_at=datetime.now()
                )
                session.add(execution)
                session.flush()  # 获取ID
                
                # 保存匹配的股票信号
                for stock in matched_stocks:
                    signal = StrategySignal(
                        strategy_id=strategy_id,
                        execution_id=execution.id,
                        stock_code=stock["symbol"],
                        signal_type="BUY",
                        trigger_price=stock.get("price", 0),
                        confidence=1.0,
                        reason=stock.get("reason", "符合筛选条件"),
                        created_at=datetime.now()
                    )
                    session.add(signal)
                
                session.commit()
                logger.info(f"保存筛选结果成功: 策略{strategy_id}, 匹配{len(matched_stocks)}只股票")
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"保存筛选结果失败: {e}")