#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实模式启动脚本
启动量化交易系统的真实模式
"""

import asyncio
import uvicorn
from loguru import logger
from config import get_settings
from core.database import init_database
from services.xtquant_service import XtQuantService
from services.trading_service import TradingService
from services.notification_service import NotificationService


async def check_system_status():
    """检查系统状态"""
    logger.info("🚀 启动真实模式量化交易系统...")
    
    # 检查配置
    settings = get_settings()
    logger.info(f"当前配置:")
    logger.info(f"  - 模拟模式: {settings.simulation_mode}")
    logger.info(f"  - 数据库路径: {settings.database.path}")
    logger.info(f"  - XtQuant路径: {settings.xtquant.path}")
    logger.info(f"  - 账户ID: {settings.xtquant.account_id}")
    
    if settings.simulation_mode:
        logger.warning("⚠️ 系统配置为模拟模式，请检查config.json")
        return False
    
    # 初始化数据库
    logger.info("📊 初始化数据库...")
    try:
        init_database()
        logger.success("✅ 数据库初始化成功")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        return False
    
    # 检查XtQuant服务
    logger.info("🔌 检查XtQuant服务...")
    xtquant_service = XtQuantService()
    try:
        await xtquant_service.start()
        
        # 测试数据连接
        if xtquant_service.is_data_connected:
            logger.success("✅ XtQuant数据服务连接成功")
        else:
            logger.error("❌ XtQuant数据服务连接失败")
            return False
        
        # 测试交易连接（可能失败，这是正常的）
        if xtquant_service.is_trading_connected:
            logger.success("✅ XtQuant交易服务连接成功")
        else:
            logger.warning("⚠️ XtQuant交易服务连接失败，请确保QMT客户端已启动并登录")
            logger.info("💡 提示: 数据服务可以正常工作，交易功能需要QMT客户端支持")
        
    except Exception as e:
        logger.error(f"❌ XtQuant服务启动失败: {e}")
        return False
    finally:
        await xtquant_service.stop()
    
    return True


def main():
    """主函数"""
    # 检查系统状态
    if not asyncio.run(check_system_status()):
        logger.error("❌ 系统检查失败，请检查配置")
        return
    
    logger.success("🎉 系统检查通过，启动Web服务...")
    
    # 启动FastAPI应用
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("👋 用户中断，正在关闭系统...")
    except Exception as e:
        logger.error(f"❌ 服务启动失败: {e}")


if __name__ == "__main__":
    main()