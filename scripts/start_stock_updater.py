#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动股票基础信息每日更新服务
"""

import asyncio
import sys
from pathlib import Path
import signal

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.stock_info_updater import StockInfoUpdater
from loguru import logger


class StockUpdaterService:
    """股票信息更新服务"""
    
    def __init__(self):
        self.updater = StockInfoUpdater()
        self.running = False
    
    async def start(self):
        """启动服务"""
        logger.info("启动股票基础信息更新服务...")
        
        try:
            # 启动调度器
            await self.updater.start_scheduler()
            self.running = True
            
            logger.info("股票基础信息更新服务已启动")
            logger.info("服务将在每个交易日的 09:00 自动更新股票基础信息")
            
            # 显示当前状态
            await self.show_status()
            
            # 询问是否立即执行一次更新
            print("\n是否立即执行一次股票基础信息更新？(y/n): ", end="")
            choice = input().strip().lower()
            
            if choice in ['y', 'yes', '是']:
                logger.info("开始立即更新股票基础信息...")
                await self.manual_update()
            
            # 保持服务运行
            logger.info("服务正在运行中，按 Ctrl+C 停止服务")
            await self.keep_running()
            
        except KeyboardInterrupt:
            logger.info("收到停止信号，正在关闭服务...")
        except Exception as e:
            logger.error(f"服务启动失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
        finally:
            await self.stop()
    
    async def stop(self):
        """停止服务"""
        if self.running:
            logger.info("正在停止股票基础信息更新服务...")
            await self.updater.stop_scheduler()
            self.running = False
            logger.info("股票基础信息更新服务已停止")
    
    async def show_status(self):
        """显示服务状态"""
        try:
            status = await self.updater.get_update_status()
            
            print("\n=== 股票基础信息更新服务状态 ===")
            print(f"调度器运行状态: {'运行中' if status.get('is_scheduler_running') else '已停止'}")
            print(f"最后更新时间: {status.get('last_update', '未知')}")
            print(f"数据库中股票总数: {status.get('total_count', 0)}")
            print(f"ST股票数量: {status.get('st_count', 0)}")
            print(f"可交易股票数量: {status.get('trading_count', 0)}")
            
            if status.get('error'):
                print(f"错误信息: {status['error']}")
            
            print("=" * 40)
            
        except Exception as e:
            logger.error(f"获取服务状态失败: {e}")
    
    async def manual_update(self):
        """手动执行更新"""
        try:
            # 获取A股股票列表进行更新
            a_share_stocks = self.updater._get_a_share_stock_list()
            
            if not a_share_stocks:
                logger.warning("未找到A股股票列表，使用测试股票进行更新")
                a_share_stocks = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '000858.SZ']
            
            # 限制更新数量，避免过长时间
            if len(a_share_stocks) > 50:
                logger.info(f"股票数量较多({len(a_share_stocks)})，仅更新前50只股票作为示例")
                a_share_stocks = a_share_stocks[:50]
            
            logger.info(f"开始更新 {len(a_share_stocks)} 只股票的基础信息...")
            
            result = await self.updater.manual_update_stock_info(a_share_stocks)
            
            if result.get('success'):
                logger.info(f"✓ 手动更新完成: 成功 {result['success_count']}/{result['total_count']}")
            else:
                logger.error(f"✗ 手动更新失败: {result.get('message', '未知错误')}")
            
            # 显示更新后的状态
            await self.show_status()
            
        except Exception as e:
            logger.error(f"手动更新失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
    
    async def keep_running(self):
        """保持服务运行"""
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass


def setup_signal_handlers(service):
    """设置信号处理器"""
    def signal_handler(signum, frame):
        logger.info(f"收到信号 {signum}，正在停止服务...")
        service.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """主函数"""
    print("股票基础信息每日更新服务")
    print("=" * 40)
    
    service = StockUpdaterService()
    setup_signal_handlers(service)
    
    await service.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        logger.error(f"服务运行异常: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")