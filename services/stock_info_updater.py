#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票基础信息更新服务
负责每日更新股票基础信息表，包括新股上市、ST状态变更等
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.database import get_db, StockBasicInfo, init_database
from services.xtquant_service import XtQuantService
from services.stock_info_cache_service import StockInfoCacheService
from core.time_utils import TimeUtils
from config import get_settings


class StockInfoUpdater:
    """股票基础信息更新器（单例模式）"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StockInfoUpdater, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # 避免重复初始化
        if self._initialized:
            return
            
        self.xtquant_service = XtQuantService()
        self.settings = get_settings()
        self.time_utils = TimeUtils()
        self.is_running = False
        self.update_task = None
        self._initialized = True
    
    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
        
    async def start_daily_update_scheduler(self):
        """启动每日更新调度器"""
        if self.is_running:
            logger.warning("股票信息更新调度器已在运行")
            return
            
        self.is_running = True
        self.update_task = asyncio.create_task(self._daily_update_loop())
        logger.info("股票基础信息每日更新调度器已启动")
        
    async def stop_daily_update_scheduler(self):
        """停止每日更新调度器"""
        self.is_running = False
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
        logger.info("股票基础信息每日更新调度器已停止")
        
    async def _daily_update_loop(self):
        """每日更新循环"""
        while self.is_running:
            try:
                # 检查是否为交易日
                if not self.time_utils.is_trading_day():
                    logger.info("今日非交易日，跳过股票基础信息更新")
                    await asyncio.sleep(3600)  # 1小时后再检查
                    continue
                    
                # 检查是否到了更新时间（每日9:00更新）
                now = datetime.now()
                update_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
                
                if now < update_time:
                    # 还没到更新时间，等待
                    sleep_seconds = (update_time - now).total_seconds()
                    logger.info(f"等待到更新时间 {update_time.strftime('%H:%M:%S')}，还需等待 {sleep_seconds:.0f} 秒")
                    await asyncio.sleep(min(sleep_seconds, 3600))
                    continue
                    
                # 检查今日是否已更新
                if await self._is_updated_today():
                    logger.info("今日股票基础信息已更新，等待明日")
                    # 等待到明日9点
                    tomorrow_update = update_time + timedelta(days=1)
                    sleep_seconds = (tomorrow_update - now).total_seconds()
                    await asyncio.sleep(min(sleep_seconds, 3600))
                    continue
                    
                # 执行更新
                logger.info("开始执行每日股票基础信息更新")
                await self.update_all_stock_basic_info()
                
                # 更新完成后等待到明日
                tomorrow_update = update_time + timedelta(days=1)
                sleep_seconds = (tomorrow_update - datetime.now()).total_seconds()
                logger.info(f"股票基础信息更新完成，等待明日更新，休眠 {sleep_seconds:.0f} 秒")
                await asyncio.sleep(min(sleep_seconds, 3600))
                
            except Exception as e:
                logger.error(f"每日更新循环出错: {e}")
                await asyncio.sleep(300)  # 出错后等待5分钟再试
                
    async def _is_updated_today(self) -> bool:
        """检查今日是否已更新"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            def check_update(db: Session) -> bool:
                # 检查今日是否有更新记录
                result = db.execute(text("""
                    SELECT COUNT(*) as count 
                    FROM stock_basic_info 
                    WHERE DATE(updated_at) = :today
                """), {'today': today})
                count = result.fetchone()[0]
                return count > 0
                
            db_gen = get_db()
            db = next(db_gen)
            try:
                return check_update(db)
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"检查今日更新状态失败: {e}")
            return False
            
    async def update_all_stock_basic_info(self) -> Dict[str, Any]:
        """更新所有股票基础信息
        
        Returns:
            更新结果统计
        """
        start_time = time.time()
        logger.info("开始更新所有股票基础信息")
        
        try:
            # 获取所有A股股票列表
            stock_list = await self._get_all_a_share_stocks()
            if not stock_list:
                logger.warning("未获取到股票列表")
                return {'success': False, 'message': '未获取到股票列表'}
                
            logger.info(f"获取到 {len(stock_list)} 只股票，开始更新基础信息")
            
            # 批量更新
            results = await self.xtquant_service.batch_update_stock_basic_info(stock_list)
            
            # 统计结果
            success_count = sum(1 for success in results.values() if success)
            failed_count = len(results) - success_count
            
            # 记录更新日志
            await self._log_update_result({
                'total_count': len(stock_list),
                'success_count': success_count,
                'failed_count': failed_count,
                'duration': time.time() - start_time
            })
            
            # 刷新股票信息缓存
            try:
                cache_service = StockInfoCacheService()
                await cache_service.refresh_cache()
                logger.info("股票信息缓存刷新完成")
            except Exception as e:
                logger.error(f"刷新股票信息缓存失败: {e}")
            
            logger.info(f"股票基础信息更新完成: 成功 {success_count}/{len(stock_list)}, 耗时 {time.time() - start_time:.2f}秒")
            
            return {
                'success': True,
                'total_count': len(stock_list),
                'success_count': success_count,
                'failed_count': failed_count,
                'duration': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"更新所有股票基础信息失败: {e}")
            return {'success': False, 'message': str(e)}
            
    async def _get_all_a_share_stocks(self) -> List[str]:
        """获取所有A股股票代码列表"""
        try:
            # 获取沪深两市股票列表
            sz_stocks = await self.xtquant_service.get_stock_list("SZ")
            sh_stocks = await self.xtquant_service.get_stock_list("SH")
            
            all_stocks = [stock['stock_code'] for stock in sz_stocks + sh_stocks]     
            logger.info(f"获取到A股股票 {len(all_stocks)} 只")
            return all_stocks
            
        except Exception as e:
            logger.error(f"获取A股股票列表失败: {e}")
            return []
            
    async def _log_update_result(self, result: Dict[str, Any]):
        """记录更新结果到数据库"""
        try:
            def log_result(db: Session):
                message = f"股票基础信息更新完成: 总数{result['total_count']}, 成功{result['success_count']}, 失败{result['failed_count']}, 耗时{result['duration']:.2f}秒"
                db.execute(text("""
                    INSERT INTO notification_logs 
                    (type, title, content, level, is_sent, created_at) 
                    VALUES (:type, :title, :content, :level, :is_sent, :created_at)
                """), {
                    'type': 'SYSTEM',
                    'title': '股票基础信息更新',
                    'content': message,
                    'level': 'INFO',
                    'is_sent': False,
                    'created_at': datetime.now()
                })
                db.commit()
                
            db_gen = get_db()
            db = next(db_gen)
            try:
                log_result(db)
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"记录更新结果失败: {e}")
            
    async def manual_update_stock_info(self, stock_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """手动更新股票基础信息
        
        Args:
            stock_codes: 指定股票代码列表，为None时更新所有股票
            
        Returns:
            更新结果
        """
        if stock_codes is None:
            return await self.update_all_stock_basic_info()
        else:
            logger.info(f"手动更新指定股票基础信息: {len(stock_codes)} 只")
            results = await self.xtquant_service.batch_update_stock_basic_info(stock_codes)
            
            success_count = sum(1 for success in results.values() if success)
            failed_count = len(results) - success_count
            
            # 如果有成功更新的股票，刷新缓存
            if success_count > 0:
                try:
                    cache_service = StockInfoCacheService()
                    await cache_service.refresh_cache()
                    logger.info("股票信息缓存刷新完成")
                except Exception as e:
                    logger.error(f"刷新股票信息缓存失败: {e}")
            
            logger.info(f"手动更新完成: 成功 {success_count}/{len(stock_codes)}")
            
            return {
                'success': True,
                'total_count': len(stock_codes),
                'success_count': success_count,
                'failed_count': failed_count,
                'results': results
            }
            
    async def get_update_status(self) -> Dict[str, Any]:
        """获取更新状态"""
        try:
            # 确保数据库已初始化
            init_database()
            
            def get_status(db: Session) -> Dict[str, Any]:
                # 获取最近更新时间
                result = db.execute(text("""
                    SELECT MAX(updated_at) as last_update,
                           COUNT(*) as total_count,
                           COUNT(CASE WHEN is_st = true THEN 1 END) as st_count,
                           COUNT(CASE WHEN is_trading = true THEN 1 END) as trading_count
                    FROM stock_basic_info
                """))
                row = result.fetchone()
                
                return {
                    'last_update': row[0].strftime('%Y-%m-%d %H:%M:%S') if row[0] else None,
                    'total_count': row[1] or 0,
                    'st_count': row[2] or 0,
                    'trading_count': row[3] or 0,
                    'is_scheduler_running': self.is_running
                }
                
            db_gen = get_db()
            db = next(db_gen)
            try:
                return get_status(db)
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取更新状态失败: {e}")
            return {
                'last_update': None,
                'total_count': 0,
                'st_count': 0,
                'trading_count': 0,
                'is_scheduler_running': self.is_running,
                'error': str(e)
            }


# 全局单例实例
stock_info_updater = StockInfoUpdater.get_instance()


async def main():
    """测试主函数"""
    updater = StockInfoUpdater()
    
    # 测试手动更新几只股票
    test_stocks = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH']
    result = await updater.manual_update_stock_info(test_stocks)
    print(f"更新结果: {result}")
    
    # 获取更新状态
    status = await updater.get_update_status()
    print(f"更新状态: {status}")


if __name__ == "__main__":
    asyncio.run(main())