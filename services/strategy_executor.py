# -*- coding: utf-8 -*-
"""
策略执行服务模块
负责解析和执行策略条件，生成交易信号
"""

import traceback
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, and_, desc

from config import get_settings
from core.database import (
    get_db, Strategy, StrategyCondition, StrategyExecution, 
    StrategySignal, StockData
)
from core.redis_client import get_redis
from services.data_service import DataService
from services.strategy_manager import StrategyManager, SignalType, ExecutionStatus


class StrategyExecutor:
    """策略执行器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = get_redis()
        self.data_service = None  # 延迟初始化
        self.strategy_manager = None  # 延迟初始化
        
        # 技术指标计算函数映射
        self.technical_calculators = {
            "ma": self._calculate_ma,
            "ema": self._calculate_ema,
            "rsi": self._calculate_rsi,
            "macd": self._calculate_macd,
            "kdj": self._calculate_kdj,
            "bollinger": self._calculate_bollinger,
            "volume": self._calculate_volume,
            "turnover_rate": self._calculate_turnover_rate,
            "price_change": self._calculate_price_change,
            "price_change_pct": self._calculate_price_change_pct
        }
        
        # 操作符函数映射
        self.operators = {
            ">": lambda x, y: x > y,
            "<": lambda x, y: x < y,
            ">=": lambda x, y: x >= y,
            "<=": lambda x, y: x <= y,
            "==": lambda x, y: x == y,
            "!=": lambda x, y: x != y,
            "between": lambda x, y: y["min"] <= x <= y["max"] if isinstance(y, dict) else None,
            "in": lambda x, y: x in y if isinstance(y, list) else None,
            "not_in": lambda x, y: x not in y if isinstance(y, list) else None
        }
    
    def set_data_service(self, data_service: DataService):
        """设置数据服务"""
        self.data_service = data_service
    
    def set_strategy_manager(self, strategy_manager: StrategyManager):
        """设置策略管理器"""
        self.strategy_manager = strategy_manager
    
    async def execute_strategy(self, strategy_id: int, 
                             stock_codes: Optional[List[str]] = None,
                             execution_type: str = "scan") -> Dict[str, Any]:
        """执行策略"""
        try:
            # 获取策略详情
            if not self.strategy_manager:
                return {
                    "success": False,
                    "message": "策略管理器未初始化",
                    "data": None
                }
            
            strategy = await self.strategy_manager.get_strategy_detail(strategy_id)
            if not strategy:
                return {
                    "success": False,
                    "message": "策略不存在",
                    "data": None
                }
            
            # 创建执行记录
            execution_id = await self._create_execution_record(
                strategy_id, execution_type
            )
            
            # 获取股票列表
            if not stock_codes:
                if self.data_service:
                    stock_list = await self.data_service.get_stock_list()
                    stock_codes = [stock["stock_code"] for stock in stock_list[:100]]  # 限制数量
                else:
                    stock_codes = ["000001.SZ", "000002.SZ", "600000.SH", "600036.SH"]
            
            # 执行策略条件
            signals = []
            total_stocks = len(stock_codes)
            signal_count = 0
            
            for stock_code in stock_codes:
                try:
                    # 获取股票数据
                    if not self.data_service:
                        continue
                    
                    # 获取历史数据
                    end_date = datetime.now().strftime("%Y-%m-%d")
                    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
                    
                    df = await self.data_service.get_stock_daily_data(
                        stock_code, start_date, end_date
                    )
                    
                    if df.empty:
                        continue
                    
                    # 计算技术指标
                    df = self._calculate_indicators(df, strategy)
                    
                    # 评估条件
                    signal = await self._evaluate_conditions(
                        stock_code, df, strategy, execution_id
                    )
                    
                    if signal:
                        signals.append(signal)
                        signal_count += 1
                    
                except Exception as e:
                    logger.error(f"执行策略{strategy_id}处理{stock_code}失败: {e}, {traceback.format_exc()}")
                    continue
            
            # 更新执行记录
            await self._update_execution_record(
                execution_id, 
                ExecutionStatus.COMPLETED.value,
                total_stocks,
                signal_count,
                signals
            )
            
            # 按信号强度排序
            signals.sort(key=lambda x: x.get("signal_strength", 0), reverse=True)
            
            logger.info(f"策略{strategy_id}执行完成，扫描{total_stocks}只股票，发现{signal_count}个信号")
            return {
                "success": True,
                "message": "策略执行成功",
                "data": {
                    "execution_id": execution_id,
                    "strategy_id": strategy_id,
                    "strategy_name": strategy["name"],
                    "total_stocks": total_stocks,
                    "signal_count": signal_count,
                    "signals": signals,
                    "execution_time": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"执行策略失败: {e}, {traceback.format_exc()}")
            # 更新执行记录为失败状态
            if 'execution_id' in locals():
                await self._update_execution_record(
                    execution_id,
                    ExecutionStatus.FAILED.value,
                    error_message=str(e)
                )
            
            return {
                "success": False,
                "message": f"执行策略失败: {str(e)}",
                "data": None
            }
    
    async def _create_execution_record(self, strategy_id: int, 
                                     execution_type: str) -> int:
        """创建执行记录"""
        try:
            async for db in get_db():
                execution_record = {
                    "strategy_id": strategy_id,
                    "execution_type": execution_type,
                    "status": ExecutionStatus.RUNNING.value,
                    "start_time": datetime.now(),
                    "created_at": datetime.now()
                }
                
                stmt = insert(StrategyExecution).values(**execution_record)
                result = await db.execute(stmt)
                execution_id = result.inserted_primary_key[0]
                
                await db.commit()
                return execution_id
                
        except Exception as e:
            logger.error(f"创建执行记录失败: {e}, {traceback.format_exc()}")
            raise
    
    async def _update_execution_record(self, execution_id: int, status: str,
                                     total_stocks: int = 0, signal_count: int = 0,
                                     result_data: Any = None, error_message: str = None):
        """更新执行记录"""
        try:
            async for db in get_db():
                update_data = {
                    "status": status,
                    "end_time": datetime.now()
                }
                
                if total_stocks > 0:
                    update_data["total_stocks"] = total_stocks
                
                if signal_count > 0:
                    update_data["signal_count"] = signal_count
                
                if result_data is not None:
                    update_data["result_data"] = result_data
                
                if error_message is not None:
                    update_data["error_message"] = error_message
                
                stmt = update(StrategyExecution).where(
                    StrategyExecution.id == execution_id
                ).values(**update_data)
                
                await db.execute(stmt)
                await db.commit()
                
        except Exception as e:
            logger.error(f"更新执行记录失败: {e}, {traceback.format_exc()}")
    
    def _calculate_indicators(self, df: pd.DataFrame, strategy: Dict[str, Any]) -> pd.DataFrame:
        """计算技术指标"""
        # 确保日期索引
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'trade_date' in df.columns:
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                df.set_index('trade_date', inplace=True)
            else:
                df = df.copy()
        
        # 根据策略条件计算所需指标
        conditions = strategy.get("condition_details", [])
        for condition in conditions:
            if condition["condition_type"] == "technical":
                indicator = condition["indicator"]
                if indicator in self.technical_calculators:
                    calculator = self.technical_calculators[indicator]
                    df = calculator(df, condition["value"])
        
        return df
    
    async def _evaluate_conditions(self, stock_code: str, df: pd.DataFrame, 
                                 strategy: Dict[str, Any], execution_id: int) -> Optional[Dict[str, Any]]:
        """评估策略条件"""
        if df.empty or len(df) < 2:
            return None
        
        # 获取最新数据行
        latest_row = df.iloc[-1]
        
        # 评估所有条件
        conditions = strategy.get("condition_details", [])
        if not conditions:
            return None
        
        all_conditions_met = True
        condition_results = []
        signal_reasons = []
        
        for condition in conditions:
            if not condition["is_active"]:
                continue
            
            result = self._evaluate_single_condition(latest_row, df, condition)
            condition_results.append(result)
            
            if result["result"]:
                signal_reasons.append(result["description"])
            
            # 处理逻辑操作符
            if condition["logic_operator"] == "AND" and not result["result"]:
                all_conditions_met = False
                break
            elif condition["logic_operator"] == "OR" and result["result"]:
                all_conditions_met = True
                break
        
        # 如果所有条件都满足，创建信号
        if all_conditions_met and signal_reasons:
            # 获取当前价格
            current_price = latest_row.get("close_price", 0)
            
            # 创建信号记录
            signal_data = {
                "strategy_id": strategy["id"],
                "execution_id": execution_id,
                "stock_code": stock_code,
                "signal_type": SignalType.BUY.value,  # 默认为买入信号
                "signal_strength": 0.8,  # 默认信号强度
                "trigger_price": current_price,
                "reason": "\n".join(signal_reasons),
                "confidence": 0.8,  # 默认置信度
                "created_at": datetime.now()
            }
            
            # 保存信号记录
            await self._save_signal(signal_data)
            
            # 返回信号信息
            return {
                "stock_code": stock_code,
                "signal_type": SignalType.BUY.value,
                "signal_strength": 0.8,
                "trigger_price": current_price,
                "reason": "\n".join(signal_reasons),
                "timestamp": datetime.now().isoformat()
            }
        
        return None
    
    def _evaluate_single_condition(self, row: pd.Series, df: pd.DataFrame, 
                                condition: Dict[str, Any]) -> Dict[str, Any]:
        """评估单个条件"""
        condition_type = condition["condition_type"]
        indicator = condition["indicator"]
        operator = condition["operator"]
        value = condition["value"]
        
        # 获取指标值
        indicator_value = None
        if condition_type == "technical":
            # 技术指标可能有特定的列名
            if indicator == "ma":
                period = value.get("period", 20)
                col_name = f"ma_{period}"
                indicator_value = row.get(col_name)
            elif indicator == "ema":
                period = value.get("period", 20)
                col_name = f"ema_{period}"
                indicator_value = row.get(col_name)
            elif indicator == "rsi":
                period = value.get("period", 14)
                col_name = f"rsi_{period}"
                indicator_value = row.get(col_name)
            elif indicator == "macd":
                component = value.get("component", "macd")
                col_name = f"macd_{component}"
                indicator_value = row.get(col_name)
            elif indicator == "kdj":
                component = value.get("component", "k")
                col_name = f"kdj_{component}"
                indicator_value = row.get(col_name)
            elif indicator == "bollinger":
                component = value.get("component", "middle")
                col_name = f"bollinger_{component}"
                indicator_value = row.get(col_name)
            else:
                # 其他指标直接使用列名
                indicator_value = row.get(indicator)
        elif condition_type == "fundamental":
            # 基本面指标直接使用列名
            indicator_value = row.get(indicator)
        
        # 如果指标值不存在，条件不满足
        if indicator_value is None:
            return {
                "result": False,
                "description": f"指标{indicator}不存在"
            }
        
        # 评估条件
        operator_func = self.operators.get(operator)
        if not operator_func:
            return {
                "result": False,
                "description": f"操作符{operator}不支持"
            }
        
        result = operator_func(indicator_value, value)
        
        # 生成描述
        description = self._generate_condition_description(
            indicator, operator, value, indicator_value
        )
        
        return {
            "result": result,
            "description": description
        }
    
    def _generate_condition_description(self, indicator: str, operator: str, 
                                      value: Any, actual_value: Any) -> str:
        """生成条件描述"""
        indicator_name = self._get_indicator_display_name(indicator)
        operator_name = self._get_operator_display_name(operator)
        
        if operator == "between":
            if isinstance(value, dict) and "min" in value and "max" in value:
                return f"{indicator_name}{operator_name}{value['min']}和{value['max']}，实际值为{actual_value:.2f}"
        elif operator in ["in", "not_in"]:
            if isinstance(value, list):
                return f"{indicator_name}{operator_name}{', '.join(map(str, value))}，实际值为{actual_value}"
        else:
            if isinstance(value, (int, float)) and isinstance(actual_value, (int, float)):
                return f"{indicator_name}{operator_name}{value}，实际值为{actual_value:.2f}"
            else:
                return f"{indicator_name}{operator_name}{value}，实际值为{actual_value}"
        
        return f"{indicator_name}满足条件"
    
    def _get_indicator_display_name(self, indicator: str) -> str:
        """获取指标显示名称"""
        indicator_names = {
            "ma": "移动平均线",
            "ema": "指数移动平均线",
            "rsi": "相对强弱指数",
            "macd": "MACD指标",
            "kdj": "KDJ指标",
            "bollinger": "布林带",
            "volume": "成交量",
            "turnover_rate": "换手率",
            "price_change": "价格变化",
            "price_change_pct": "价格变化百分比",
            "pe_ratio": "市盈率",
            "pb_ratio": "市净率"
        }
        
        return indicator_names.get(indicator, indicator)
    
    def _get_operator_display_name(self, operator: str) -> str:
        """获取操作符显示名称"""
        operator_names = {
            ">": "大于",
            "<": "小于",
            ">=": "大于等于",
            "<=": "小于等于",
            "==": "等于",
            "!=": "不等于",
            "between": "介于",
            "in": "包含于",
            "not_in": "不包含于"
        }
        
        return operator_names.get(operator, operator)
    
    async def _save_signal(self, signal_data: Dict[str, Any]) -> int:
        """保存信号记录"""
        try:
            async for db in get_db():
                stmt = insert(StrategySignal).values(**signal_data)
                result = await db.execute(stmt)
                signal_id = result.inserted_primary_key[0]
                
                await db.commit()
                return signal_id
                
        except Exception as e:
            logger.error(f"保存信号记录失败: {e}, {traceback.format_exc()}")
            return 0
    
    # 技术指标计算函数
    def _calculate_ma(self, df: pd.DataFrame, params: Any) -> pd.DataFrame:
        """计算移动平均线"""
        period = params.get("period", 20) if isinstance(params, dict) else 20
        df[f'ma_{period}'] = df['close_price'].rolling(window=period).mean()
        return df
    
    def _calculate_ema(self, df: pd.DataFrame, params: Any) -> pd.DataFrame:
        """计算指数移动平均线"""
        period = params.get("period", 20) if isinstance(params, dict) else 20
        df[f'ema_{period}'] = df['close_price'].ewm(span=period, adjust=False).mean()
        return df
    
    def _calculate_rsi(self, df: pd.DataFrame, params: Any) -> pd.DataFrame:
        """计算相对强弱指数"""
        period = params.get("period", 14) if isinstance(params, dict) else 14
        delta = df['close_price'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
        return df
    
    def _calculate_macd(self, df: pd.DataFrame, params: Any) -> pd.DataFrame:
        """计算MACD指标"""
        fast_period = params.get("fast_period", 12) if isinstance(params, dict) else 12
        slow_period = params.get("slow_period", 26) if isinstance(params, dict) else 26
        signal_period = params.get("signal_period", 9) if isinstance(params, dict) else 9
        
        # 计算快速和慢速EMA
        df['ema_fast'] = df['close_price'].ewm(span=fast_period, adjust=False).mean()
        df['ema_slow'] = df['close_price'].ewm(span=slow_period, adjust=False).mean()
        
        # 计算MACD线和信号线
        df['macd_line'] = df['ema_fast'] - df['ema_slow']
        df['macd_signal'] = df['macd_line'].ewm(span=signal_period, adjust=False).mean()
        
        # 计算MACD柱状图
        df['macd_histogram'] = df['macd_line'] - df['macd_signal']
        
        return df
    
    def _calculate_kdj(self, df: pd.DataFrame, params: Any) -> pd.DataFrame:
        """计算KDJ指标"""
        period = params.get("period", 9) if isinstance(params, dict) else 9
        k_period = params.get("k_period", 3) if isinstance(params, dict) else 3
        d_period = params.get("d_period", 3) if isinstance(params, dict) else 3
        
        # 计算最低价和最高价的周期内最小值和最大值
        low_min = df['low_price'].rolling(window=period).min()
        high_max = df['high_price'].rolling(window=period).max()
        
        # 计算RSV值
        df['rsv'] = 100 * ((df['close_price'] - low_min) / (high_max - low_min))
        
        # 计算K值、D值和J值
        df['kdj_k'] = df['rsv'].ewm(alpha=1/k_period, adjust=False).mean()
        df['kdj_d'] = df['kdj_k'].ewm(alpha=1/d_period, adjust=False).mean()
        df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
        
        return df
    
    def _calculate_bollinger(self, df: pd.DataFrame, params: Any) -> pd.DataFrame:
        """计算布林带指标"""
        period = params.get("period", 20) if isinstance(params, dict) else 20
        std_dev = params.get("std_dev", 2) if isinstance(params, dict) else 2
        
        # 计算移动平均线
        df['bollinger_middle'] = df['close_price'].rolling(window=period).mean()
        
        # 计算标准差
        df['bollinger_std'] = df['close_price'].rolling(window=period).std()
        
        # 计算上轨和下轨
        df['bollinger_upper'] = df['bollinger_middle'] + (df['bollinger_std'] * std_dev)
        df['bollinger_lower'] = df['bollinger_middle'] - (df['bollinger_std'] * std_dev)
        
        return df
    
    def _calculate_volume(self, df: pd.DataFrame, params: Any) -> pd.DataFrame:
        """计算成交量指标"""
        period = params.get("period", 20) if isinstance(params, dict) else 20
        df['volume_ma'] = df['volume'].rolling(window=period).mean()
        return df
    
    def _calculate_turnover_rate(self, df: pd.DataFrame, params: Any) -> pd.DataFrame:
        """计算换手率指标"""
        # 换手率通常已经在数据中
        return df
    
    def _calculate_price_change(self, df: pd.DataFrame, params: Any) -> pd.DataFrame:
        """计算价格变化指标"""
        df['price_change'] = df['close_price'].diff()
        return df
    
    def _calculate_price_change_pct(self, df: pd.DataFrame, params: Any) -> pd.DataFrame:
        """计算价格变化百分比指标"""
        df['price_change_pct'] = df['close_price'].pct_change() * 100
        return df
    
    async def get_strategy_signals(self, strategy_id: Optional[int] = None, 
                                 execution_id: Optional[int] = None,
                                 stock_code: Optional[str] = None,
                                 signal_type: Optional[str] = None,
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None,
                                 limit: int = 100) -> List[Dict[str, Any]]:
        """获取策略信号"""
        try:
            async for db in get_db():
                query = select(StrategySignal).order_by(desc(StrategySignal.created_at))
                
                # 添加过滤条件
                if strategy_id is not None:
                    query = query.where(StrategySignal.strategy_id == strategy_id)
                
                if execution_id is not None:
                    query = query.where(StrategySignal.execution_id == execution_id)
                
                if stock_code is not None:
                    query = query.where(StrategySignal.stock_code == stock_code)
                
                if signal_type is not None:
                    query = query.where(StrategySignal.signal_type == signal_type)
                
                if start_date is not None:
                    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                    query = query.where(StrategySignal.created_at >= start_datetime)
                
                if end_date is not None:
                    end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                    query = query.where(StrategySignal.created_at < end_datetime)
                
                # 限制结果数量
                query = query.limit(limit)
                
                result = await db.execute(query)
                signals = result.scalars().all()
                
                return [
                    {
                        "id": signal.id,
                        "strategy_id": signal.strategy_id,
                        "execution_id": signal.execution_id,
                        "stock_code": signal.stock_code,
                        "signal_type": signal.signal_type,
                        "signal_strength": signal.signal_strength,
                        "trigger_price": signal.trigger_price,
                        "target_price": signal.target_price,
                        "stop_loss_price": signal.stop_loss_price,
                        "reason": signal.reason,
                        "confidence": signal.confidence,
                        "is_processed": signal.is_processed,
                        "created_at": signal.created_at.isoformat() if signal.created_at else None
                    }
                    for signal in signals
                ]
                
        except Exception as e:
            logger.error(f"获取策略信号失败: {e}, {traceback.format_exc()}")
            return []
    
    async def get_execution_history(self, strategy_id: Optional[int] = None,
                                  execution_type: Optional[str] = None,
                                  status: Optional[str] = None,
                                  limit: int = 20) -> List[Dict[str, Any]]:
        """获取执行历史记录"""
        try:
            async for db in get_db():
                query = select(StrategyExecution).order_by(desc(StrategyExecution.start_time))
                
                # 添加过滤条件
                if strategy_id is not None:
                    query = query.where(StrategyExecution.strategy_id == strategy_id)
                
                if execution_type is not None:
                    query = query.where(StrategyExecution.execution_type == execution_type)
                
                if status is not None:
                    query = query.where(StrategyExecution.status == status)
                
                # 限制结果数量
                query = query.limit(limit)
                
                result = await db.execute(query)
                executions = result.scalars().all()
                
                return [
                    {
                        "id": execution.id,
                        "strategy_id": execution.strategy_id,
                        "execution_type": execution.execution_type,
                        "status": execution.status,
                        "start_time": execution.start_time.isoformat() if execution.start_time else None,
                        "end_time": execution.end_time.isoformat() if execution.end_time else None,
                        "total_stocks": execution.total_stocks,
                        "signal_count": execution.signal_count,
                        "success_rate": execution.success_rate,
                        "error_message": execution.error_message,
                        "created_at": execution.created_at.isoformat() if execution.created_at else None
                    }
                    for execution in executions
                ]
                
        except Exception as e:
            logger.error(f"获取执行历史记录失败: {e}, {traceback.format_exc()}")
            return []