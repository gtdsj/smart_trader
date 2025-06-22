#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理演示脚本
展示如何使用JSON配置文件和环境变量
"""

import os
from config import (
    get_settings, 
    reload_settings, 
    save_settings, 
    create_default_config_file,
    SystemConfig,
    DatabaseConfig,
    TradingConfig
)


def demo_basic_usage():
    """基本使用示例"""
    print("=== 基本配置使用示例 ===")
    
    # 获取当前配置
    settings = get_settings()
    print(f"应用名称: {settings.app_name}")
    print(f"版本: {settings.version}")
    print(f"API端口: {settings.api_port}")
    print(f"数据库URL: {settings.database.url}")
    print(f"Redis URL: {settings.redis.url}")
    print()


def demo_modify_config():
    """修改配置示例"""
    print("=== 修改配置示例 ===")
    
    # 获取当前配置
    settings = get_settings()
    
    # 修改配置
    settings.api_port = 9000
    settings.database.host = "192.168.1.100"
    settings.trading.max_position_ratio = 0.8
    
    # 保存配置
    if save_settings(settings):
        print("配置保存成功")
    else:
        print("配置保存失败")
    
    # 重新加载配置验证
    new_settings = reload_settings()
    print(f"新的API端口: {new_settings.api_port}")
    print(f"新的数据库主机: {new_settings.database.host}")
    print(f"新的最大仓位比例: {new_settings.trading.max_position_ratio}")
    print()


def demo_env_override():
    """环境变量覆盖示例"""
    print("=== 环境变量覆盖示例 ===")
    
    # 设置环境变量
    os.environ['API_PORT'] = '7000'
    os.environ['DB_HOST'] = 'env-database-host'
    os.environ['TRADING_MAX_POSITION_RATIO'] = '0.7'
    os.environ['DINGTALK_ENABLED'] = 'true'
    
    # 重新加载配置
    settings = reload_settings()
    
    print(f"API端口 (来自环境变量): {settings.api_port}")
    print(f"数据库主机 (来自环境变量): {settings.database.host}")
    print(f"最大仓位比例 (来自环境变量): {settings.trading.max_position_ratio}")
    print(f"钉钉通知启用 (来自环境变量): {settings.dingtalk.enabled}")
    
    # 清理环境变量
    for key in ['API_PORT', 'DB_HOST', 'TRADING_MAX_POSITION_RATIO', 'DINGTALK_ENABLED']:
        if key in os.environ:
            del os.environ[key]
    print()


def demo_create_custom_config():
    """创建自定义配置示例"""
    print("=== 创建自定义配置示例 ===")
    
    # 创建自定义配置
    custom_config = SystemConfig(
        app_name="My Trading Bot",
        version="2.0.0",
        debug=False,
        api_port=8888,
        database={
            "host": "prod-db-server",
            "port": 5432,
            "username": "trader",
            "password": "secure_password",
            "database": "trading_db"
        },
        trading={
            "max_position_ratio": 0.9,
            "stop_loss_ratio": 0.03,
            "take_profit_ratio": 0.2
        }
    )
    
    # 保存自定义配置
    if save_settings(custom_config):
        print("自定义配置保存成功")
        print(f"应用名称: {custom_config.app_name}")
        print(f"版本: {custom_config.version}")
        print(f"数据库URL: {custom_config.database.url}")
        print(f"止损比例: {custom_config.trading.stop_loss_ratio}")
    print()


def demo_config_validation():
    """配置验证示例"""
    print("=== 配置验证示例 ===")
    
    settings = get_settings()
    
    # 验证XtQuant路径
    if os.path.exists(settings.xtquant.path):
        print(f"✓ XtQuant路径有效: {settings.xtquant.path}")
    else:
        print(f"✗ XtQuant路径无效: {settings.xtquant.path}")
    
    # 验证交易参数
    if 0 < settings.trading.max_position_ratio <= 1:
        print(f"✓ 最大仓位比例有效: {settings.trading.max_position_ratio}")
    else:
        print(f"✗ 最大仓位比例无效: {settings.trading.max_position_ratio}")
    
    # 验证钉钉配置
    if settings.dingtalk.enabled and settings.dingtalk.webhook_url:
        print(f"✓ 钉钉配置有效")
    elif settings.dingtalk.enabled:
        print(f"✗ 钉钉已启用但缺少Webhook URL")
    else:
        print(f"- 钉钉通知未启用")
    print()


if __name__ == "__main__":
    print("Smart Trader 配置管理演示\n")
    
    # 确保有默认配置文件
    if not os.path.exists("config.json"):
        print("创建默认配置文件...")
        create_default_config_file()
        print()
    
    # 运行示例
    demo_basic_usage()
    demo_modify_config()
    demo_env_override()
    demo_create_custom_config()
    demo_config_validation()
    
    print("演示运行完成！")