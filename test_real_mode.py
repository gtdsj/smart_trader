#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试真实模式下的系统运行
"""

import asyncio
import sys
import os
from pathlib import Path
from loguru import logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import get_settings
from core.database import init_database
from services.xtquant_service import XtQuantService
from services.trading_service import TradingService
from services.data_service import DataService


async def test_real_mode():
    """测试真实模式下的系统功能"""
    logger.info("开始测试真实模式...")
    
    try:
        # 1. 检查配置
        settings = get_settings()
        logger.info(f"当前配置:")
        logger.info(f"  - 模拟模式: {getattr(settings, 'simulation_mode', '未设置')}")
        logger.info(f"  - 数据库内存模式: {settings.database.memory}")
        logger.info(f"  - 数据库路径: {settings.database.path}")
        logger.info(f"  - XtQuant路径: {settings.xtquant.path}")
        logger.info(f"  - 账户ID: {settings.xtquant.account_id}")
        
        # 2. 初始化数据库
        logger.info("初始化数据库...")
        init_database()
        logger.info("数据库初始化完成")
        
        # 3. 测试XtQuant服务连接
        logger.info("测试XtQuant服务连接...")
        xtquant_service = XtQuantService()
        
        try:
            await xtquant_service.start()
            logger.info(f"XtQuant服务连接状态: {xtquant_service.is_connected}")
            logger.info(f"  - 数据连接: {xtquant_service.is_data_connected}")
            logger.info(f"  - 交易连接: {xtquant_service.is_trading_connected}")
            
            if xtquant_service.is_connected:
                logger.success("✅ XtQuant服务连接成功！")
                
                # 4. 测试基本功能
                logger.info("测试获取股票列表...")
                stock_list = await xtquant_service.get_stock_list("SH")
                logger.info(f"获取到 {len(stock_list)} 只上证股票")
                
                if stock_list:
                    # 显示前5只股票
                    for i, stock in enumerate(stock_list[:5]):
                        logger.info(f"  {i+1}. {stock['stock_code']} - {stock['stock_name']}")
                
                # 5. 测试历史数据获取
                if stock_list:
                    test_stock = stock_list[0]['stock_code']
                    logger.info(f"测试获取 {test_stock} 的历史数据...")
                    
                    from services.xtquant_service import Period
                    history_data = await xtquant_service.get_history_data(
                        [test_stock], 
                        period=Period.DAILY,
                        count=10
                    )
                    
                    if test_stock in history_data and not history_data[test_stock].empty:
                        df = history_data[test_stock]
                        logger.info(f"获取到 {len(df)} 条历史数据")
                        logger.info(f"数据列: {list(df.columns)}")
                        logger.info(f"最新数据: {df.iloc[-1].to_dict()}")
                    else:
                        logger.warning("未获取到历史数据")
                
            else:
                logger.error("❌ XtQuant服务连接失败")
                
        except Exception as e:
            logger.error(f"❌ XtQuant服务启动失败: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
        finally:
            # 停止服务
            try:
                await xtquant_service.stop()
                logger.info("XtQuant服务已停止")
            except Exception as e:
                logger.error(f"停止XtQuant服务失败: {e}")
        
        # 6. 测试交易服务
        logger.info("测试交易服务...")
        trading_service = TradingService()
        
        try:
            await trading_service.start()
            logger.info(f"交易服务连接状态: {trading_service.connected}")
            
            if trading_service.connected:
                logger.success("✅ 交易服务连接成功！")
            else:
                logger.error("❌ 交易服务连接失败")
                
        except Exception as e:
            logger.error(f"❌ 交易服务启动失败: {e}")
        finally:
            try:
                await trading_service.stop()
                logger.info("交易服务已停止")
            except Exception as e:
                logger.error(f"停止交易服务失败: {e}")
        
        logger.success("✅ 真实模式测试完成")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return False
    
    return True


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # 运行测试
    success = asyncio.run(test_real_mode())
    
    if success:
        logger.success("🎉 所有测试通过！系统已配置为真实模式")
        sys.exit(0)
    else:
        logger.error("💥 测试失败！请检查配置和连接")
        sys.exit(1)