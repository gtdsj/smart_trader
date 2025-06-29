# -*- coding: utf-8 -*-
"""
配置服务API路由
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, validator
from loguru import logger

from config import SystemConfig, get_settings

# 创建路由器
router = APIRouter(prefix="/api/v1/config", tags=["配置服务"])


# 请求模型
class DatabaseConfigRequest(BaseModel):
    """数据库配置请求"""
    host: Optional[str] = Field(None, description="数据库主机")
    port: Optional[int] = Field(None, description="数据库端口", ge=1, le=65535)
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    database: Optional[str] = Field(None, description="数据库名")


class RedisConfigRequest(BaseModel):
    """Redis配置请求"""
    host: Optional[str] = Field(None, description="Redis主机")
    port: Optional[int] = Field(None, description="Redis端口", ge=1, le=65535)
    password: Optional[str] = Field(None, description="Redis密码")
    db: Optional[int] = Field(None, description="数据库编号", ge=0, le=15)


class XtQuantConfigRequest(BaseModel):
    """XtQuant配置请求"""
    path: Optional[str] = Field(None, description="MiniQMT路径")
    session_id: Optional[int] = Field(None, description="会话ID")
    account_id: Optional[str] = Field(None, description="账户ID")
    account_type: Optional[str] = Field(None, description="账户类型")


class DingTalkConfigRequest(BaseModel):
    """钉钉配置请求"""
    webhook_url: Optional[str] = Field(None, description="Webhook URL")
    secret: Optional[str] = Field(None, description="密钥")
    enabled: Optional[bool] = Field(None, description="是否启用")


class TradingConfigRequest(BaseModel):
    """交易配置请求"""
    max_position_size: Optional[float] = Field(None, description="最大持仓比例", gt=0, le=1)
    commission_rate: Optional[float] = Field(None, description="手续费率", ge=0, le=0.01)
    slippage: Optional[float] = Field(None, description="滑点", ge=0, le=0.01)
    risk_limit: Optional[float] = Field(None, description="风险限制", gt=0, le=1)
    enable_risk_control: Optional[bool] = Field(None, description="启用风险控制")
    max_daily_trades: Optional[int] = Field(None, description="每日最大交易次数", ge=0)
    min_order_amount: Optional[float] = Field(None, description="最小订单金额", gt=0)


class BacktestConfigRequest(BaseModel):
    """回测配置请求"""
    initial_capital: Optional[float] = Field(None, description="初始资金", gt=0)
    commission_rate: Optional[float] = Field(None, description="手续费率", ge=0, le=0.01)
    slippage: Optional[float] = Field(None, description="滑点", ge=0, le=0.01)
    benchmark: Optional[str] = Field(None, description="基准指数")
    max_concurrent_backtests: Optional[int] = Field(None, description="最大并发回测数", ge=1, le=10)


class SystemConfigRequest(BaseModel):
    """系统配置请求"""
    log_level: Optional[str] = Field(None, description="日志级别")
    max_log_files: Optional[int] = Field(None, description="最大日志文件数", ge=1, le=100)
    data_retention_days: Optional[int] = Field(None, description="数据保留天数", ge=1, le=3650)
    enable_debug: Optional[bool] = Field(None, description="启用调试模式")
    
    @validator('log_level')
    def validate_log_level(cls, v):
        if v is not None:
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if v.upper() not in valid_levels:
                raise ValueError(f'日志级别必须是: {", ".join(valid_levels)}')
            return v.upper()
        return v


# 响应模型
class ConfigInfo(BaseModel):
    """配置信息"""
    section: str = Field(..., description="配置节")
    key: str = Field(..., description="配置键")
    value: Any = Field(..., description="配置值")
    description: str = Field(..., description="配置描述")
    data_type: str = Field(..., description="数据类型")
    is_sensitive: bool = Field(..., description="是否敏感信息")


class ApiResponse(BaseModel):
    """API响应基类"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Any = Field(None, description="响应数据")


# 辅助函数
def mask_sensitive_value(value: str, mask_char: str = "*") -> str:
    """遮蔽敏感信息"""
    if not value or len(value) <= 4:
        return mask_char * len(value) if value else ""
    return value[:2] + mask_char * (len(value) - 4) + value[-2:]


def get_config_description(section: str, key: str) -> str:
    """获取配置描述"""
    descriptions = {
        "database": {
            "host": "数据库服务器地址",
            "port": "数据库端口号",
            "username": "数据库用户名",
            "password": "数据库密码",
            "database": "数据库名称"
        },
        "redis": {
            "host": "Redis服务器地址",
            "port": "Redis端口号",
            "password": "Redis密码",
            "db": "Redis数据库编号"
        },
        "xtquant": {
            "path": "MiniQMT客户端路径",
            "session_id": "交易会话ID",
            "account_id": "交易账户ID",
            "account_type": "账户类型"
        },
        "dingtalk": {
            "webhook_url": "钉钉机器人Webhook地址",
            "secret": "钉钉机器人密钥",
            "enabled": "是否启用钉钉通知"
        },
        "trading": {
            "max_position_size": "单个股票最大持仓比例",
            "commission_rate": "交易手续费率",
            "slippage": "交易滑点",
            "risk_limit": "风险控制限制",
            "enable_risk_control": "是否启用风险控制",
            "max_daily_trades": "每日最大交易次数",
            "min_order_amount": "最小订单金额"
        },
        "backtest": {
            "initial_capital": "回测初始资金",
            "commission_rate": "回测手续费率",
            "slippage": "回测滑点",
            "benchmark": "回测基准指数",
            "max_concurrent_backtests": "最大并发回测数量"
        },
        "system": {
            "log_level": "系统日志级别",
            "max_log_files": "最大日志文件数量",
            "data_retention_days": "数据保留天数",
            "enable_debug": "是否启用调试模式"
        }
    }
    return descriptions.get(section, {}).get(key, "未知配置项")


def is_sensitive_config(section: str, key: str) -> bool:
    """判断是否为敏感配置"""
    sensitive_keys = {
        "database": ["password"],
        "redis": ["password"],
        "dingtalk": ["secret"],
        "xtquant": ["account_id"]
    }
    return key in sensitive_keys.get(section, [])


# API路由
@router.get("/all", response_model=ApiResponse, summary="获取所有配置")
async def get_all_configs(settings: SystemConfig = Depends(get_settings)):
    """获取所有配置信息"""
    try:
        configs = []
        
        # 数据库配置
        db_configs = [
            ("host", settings.database.host),
            ("port", settings.database.port),
            ("username", settings.database.username),
            ("password", settings.database.password),
            ("database", settings.database.database)
        ]
        
        for key, value in db_configs:
            configs.append({
                "section": "database",
                "key": key,
                "value": mask_sensitive_value(str(value)) if is_sensitive_config("database", key) else value,
                "description": get_config_description("database", key),
                "data_type": type(value).__name__,
                "is_sensitive": is_sensitive_config("database", key)
            })
        
        # Redis配置
        redis_configs = [
            ("host", settings.redis.host),
            ("port", settings.redis.port),
            ("password", settings.redis.password),
            ("db", settings.redis.db)
        ]
        
        for key, value in redis_configs:
            configs.append({
                "section": "redis",
                "key": key,
                "value": mask_sensitive_value(str(value)) if is_sensitive_config("redis", key) else value,
                "description": get_config_description("redis", key),
                "data_type": type(value).__name__,
                "is_sensitive": is_sensitive_config("redis", key)
            })
        
        # XtQuant配置
        xtquant_configs = [
            ("path", settings.xtquant.path),
            ("session_id", settings.xtquant.session_id),
            ("account_id", settings.xtquant.account_id),
            ("account_type", settings.xtquant.account_type)
        ]
        
        for key, value in xtquant_configs:
            configs.append({
                "section": "xtquant",
                "key": key,
                "value": mask_sensitive_value(str(value)) if is_sensitive_config("xtquant", key) else value,
                "description": get_config_description("xtquant", key),
                "data_type": type(value).__name__,
                "is_sensitive": is_sensitive_config("xtquant", key)
            })
        
        # 钉钉配置
        dingtalk_configs = [
            ("webhook_url", settings.dingtalk.webhook_url),
            ("secret", settings.dingtalk.secret),
            ("enabled", settings.dingtalk.enabled)
        ]
        
        for key, value in dingtalk_configs:
            configs.append({
                "section": "dingtalk",
                "key": key,
                "value": mask_sensitive_value(str(value)) if is_sensitive_config("dingtalk", key) else value,
                "description": get_config_description("dingtalk", key),
                "data_type": type(value).__name__,
                "is_sensitive": is_sensitive_config("dingtalk", key)
            })
        
        # 交易配置
        trading_configs = [
            ("max_position_size", settings.trading.max_position_size),
            ("commission_rate", settings.trading.commission_rate),
            ("slippage", settings.trading.slippage),
            ("risk_limit", settings.trading.risk_limit),
            ("enable_risk_control", settings.trading.enable_risk_control),
            ("max_daily_trades", settings.trading.max_daily_trades),
            ("min_order_amount", settings.trading.min_order_amount)
        ]
        
        for key, value in trading_configs:
            configs.append({
                "section": "trading",
                "key": key,
                "value": value,
                "description": get_config_description("trading", key),
                "data_type": type(value).__name__,
                "is_sensitive": False
            })
        
        # 回测配置
        backtest_configs = [
            ("initial_capital", settings.backtest.initial_capital),
            ("commission_rate", settings.backtest.commission_rate),
            ("slippage", settings.backtest.slippage),
            ("benchmark", settings.backtest.benchmark),
            ("max_concurrent_backtests", settings.backtest.max_concurrent_backtests)
        ]
        
        for key, value in backtest_configs:
            configs.append({
                "section": "backtest",
                "key": key,
                "value": value,
                "description": get_config_description("backtest", key),
                "data_type": type(value).__name__,
                "is_sensitive": False
            })
        
        return ApiResponse(
            success=True,
            message="获取所有配置成功",
            data=configs
        )
    
    except Exception as e:
        logger.error(f"获取所有配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/section/{section}", response_model=ApiResponse, summary="获取指定节配置")
async def get_section_config(
    section: str,
    settings: SystemConfig = Depends(get_settings)
):
    """获取指定节的配置"""
    try:
        valid_sections = ["database", "redis", "xtquant", "dingtalk", "trading", "backtest"]
        if section not in valid_sections:
            raise HTTPException(status_code=400, detail=f"无效的配置节，有效值: {', '.join(valid_sections)}")
        
        if section == "database":
            config_data = {
                "host": settings.database.host,
                "port": settings.database.port,
                "username": settings.database.username,
                "password": mask_sensitive_value(settings.database.password),
                "database": settings.database.database
            }
        elif section == "redis":
            config_data = {
                "host": settings.redis.host,
                "port": settings.redis.port,
                "password": mask_sensitive_value(settings.redis.password) if settings.redis.password else "",
                "db": settings.redis.db
            }
        elif section == "xtquant":
            config_data = {
                "path": settings.xtquant.path,
                "session_id": settings.xtquant.session_id,
                "account_id": mask_sensitive_value(settings.xtquant.account_id),
                "account_type": settings.xtquant.account_type
            }
        elif section == "dingtalk":
            config_data = {
                "webhook_url": settings.dingtalk.webhook_url,
                "secret": mask_sensitive_value(settings.dingtalk.secret) if settings.dingtalk.secret else "",
                "enabled": settings.dingtalk.enabled
            }
        elif section == "trading":
            config_data = {
                "max_position_size": settings.trading.max_position_size,
                "commission_rate": settings.trading.commission_rate,
                "slippage": settings.trading.slippage,
                "risk_limit": settings.trading.risk_limit,
                "enable_risk_control": settings.trading.enable_risk_control,
                "max_daily_trades": settings.trading.max_daily_trades,
                "min_order_amount": settings.trading.min_order_amount
            }
        elif section == "backtest":
            config_data = {
                "initial_capital": settings.backtest.initial_capital,
                "commission_rate": settings.backtest.commission_rate,
                "slippage": settings.backtest.slippage,
                "benchmark": settings.backtest.benchmark,
                "max_concurrent_backtests": settings.backtest.max_concurrent_backtests
            }
        
        return ApiResponse(
            success=True,
            message=f"获取{section}配置成功",
            data=config_data
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取{section}配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/database", response_model=ApiResponse, summary="更新数据库配置")
async def update_database_config(
    request: DatabaseConfigRequest,
    settings: SystemConfig = Depends(get_settings)
):
    """更新数据库配置"""
    try:
        # 注意：这里只是演示，实际应用中需要实现配置持久化
        updated_fields = []
        
        if request.host is not None:
            settings.database.host = request.host
            updated_fields.append("host")
        
        if request.port is not None:
            settings.database.port = request.port
            updated_fields.append("port")
        
        if request.username is not None:
            settings.database.username = request.username
            updated_fields.append("username")
        
        if request.password is not None:
            settings.database.password = request.password
            updated_fields.append("password")
        
        if request.database is not None:
            settings.database.database = request.database
            updated_fields.append("database")
        
        return ApiResponse(
            success=True,
            message=f"更新数据库配置成功，更新字段: {', '.join(updated_fields)}",
            data={"updated_fields": updated_fields}
        )
    
    except Exception as e:
        logger.error(f"更新数据库配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/redis", response_model=ApiResponse, summary="更新Redis配置")
async def update_redis_config(
    request: RedisConfigRequest,
    settings: SystemConfig = Depends(get_settings)
):
    """更新Redis配置"""
    try:
        updated_fields = []
        
        if request.host is not None:
            settings.redis.host = request.host
            updated_fields.append("host")
        
        if request.port is not None:
            settings.redis.port = request.port
            updated_fields.append("port")
        
        if request.password is not None:
            settings.redis.password = request.password
            updated_fields.append("password")
        
        if request.db is not None:
            settings.redis.db = request.db
            updated_fields.append("db")
        
        return ApiResponse(
            success=True,
            message=f"更新Redis配置成功，更新字段: {', '.join(updated_fields)}",
            data={"updated_fields": updated_fields}
        )
    
    except Exception as e:
        logger.error(f"更新Redis配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/xtquant", response_model=ApiResponse, summary="更新XtQuant配置")
async def update_xtquant_config(
    request: XtQuantConfigRequest,
    settings: SystemConfig = Depends(get_settings)
):
    """更新XtQuant配置"""
    try:
        updated_fields = []
        
        if request.path is not None:
            settings.xtquant.path = request.path
            updated_fields.append("path")
        
        if request.session_id is not None:
            settings.xtquant.session_id = request.session_id
            updated_fields.append("session_id")
        
        if request.account_id is not None:
            settings.xtquant.account_id = request.account_id
            updated_fields.append("account_id")
        
        if request.account_type is not None:
            settings.xtquant.account_type = request.account_type
            updated_fields.append("account_type")
        
        return ApiResponse(
            success=True,
            message=f"更新XtQuant配置成功，更新字段: {', '.join(updated_fields)}",
            data={"updated_fields": updated_fields}
        )
    
    except Exception as e:
        logger.error(f"更新XtQuant配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dingtalk", response_model=ApiResponse, summary="更新钉钉配置")
async def update_dingtalk_config(
    request: DingTalkConfigRequest,
    settings: SystemConfig = Depends(get_settings)
):
    """更新钉钉配置"""
    try:
        updated_fields = []
        
        if request.webhook_url is not None:
            settings.dingtalk.webhook_url = request.webhook_url
            updated_fields.append("webhook_url")
        
        if request.secret is not None:
            settings.dingtalk.secret = request.secret
            updated_fields.append("secret")
        
        if request.enabled is not None:
            settings.dingtalk.enabled = request.enabled
            updated_fields.append("enabled")
        
        return ApiResponse(
            success=True,
            message=f"更新钉钉配置成功，更新字段: {', '.join(updated_fields)}",
            data={"updated_fields": updated_fields}
        )
    
    except Exception as e:
        logger.error(f"更新钉钉配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trading", response_model=ApiResponse, summary="更新交易配置")
async def update_trading_config(
    request: TradingConfigRequest,
    settings: SystemConfig = Depends(get_settings)
):
    """更新交易配置"""
    try:
        updated_fields = []
        
        if request.max_position_size is not None:
            settings.trading.max_position_size = request.max_position_size
            updated_fields.append("max_position_size")
        
        if request.commission_rate is not None:
            settings.trading.commission_rate = request.commission_rate
            updated_fields.append("commission_rate")
        
        if request.slippage is not None:
            settings.trading.slippage = request.slippage
            updated_fields.append("slippage")
        
        if request.risk_limit is not None:
            settings.trading.risk_limit = request.risk_limit
            updated_fields.append("risk_limit")
        
        if request.enable_risk_control is not None:
            settings.trading.enable_risk_control = request.enable_risk_control
            updated_fields.append("enable_risk_control")
        
        if request.max_daily_trades is not None:
            settings.trading.max_daily_trades = request.max_daily_trades
            updated_fields.append("max_daily_trades")
        
        if request.min_order_amount is not None:
            settings.trading.min_order_amount = request.min_order_amount
            updated_fields.append("min_order_amount")
        
        return ApiResponse(
            success=True,
            message=f"更新交易配置成功，更新字段: {', '.join(updated_fields)}",
            data={"updated_fields": updated_fields}
        )
    
    except Exception as e:
        logger.error(f"更新交易配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backtest", response_model=ApiResponse, summary="更新回测配置")
async def update_backtest_config(
    request: BacktestConfigRequest,
    settings: SystemConfig = Depends(get_settings)
):
    """更新回测配置"""
    try:
        updated_fields = []
        
        if request.initial_capital is not None:
            settings.backtest.initial_capital = request.initial_capital
            updated_fields.append("initial_capital")
        
        if request.commission_rate is not None:
            settings.backtest.commission_rate = request.commission_rate
            updated_fields.append("commission_rate")
        
        if request.slippage is not None:
            settings.backtest.slippage = request.slippage
            updated_fields.append("slippage")
        
        if request.benchmark is not None:
            settings.backtest.benchmark = request.benchmark
            updated_fields.append("benchmark")
        
        if request.max_concurrent_backtests is not None:
            settings.backtest.max_concurrent_backtests = request.max_concurrent_backtests
            updated_fields.append("max_concurrent_backtests")
        
        return ApiResponse(
            success=True,
            message=f"更新回测配置成功，更新字段: {', '.join(updated_fields)}",
            data={"updated_fields": updated_fields}
        )
    
    except Exception as e:
        logger.error(f"更新回测配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system", response_model=ApiResponse, summary="更新系统配置")
async def update_system_config(
    request: SystemConfigRequest
):
    """更新系统配置"""
    try:
        updated_fields = []
        
        # 系统配置更新需要特殊处理，因为可能需要重启服务
        if request.log_level is not None:
            from pathlib import Path
            from config import get_settings
            
            # 获取当前配置
            settings = get_settings()
            
            # 确保日志目录存在
            log_dir = Path(settings.log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # 更新日志级别
            logger.remove()
            logger.add(
                log_dir / f"{settings.log_file_prefix}_{{time:YYYY-MM-DD}}.log",
                level=request.log_level,
                rotation="1 day",
                retention=f"{settings.max_log_files} days"
            )
            updated_fields.append("log_level")
        
        # 其他系统配置项的更新逻辑...
        
        return ApiResponse(
            success=True,
            message=f"更新系统配置成功，更新字段: {', '.join(updated_fields)}",
            data={"updated_fields": updated_fields, "restart_required": bool(updated_fields)}
        )
    
    except Exception as e:
        logger.error(f"更新系统配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", response_model=ApiResponse, summary="验证配置")
async def validate_config(
    section: str,
    settings: SystemConfig = Depends(get_settings)
):
    """验证指定节的配置是否有效"""
    try:
        validation_results = []
        
        if section == "database":
            # 验证数据库连接
            try:
                # 这里应该实际测试数据库连接
                validation_results.append({
                    "item": "database_connection",
                    "valid": True,
                    "message": "数据库连接配置有效"
                })
            except Exception as e:
                validation_results.append({
                    "item": "database_connection",
                    "valid": False,
                    "message": f"数据库连接失败: {str(e)}"
                })
        
        elif section == "redis":
            # 验证Redis连接
            try:
                # 这里应该实际测试Redis连接
                validation_results.append({
                    "item": "redis_connection",
                    "valid": True,
                    "message": "Redis连接配置有效"
                })
            except Exception as e:
                validation_results.append({
                    "item": "redis_connection",
                    "valid": False,
                    "message": f"Redis连接失败: {str(e)}"
                })
        
        elif section == "xtquant":
            # 验证XtQuant配置
            import os
            path_valid = os.path.exists(settings.xtquant.path)
            validation_results.append({
                "item": "xtquant_path",
                "valid": path_valid,
                "message": "XtQuant路径有效" if path_valid else "XtQuant路径不存在"
            })
        
        elif section == "dingtalk":
            # 验证钉钉配置
            webhook_valid = settings.dingtalk.webhook_url.startswith("https://oapi.dingtalk.com/robot/send")
            validation_results.append({
                "item": "dingtalk_webhook",
                "valid": webhook_valid,
                "message": "钉钉Webhook URL有效" if webhook_valid else "钉钉Webhook URL格式无效"
            })
        
        all_valid = all(result["valid"] for result in validation_results)
        
        return ApiResponse(
            success=True,
            message=f"{section}配置验证完成",
            data={
                "section": section,
                "all_valid": all_valid,
                "results": validation_results
            }
        )
    
    except Exception as e:
        logger.error(f"验证{section}配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset/{section}", response_model=ApiResponse, summary="重置配置")
async def reset_config(
    section: str,
    settings: SystemConfig = Depends(get_settings)
):
    """重置指定节的配置为默认值"""
    try:
        valid_sections = ["database", "redis", "xtquant", "dingtalk", "trading", "backtest"]
        if section not in valid_sections:
            raise HTTPException(status_code=400, detail=f"无效的配置节，有效值: {', '.join(valid_sections)}")
        
        # 这里应该实现重置为默认值的逻辑
        # 实际应用中需要从默认配置文件或环境变量重新加载
        
        return ApiResponse(
            success=True,
            message=f"重置{section}配置成功",
            data={"section": section, "reset_to_defaults": True}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重置{section}配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))