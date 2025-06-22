#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能量化交易系统 - Flask版本
"""

from flask import Flask, jsonify
import json
from datetime import datetime
from config_simple import get_settings
from core.local_cache import get_cache, init_cache
from core.duckdb_adapter import get_duckdb, init_duckdb

# 移除loguru以避免Python 3.6兼容性问题
# from loguru import logger

# 简单的日志函数
def log_info(msg):
    print(f"[INFO] {msg}")

def log_error(msg):
    print(f"[ERROR] {msg}")

def log_warning(msg):
    print(f"[WARNING] {msg}")

# 获取配置
settings = get_settings()

# 创建Flask应用
app = Flask(__name__)
app.config['DEBUG'] = settings.debug

@app.route('/')
def root():
    """根路径"""
    return jsonify({
        "message": "Smart Trader 智能量化交易系统",
        "version": "1.0.0",
        "status": "running"
    })

@app.route('/health')
def health_check():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/v1/status')
def get_system_status():
    """获取系统状态"""
    return jsonify({
        "system": "Smart Trader",
        "services": {
            "data_service": "stopped",
            "trading_service": "stopped",
            "strategy_service": "stopped",
            "backtest_service": "stopped",
            "notification_service": "stopped"
        },
        "message": "系统已启动，服务模块待初始化"
    })

@app.route('/api/v1/data/stocks')
def get_stocks():
    """获取股票列表"""
    return jsonify({
        "stocks": [
            {"code": "000001.SZ", "name": "平安银行"},
            {"code": "000002.SZ", "name": "万科A"},
            {"code": "600000.SH", "name": "浦发银行"},
            {"code": "600036.SH", "name": "招商银行"}
        ],
        "total": 4
    })

@app.route('/api/v1/trading/account')
def get_account_info():
    """获取账户信息"""
    try:
        # 先从缓存获取
        cache = get_cache()
        cache_key = "account_info"
        cached_data = cache.get_json(cache_key)
        
        if cached_data:
            cached_data["source"] = "cache"
            return jsonify(cached_data)
        
        # 从数据库或XtQuant获取（这里先返回模拟数据）
        account_info = {
            "account_id": "demo_account",
            "cash": 100000.0,
            "market_value": 0.0,
            "total_asset": 100000.0,
            "status": "disconnected",
            "source": "database",
            "timestamp": datetime.now().isoformat()
        }
        
        # 缓存数据（1分钟过期）
        cache.set_json(cache_key, account_info, expire=60)
        
        return jsonify(account_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stock/<stock_code>')
def get_stock_data(stock_code):
    """获取股票数据"""
    try:
        # 先从缓存获取
        cache = get_cache()
        cache_key = f"stock_data:{stock_code}"
        cached_data = cache.get_json(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
        
        # 从数据库查询（这里先返回模拟数据）
        stock_data = {
            "stock_code": stock_code,
            "name": f"股票{stock_code}",
            "price": 10.50,
            "change": 0.25,
            "change_percent": 2.44,
            "volume": 1000000,
            "timestamp": datetime.now().isoformat(),
            "source": "database"
        }
        
        # 缓存数据（5分钟过期）
        cache.set_json(cache_key, stock_data, expire=300)
        
        return jsonify(stock_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config')
def get_config():
    """获取系统配置"""
    config = {
        "app_name": settings.app_name,
        "version": settings.version,
        "debug": settings.debug,
        "api_port": settings.api_port,
        "database": {
            "host": settings.database.host,
            "port": settings.database.port,
            "database": settings.database.database
        },
        "trading": {
            "max_position_ratio": settings.trading.max_position_ratio,
            "stop_loss_ratio": settings.trading.stop_loss_ratio,
            "take_profit_ratio": settings.trading.take_profit_ratio
        }
    }
    return jsonify(config)

@app.route('/api/cache/info')
def get_cache_info():
    """获取缓存信息"""
    try:
        cache = get_cache()
        cache_info = cache.info()
        cache_info['status'] = 'active'
        return jsonify(cache_info)
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500

@app.route('/api/cache/clear')
def clear_cache():
    """清空缓存"""
    try:
        cache = get_cache()
        cache.clear()
        return jsonify({"message": "缓存已清空", "status": "success"})
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500

@app.route('/api/database/info')
def get_database_info():
    """获取数据库信息"""
    try:
        db = get_duckdb()
        # 获取数据库基本信息
        info = {
            "type": "DuckDB",
            "path": settings.database.path if not settings.database.memory else ":memory:",
            "memory": settings.database.memory,
            "status": "connected"
        }
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500

@app.route('/api/positions')
def get_positions():
    """获取当前持仓"""
    try:
        # 先从缓存获取
        cache = get_cache()
        cache_key = "positions"
        cached_data = cache.get_json(cache_key)
        
        if cached_data:
            cached_data["source"] = "cache"
            return jsonify(cached_data)
        
        # 从数据库或XtQuant获取（这里先返回模拟数据）
        positions = {
            "total_positions": 3,
            "total_market_value": 52500.0,
            "positions": [
                {
                    "stock_code": "600000.SH",
                    "stock_name": "浦发银行",
                    "quantity": 1000,
                    "available_quantity": 1000,
                    "avg_cost": 10.50,
                    "current_price": 10.75,
                    "market_value": 10750.0,
                    "profit_loss": 250.0,
                    "profit_loss_ratio": 2.38,
                    "position_ratio": 20.48
                },
                {
                    "stock_code": "000001.SZ",
                    "stock_name": "平安银行",
                    "quantity": 2000,
                    "available_quantity": 2000,
                    "avg_cost": 12.30,
                    "current_price": 12.60,
                    "market_value": 25200.0,
                    "profit_loss": 600.0,
                    "profit_loss_ratio": 2.44,
                    "position_ratio": 48.00
                },
                {
                    "stock_code": "002415.SZ",
                    "stock_name": "海康威视",
                    "quantity": 500,
                    "available_quantity": 500,
                    "avg_cost": 32.20,
                    "current_price": 33.10,
                    "market_value": 16550.0,
                    "profit_loss": 450.0,
                    "profit_loss_ratio": 2.80,
                    "position_ratio": 31.52
                }
            ],
            "source": "database",
            "timestamp": datetime.now().isoformat()
        }
        
        # 缓存数据（30秒过期）
        cache.set_json(cache_key, positions, expire=30)
        
        return jsonify(positions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/positions/<stock_code>')
def get_position(stock_code):
    """获取指定股票的持仓"""
    try:
        # 先从缓存获取
        cache = get_cache()
        cache_key = f"position:{stock_code}"
        cached_data = cache.get_json(cache_key)
        
        if cached_data:
            cached_data["source"] = "cache"
            return jsonify(cached_data)
        
        # 模拟数据 - 根据股票代码返回对应持仓
        positions_data = {
            "600000.SH": {
                "stock_code": "600000.SH",
                "stock_name": "浦发银行",
                "quantity": 1000,
                "available_quantity": 1000,
                "avg_cost": 10.50,
                "current_price": 10.75,
                "market_value": 10750.0,
                "profit_loss": 250.0,
                "profit_loss_ratio": 2.38,
                "position_ratio": 20.48
            },
            "000001.SZ": {
                "stock_code": "000001.SZ",
                "stock_name": "平安银行",
                "quantity": 2000,
                "available_quantity": 2000,
                "avg_cost": 12.30,
                "current_price": 12.60,
                "market_value": 25200.0,
                "profit_loss": 600.0,
                "profit_loss_ratio": 2.44,
                "position_ratio": 48.00
            },
            "002415.SZ": {
                "stock_code": "002415.SZ",
                "stock_name": "海康威视",
                "quantity": 500,
                "available_quantity": 500,
                "avg_cost": 32.20,
                "current_price": 33.10,
                "market_value": 16550.0,
                "profit_loss": 450.0,
                "profit_loss_ratio": 2.80,
                "position_ratio": 31.52
            }
        }
        
        position = positions_data.get(stock_code)
        if position:
            position["source"] = "database"
            position["timestamp"] = datetime.now().isoformat()
            
            # 缓存数据（30秒过期）
            cache.set_json(cache_key, position, expire=30)
            
            return jsonify(position)
        else:
            return jsonify({
                "message": f"未找到股票 {stock_code} 的持仓",
                "stock_code": stock_code,
                "quantity": 0,
                "timestamp": datetime.now().isoformat()
            }), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(f"Smart Trader Flask服务启动中...")
    print(f"应用名称: {settings.app_name}")
    print(f"版本: {settings.version}")
    
    # 初始化服务
    try:
        print("初始化本地缓存...")
        init_cache()
        
        print("初始化DuckDB数据库...")
        init_duckdb()
        
        print("所有服务初始化完成")
    except Exception as e:
        print(f"服务初始化失败: {e}")
        exit(1)
    
    print(f"访问地址: http://localhost:{settings.api_port}")
    print(f"API端点:")
    print(f"  - 系统状态: http://localhost:{settings.api_port}/api/status")
    print(f"  - 配置信息: http://localhost:{settings.api_port}/api/config")
    print(f"  - 缓存信息: http://localhost:{settings.api_port}/api/cache/info")
    print(f"  - 数据库信息: http://localhost:{settings.api_port}/api/database/info")
    print(f"  - 股票数据: http://localhost:{settings.api_port}/api/stock/<股票代码>")
    print(f"  - 账户信息: http://localhost:{settings.api_port}/api/account")
    print(f"  - 所有持仓: http://localhost:{settings.api_port}/api/positions")
    print(f"  - 单个持仓: http://localhost:{settings.api_port}/api/positions/<股票代码>")
    
    app.run(host='0.0.0.0', port=settings.api_port, debug=settings.debug)