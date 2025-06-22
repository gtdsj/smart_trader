# -*- coding: utf-8 -*-
"""
Smart Trader FastAPI应用 - 模块化版本
基于FastAPI框架的量化交易系统API服务
采用模块化路由架构，便于维护和扩展
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import uvicorn

# 导入配置和核心模块
from config import get_settings
from core.local_cache import get_cache, init_cache
from core.duckdb_adapter import get_duckdb, init_duckdb

# 导入模块化路由
from api.routes import router as api_router, get_route_info

# 简单的日志函数
def log_info(msg):
    print("[INFO] {}".format(msg))

def log_error(msg):
    print("[ERROR] {}".format(msg))

def log_warning(msg):
    print("[WARNING] {}".format(msg))

# 获取配置
settings = get_settings()

# 创建FastAPI应用
app = FastAPI(
    title="Smart Trader API",
    description="智能量化交易系统API - 模块化架构",
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册所有API路由
app.include_router(api_router)

# 响应模型类
class ApiResponse:
    def __init__(self, success=True, message="", data=None):
        self.success = success
        self.message = message
        self.data = data
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp
        }

# 根路径重定向到API文档
@app.get("/", include_in_schema=False)
def root():
    """根路径，重定向到API文档"""
    return {
        "message": "欢迎使用 Smart Trader API",
        "version": settings.version,
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "api_info": "/api/info",
        "routes": "/api/routes"
    }

# API路由信息端点
@app.get("/api/routes", tags=["系统信息"], summary="API路由信息")
def get_api_routes():
    """获取所有API路由信息"""
    try:
        route_info = get_route_info()
        
        return ApiResponse(
            message="获取API路由信息成功",
            data=route_info
        ).to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    log_error("全局异常: {}".format(str(exc)))
    
    return JSONResponse(
        status_code=500,
        content=ApiResponse(
            success=False,
            message="服务器内部错误",
            data={"error": str(exc)}
        ).to_dict()
    )

# 启动事件
@app.on_event("startup")
def startup_event():
    """应用启动时初始化服务"""
    try:
        log_info("Smart Trader FastAPI服务启动中...")
        log_info("应用名称: {}".format(settings.app_name))
        log_info("版本: {}".format(settings.version))
        log_info("架构: 模块化路由")
        
        log_info("初始化本地缓存...")
        init_cache()
        
        log_info("初始化DuckDB数据库...")
        init_duckdb()
        
        log_info("所有服务初始化完成")
        
        # 打印路由信息
        route_info = get_route_info()
        log_info("已注册的API模块:")
        for module_name, module_info in route_info.items():
            log_info("  - {}: {}".format(module_name, module_info.get('description', '')))
            
    except Exception as e:
        log_error("服务初始化失败: {}".format(e))
        raise

# 关闭事件
@app.on_event("shutdown")
def shutdown_event():
    """应用关闭时清理资源"""
    log_info("Smart Trader FastAPI服务正在关闭...")
    log_info("清理资源完成")

if __name__ == '__main__':
    print("="*60)
    print("Smart Trader FastAPI服务启动中...")
    print("="*60)
    print("应用信息:")
    print("  应用名称: {}".format(settings.app_name))
    print("  版本: {}".format(settings.version))
    print("  架构: 模块化路由")
    print("  访问地址: http://localhost:{}".format(settings.api_port))
    print("")
    print("API文档:")
    print("  Swagger UI: http://localhost:{}/docs".format(settings.api_port))
    print("  ReDoc: http://localhost:{}/redoc".format(settings.api_port))
    print("  OpenAPI JSON: http://localhost:{}/openapi.json".format(settings.api_port))
    print("")
    print("系统API:")
    print("  根路径: http://localhost:{}/".format(settings.api_port))
    print("  系统状态: http://localhost:{}/api/status".format(settings.api_port))
    print("  健康检查: http://localhost:{}/api/health".format(settings.api_port))
    print("  系统信息: http://localhost:{}/api/info".format(settings.api_port))
    print("  路由信息: http://localhost:{}/api/routes".format(settings.api_port))
    print("")
    print("配置API:")
    print("  配置管理: http://localhost:{}/api/config".format(settings.api_port))
    print("  数据库配置: http://localhost:{}/api/config/database".format(settings.api_port))
    print("  交易配置: http://localhost:{}/api/config/trading".format(settings.api_port))
    print("")
    print("业务API (v1):")
    print("  交易服务: http://localhost:{}/api/v1/trading".format(settings.api_port))
    print("  数据服务: http://localhost:{}/api/v1/data".format(settings.api_port))
    print("  策略服务: http://localhost:{}/api/v1/strategy".format(settings.api_port))
    print("  回测服务: http://localhost:{}/api/v1/backtest".format(settings.api_port))
    print("  通知服务: http://localhost:{}/api/v1/notification".format(settings.api_port))
    print("="*60)
    
    uvicorn.run(
        "main_fastapi_modular:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=settings.debug,
        log_level="info"
    )