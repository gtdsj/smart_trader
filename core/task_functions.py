#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务执行函数模块
定义各种定时任务的具体执行逻辑
"""

import asyncio
from datetime import datetime, date
from typing import Dict, Any, Optional
from loguru import logger

from services.xtquant_service import XtQuantService
from services.stock_info_updater import StockInfoUpdater
from services.data_service import DataService
from core.time_utils import TimeUtils


class TaskFunctions:
    """任务执行函数集合"""
    
    def __init__(self):
        self._xt_service: Optional[XtQuantService] = None
        self._stock_updater: Optional[StockInfoUpdater] = None
        self._data_service: Optional[DataService] = None
        
    async def initialize_services(self):
        """初始化服务"""
        try:
            # 初始化XtQuant服务
            if not self._xt_service:
                self._xt_service = XtQuantService()
                await self._xt_service.start()
                
            # 初始化股票信息更新器
            if not self._stock_updater:
                self._stock_updater = StockInfoUpdater()
                
            # 初始化数据服务
            if not self._data_service:
                self._data_service = DataService()
                await self._data_service.initialize()
                
            logger.info("任务执行服务初始化完成")
            
        except Exception as e:
            logger.error(f"任务执行服务初始化失败: {e}")
            raise
            
    async def cleanup_services(self):
        """清理服务"""
        try:
            if self._xt_service:
                await self._xt_service.cleanup()
                
            if self._data_service:
                await self._data_service.cleanup()
                
            logger.info("任务执行服务清理完成")
            
        except Exception as e:
            logger.error(f"任务执行服务清理失败: {e}")
            
    async def update_stock_basic_info(self, **kwargs) -> Dict[str, Any]:
        """更新股票基础信息任务"""
        logger.info("开始执行股票基础信息更新任务")
        
        try:
            await self.initialize_services()
            
            if not self._stock_updater:
                raise RuntimeError("股票信息更新器未初始化")
                
            # 执行更新
            result = await self._stock_updater.update_all_stocks()
            
            logger.info(f"股票基础信息更新完成: {result}")
            return {
                'success': True,
                'message': '股票基础信息更新成功',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"股票基础信息更新失败: {e}")
            return {
                'success': False,
                'message': f'股票基础信息更新失败: {str(e)}',
                'error': str(e)
            }
            
    async def update_daily_stock_data(self, **kwargs) -> Dict[str, Any]:
        """更新日线股票数据任务"""
        logger.info("开始执行日线股票数据更新任务")
        
        try:
            # 检查是否为交易日
            today = date.today()
            if not TimeUtils.is_trading_day(today):
                message = "今日非交易日，跳过日线数据更新"
                logger.info(message)
                return {
                    'success': True,
                    'message': message,
                    'skipped': True
                }
                
            await self.initialize_services()
            
            if not self._data_service:
                raise RuntimeError("数据服务未初始化")
                
            # 获取所有活跃股票代码
            stock_codes = await self._data_service.get_all_active_stock_codes()
            
            if not stock_codes:
                message = "未找到活跃股票代码"
                logger.warning(message)
                return {
                    'success': False,
                    'message': message
                }
                
            # 更新日线数据
            success_count = 0
            failed_count = 0
            
            for stock_code in stock_codes:
                try:
                    # 获取并保存当日数据
                    data = await self._data_service.get_daily_data(
                        stock_code, today, today
                    )
                    
                    if data and not data.empty:
                        await self._data_service.save_daily_data(stock_code, data)
                        success_count += 1
                    else:
                        logger.warning(f"股票 {stock_code} 当日无数据")
                        
                except Exception as e:
                    logger.error(f"更新股票 {stock_code} 日线数据失败: {e}")
                    failed_count += 1
                    
                # 避免请求过于频繁
                await asyncio.sleep(0.1)
                
            result = {
                'total_stocks': len(stock_codes),
                'success_count': success_count,
                'failed_count': failed_count,
                'update_date': today.isoformat()
            }
            
            logger.info(f"日线股票数据更新完成: {result}")
            return {
                'success': True,
                'message': '日线股票数据更新成功',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"日线股票数据更新失败: {e}")
            return {
                'success': False,
                'message': f'日线股票数据更新失败: {str(e)}',
                'error': str(e)
            }
            
    async def run_stock_selection(self, **kwargs) -> Dict[str, Any]:
        """执行选股任务"""
        logger.info("开始执行选股任务")
        
        try:
            await self.initialize_services()
            
            if not self._data_service:
                raise RuntimeError("数据服务未初始化")
                
            # 这里可以实现具体的选股逻辑
            # 目前先实现一个简单的示例
            
            # 获取所有活跃股票
            stock_codes = await self._data_service.get_all_active_stock_codes()
            
            if not stock_codes:
                message = "未找到活跃股票代码"
                logger.warning(message)
                return {
                    'success': False,
                    'message': message
                }
                
            # 简单的选股逻辑示例：随机选择一些股票
            import random
            selected_count = min(10, len(stock_codes))  # 最多选择10只股票
            selected_stocks = random.sample(stock_codes, selected_count)
            
            result = {
                'total_stocks': len(stock_codes),
                'selected_stocks': selected_stocks,
                'selected_count': len(selected_stocks),
                'selection_date': date.today().isoformat(),
                'selection_method': 'random_sample'
            }
            
            logger.info(f"选股任务完成: 从 {len(stock_codes)} 只股票中选择了 {len(selected_stocks)} 只")
            return {
                'success': True,
                'message': '选股任务执行成功',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"选股任务执行失败: {e}")
            return {
                'success': False,
                'message': f'选股任务执行失败: {str(e)}',
                'error': str(e)
            }
            
    async def health_check_task(self, **kwargs) -> Dict[str, Any]:
        """系统健康检查任务"""
        logger.info("开始执行系统健康检查任务")
        
        try:
            health_status = {
                'timestamp': datetime.now().isoformat(),
                'services': {}
            }
            
            # 检查XtQuant服务
            try:
                if not self._xt_service:
                    self._xt_service = XtQuantService()
                    await self._xt_service.start()
                    
                is_connected = self._xt_service.is_connected
                health_status['services']['xtquant'] = {
                    'status': 'healthy' if is_connected else 'unhealthy',
                    'details': {
                        'connected': is_connected,
                        'data_connected': self._xt_service.is_data_connected,
                        'trading_connected': self._xt_service.is_trading_connected
                    }
                }
            except Exception as e:
                health_status['services']['xtquant'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                
            # 检查数据库连接
            try:
                from core.database import get_db
                with get_db() as db:
                    # 简单查询测试数据库连接
                    db.execute("SELECT 1")
                    health_status['services']['database'] = {
                        'status': 'healthy'
                    }
            except Exception as e:
                health_status['services']['database'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                
            # 计算整体健康状态
            all_healthy = all(
                service['status'] == 'healthy' 
                for service in health_status['services'].values()
            )
            
            health_status['overall_status'] = 'healthy' if all_healthy else 'unhealthy'
            
            logger.info(f"系统健康检查完成: {health_status['overall_status']}")
            return {
                'success': True,
                'message': '系统健康检查完成',
                'result': health_status
            }
            
        except Exception as e:
            logger.error(f"系统健康检查失败: {e}")
            return {
                'success': False,
                'message': f'系统健康检查失败: {str(e)}',
                'error': str(e)
            }


# 创建全局任务函数实例
task_functions = TaskFunctions()


# 导出任务函数
def get_task_functions() -> Dict[str, callable]:
    """获取所有任务函数"""
    return {
        'update_stock_basic_info': task_functions.update_stock_basic_info,
        'update_daily_stock_data': task_functions.update_daily_stock_data,
        'run_stock_selection': task_functions.run_stock_selection,
        'health_check_task': task_functions.health_check_task,
    }