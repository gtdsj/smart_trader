#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化交易系统配置模块
支持从JSON文件和环境变量读取配置
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    # 兼容旧版本pydantic
    from pydantic import BaseSettings
    SettingsConfigDict = None


class DatabaseConfig(BaseModel):
    """数据库配置"""
    host: str = Field(default="localhost", description="数据库主机")
    port: int = Field(default=5432, description="数据库端口")
    username: str = Field(default="postgres", description="数据库用户名")
    password: str = Field(default="password", description="数据库密码")
    database: str = Field(default="smart_trader", description="数据库名称")
    # DuckDB配置
    memory: bool = Field(default=False, description="是否使用内存数据库")
    path: str = Field(default="data/smart_trader.db", description="数据库文件路径")
    
    @property
    def url(self) -> str:
        if self.memory:
            return "duckdb:///:memory:"
        else:
            # 确保路径使用正斜杠，避免编码问题
            import os
            normalized_path = os.path.abspath(self.path).replace('\\', '/')
            return f"duckdb:///{normalized_path}"


# Redis配置已移除，使用本地缓存替代


class XtQuantConfig(BaseModel):
    """XtQuant配置"""
    path: str = Field(default="D:\\迅投极速交易终端 睿智融科版\\userdata_mini", description="MiniQMT客户端路径")
    session_id: int = Field(default=123456, description="会话编号")
    account_id: str = Field(default="1000000365", description="资金账号")
    account_type: str = Field(default="STOCK", description="账号类型")
    mock_mode: bool = Field(default=False, description="是否使用模拟模式")


class DingTalkConfig(BaseModel):
    """钉钉机器人配置"""
    webhook_url: str = Field(default="", description="钉钉机器人Webhook地址")
    secret: Optional[str] = Field(default=None, description="钉钉机器人密钥")
    enabled: bool = Field(default=False, description="是否启用钉钉通知")


class FeishuConfig(BaseModel):
    """飞书机器人配置"""
    app_id: str = Field(default="", description="飞书应用ID")
    app_secret: str = Field(default="", description="飞书应用密钥")
    enabled: bool = Field(default=False, description="是否启用飞书机器人")


class TradingConfig(BaseModel):
    """交易配置"""
    max_position_ratio: float = Field(default=0.95, description="最大仓位比例")
    max_single_stock_ratio: float = Field(default=0.1, description="单只股票最大仓位比例")
    stop_loss_ratio: float = Field(default=0.05, description="止损比例")
    take_profit_ratio: float = Field(default=0.15, description="止盈比例")
    min_trade_amount: float = Field(default=1000.0, description="最小交易金额")
    commission_rate: float = Field(default=0.0003, description="手续费率")
    slippage_rate: float = Field(default=0.001, description="滑点率")


class BacktestConfig(BaseModel):
    """回测配置"""
    initial_cash: float = Field(default=1000000.0, description="初始资金")
    start_date: str = Field(default="2020-01-01", description="回测开始日期")
    end_date: str = Field(default="2023-12-31", description="回测结束日期")
    benchmark: str = Field(default="000300.SH", description="基准指数")


class SystemConfig(BaseModel):
    """系统主配置"""
    # 基础配置
    app_name: str = Field(default="Smart Trader", description="应用名称")
    version: str = Field(default="1.0.0", description="版本号")
    debug: bool = Field(default=True, description="调试模式")
    log_level: str = Field(default="INFO", description="日志级别")
    log_dir: str = Field(default="logs", description="日志文件目录")
    log_file_prefix: str = Field(default="app", description="日志文件前缀")
    max_log_files: int = Field(default=30, description="最大日志文件数", ge=1, le=365)
    simulation_mode: bool = Field(default=False, description="是否启用模拟模式")
    
    # API配置
    api_host: str = Field(default="0.0.0.0", description="API主机")
    api_port: int = Field(default=8000, description="API端口")
    
    # 子配置
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    # redis: RedisConfig = Field(default_factory=RedisConfig)  # 已移除Redis配置
    xtquant: XtQuantConfig = Field(default_factory=XtQuantConfig)
    dingtalk: DingTalkConfig = Field(default_factory=DingTalkConfig)
    feishu: FeishuConfig = Field(default_factory=FeishuConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)


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
            'LOG_DIR': ['log_dir'],
            'LOG_FILE_PREFIX': ['log_file_prefix'],
            'MAX_LOG_FILES': ['max_log_files'],
            'API_HOST': ['api_host'],
            'API_PORT': ['api_port'],
            
            # 数据库配置
            'DB_HOST': ['database', 'host'],
            'DB_PORT': ['database', 'port'],
            'DB_USERNAME': ['database', 'username'],
            'DB_PASSWORD': ['database', 'password'],
            'DB_DATABASE': ['database', 'database'],
            'DB_MEMORY': ['database', 'memory'],
            'DB_PATH': ['database', 'path'],
            
            # Redis配置已移除
    # 'REDIS_HOST': ['redis', 'host'],
    # 'REDIS_PORT': ['redis', 'port'],
    # 'REDIS_PASSWORD': ['redis', 'password'],
    # 'REDIS_DB': ['redis', 'db'],
            
            # XtQuant配置
            'XTQUANT_PATH': ['xtquant', 'path'],
            'XTQUANT_SESSION_ID': ['xtquant', 'session_id'],
            'XTQUANT_ACCOUNT_ID': ['xtquant', 'account_id'],
            'XTQUANT_ACCOUNT_TYPE': ['xtquant', 'account_type'],
            
            # 钉钉配置
            'DINGTALK_WEBHOOK_URL': ['dingtalk', 'webhook_url'],
            'DINGTALK_SECRET': ['dingtalk', 'secret'],
            'DINGTALK_ENABLED': ['dingtalk', 'enabled'],
            
            # 飞书配置
            'FEISHU_APP_ID': ['feishu', 'app_id'],
            'FEISHU_APP_SECRET': ['feishu', 'app_secret'],
            'FEISHU_ENABLED': ['feishu', 'enabled'],
            
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
                elif env_key.endswith('_DEBUG') or env_key.endswith('_ENABLED') or env_key.endswith('_MEMORY'):
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
            config_dict = config.dict()
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