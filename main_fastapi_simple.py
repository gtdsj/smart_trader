#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Trader 极简FastAPI应用
完全不依赖pydantic的简化版本
"""

from datetime import datetime
import json

# 手动实现简单的HTTP服务器
class SimpleHTTPHandler:
    def __init__(self):
        self.routes = {}
        
    def route(self, path, method='GET'):
        def decorator(func):
            self.routes[(method, path)] = func
            return func
        return decorator
        
    def handle_request(self, method, path, query_params=None):
        # 处理路径参数
        for (route_method, route_path), handler in self.routes.items():
            if route_method == method:
                if route_path == path:
                    return handler()
                # 处理路径参数 {param}
                elif '{' in route_path and '}' in route_path:
                    route_parts = route_path.split('/')
                    path_parts = path.split('/')
                    if len(route_parts) == len(path_parts):
                        params = {}
                        match = True
                        for i, part in enumerate(route_parts):
                            if part.startswith('{') and part.endswith('}'):
                                param_name = part[1:-1]
                                params[param_name] = path_parts[i]
                            elif part != path_parts[i]:
                                match = False
                                break
                        if match:
                            return handler(**params)
        return self.not_found()
        
    def not_found(self):
        return {
            "success": False,
            "message": "接口不存在",
            "data": None,
            "timestamp": datetime.now().isoformat()
        }

# 创建应用实例
app = SimpleHTTPHandler()

# 模拟配置
class Settings:
    def __init__(self):
        self.app_name = "Smart Trader"
        self.version = "1.0.0"
        self.api_port = 8888
        self.debug = True

settings = Settings()

# 模拟缓存
class SimpleCache:
    def __init__(self):
        self.data = {}
        self.expire_times = {}
        
    def get_json(self, key):
        if key in self.data:
            if key in self.expire_times:
                if datetime.now().timestamp() > self.expire_times[key]:
                    del self.data[key]
                    del self.expire_times[key]
                    return None
            return self.data[key]
        return None
        
    def set_json(self, key, value, expire=None):
        self.data[key] = value
        if expire:
            self.expire_times[key] = datetime.now().timestamp() + expire
            
    def clear(self):
        self.data.clear()
        self.expire_times.clear()
        
    def info(self):
        return {
            "total_keys": len(self.data),
            "expired_keys": 0
        }

cache = SimpleCache()

# API响应格式
def api_response(success=True, message="", data=None):
    return {
        "success": success,
        "message": message,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }

# 路由定义
@app.route("/")
def root():
    return api_response(
        message="欢迎使用 {} v{}".format(settings.app_name, settings.version),
        data={
            "app_name": settings.app_name,
            "version": settings.version,
            "docs": "/docs",
            "redoc": "/redoc"
        }
    )

@app.route("/api/status")
def get_status():
    status = {
        "app_name": settings.app_name,
        "version": settings.version,
        "status": "running",
        "cache_status": "active",
        "database_status": "connected",
        "timestamp": datetime.now().isoformat()
    }
    return api_response(message="系统运行正常", data=status)

@app.route("/api/account")
def get_account():
    # 先从缓存获取
    cache_key = "account_info"
    cached_data = cache.get_json(cache_key)
    
    if cached_data:
        cached_data["source"] = "cache"
        return api_response(message="获取账户信息成功", data=cached_data)
    
    # 模拟数据
    account_info = {
        "account_id": "demo_account",
        "cash": 100000.0,
        "market_value": 52500.0,
        "total_asset": 152500.0,
        "available_cash": 95000.0,
        "frozen_cash": 5000.0,
        "profit_loss": 1300.0,
        "profit_loss_ratio": 0.86,
        "status": "connected",
        "source": "database",
        "timestamp": datetime.now().isoformat()
    }
    
    # 缓存数据（1分钟过期）
    cache.set_json(cache_key, account_info, expire=60)
    
    return api_response(message="获取账户信息成功", data=account_info)

@app.route("/api/stock/{stock_code}")
def get_stock_data(stock_code):
    # 先从缓存获取
    cache_key = "stock_data:{}".format(stock_code)
    cached_data = cache.get_json(cache_key)
    
    if cached_data:
        return api_response(message="获取股票数据成功", data=cached_data)
    
    # 模拟数据
    stock_data = {
        "stock_code": stock_code,
        "name": "股票{}".format(stock_code),
        "price": 10.50,
        "change": 0.25,
        "change_percent": 2.44,
        "volume": 1000000,
        "turnover": 10500000.0,
        "high": 10.80,
        "low": 10.20,
        "open": 10.25,
        "prev_close": 10.25,
        "timestamp": datetime.now().isoformat(),
        "source": "database"
    }
    
    # 缓存数据（5分钟过期）
    cache.set_json(cache_key, stock_data, expire=300)
    
    return api_response(message="获取股票数据成功", data=stock_data)

@app.route("/api/positions")
def get_positions():
    # 先从缓存获取
    cache_key = "positions"
    cached_data = cache.get_json(cache_key)
    
    if cached_data:
        cached_data["source"] = "cache"
        return api_response(message="获取持仓信息成功", data=cached_data)
    
    # 模拟数据
    positions = {
        "total_positions": 3,
        "total_market_value": 52500.0,
        "total_cost": 51200.0,
        "total_profit_loss": 1300.0,
        "total_profit_loss_ratio": 2.54,
        "positions": [
            {
                "stock_code": "600000.SH",
                "stock_name": "浦发银行",
                "quantity": 1000,
                "available_quantity": 1000,
                "avg_cost": 10.50,
                "current_price": 10.75,
                "market_value": 10750.0,
                "cost_value": 10500.0,
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
                "cost_value": 24600.0,
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
                "cost_value": 16100.0,
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
    
    return api_response(message="获取持仓信息成功", data=positions)

@app.route("/api/positions/{stock_code}")
def get_position(stock_code):
    # 先从缓存获取
    cache_key = "position:{}".format(stock_code)
    cached_data = cache.get_json(cache_key)
    
    if cached_data:
        cached_data["source"] = "cache"
        return api_response(message="获取持仓信息成功", data=cached_data)
    
    # 模拟数据
    positions_data = {
        "600000.SH": {
            "stock_code": "600000.SH",
            "stock_name": "浦发银行",
            "quantity": 1000,
            "available_quantity": 1000,
            "avg_cost": 10.50,
            "current_price": 10.75,
            "market_value": 10750.0,
            "cost_value": 10500.0,
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
            "cost_value": 24600.0,
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
            "cost_value": 16100.0,
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
        
        return api_response(message="获取持仓信息成功", data=position)
    else:
        return api_response(
            success=False,
            message="未找到股票 {} 的持仓".format(stock_code),
            data={
                "stock_code": stock_code,
                "quantity": 0,
                "timestamp": datetime.now().isoformat()
            }
        )

@app.route("/api/config")
def get_config():
    config = {
        "app_name": settings.app_name,
        "version": settings.version,
        "debug": settings.debug,
        "api_port": settings.api_port
    }
    return api_response(message="获取配置信息成功", data=config)

@app.route("/api/cache/info")
def get_cache_info():
    cache_info = cache.info()
    cache_info['status'] = 'active'
    return api_response(message="获取缓存信息成功", data=cache_info)

# 使用内置的http.server实现简单的HTTP服务器
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        try:
            response_data = app.handle_request('GET', path, query_params)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            error_response = api_response(success=False, message=str(e))
            self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode('utf-8'))
    
    def do_POST(self):
        self.do_GET()  # 简化处理，POST也按GET处理
        
    def log_message(self, format, *args):
        # 简化日志输出
        print("[{}] {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), format % args))

if __name__ == '__main__':
    print("Smart Trader 极简API服务启动中...")
    print("应用名称: {}".format(settings.app_name))
    print("版本: {}".format(settings.version))
    print("访问地址: http://localhost:{}".format(settings.api_port))
    print("API端点:")
    print("  - 系统状态: http://localhost:{}/api/status".format(settings.api_port))
    print("  - 配置信息: http://localhost:{}/api/config".format(settings.api_port))
    print("  - 缓存信息: http://localhost:{}/api/cache/info".format(settings.api_port))
    print("  - 股票数据: http://localhost:{}/api/stock/<股票代码>".format(settings.api_port))
    print("  - 账户信息: http://localhost:{}/api/account".format(settings.api_port))
    print("  - 所有持仓: http://localhost:{}/api/positions".format(settings.api_port))
    print("  - 单个持仓: http://localhost:{}/api/positions/<股票代码>".format(settings.api_port))
    
    server = HTTPServer(('0.0.0.0', settings.api_port), APIHandler)
    print("服务器启动成功，按 Ctrl+C 停止服务")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.server_close()