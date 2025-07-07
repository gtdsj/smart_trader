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
        # 使用传入的数据服务或获取单例实例
        self.data_service = data_service or DataService.get_instance()
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
            if not strategy_detail:
                return {
                    "success": False,
                    "message": "策略不存在或获取失败",
                    "matched_stocks": [],
                    "total_checked": 0,
                    "execution_time": 0
                }
            
            strategy = strategy_detail
            logger.info(f"策略详情: {strategy}")
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
            stock_list_data = await self.data_service.get_stock_list()
            
            # 提取股票代码字符串
            stock_codes = []
            for stock_info in stock_list_data:
                if isinstance(stock_info, dict):
                    # 从字典中提取股票代码
                    stock_code = stock_info.get('code') or stock_info.get('stock_code') or stock_info.get('symbol')
                    if stock_code:
                        stock_codes.append(stock_code)
                elif isinstance(stock_info, str):
                    # 如果已经是字符串，直接添加
                    stock_codes.append(stock_info)
            
            logger.info(f"获取股票列表成功，共{len(stock_codes)}只股票")
            return stock_codes
            
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
        """处理股票批次（策略模式）- 使用批量数据获取和DataFrame计算"""
        matched_stocks = []
        
        try:
            # 批量获取历史数据
            end_date = screen_date
            start_date = (datetime.strptime(screen_date, '%Y-%m-%d') - timedelta(days=365)).strftime('%Y-%m-%d')
            
            batch_data = await self.data_service.get_batch_historical_data(
                stock_codes=stock_batch,
                start_date=start_date,
                end_date=end_date
            )
            
            # 获取策略条件
            conditions = strategy.get("condition_details", [])
            if not conditions:
                logger.warning("策略无条件，跳过批次处理")
                return matched_stocks
            
            # 批量处理股票策略评估
            try:
                matched_stocks = self._process_batch_strategy_vectorized(batch_data, conditions, stock_batch)
            except Exception as e:
                logger.warning(f"批量向量化处理失败: {e}，回退到逐个处理")
                matched_stocks = self._process_batch_strategy_one_by_one(batch_data, conditions, stock_batch)
                
            
            logger.info(f"批量策略处理完成: {len(matched_stocks)}/{len(stock_batch)} 只股票符合条件")
            return matched_stocks
            
        except Exception as e:
            logger.error(f"批量策略处理失败: {e}, 回退到线程池处理")
            # 回退到原有的线程池处理方式
            return await self._process_stock_batch_strategy_fallback(stock_batch, strategy, screen_date)
    
    async def _process_stock_batch_strategy_fallback(self, stock_batch: List[str], strategy: Dict[str, Any], 
                                                   screen_date: str) -> List[Dict[str, Any]]:
        """处理股票批次（策略模式）- 回退方案"""
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
        """处理股票批次（表达式模式）- 使用批量数据获取和DataFrame计算"""
        matched_stocks = []
        
        try:
            # 批量获取历史数据
            end_date = screen_date
            start_date = (datetime.strptime(screen_date, '%Y-%m-%d') - timedelta(days=365)).strftime('%Y-%m-%d')
            
            batch_data = await self.data_service.get_batch_historical_data(
                stock_codes=stock_batch,
                start_date=start_date,
                end_date=end_date
            )
            
            # 对每个股票进行表达式评估
            for stock_code in stock_batch:
                try:
                    stock_data = batch_data.get(stock_code, pd.DataFrame())
                    if stock_data.empty:
                        logger.debug(f"股票 {stock_code} 无数据")
                        continue
                    
                    # 评估表达式
                    evaluation_result = await self.strategy_manager.evaluate_strategy_expression(
                        expression, stock_data, stock_code
                    )
                    
                    if not evaluation_result["success"]:
                        logger.debug(f"股票 {stock_code} 表达式评估失败: {evaluation_result['message']}")
                        continue
                    
                    if evaluation_result["result"]:
                        current_price = stock_data['close_price'].iloc[-1] if 'close_price' in stock_data.columns else 0
                        matched_stocks.append({
                            "matched": True,
                            "symbol": stock_code,
                            "price": float(current_price),
                            "reason": "符合表达式条件",
                            "indicators": {k: float(v) if isinstance(v, (int, float, np.number)) else str(v) 
                                         for k, v in evaluation_result["indicators"].items()}
                        })
                        
                except Exception as e:
                    logger.error(f"处理股票 {stock_code} 表达式失败: {e}")
                    continue
            
            logger.info(f"批量表达式处理完成: {len(matched_stocks)}/{len(stock_batch)} 只股票符合条件")
            return matched_stocks
            
        except Exception as e:
            logger.error(f"批量表达式处理失败: {e}, 回退到线程池处理")
            # 回退到原有的线程池处理方式
            return await self._process_stock_batch_expression_fallback(stock_batch, expression, screen_date)
    
    async def _process_stock_batch_expression_fallback(self, stock_batch: List[str], expression: str, 
                                                     screen_date: str) -> List[Dict[str, Any]]:
        """处理股票批次（表达式模式）- 回退方案"""
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
    
    def _process_batch_strategy_vectorized(self, batch_data: Dict[str, pd.DataFrame], 
                                         conditions: List[Dict[str, Any]], 
                                         stock_batch: List[str]) -> List[Dict[str, Any]]:
        """批量向量化处理股票策略评估 - 真正的向量化实现"""
        matched_stocks = []
        
        if not batch_data or not conditions:
            return matched_stocks
        
        try:
            # 第一步：构建多股票数据矩阵
            stock_matrices = self._build_stock_matrices(batch_data, stock_batch)
            if not stock_matrices:
                logger.info("股票数据矩阵构建失败")
                return matched_stocks
            
            # 第二步：批量计算所有技术指标
            indicator_matrices = self._calculate_indicators_vectorized(stock_matrices, conditions)
            logger.info(f"指标矩阵: {indicator_matrices}")
            
            # 第三步：批量评估所有条件
            condition_results = self._evaluate_conditions_vectorized(stock_matrices, indicator_matrices, conditions)
            
            # 第四步：组合条件结果并筛选匹配股票
            matched_stocks = self._filter_matched_stocks_vectorized(
                stock_matrices, indicator_matrices, condition_results, conditions, stock_batch
            )
            
            return matched_stocks
            
        except Exception as e:
            logger.error(f"向量化处理失败: {e}")
            raise e
    
    def _build_stock_matrices(self, batch_data: Dict[str, pd.DataFrame], 
                            stock_batch: List[str]) -> Dict[str, Any]:
        """构建股票数据矩阵"""
        matrices = {
            'close_prices': {},
            'high_prices': {},
            'low_prices': {},
            'volumes': {},
            'stock_codes': [],
            'valid_stocks': []
        }
        
        for stock_code in stock_batch:
            stock_data = batch_data.get(stock_code, pd.DataFrame())
            if stock_data.empty or len(stock_data) < 20:  # 至少需要20天数据
                continue
                
            matrices['close_prices'][stock_code] = stock_data['close_price']
            matrices['high_prices'][stock_code] = stock_data['high_price']
            matrices['low_prices'][stock_code] = stock_data['low_price']
            matrices['volumes'][stock_code] = stock_data['volume']
            matrices['valid_stocks'].append(stock_code)
        
        matrices['stock_codes'] = matrices['valid_stocks']
        return matrices if matrices['valid_stocks'] else {}
    
    def _calculate_indicators_vectorized(self, stock_matrices: Dict[str, Any], 
                                       conditions: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """批量计算技术指标"""
        indicator_results = {}
        
        # 收集需要计算的指标
        required_indicators = set()
        for condition in conditions:
            if condition.get("condition_type") == "technical":
                required_indicators.add(condition["indicator"])
        
        # 为每个指标批量计算所有股票
        for indicator in required_indicators:
            indicator_results[indicator] = {}
            
            for stock_code in stock_matrices['valid_stocks']:
                try:
                    close_prices = stock_matrices['close_prices'][stock_code]
                    high_prices = stock_matrices['high_prices'][stock_code]
                    low_prices = stock_matrices['low_prices'][stock_code]
                    volumes = stock_matrices['volumes'][stock_code]
                    
                    # 直接使用pandas向量化计算，避免调用指标管理器的开销
                    if indicator == "rsi":
                        # RSI计算
                        delta = close_prices.diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        rsi_value = 100 - (100 / (1 + rs))
                        indicator_results[indicator][stock_code] = rsi_value.iloc[-1] if not rsi_value.empty else None
                        
                    elif indicator == "ma":
                        # 移动平均线
                        ma_value = close_prices.rolling(window=20).mean()
                        indicator_results[indicator][stock_code] = ma_value.iloc[-1] if not ma_value.empty else None
                        
                    elif indicator == "ema":
                        # 指数移动平均线
                        ema_value = close_prices.ewm(span=12).mean()
                        indicator_results[indicator][stock_code] = ema_value.iloc[-1] if not ema_value.empty else None
                        
                    elif indicator == "volume":
                        # 成交量比率
                        volume_ma = volumes.rolling(window=20).mean()
                        volume_ratio = volumes / volume_ma
                        indicator_results[indicator][stock_code] = volume_ratio.iloc[-1] if not volume_ratio.empty else None
                        
                    elif indicator == "atr":
                        # 平均真实波幅
                        high_low = high_prices - low_prices
                        high_close = np.abs(high_prices - close_prices.shift())
                        low_close = np.abs(low_prices - close_prices.shift())
                        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
                        atr_value = true_range.rolling(window=14).mean()
                        indicator_results[indicator][stock_code] = atr_value.iloc[-1] if not atr_value.empty else None
                        
                    else:
                        # 其他指标使用原有方法
                        stock_data = pd.DataFrame({
                            'close_price': close_prices,
                            'high_price': high_prices,
                            'low_price': low_prices,
                            'volume': volumes
                        })
                        result_df = self.indicator_manager.calculate_indicator(indicator, stock_data)
                        
                        # 提取指标值
                        if indicator in result_df.columns:
                            indicator_results[indicator][stock_code] = result_df[indicator].iloc[-1]
                        else:
                            indicator_results[indicator][stock_code] = None
                            
                except Exception as e:
                    logger.error(f"计算股票 {stock_code} 指标 {indicator} 失败: {e}")
                    indicator_results[indicator][stock_code] = None
        
        return indicator_results
    
    def _evaluate_conditions_vectorized(self, stock_matrices: Dict[str, Any], 
                                      indicator_matrices: Dict[str, Dict[str, Any]], 
                                      conditions: List[Dict[str, Any]]) -> Dict[str, List[bool]]:
        """批量评估条件"""
        condition_results = {}
        
        for stock_code in stock_matrices['valid_stocks']:
            condition_results[stock_code] = []
            
            for condition in conditions:
                try:
                    condition_type = condition.get("condition_type")
                    indicator = condition.get("indicator")
                    operator = condition.get("operator")
                    value = condition.get("value")
                    
                    # 获取指标值
                    if condition_type == "technical":
                        if indicator in indicator_matrices and stock_code in indicator_matrices[indicator]:
                            indicator_value = indicator_matrices[indicator][stock_code]
                        else:
                            condition_results[stock_code].append(False)
                            continue
                    elif condition_type == "fundamental":
                        # 基本面数据直接从原始数据获取
                        if indicator == "volume":
                            indicator_value = stock_matrices['volumes'][stock_code].iloc[-1]
                        else:
                            condition_results[stock_code].append(False)
                            continue
                    else:
                        condition_results[stock_code].append(False)
                        continue
                    
                    # 检查指标值有效性
                    if indicator_value is None or pd.isna(indicator_value):
                        condition_results[stock_code].append(False)
                        continue
                    
                    # 评估条件
                    result = self.operator_manager.evaluate_condition(indicator_value, operator, value)
                    condition_results[stock_code].append(result)
                    
                except Exception as e:
                    logger.error(f"评估股票 {stock_code} 条件失败: {e}")
                    condition_results[stock_code].append(False)
        
        return condition_results
    
    def _filter_matched_stocks_vectorized(self, stock_matrices: Dict[str, Any], 
                                        indicator_matrices: Dict[str, Dict[str, Any]], 
                                        condition_results: Dict[str, List[bool]], 
                                        conditions: List[Dict[str, Any]], 
                                        stock_batch: List[str]) -> List[Dict[str, Any]]:
        """筛选匹配的股票"""
        matched_stocks = []
        
        for stock_code in stock_matrices['valid_stocks']:
            try:
                # 组合条件结果
                stock_condition_results = condition_results.get(stock_code, [])
                final_result = self._combine_condition_results(stock_condition_results, conditions)
                
                if final_result:
                    current_price = stock_matrices['close_prices'][stock_code].iloc[-1]
                    
                    # 收集指标值
                    indicators = {}
                    for indicator, stock_values in indicator_matrices.items():
                        if stock_code in stock_values and stock_values[stock_code] is not None:
                            indicators[indicator] = stock_values[stock_code]
                    
                    matched_stocks.append({
                        "matched": True,
                        "symbol": stock_code,
                        "price": float(current_price),
                        "reason": "符合策略条件",
                        "indicators": {k: float(v) if isinstance(v, (int, float, np.number)) and not pd.isna(v) else str(v) 
                                     for k, v in indicators.items()}
                    })
                    
            except Exception as e:
                logger.error(f"筛选股票 {stock_code} 失败: {e}")
                continue
        
        return matched_stocks
    
    def _process_batch_strategy_one_by_one(self, batch_data: Dict[str, pd.DataFrame], conditions: List[Dict[str, Any]], stock_batch: List[str]):
        """逐个处理股票批次（策略模式）"""
        # 回退到原有的逐个处理方式
        matched_stocks = []
        for stock_code in stock_batch:
            try:
                stock_data = batch_data.get(stock_code, pd.DataFrame())
                if stock_data.empty:
                    logger.debug(f"股票 {stock_code} 无数据")
                    continue
                
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
                    current_price = stock_data['close_price'].iloc[-1] if 'close_price' in stock_data.columns else 0
                    matched_stocks.append({
                        "matched": True,
                        "symbol": stock_code,
                        "price": float(current_price),
                        "reason": "符合策略条件",
                        "indicators": {k: float(v) if isinstance(v, (int, float, np.number)) else str(v) 
                                        for k, v in indicators.items()}
                    })
                    
            except Exception as e:
                logger.error(f"处理股票 {stock_code} 策略失败: {e}")
                continue
        return matched_stocks

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