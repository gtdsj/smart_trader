#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统启动服务
负责在系统启动时初始化各种服务和缓存
"""

import asyncio
from loguru import logger
from typing import Dict, Any

from core.database import init_database
from services.stock_info_cache_service import StockInfoCacheService
from services.stock_info_updater import StockInfoUpdater


class StartupService:
    """系统启动服务"""
    
    def __init__(self):
        self.is_initialized = False
        
    async def initialize_system(self) -> Dict[str, Any]:
        """初始化系统
        
        Returns:
            初始化结果
        """
        try:
            logger.info("开始初始化系统...")
            
            # 1. 初始化数据库
            logger.info("初始化数据库...")
            init_database()
            logger.info("数据库初始化完成")
            
            # 2. 初始化股票信息缓存
            logger.info("初始化股票信息缓存...")
            cache_service = StockInfoCacheService()
            await cache_service.initialize()
            logger.info("股票信息缓存初始化完成")
            
            # 3. 启动股票信息定时更新器
            logger.info("启动股票信息定时更新器...")
            updater = StockInfoUpdater()
            await updater.start_daily_update_scheduler()
            logger.info("股票信息定时更新器启动完成")
            
            self.is_initialized = True
            logger.info("系统初始化完成")
            
            return {
                'success': True,
                'message': '系统初始化完成',
                'services': {
                    'database': True,
                    'stock_cache': True,
                    'stock_updater': True
                }
            }
            
        except Exception as e:
            logger.error(f"系统初始化失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return {
                'success': False,
                'message': f'系统初始化失败: {str(e)}',
                'error': str(e)
            }
            
    async def shutdown_system(self) -> Dict[str, Any]:
        """关闭系统
        
        Returns:
            关闭结果
        """
        try:
            logger.info("开始关闭系统...")
            
            # 停止股票信息定时更新器
            logger.info("停止股票信息定时更新器...")
            updater = StockInfoUpdater()
            await updater.stop_daily_update_scheduler()
            logger.info("股票信息定时更新器已停止")
            
            # 清理股票信息缓存
            logger.info("清理股票信息缓存...")
            cache_service = StockInfoCacheService()
            cache_service.clear_cache()
            logger.info("股票信息缓存已清理")
            
            self.is_initialized = False
            logger.info("系统关闭完成")
            
            return {
                'success': True,
                'message': '系统关闭完成'
            }
            
        except Exception as e:
            logger.error(f"系统关闭失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return {
                'success': False,
                'message': f'系统关闭失败: {str(e)}',
                'error': str(e)
            }
            
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态
        
        Returns:
            系统状态信息
        """
        try:
            # 检查股票缓存状态
            cache_service = StockInfoCacheService()
            cache_status = cache_service.get_cache_status()
            
            # 检查更新器状态
            updater = StockInfoUpdater()
            updater_status = updater.is_running
            
            return {
                'is_initialized': self.is_initialized,
                'cache_status': cache_status,
                'updater_running': updater_status,
                'timestamp': cache_status.get('last_update_time')
            }
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {
                'is_initialized': self.is_initialized,
                'error': str(e)
            }


# 全局实例
startup_service = StartupService()


async def main():
    """测试主函数"""
    service = StartupService()
    
    # 初始化系统
    result = await service.initialize_system()
    print(f"初始化结果: {result}")
    
    # 获取系统状态
    status = service.get_system_status()
    print(f"系统状态: {status}")
    
    # 等待一段时间
    await asyncio.sleep(5)
    
    # 关闭系统
    shutdown_result = await service.shutdown_system()
    print(f"关闭结果: {shutdown_result}")


if __name__ == "__main__":
    asyncio.run(main())