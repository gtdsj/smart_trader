#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化交易系统配置模块 - 简化版本
支持从JSON文件和环境变量读取配置
不依赖Pydantic，兼容Python 3.6+
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any


class DatabaseConfig:
    """数据库配置"""
    
    def __init__(self, **kwargs):
        self.type = kwargs.get('type', 'duckdb')
        self.path = kwargs.get('path', 'data/smart_trader.db')
        self.memory = kwargs.get('memory', False)
    
    @property
    def url(self) -> str:
        if self.type == "duckdb":
            if self.memory:
                return "duckdb:///:memory:"
            else:
                return f"duckdb:///{self.path}"
        else:
            raise ValueError(f"不支持的数据库类型: {self.type}")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type,
            'path': self.path,
            'memory': self.memory
        }


# Redis配置已移除，本地运行不需要Redis


class XtQuantConfig:
    """XtQuant配置"""
    
    def __init__(self, **kwargs):
        self.path = kwargs.get('path', 'D:\\迅投极速交易终端 睿智融科版\\userdata_mini')
        self.session_id = kwargs.get('session_id', 123456)
        self.account_id = kwargs.get('account_id', '1000000365')
        self.account_type = kwargs.get('account_type', 'STOCK')
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'path': self.path,
            'session_id': self.session_id,
            'account_id': self.account_id,
            'account_type': self.account_type
        }


class DingTalkConfig:
    """钉钉机器人配置"""
    
    def __init__(self, **kwargs):
        self.webhook_url = kwargs.get('webhook_url', '')
        self.secret = kwargs.get('secret')
        self.enabled = kwargs.get('enabled', False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'webhook_url': self.webhook_url,
            'secret': self.secret,
            'enabled': self.enabled
        }


class TradingConfig:
    """交易配置"""
    
    def __init__(self, **kwargs):
        self.max_position_ratio = kwargs.get('max_position_ratio', 0.95)
        self.max_single_stock_ratio = kwargs.get('max_single_stock_ratio', 0.1)
        self.stop_loss_ratio = kwargs.get('stop_loss_ratio', 0.05)
        self.take_profit_ratio = kwargs.get('take_profit_ratio', 0.15)
        self.min_trade_amount = kwargs.get('min_trade_amount', 1000.0)
        self.commission_rate = kwargs.get('commission_rate', 0.0003)
        self.slippage_rate = kwargs.get('slippage_rate', 0.001)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'max_position_ratio': self.max_position_ratio,
            'max_single_stock_ratio': self.max_single_stock_ratio,
            'stop_loss_ratio': self.stop_loss_ratio,
            'take_profit_ratio': self.take_profit_ratio,
            'min_trade_amount': self.min_trade_amount,
            'commission_rate': self.commission_rate,
            'slippage_rate': self.slippage_rate
        }


class BacktestConfig:
    """回测配置"""
    
    def __init__(self, **kwargs):
        self.initial_cash = kwargs.get('initial_cash', 1000000.0)
        self.start_date = kwargs.get('start_date', '2020-01-01')
        self.end_date = kwargs.get('end_date', '2023-12-31')
        self.benchmark = kwargs.get('benchmark', '000300.SH')
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'initial_cash': self.initial_cash,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'benchmark': self.benchmark
        }


class SystemConfig:
    """系统主配置"""
    
    def __init__(self, **kwargs):
        # 基础配置
        self.app_name = kwargs.get('app_name', 'Smart Trader')
        self.version = kwargs.get('version', '1.0.0')
        self.debug = kwargs.get('debug', True)
        self.log_level = kwargs.get('log_level', 'INFO')
        
        # API配置
        self.api_host = kwargs.get('api_host', '0.0.0.0')
        self.api_port = kwargs.get('api_port', 8000)
        
        # 子配置
        db_config = kwargs.get('database', {})
        self.database = DatabaseConfig(**db_config)
        
        # Redis配置已移除，本地运行不需要Redis
        
        xtquant_config = kwargs.get('xtquant', {})
        self.xtquant = XtQuantConfig(**xtquant_config)
        
        dingtalk_config = kwargs.get('dingtalk', {})
        self.dingtalk = DingTalkConfig(**dingtalk_config)
        
        trading_config = kwargs.get('trading', {})
        self.trading = TradingConfig(**trading_config)
        
        backtest_config = kwargs.get('backtest', {})
        self.backtest = BacktestConfig(**backtest_config)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'app_name': self.app_name,
            'version': self.version,
            'debug': self.debug,
            'log_level': self.log_level,
            'api_host': self.api_host,
            'api_port': self.api_port,
            'database': self.database.to_dict(),
            # 'redis': self.redis.to_dict(),  # Redis配置已移除
            'xtquant': self.xtquant.to_dict(),
            'dingtalk': self.dingtalk.to_dict(),
            'trading': self.trading.to_dict(),
            'backtest': self.backtest.to_dict()
        }


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self._config: Optional[SystemConfig] = None
    
    def load_config(self) -> SystemConfig:
        """加载配置"""
        if self._config is not None:
            return self._config
        
        # 默认配置
        config_data = {}
        
        # 1. 尝试从JSON文件加载
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                print(f"已从 {self.config_file} 加载配置")
            except Exception as e:
                print(f"加载配置文件失败: {e}，使用默认配置")
        
        # 2. 从环境变量覆盖配置
        config_data = self._load_from_env(config_data)
        
        # 3. 创建配置对象
        self._config = SystemConfig(**config_data)
        return self._config
    
    def _load_from_env(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """从环境变量加载配置"""
        env_mapping = {
            # 系统配置
            'APP_NAME': ['app_name'],
            'VERSION': ['version'],
            'DEBUG': ['debug'],
            'LOG_LEVEL': ['log_level'],
            'API_HOST': ['api_host'],
            'API_PORT': ['api_port'],
            
            # 数据库配置
            'DB_HOST': ['database', 'host'],
            'DB_PORT': ['database', 'port'],
            'DB_USERNAME': ['database', 'username'],
            'DB_PASSWORD': ['database', 'password'],
            'DB_DATABASE': ['database', 'database'],
            
            # Redis配置
            'REDIS_HOST': ['redis', 'host'],
            'REDIS_PORT': ['redis', 'port'],
            'REDIS_PASSWORD': ['redis', 'password'],
            'REDIS_DB': ['redis', 'db'],
            
            # XtQuant配置
            'XTQUANT_PATH': ['xtquant', 'path'],
            'XTQUANT_SESSION_ID': ['xtquant', 'session_id'],
            'XTQUANT_ACCOUNT_ID': ['xtquant', 'account_id'],
            'XTQUANT_ACCOUNT_TYPE': ['xtquant', 'account_type'],
            
            # 钉钉配置
            'DINGTALK_WEBHOOK_URL': ['dingtalk', 'webhook_url'],
            'DINGTALK_SECRET': ['dingtalk', 'secret'],
            'DINGTALK_ENABLED': ['dingtalk', 'enabled'],
            
            # 交易配置
            'TRADING_MAX_POSITION_RATIO': ['trading', 'max_position_ratio'],
            'TRADING_MAX_SINGLE_STOCK_RATIO': ['trading', 'max_single_stock_ratio'],
            'TRADING_STOP_LOSS_RATIO': ['trading', 'stop_loss_ratio'],
            'TRADING_TAKE_PROFIT_RATIO': ['trading', 'take_profit_ratio'],
            'TRADING_MIN_TRADE_AMOUNT': ['trading', 'min_trade_amount'],
            'TRADING_COMMISSION_RATE': ['trading', 'commission_rate'],
            'TRADING_SLIPPAGE_RATE': ['trading', 'slippage_rate'],
            
            # 回测配置
            'BACKTEST_INITIAL_CASH': ['backtest', 'initial_cash'],
            'BACKTEST_START_DATE': ['backtest', 'start_date'],
            'BACKTEST_END_DATE': ['backtest', 'end_date'],
            'BACKTEST_BENCHMARK': ['backtest', 'benchmark'],
        }
        
        for env_key, config_path in env_mapping.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                # 类型转换
                if env_key.endswith('_PORT') or env_key.endswith('_SESSION_ID') or env_key.endswith('_DB'):
                    env_value = int(env_value)
                elif env_key.endswith('_DEBUG') or env_key.endswith('_ENABLED'):
                    env_value = env_value.lower() in ('true', '1', 'yes', 'on')
                elif env_key.startswith('TRADING_') or env_key.startswith('BACKTEST_'):
                    if env_key.endswith('_RATIO') or env_key.endswith('_RATE') or env_key.endswith('_AMOUNT') or env_key.endswith('_CASH'):
                        env_value = float(env_value)
                
                # 设置嵌套配置
                current = config_data
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[config_path[-1]] = env_value
        
        return config_data
    
    def save_config(self, config: SystemConfig) -> bool:
        """保存配置到JSON文件"""
        try:
            config_dict = config.to_dict()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, ensure_ascii=False, indent=2)
            print(f"配置已保存到 {self.config_file}")
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def create_default_config(self) -> bool:
        """创建默认配置文件"""
        default_config = SystemConfig()
        return self.save_config(default_config)
    
    def reload_config(self) -> SystemConfig:
        """重新加载配置"""
        self._config = None
        return self.load_config()


# 全局配置管理器
config_manager = ConfigManager()

# 全局配置实例
settings = config_manager.load_config()


def get_settings() -> SystemConfig:
    """获取配置实例"""
    return settings


def reload_settings() -> SystemConfig:
    """重新加载配置"""
    global settings
    settings = config_manager.reload_config()
    return settings


def save_settings(config: SystemConfig) -> bool:
    """保存配置"""
    return config_manager.save_config(config)


def create_default_config_file() -> bool:
    """创建默认配置文件"""
    return config_manager.create_default_config()