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
    
    # 从XtQuant获取真实账户信息
    try:
        from services.xtquant_service import XtQuantService
        from config import get_settings
        xtquant_service = XtQuantService()
        
        # 获取账户资产
        asset_data = await xtquant_service.get_account_asset()
        
        if asset_data:
            account_info = {
                "account_id": get_settings().xtquant.account_id,
                "cash": asset_data.get("cash", 0.0),
                "market_value": asset_data.get("market_value", 0.0),
                "total_asset": asset_data.get("total_asset", 0.0),
                "available_cash": asset_data.get("available_cash", 0.0),
                "frozen_cash": asset_data.get("frozen_cash", 0.0),
                "profit_loss": asset_data.get("profit_loss", 0.0),
                "profit_loss_ratio": asset_data.get("profit_loss_ratio", 0.0),
                "status": "connected" if xtquant_service.is_trading_connected else "disconnected",
                "source": "xtquant",
                "timestamp": datetime.now().isoformat()
            }
        else:
            # 如果无法获取真实数据，返回基础信息
            account_info = {
                "account_id": get_settings().xtquant.account_id,
                "cash": 0.0,
                "market_value": 0.0,
                "total_asset": 0.0,
                "available_cash": 0.0,
                "frozen_cash": 0.0,
                "profit_loss": 0.0,
                "profit_loss_ratio": 0.0,
                "status": "disconnected",
                "source": "xtquant",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        print(f"获取账户信息失败: {e}")
        # 返回错误状态的账户信息
        account_info = {
            "account_id": get_settings().xtquant.account_id if hasattr(get_settings(), 'xtquant') else "unknown",
            "cash": 0.0,
            "market_value": 0.0,
            "total_asset": 0.0,
            "available_cash": 0.0,
            "frozen_cash": 0.0,
            "profit_loss": 0.0,
            "profit_loss_ratio": 0.0,
            "status": "error",
            "source": "xtquant",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
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
    
    # 从XtQuant获取真实股票数据
    try:
        from services.xtquant_service import XtQuantService
        xtquant_service = XtQuantService()
        
        # 获取实时行情数据
        realtime_data = await xtquant_service.get_realtime_data([stock_code])
        
        if stock_code in realtime_data:
            data = realtime_data[stock_code]
            stock_data = {
                "stock_code": stock_code,
                "name": data.get("name", f"股票{stock_code}"),
                "price": data.get("last_price", 0.0),
                "change": data.get("change", 0.0),
                "change_percent": data.get("change_ratio", 0.0) * 100,
                "volume": data.get("volume", 0),
                "turnover": data.get("amount", 0.0),
                "high": data.get("high", 0.0),
                "low": data.get("low", 0.0),
                "open": data.get("open", 0.0),
                "prev_close": data.get("pre_close", 0.0),
                "timestamp": data.get("timestamp", datetime.now().isoformat()),
                "source": "xtquant"
            }
        else:
            # 如果无法获取实时数据，返回基础信息
            stock_data = {
                "stock_code": stock_code,
                "name": f"股票{stock_code}",
                "price": 0.0,
                "change": 0.0,
                "change_percent": 0.0,
                "volume": 0,
                "turnover": 0.0,
                "high": 0.0,
                "low": 0.0,
                "open": 0.0,
                "prev_close": 0.0,
                "timestamp": datetime.now().isoformat(),
                "source": "xtquant",
                "status": "no_data"
            }
    except Exception as e:
        print(f"获取股票{stock_code}数据失败: {e}")
        # 返回错误状态的股票信息
        stock_data = {
            "stock_code": stock_code,
            "name": f"股票{stock_code}",
            "price": 0.0,
            "change": 0.0,
            "change_percent": 0.0,
            "volume": 0,
            "turnover": 0.0,
            "high": 0.0,
            "low": 0.0,
            "open": 0.0,
            "prev_close": 0.0,
            "timestamp": datetime.now().isoformat(),
            "source": "xtquant",
            "status": "error",
            "error": str(e)
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
    
    # 从XtQuant获取真实持仓数据
    try:
        from services.xtquant_service import XtQuantService
        xtquant_service = XtQuantService()
        
        # 获取持仓列表
        position_list = await xtquant_service.get_positions()
        
        if position_list:
            # 计算汇总数据
            total_market_value = sum(pos.get("market_value", 0) for pos in position_list)
            total_cost_value = sum(pos.get("cost_value", 0) for pos in position_list)
            total_profit_loss = total_market_value - total_cost_value
            total_profit_loss_ratio = (total_profit_loss / total_cost_value * 100) if total_cost_value > 0 else 0
            
            positions = {
                "total_positions": len(position_list),
                "total_market_value": total_market_value,
                "total_cost": total_cost_value,
                "total_profit_loss": total_profit_loss,
                "total_profit_loss_ratio": total_profit_loss_ratio,
                "positions": position_list,
                "source": "xtquant",
                "timestamp": datetime.now().isoformat()
            }
        else:
            # 如果没有持仓数据
            positions = {
                "total_positions": 0,
                "total_market_value": 0.0,
                "total_cost": 0.0,
                "total_profit_loss": 0.0,
                "total_profit_loss_ratio": 0.0,
                "positions": [],
                "source": "xtquant",
                "timestamp": datetime.now().isoformat(),
                "status": "no_positions"
            }
    except Exception as e:
        print(f"获取持仓信息失败: {e}")
        # 返回错误状态的持仓信息
        positions = {
            "total_positions": 0,
            "total_market_value": 0.0,
            "total_cost": 0.0,
            "total_profit_loss": 0.0,
            "total_profit_loss_ratio": 0.0,
            "positions": [],
            "source": "xtquant",
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
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
    
    # 从XtQuant获取真实持仓数据
    try:
        from services.xtquant_service import XtQuantService
        xtquant_service = XtQuantService()
        
        # 获取所有持仓
        position_list = await xtquant_service.get_positions()
        
        # 查找指定股票的持仓
        position = None
        if position_list:
            for pos in position_list:
                if pos.get("stock_code") == stock_code:
                    position = pos
                    break
        
        if position:
            position["source"] = "xtquant"
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
                    "source": "xtquant",
                    "timestamp": datetime.now().isoformat(),
                    "status": "no_position"
                }
            )
    except Exception as e:
        print(f"获取股票 {stock_code} 持仓信息失败: {e}")
        return api_response(
            success=False,
            message="获取股票 {} 持仓信息失败: {}".format(stock_code, str(e)),
            data={
                "stock_code": stock_code,
                "quantity": 0,
                "source": "xtquant",
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
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