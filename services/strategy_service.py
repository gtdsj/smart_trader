# -*- coding: utf-8 -*-
"""
选股服务模块
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import pandas as pd
import numpy as np
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, and_, desc

from config import get_settings
from core.database import get_db, Strategy, StockData
from core.redis_client import get_redis
from services.notification_service import NotificationService
from services.data_service import DataService


class StrategyType(Enum):
    """策略类型枚举"""
    TECHNICAL = "technical"  # 技术分析
    FUNDAMENTAL = "fundamental"  # 基本面分析
    QUANTITATIVE = "quantitative"  # 量化分析
    MOMENTUM = "momentum"  # 动量策略
    MEAN_REVERSION = "mean_reversion"  # 均值回归
    BREAKOUT = "breakout"  # 突破策略


class SignalType(Enum):
    """信号类型枚举"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class StrategyService:
    """选股服务"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = get_redis()
        self.notification_service = NotificationService()
        self.data_service = None  # 延迟初始化
        
        # 策略注册表
        self.strategies = {
            "ma_cross": self._ma_cross_strategy,
            "rsi_oversold": self._rsi_oversold_strategy,
            "bollinger_bands": self._bollinger_bands_strategy,
            "volume_breakout": self._volume_breakout_strategy,
            "momentum": self._momentum_strategy,
            "mean_reversion": self._mean_reversion_strategy,
            "macd_signal": self._macd_signal_strategy,
            "kdj_signal": self._kdj_signal_strategy
        }
    
    def set_data_service(self, data_service: DataService):
        """设置数据服务"""
        self.data_service = data_service
    
    async def create_strategy(self, name: str, description: str, 
                            strategy_type: str, parameters: Dict[str, Any]) -> bool:
        """创建策略"""
        try:
            async for db in get_db():
                strategy_data = {
                    "name": name,
                    "description": description,
                    "strategy_type": strategy_type,
                    "parameters": parameters,
                    "is_active": False,
                    "created_at": datetime.now()
                }
                
                stmt = insert(Strategy).values(**strategy_data)
                await db.execute(stmt)
                await db.commit()
                
                logger.info(f"创建策略成功: {name}")
                return True
                
        except Exception as e:
            logger.error(f"创建策略失败: {e}")
            return False
    
    async def get_strategies(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """获取策略列表"""
        try:
            async for db in get_db():
                query = select(Strategy).order_by(desc(Strategy.created_at))
                
                if active_only:
                    query = query.where(Strategy.is_active == True)
                
                result = await db.execute(query)
                strategies = result.scalars().all()
                
                return [
                    {
                        "id": strategy.id,
                        "name": strategy.name,
                        "description": strategy.description,
                        "strategy_type": strategy.strategy_type,
                        "parameters": strategy.parameters,
                        "is_active": strategy.is_active,
                        "created_at": strategy.created_at.isoformat() if strategy.created_at else None
                    }
                    for strategy in strategies
                ]
                
        except Exception as e:
            logger.error(f"获取策略列表失败: {e}")
            return []
    
    async def activate_strategy(self, strategy_id: int) -> bool:
        """激活策略"""
        try:
            async for db in get_db():
                stmt = update(Strategy).where(
                    Strategy.id == strategy_id
                ).values(
                    is_active=True,
                    updated_at=datetime.now()
                )
                
                await db.execute(stmt)
                await db.commit()
                
                logger.info(f"激活策略: {strategy_id}")
                return True
                
        except Exception as e:
            logger.error(f"激活策略失败: {e}")
            return False
    
    async def deactivate_strategy(self, strategy_id: int) -> bool:
        """停用策略"""
        try:
            async for db in get_db():
                stmt = update(Strategy).where(
                    Strategy.id == strategy_id
                ).values(
                    is_active=False,
                    updated_at=datetime.now()
                )
                
                await db.execute(stmt)
                await db.commit()
                
                logger.info(f"停用策略: {strategy_id}")
                return True
                
        except Exception as e:
            logger.error(f"停用策略失败: {e}")
            return False
    
    async def run_strategy_scan(self, strategy_name: str, 
                              stock_codes: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """运行策略扫描"""
        try:
            if strategy_name not in self.strategies:
                logger.error(f"未知策略: {strategy_name}")
                return []
            
            # 获取股票列表
            if stock_codes is None:
                if self.data_service:
                    stock_list = await self.data_service.get_stock_list()
                    stock_codes = [stock["stock_code"] for stock in stock_list[:100]]  # 限制数量
                else:
                    stock_codes = ["000001.SZ", "000002.SZ", "600000.SH", "600036.SH"]
            
            # 运行策略
            strategy_func = self.strategies[strategy_name]
            signals = []
            
            for stock_code in stock_codes:
                try:
                    signal = await strategy_func(stock_code)
                    if signal and signal["signal"] != SignalType.HOLD:
                        signals.append(signal)
                except Exception as e:
                    logger.error(f"策略{strategy_name}处理{stock_code}失败: {e}")
                    continue
            
            # 按信号强度排序
            signals.sort(key=lambda x: x.get("strength", 0), reverse=True)
            
            logger.info(f"策略{strategy_name}扫描完成，发现{len(signals)}个信号")
            return signals
            
        except Exception as e:
            logger.error(f"运行策略扫描失败: {e}")
            return []
    
    async def run_all_active_strategies(self) -> Dict[str, List[Dict[str, Any]]]:
        """运行所有激活的策略"""
        try:
            active_strategies = await self.get_strategies(active_only=True)
            results = {}
            
            for strategy in active_strategies:
                strategy_name = strategy["name"]
                if strategy_name in self.strategies:
                    signals = await self.run_strategy_scan(strategy_name)
                    results[strategy_name] = signals
                    
                    # 发送信号通知
                    if signals:
                        await self._send_strategy_signals_notification(strategy_name, signals)
            
            return results
            
        except Exception as e:
            logger.error(f"运行所有激活策略失败: {e}")
            return {}
    
    async def _get_stock_data(self, stock_code: str, days: int = 30) -> pd.DataFrame:
        """获取股票数据"""
        try:
            if self.data_service:
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                df = await self.data_service.get_historical_data(stock_code, start_date, end_date)
                return df
            else:
                raise Exception("数据服务未初始化，无法获取股票数据")
                
        except Exception as e:
            logger.error(f"获取{stock_code}数据失败: {e}")
            return pd.DataFrame()
    
    async def _ma_cross_strategy(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """均线交叉策略"""
        try:
            df = await self._get_stock_data(stock_code, 60)
            if df.empty or len(df) < 20:
                return None
            
            # 计算移动平均线
            df['ma5'] = df['close_price'].rolling(window=5).mean()
            df['ma20'] = df['close_price'].rolling(window=20).mean()
            
            # 获取最新数据
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # 判断交叉信号
            if prev['ma5'] <= prev['ma20'] and latest['ma5'] > latest['ma20']:
                # 金叉
                return {
                    "stock_code": stock_code,
                    "signal": SignalType.BUY,
                    "strategy": "ma_cross",
                    "reason": "MA5上穿MA20金叉",
                    "strength": 0.7,
                    "price": latest['close_price'],
                    "timestamp": datetime.now().isoformat()
                }
            elif prev['ma5'] >= prev['ma20'] and latest['ma5'] < latest['ma20']:
                # 死叉
                return {
                    "stock_code": stock_code,
                    "signal": SignalType.SELL,
                    "strategy": "ma_cross",
                    "reason": "MA5下穿MA20死叉",
                    "strength": 0.7,
                    "price": latest['close_price'],
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "stock_code": stock_code,
                "signal": SignalType.HOLD,
                "strategy": "ma_cross",
                "reason": "无交叉信号",
                "strength": 0.0,
                "price": latest['close_price'],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"均线交叉策略处理{stock_code}失败: {e}")
            return None
    
    async def _rsi_oversold_strategy(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """RSI超卖策略"""
        try:
            df = await self._get_stock_data(stock_code, 30)
            if df.empty or len(df) < 14:
                return None
            
            # 计算RSI
            delta = df['close_price'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            latest_rsi = rsi.iloc[-1]
            latest_price = df['close_price'].iloc[-1]
            
            if latest_rsi < 30:
                # 超卖
                return {
                    "stock_code": stock_code,
                    "signal": SignalType.BUY,
                    "strategy": "rsi_oversold",
                    "reason": f"RSI超卖({latest_rsi:.2f})",
                    "strength": (30 - latest_rsi) / 30,
                    "price": latest_price,
                    "timestamp": datetime.now().isoformat()
                }
            elif latest_rsi > 70:
                # 超买
                return {
                    "stock_code": stock_code,
                    "signal": SignalType.SELL,
                    "strategy": "rsi_oversold",
                    "reason": f"RSI超买({latest_rsi:.2f})",
                    "strength": (latest_rsi - 70) / 30,
                    "price": latest_price,
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "stock_code": stock_code,
                "signal": SignalType.HOLD,
                "strategy": "rsi_oversold",
                "reason": f"RSI正常({latest_rsi:.2f})",
                "strength": 0.0,
                "price": latest_price,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"RSI策略处理{stock_code}失败: {e}")
            return None
    
    async def _bollinger_bands_strategy(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """布林带策略"""
        try:
            df = await self._get_stock_data(stock_code, 30)
            if df.empty or len(df) < 20:
                return None
            
            # 计算布林带
            df['ma20'] = df['close_price'].rolling(window=20).mean()
            df['std20'] = df['close_price'].rolling(window=20).std()
            df['upper_band'] = df['ma20'] + (df['std20'] * 2)
            df['lower_band'] = df['ma20'] - (df['std20'] * 2)
            
            latest = df.iloc[-1]
            
            if latest['close_price'] <= latest['lower_band']:
                # 触及下轨
                return {
                    "stock_code": stock_code,
                    "signal": SignalType.BUY,
                    "strategy": "bollinger_bands",
                    "reason": "价格触及布林带下轨",
                    "strength": 0.6,
                    "price": latest['close_price'],
                    "timestamp": datetime.now().isoformat()
                }
            elif latest['close_price'] >= latest['upper_band']:
                # 触及上轨
                return {
                    "stock_code": stock_code,
                    "signal": SignalType.SELL,
                    "strategy": "bollinger_bands",
                    "reason": "价格触及布林带上轨",
                    "strength": 0.6,
                    "price": latest['close_price'],
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "stock_code": stock_code,
                "signal": SignalType.HOLD,
                "strategy": "bollinger_bands",
                "reason": "价格在布林带中轨附近",
                "strength": 0.0,
                "price": latest['close_price'],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"布林带策略处理{stock_code}失败: {e}")
            return None
    
    async def _volume_breakout_strategy(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """成交量突破策略"""
        try:
            df = await self._get_stock_data(stock_code, 30)
            if df.empty or len(df) < 20:
                return None
            
            # 计算成交量均值
            df['volume_ma20'] = df['volume'].rolling(window=20).mean()
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # 成交量突破且价格上涨
            volume_ratio = latest['volume'] / latest['volume_ma20']
            price_change = (latest['close_price'] - prev['close_price']) / prev['close_price']
            
            if volume_ratio > 2.0 and price_change > 0.03:
                # 放量上涨
                return {
                    "stock_code": stock_code,
                    "signal": SignalType.BUY,
                    "strategy": "volume_breakout",
                    "reason": f"放量上涨(量比{volume_ratio:.2f}, 涨幅{price_change:.2%})",
                    "strength": min(volume_ratio / 5.0, 1.0),
                    "price": latest['close_price'],
                    "timestamp": datetime.now().isoformat()
                }
            elif volume_ratio > 2.0 and price_change < -0.03:
                # 放量下跌
                return {
                    "stock_code": stock_code,
                    "signal": SignalType.SELL,
                    "strategy": "volume_breakout",
                    "reason": f"放量下跌(量比{volume_ratio:.2f}, 跌幅{price_change:.2%})",
                    "strength": min(volume_ratio / 5.0, 1.0),
                    "price": latest['close_price'],
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "stock_code": stock_code,
                "signal": SignalType.HOLD,
                "strategy": "volume_breakout",
                "reason": f"成交量正常(量比{volume_ratio:.2f})",
                "strength": 0.0,
                "price": latest['close_price'],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"成交量突破策略处理{stock_code}失败: {e}")
            return None
    
    async def _momentum_strategy(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """动量策略"""
        try:
            df = await self._get_stock_data(stock_code, 30)
            if df.empty or len(df) < 10:
                return None
            
            # 计算动量指标
            df['momentum_5'] = df['close_price'] / df['close_price'].shift(5) - 1
            df['momentum_10'] = df['close_price'] / df['close_price'].shift(10) - 1
            
            latest = df.iloc[-1]
            
            momentum_5 = latest['momentum_5']
            momentum_10 = latest['momentum_10']
            
            if momentum_5 > 0.05 and momentum_10 > 0.1:
                # 强势上涨动量
                return {
                    "stock_code": stock_code,
                    "signal": SignalType.BUY,
                    "strategy": "momentum",
                    "reason": f"强势上涨动量(5日{momentum_5:.2%}, 10日{momentum_10:.2%})",
                    "strength": min((momentum_5 + momentum_10) / 0.3, 1.0),
                    "price": latest['close_price'],
                    "timestamp": datetime.now().isoformat()
                }
            elif momentum_5 < -0.05 and momentum_10 < -0.1:
                # 强势下跌动量
                return {
                    "stock_code": stock_code,
                    "signal": SignalType.SELL,
                    "strategy": "momentum",
                    "reason": f"强势下跌动量(5日{momentum_5:.2%}, 10日{momentum_10:.2%})",
                    "strength": min(abs(momentum_5 + momentum_10) / 0.3, 1.0),
                    "price": latest['close_price'],
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "stock_code": stock_code,
                "signal": SignalType.HOLD,
                "strategy": "momentum",
                "reason": f"动量正常(5日{momentum_5:.2%}, 10日{momentum_10:.2%})",
                "strength": 0.0,
                "price": latest['close_price'],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"动量策略处理{stock_code}失败: {e}")
            return None
    
    async def _mean_reversion_strategy(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """均值回归策略"""
        try:
            df = await self._get_stock_data(stock_code, 30)
            if df.empty or len(df) < 20:
                return None
            
            # 计算价格偏离度
            df['ma20'] = df['close_price'].rolling(window=20).mean()
            df['deviation'] = (df['close_price'] - df['ma20']) / df['ma20']
            
            latest = df.iloc[-1]
            deviation = latest['deviation']
            
            if deviation < -0.1:
                # 严重低估
                return {
                    "stock_code": stock_code,
                    "signal": SignalType.BUY,
                    "strategy": "mean_reversion",
                    "reason": f"价格严重偏离均值({deviation:.2%})",
                    "strength": min(abs(deviation) / 0.2, 1.0),
                    "price": latest['close_price'],
                    "timestamp": datetime.now().isoformat()
                }
            elif deviation > 0.1:
                # 严重高估
                return {
                    "stock_code": stock_code,
                    "signal": SignalType.SELL,
                    "strategy": "mean_reversion",
                    "reason": f"价格严重偏离均值({deviation:.2%})",
                    "strength": min(deviation / 0.2, 1.0),
                    "price": latest['close_price'],
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "stock_code": stock_code,
                "signal": SignalType.HOLD,
                "strategy": "mean_reversion",
                "reason": f"价格接近均值({deviation:.2%})",
                "strength": 0.0,
                "price": latest['close_price'],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"均值回归策略处理{stock_code}失败: {e}")
            return None
    
    async def _macd_signal_strategy(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """MACD信号策略"""
        try:
            df = await self._get_stock_data(stock_code, 60)
            if df.empty or len(df) < 26:
                return None
            
            # 计算MACD
            exp1 = df['close_price'].ewm(span=12).mean()
            exp2 = df['close_price'].ewm(span=26).mean()
            df['macd'] = exp1 - exp2
            df['signal'] = df['macd'].ewm(span=9).mean()
            df['histogram'] = df['macd'] - df['signal']
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # MACD金叉死叉
            if prev['macd'] <= prev['signal'] and latest['macd'] > latest['signal']:
                # 金叉
                return {
                    "stock_code": stock_code,
                    "signal": SignalType.BUY,
                    "strategy": "macd_signal",
                    "reason": "MACD金叉",
                    "strength": 0.6,
                    "price": latest['close_price'],
                    "timestamp": datetime.now().isoformat()
                }
            elif prev['macd'] >= prev['signal'] and latest['macd'] < latest['signal']:
                # 死叉
                return {
                    "stock_code": stock_code,
                    "signal": SignalType.SELL,
                    "strategy": "macd_signal",
                    "reason": "MACD死叉",
                    "strength": 0.6,
                    "price": latest['close_price'],
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "stock_code": stock_code,
                "signal": SignalType.HOLD,
                "strategy": "macd_signal",
                "reason": "MACD无明显信号",
                "strength": 0.0,
                "price": latest['close_price'],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"MACD策略处理{stock_code}失败: {e}")
            return None
    
    async def _kdj_signal_strategy(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """KDJ信号策略"""
        try:
            df = await self._get_stock_data(stock_code, 30)
            if df.empty or len(df) < 9:
                return None
            
            # 计算KDJ
            low_min = df['low_price'].rolling(window=9).min()
            high_max = df['high_price'].rolling(window=9).max()
            
            df['rsv'] = (df['close_price'] - low_min) / (high_max - low_min) * 100
            df['k'] = df['rsv'].ewm(com=2).mean()
            df['d'] = df['k'].ewm(com=2).mean()
            df['j'] = 3 * df['k'] - 2 * df['d']
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            k_val = latest['k']
            d_val = latest['d']
            j_val = latest['j']
            
            # KDJ超卖超买
            if k_val < 20 and d_val < 20 and j_val < 0:
                # 超卖
                return {
                    "stock_code": stock_code,
                    "signal": SignalType.BUY,
                    "strategy": "kdj_signal",
                    "reason": f"KDJ超卖(K:{k_val:.1f}, D:{d_val:.1f}, J:{j_val:.1f})",
                    "strength": (20 - k_val) / 20,
                    "price": latest['close_price'],
                    "timestamp": datetime.now().isoformat()
                }
            elif k_val > 80 and d_val > 80 and j_val > 100:
                # 超买
                return {
                    "stock_code": stock_code,
                    "signal": SignalType.SELL,
                    "strategy": "kdj_signal",
                    "reason": f"KDJ超买(K:{k_val:.1f}, D:{d_val:.1f}, J:{j_val:.1f})",
                    "strength": (k_val - 80) / 20,
                    "price": latest['close_price'],
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "stock_code": stock_code,
                "signal": SignalType.HOLD,
                "strategy": "kdj_signal",
                "reason": f"KDJ正常(K:{k_val:.1f}, D:{d_val:.1f}, J:{j_val:.1f})",
                "strength": 0.0,
                "price": latest['close_price'],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"KDJ策略处理{stock_code}失败: {e}")
            return None
    
    async def _send_strategy_signals_notification(self, strategy_name: str, 
                                                signals: List[Dict[str, Any]]):
        """发送策略信号通知"""
        try:
            if not signals:
                return
            
            # 只通知强信号
            strong_signals = [s for s in signals if s.get("strength", 0) > 0.6]
            
            if strong_signals:
                content = f"策略 **{strategy_name}** 发现 {len(strong_signals)} 个强信号:\n\n"
                
                for signal in strong_signals[:5]:  # 最多显示5个
                    content += f"- **{signal['stock_code']}**: {signal['signal'].value} "
                    content += f"({signal['reason']}, 强度: {signal['strength']:.2f})\n"
                
                if len(strong_signals) > 5:
                    content += f"\n还有 {len(strong_signals) - 5} 个信号..."
                
                await self.notification_service.send_strategy_alert_notification(
                    strategy_name=strategy_name,
                    alert_message=content
                )
                
        except Exception as e:
            logger.error(f"发送策略信号通知失败: {e}")