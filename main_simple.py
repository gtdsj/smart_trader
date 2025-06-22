#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能量化交易系统 - 简化启动版本
"""

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from loguru import logger

# 创建FastAPI应用
app = FastAPI(
    title="Smart Trader",
    description="智能量化交易系统",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Smart Trader 智能量化交易系统",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z"
    }

@app.get("/api/v1/status")
async def get_system_status():
    """获取系统状态"""
    return {
        "system": "Smart Trader",
        "services": {
            "data_service": "stopped",
            "trading_service": "stopped",
            "strategy_service": "stopped",
            "backtest_service": "stopped",
            "notification_service": "stopped"
        },
        "message": "系统已启动，服务模块待初始化"
    }

if __name__ == "__main__":
    logger.info("启动 Smart Trader 系统...")
    
    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )