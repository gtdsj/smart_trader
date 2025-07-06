# -*- coding: utf-8 -*-
"""
指标管理服务模块
提供技术指标和基本面指标的统一管理和计算功能
"""

import traceback
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
import pandas as pd
import numpy as np
from loguru import logger

from config import get_settings
from core.cache_adapter import get_cache_client


class IndicatorCategory(Enum):
    """指标分类枚举"""
    TECHNICAL = "technical"  # 技术指标
    FUNDAMENTAL = "fundamental"  # 基本面指标
    MARKET = "market"  # 市场指标
    CUSTOM = "custom"  # 自定义指标


class IndicatorType(Enum):
    """指标类型枚举"""
    TREND = "trend"  # 趋势指标
    MOMENTUM = "momentum"  # 动量指标
    VOLATILITY = "volatility"  # 波动率指标
    VOLUME = "volume"  # 成交量指标
    SUPPORT_RESISTANCE = "support_resistance"  # 支撑阻力指标
    VALUATION = "valuation"  # 估值指标
    PROFITABILITY = "profitability"  # 盈利能力指标
    GROWTH = "growth"  # 成长性指标
    FINANCIAL_HEALTH = "financial_health"  # 财务健康指标


class IndicatorManager:
    """指标管理器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.cache_client = get_cache_client()
        
        # 技术指标定义
        self.technical_indicators = {
            # 趋势指标
            "ma": {
                "name": "移动平均线",
                "description": "简单移动平均线，用于判断价格趋势",
                "category": IndicatorCategory.TECHNICAL.value,
                "type": IndicatorType.TREND.value,
                "parameters": {
                    "period": {"type": "int", "default": 20, "min": 1, "max": 250, "description": "计算周期"}
                },
                "calculator": self._calculate_ma
            },
            "ema": {
                "name": "指数移动平均线",
                "description": "指数移动平均线，对近期价格赋予更高权重",
                "category": IndicatorCategory.TECHNICAL.value,
                "type": IndicatorType.TREND.value,
                "parameters": {
                    "period": {"type": "int", "default": 12, "min": 1, "max": 250, "description": "计算周期"}
                },
                "calculator": self._calculate_ema
            },
            "rsi": {
                "name": "相对强弱指数",
                "description": "衡量价格变动速度和变化的动量振荡器",
                "category": IndicatorCategory.TECHNICAL.value,
                "type": IndicatorType.MOMENTUM.value,
                "parameters": {
                    "period": {"type": "int", "default": 14, "min": 2, "max": 100, "description": "计算周期"}
                },
                "calculator": self._calculate_rsi
            },
            "macd": {
                "name": "MACD指标",
                "description": "移动平均收敛散度指标，用于判断趋势变化",
                "category": IndicatorCategory.TECHNICAL.value,
                "type": IndicatorType.MOMENTUM.value,
                "parameters": {
                    "fast_period": {"type": "int", "default": 12, "min": 1, "max": 50, "description": "快线周期"},
                    "slow_period": {"type": "int", "default": 26, "min": 1, "max": 100, "description": "慢线周期"},
                    "signal_period": {"type": "int", "default": 9, "min": 1, "max": 50, "description": "信号线周期"}
                },
                "calculator": self._calculate_macd
            },
            "kdj": {
                "name": "KDJ指标",
                "description": "随机指标，用于判断超买超卖状态",
                "category": IndicatorCategory.TECHNICAL.value,
                "type": IndicatorType.MOMENTUM.value,
                "parameters": {
                    "period": {"type": "int", "default": 9, "min": 1, "max": 50, "description": "计算周期"},
                    "k_period": {"type": "int", "default": 3, "min": 1, "max": 10, "description": "K值平滑周期"},
                    "d_period": {"type": "int", "default": 3, "min": 1, "max": 10, "description": "D值平滑周期"}
                },
                "calculator": self._calculate_kdj
            },
            "bollinger": {
                "name": "布林带",
                "description": "基于移动平均线和标准差的波动率指标",
                "category": IndicatorCategory.TECHNICAL.value,
                "type": IndicatorType.VOLATILITY.value,
                "parameters": {
                    "period": {"type": "int", "default": 20, "min": 2, "max": 100, "description": "计算周期"},
                    "std_dev": {"type": "float", "default": 2.0, "min": 0.1, "max": 5.0, "description": "标准差倍数"}
                },
                "calculator": self._calculate_bollinger
            },
            "volume": {
                "name": "成交量",
                "description": "股票交易的成交量指标",
                "category": IndicatorCategory.TECHNICAL.value,
                "type": IndicatorType.VOLUME.value,
                "parameters": {},
                "calculator": self._calculate_volume
            },
            "volume_ma": {
                "name": "成交量移动平均",
                "description": "成交量的移动平均线",
                "category": IndicatorCategory.TECHNICAL.value,
                "type": IndicatorType.VOLUME.value,
                "parameters": {
                    "period": {"type": "int", "default": 20, "min": 1, "max": 250, "description": "计算周期"}
                },
                "calculator": self._calculate_volume_ma
            },
            "turnover_rate": {
                "name": "换手率",
                "description": "股票换手率指标",
                "category": IndicatorCategory.TECHNICAL.value,
                "type": IndicatorType.VOLUME.value,
                "parameters": {},
                "calculator": self._calculate_turnover_rate
            },
            "price_change": {
                "name": "价格变化",
                "description": "价格绝对变化量",
                "category": IndicatorCategory.TECHNICAL.value,
                "type": IndicatorType.TREND.value,
                "parameters": {},
                "calculator": self._calculate_price_change
            },
            "price_change_pct": {
                "name": "价格变化百分比",
                "description": "价格相对变化百分比",
                "category": IndicatorCategory.TECHNICAL.value,
                "type": IndicatorType.TREND.value,
                "parameters": {},
                "calculator": self._calculate_price_change_pct
            },
            "atr": {
                "name": "平均真实波幅",
                "description": "衡量价格波动性的指标",
                "category": IndicatorCategory.TECHNICAL.value,
                "type": IndicatorType.VOLATILITY.value,
                "parameters": {
                    "period": {"type": "int", "default": 14, "min": 1, "max": 100, "description": "计算周期"}
                },
                "calculator": self._calculate_atr
            },
            "obv": {
                "name": "能量潮指标",
                "description": "基于成交量的累积指标",
                "category": IndicatorCategory.TECHNICAL.value,
                "type": IndicatorType.VOLUME.value,
                "parameters": {},
                "calculator": self._calculate_obv
            }
        }
        
        # 基本面指标定义
        self.fundamental_indicators = {
            "pe_ratio": {
                "name": "市盈率",
                "description": "股价与每股收益的比率",
                "category": IndicatorCategory.FUNDAMENTAL.value,
                "type": IndicatorType.VALUATION.value,
                "parameters": {},
                "calculator": self._calculate_pe_ratio
            },
            "pb_ratio": {
                "name": "市净率",
                "description": "股价与每股净资产的比率",
                "category": IndicatorCategory.FUNDAMENTAL.value,
                "type": IndicatorType.VALUATION.value,
                "parameters": {},
                "calculator": self._calculate_pb_ratio
            },
            "market_cap": {
                "name": "市值",
                "description": "公司的市场价值",
                "category": IndicatorCategory.FUNDAMENTAL.value,
                "type": IndicatorType.VALUATION.value,
                "parameters": {},
                "calculator": self._calculate_market_cap
            },
            "revenue_growth": {
                "name": "营收增长率",
                "description": "营业收入同比增长率",
                "category": IndicatorCategory.FUNDAMENTAL.value,
                "type": IndicatorType.GROWTH.value,
                "parameters": {
                    "period": {"type": "str", "default": "yoy", "options": ["yoy", "qoq"], "description": "增长周期"}
                },
                "calculator": self._calculate_revenue_growth
            },
            "profit_growth": {
                "name": "利润增长率",
                "description": "净利润同比增长率",
                "category": IndicatorCategory.FUNDAMENTAL.value,
                "type": IndicatorType.GROWTH.value,
                "parameters": {
                    "period": {"type": "str", "default": "yoy", "options": ["yoy", "qoq"], "description": "增长周期"}
                },
                "calculator": self._calculate_profit_growth
            },
            "roe": {
                "name": "净资产收益率",
                "description": "净利润与股东权益的比率",
                "category": IndicatorCategory.FUNDAMENTAL.value,
                "type": IndicatorType.PROFITABILITY.value,
                "parameters": {},
                "calculator": self._calculate_roe
            },
            "debt_ratio": {
                "name": "负债率",
                "description": "总负债与总资产的比率",
                "category": IndicatorCategory.FUNDAMENTAL.value,
                "type": IndicatorType.FINANCIAL_HEALTH.value,
                "parameters": {},
                "calculator": self._calculate_debt_ratio
            },
            "current_ratio": {
                "name": "流动比率",
                "description": "流动资产与流动负债的比率",
                "category": IndicatorCategory.FUNDAMENTAL.value,
                "type": IndicatorType.FINANCIAL_HEALTH.value,
                "parameters": {},
                "calculator": self._calculate_current_ratio
            },
            "quick_ratio": {
                "name": "速动比率",
                "description": "速动资产与流动负债的比率",
                "category": IndicatorCategory.FUNDAMENTAL.value,
                "type": IndicatorType.FINANCIAL_HEALTH.value,
                "parameters": {},
                "calculator": self._calculate_quick_ratio
            }
        }
        
        # 合并所有指标
        self.all_indicators = {**self.technical_indicators, **self.fundamental_indicators}
    
    def get_indicators_by_category(self, category: str) -> Dict[str, Any]:
        """根据分类获取指标"""
        if category == IndicatorCategory.TECHNICAL.value:
            return self.technical_indicators
        elif category == IndicatorCategory.FUNDAMENTAL.value:
            return self.fundamental_indicators
        else:
            return {}
    
    def get_indicators_by_type(self, indicator_type: str) -> Dict[str, Any]:
        """根据类型获取指标"""
        result = {}
        for key, indicator in self.all_indicators.items():
            if indicator["type"] == indicator_type:
                result[key] = indicator
        return result
    
    def get_indicator_info(self, indicator_name: str) -> Optional[Dict[str, Any]]:
        """获取指标信息"""
        return self.all_indicators.get(indicator_name)
    
    def get_all_indicators(self) -> Dict[str, Any]:
        """获取所有指标"""
        return {
            "technical": {k: {"name": v["name"], "description": v["description"], 
                             "type": v["type"], "parameters": v["parameters"]} 
                         for k, v in self.technical_indicators.items()},
            "fundamental": {k: {"name": v["name"], "description": v["description"], 
                               "type": v["type"], "parameters": v["parameters"]} 
                           for k, v in self.fundamental_indicators.items()}
        }
    
    def calculate_indicator(self, indicator_name: str, df: pd.DataFrame, 
                          parameters: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """计算指标"""
        try:
            indicator_info = self.get_indicator_info(indicator_name)
            if not indicator_info:
                raise ValueError(f"未知的指标: {indicator_name}")
            
            calculator = indicator_info["calculator"]
            if parameters is None:
                # 使用默认参数
                parameters = {}
                for param_name, param_info in indicator_info["parameters"].items():
                    parameters[param_name] = param_info["default"]
            
            return calculator(df, parameters)
            
        except Exception as e:
            logger.error(f"计算指标{indicator_name}失败: {e}, {traceback.format_exc()}")
            return df
    
    def validate_indicator_parameters(self, indicator_name: str, 
                                    parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证指标参数"""
        try:
            indicator_info = self.get_indicator_info(indicator_name)
            if not indicator_info:
                return {"valid": False, "message": f"未知的指标: {indicator_name}"}
            
            param_definitions = indicator_info["parameters"]
            validated_params = {}
            
            for param_name, param_def in param_definitions.items():
                if param_name in parameters:
                    value = parameters[param_name]
                    param_type = param_def["type"]
                    
                    # 类型验证
                    if param_type == "int":
                        if not isinstance(value, int):
                            try:
                                value = int(value)
                            except ValueError:
                                return {"valid": False, "message": f"参数{param_name}必须是整数"}
                        
                        # 范围验证
                        if "min" in param_def and value < param_def["min"]:
                            return {"valid": False, "message": f"参数{param_name}不能小于{param_def['min']}"}
                        if "max" in param_def and value > param_def["max"]:
                            return {"valid": False, "message": f"参数{param_name}不能大于{param_def['max']}"}
                    
                    elif param_type == "float":
                        if not isinstance(value, (int, float)):
                            try:
                                value = float(value)
                            except ValueError:
                                return {"valid": False, "message": f"参数{param_name}必须是数字"}
                        
                        # 范围验证
                        if "min" in param_def and value < param_def["min"]:
                            return {"valid": False, "message": f"参数{param_name}不能小于{param_def['min']}"}
                        if "max" in param_def and value > param_def["max"]:
                            return {"valid": False, "message": f"参数{param_name}不能大于{param_def['max']}"}
                    
                    elif param_type == "str":
                        if not isinstance(value, str):
                            return {"valid": False, "message": f"参数{param_name}必须是字符串"}
                        
                        # 选项验证
                        if "options" in param_def and value not in param_def["options"]:
                            return {"valid": False, "message": f"参数{param_name}必须是{param_def['options']}中的一个"}
                    
                    validated_params[param_name] = value
                else:
                    # 使用默认值
                    if "default" in param_def:
                        validated_params[param_name] = param_def["default"]
            
            return {"valid": True, "parameters": validated_params}
            
        except Exception as e:
            return {"valid": False, "message": f"参数验证失败: {str(e)}"}
    
    # 技术指标计算函数
    def _calculate_ma(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算移动平均线"""
        period = params.get("period", 20)
        df[f'ma_{period}'] = df['close_price'].rolling(window=period).mean()
        return df
    
    def _calculate_ema(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算指数移动平均线"""
        period = params.get("period", 12)
        df[f'ema_{period}'] = df['close_price'].ewm(span=period).mean()
        return df
    
    def _calculate_rsi(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算RSI指标"""
        period = params.get("period", 14)
        delta = df['close_price'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        return df
    
    def _calculate_macd(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算MACD指标"""
        fast_period = params.get("fast_period", 12)
        slow_period = params.get("slow_period", 26)
        signal_period = params.get("signal_period", 9)
        
        ema_fast = df['close_price'].ewm(span=fast_period).mean()
        ema_slow = df['close_price'].ewm(span=slow_period).mean()
        
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=signal_period).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        return df
    
    def _calculate_kdj(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算KDJ指标"""
        period = params.get("period", 9)
        k_period = params.get("k_period", 3)
        d_period = params.get("d_period", 3)
        
        low_min = df['low_price'].rolling(window=period).min()
        high_max = df['high_price'].rolling(window=period).max()
        
        rsv = (df['close_price'] - low_min) / (high_max - low_min) * 100
        df['k'] = rsv.ewm(alpha=1/k_period).mean()
        df['d'] = df['k'].ewm(alpha=1/d_period).mean()
        df['j'] = 3 * df['k'] - 2 * df['d']
        
        return df
    
    def _calculate_bollinger(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算布林带"""
        period = params.get("period", 20)
        std_dev = params.get("std_dev", 2.0)
        
        df['bb_middle'] = df['close_price'].rolling(window=period).mean()
        bb_std = df['close_price'].rolling(window=period).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * std_dev)
        df['bb_lower'] = df['bb_middle'] - (bb_std * std_dev)
        df['bb_width'] = df['bb_upper'] - df['bb_lower']
        df['bb_position'] = (df['close_price'] - df['bb_lower']) / df['bb_width']
        
        return df
    
    def _calculate_volume(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算成交量指标"""
        # 成交量已经在原始数据中，这里可以添加一些衍生指标
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(window=20).mean()
        return df
    
    def _calculate_volume_ma(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算成交量移动平均"""
        period = params.get("period", 20)
        df[f'volume_ma_{period}'] = df['volume'].rolling(window=period).mean()
        return df
    
    def _calculate_turnover_rate(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算换手率指标"""
        # 换手率已经在原始数据中，这里可以添加一些衍生指标
        df['turnover_ma'] = df['turnover_rate'].rolling(window=20).mean()
        return df
    
    def _calculate_price_change(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算价格变化"""
        df['price_change'] = df['close_price'].diff()
        return df
    
    def _calculate_price_change_pct(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算价格变化百分比"""
        df['price_change_pct'] = df['close_price'].pct_change() * 100
        return df
    
    def _calculate_atr(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算平均真实波幅"""
        period = params.get("period", 14)
        
        high_low = df['high_price'] - df['low_price']
        high_close = np.abs(df['high_price'] - df['close_price'].shift())
        low_close = np.abs(df['low_price'] - df['close_price'].shift())
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        df['atr'] = true_range.rolling(window=period).mean()
        
        return df
    
    def _calculate_obv(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算能量潮指标"""
        obv = [0]
        for i in range(1, len(df)):
            if df['close_price'].iloc[i] > df['close_price'].iloc[i-1]:
                obv.append(obv[-1] + df['volume'].iloc[i])
            elif df['close_price'].iloc[i] < df['close_price'].iloc[i-1]:
                obv.append(obv[-1] - df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        
        df['obv'] = obv
        return df
    
    # 基本面指标计算函数（这些通常需要从外部数据源获取）
    def _calculate_pe_ratio(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算市盈率"""
        # 如果数据中已有PE比率，直接使用；否则需要从基本面数据计算
        if 'pe_ratio' not in df.columns:
            # 这里需要从基本面数据源获取每股收益数据
            logger.warning("PE比率数据不可用，需要从基本面数据源获取")
        return df
    
    def _calculate_pb_ratio(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算市净率"""
        # 如果数据中已有PB比率，直接使用；否则需要从基本面数据计算
        if 'pb_ratio' not in df.columns:
            logger.warning("PB比率数据不可用，需要从基本面数据源获取")
        return df
    
    def _calculate_market_cap(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算市值"""
        # 市值 = 股价 * 总股本，需要获取总股本数据
        logger.warning("市值计算需要总股本数据")
        return df
    
    def _calculate_revenue_growth(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算营收增长率"""
        # 需要从财务报表数据计算
        logger.warning("营收增长率计算需要财务报表数据")
        return df
    
    def _calculate_profit_growth(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算利润增长率"""
        # 需要从财务报表数据计算
        logger.warning("利润增长率计算需要财务报表数据")
        return df
    
    def _calculate_roe(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算净资产收益率"""
        # 需要从财务报表数据计算
        logger.warning("ROE计算需要财务报表数据")
        return df
    
    def _calculate_debt_ratio(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算负债率"""
        # 需要从财务报表数据计算
        logger.warning("负债率计算需要财务报表数据")
        return df
    
    def _calculate_current_ratio(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算流动比率"""
        # 需要从财务报表数据计算
        logger.warning("流动比率计算需要财务报表数据")
        return df
    
    def _calculate_quick_ratio(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """计算速动比率"""
        # 需要从财务报表数据计算
        logger.warning("速动比率计算需要财务报表数据")
        return df
    
    def register_custom_indicator(self, name: str, indicator_info: Dict[str, Any]):
        """注册自定义指标"""
        try:
            # 验证指标信息
            required_fields = ["name", "description", "category", "type", "parameters", "calculator"]
            for field in required_fields:
                if field not in indicator_info:
                    raise ValueError(f"缺少必填字段: {field}")
            
            # 验证计算函数
            if not callable(indicator_info["calculator"]):
                raise ValueError("calculator必须是可调用的函数")
            
            # 注册指标
            self.all_indicators[name] = indicator_info
            
            # 根据分类添加到对应的指标字典
            if indicator_info["category"] == IndicatorCategory.TECHNICAL.value:
                self.technical_indicators[name] = indicator_info
            elif indicator_info["category"] == IndicatorCategory.FUNDAMENTAL.value:
                self.fundamental_indicators[name] = indicator_info
            
            logger.info(f"成功注册自定义指标: {name}")
            return True
            
        except Exception as e:
            logger.error(f"注册自定义指标失败: {e}")
            return False