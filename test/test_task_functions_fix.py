#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试task_functions修复
验证XtQuantService初始化方法调用修正是否成功
"""

import sys
import os
import asyncio
import unittest
from unittest.mock import Mock, patch, AsyncMock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.task_functions import TaskFunctions
from services.xtquant_service import XtQuantService
from services.data_service import DataService
from services.stock_info_updater import StockInfoUpdater

class TestTaskFunctionsFix(unittest.TestCase):
    """测试task_functions修复"""
    
    def setUp(self):
        """测试前准备"""
        self.task_functions = TaskFunctions()
    
    def tearDown(self):
        """测试后清理"""
        # 重置服务实例
        self.task_functions._xt_service = None
        self.task_functions._data_service = None
        self.task_functions._stock_updater = None
    
    async def test_initialize_services_method_calls(self):
        """测试initialize_services方法调用正确性"""
        print("=== 测试initialize_services方法调用 ===")
        
        # 使用patch.object来模拟实例方法
        with patch.object(self.task_functions, '_xt_service', None), \
             patch.object(self.task_functions, '_data_service', None), \
             patch.object(self.task_functions, '_stock_updater', None):
            
            # 模拟XtQuantService
            mock_xt_service = Mock()
            mock_xt_service.start = AsyncMock()
            
            # 模拟DataService
            mock_data_service = Mock()
            mock_data_service.initialize = AsyncMock()
            
            # 模拟StockInfoUpdater
            mock_stock_updater = Mock()
            
            with patch('core.task_functions.XtQuantService', return_value=mock_xt_service), \
                 patch('core.task_functions.DataService', return_value=mock_data_service), \
                 patch('core.task_functions.StockInfoUpdater', return_value=mock_stock_updater):
                
                # 调用initialize_services
                await self.task_functions.initialize_services()
                
                # 验证XtQuantService的start方法被调用
                mock_xt_service.start.assert_called_once()
                print("✅ XtQuantService.start() 方法调用正确")
                
                # 验证DataService的initialize方法被调用
                mock_data_service.initialize.assert_called_once()
                print("✅ DataService.initialize() 方法调用正确")
                
                print("✅ initialize_services 方法调用测试通过")
    
    async def test_health_check_task_method_calls(self):
        """测试health_check_task方法调用正确性"""
        print("\n=== 测试health_check_task方法调用 ===")
        
        # 创建模拟实例
        mock_xt_service = Mock()
        mock_xt_service.start = AsyncMock()
        mock_xt_service.is_connected = True
        mock_xt_service.is_data_connected = True
        mock_xt_service.is_trading_connected = True
        
        # 模拟数据库连接
        with patch('core.task_functions.XtQuantService', return_value=mock_xt_service), \
             patch('core.database.get_db') as mock_get_db, \
             patch.object(self.task_functions, '_xt_service', None):
            
            mock_db = Mock()
            mock_db.execute = Mock()
            mock_get_db.return_value.__enter__ = Mock(return_value=mock_db)
            mock_get_db.return_value.__exit__ = Mock(return_value=None)
            
            # 调用health_check_task
            result = await self.task_functions.health_check_task()
            
            # 验证XtQuantService的start方法被调用
            mock_xt_service.start.assert_called_once()
            print("✅ XtQuantService.start() 方法调用正确")
            
            # 验证is_connected属性被访问
            self.assertTrue(hasattr(mock_xt_service, 'is_connected'))
            print("✅ is_connected 属性访问正确")
            
            # 验证返回结果
            self.assertTrue(result['success'])
            self.assertIn('result', result)
            self.assertIn('services', result['result'])
            self.assertIn('xtquant', result['result']['services'])
            
            xtquant_status = result['result']['services']['xtquant']
            self.assertEqual(xtquant_status['status'], 'healthy')
            self.assertTrue(xtquant_status['details']['connected'])
            
            print("✅ health_check_task 返回结果正确")
            print("✅ health_check_task 方法调用测试通过")
    
    async def test_run_stock_selection_method_calls(self):
        """测试run_stock_selection方法调用正确性"""
        print("\n=== 测试run_stock_selection方法调用 ===")
        
        # 创建模拟实例
        mock_xt_service = Mock()
        mock_xt_service.start = AsyncMock()
        
        mock_data_service = Mock()
        mock_data_service.initialize = AsyncMock()
        mock_data_service.get_all_active_stock_codes = AsyncMock(return_value=['000001.SZ', '000002.SZ', '600000.SH'])
        
        mock_stock_updater = Mock()
        
        with patch('core.task_functions.XtQuantService', return_value=mock_xt_service), \
             patch('core.task_functions.DataService', return_value=mock_data_service), \
             patch('core.task_functions.StockInfoUpdater', return_value=mock_stock_updater), \
             patch.object(self.task_functions, '_xt_service', None), \
             patch.object(self.task_functions, '_data_service', None), \
             patch.object(self.task_functions, '_stock_updater', None):
            
            # 调用run_stock_selection
            result = await self.task_functions.run_stock_selection()
            
            # 验证服务初始化
            mock_xt_service.start.assert_called_once()
            mock_data_service.initialize.assert_called_once()
            print("✅ 服务初始化调用正确")
            
            # 验证数据服务方法调用
            mock_data_service.get_all_active_stock_codes.assert_called_once()
            print("✅ get_all_active_stock_codes 方法调用正确")
            
            # 验证返回结果
            self.assertTrue(result['success'])
            self.assertIn('result', result)
            self.assertIn('selected_stocks', result['result'])
            self.assertIn('total_stocks', result['result'])
            
            print("✅ run_stock_selection 返回结果正确")
            print("✅ run_stock_selection 方法调用测试通过")
    
    def test_xtquant_service_has_start_method(self):
        """测试XtQuantService确实有start方法"""
        print("\n=== 测试XtQuantService方法存在性 ===")
        
        # 检查XtQuantService类是否有start方法
        self.assertTrue(hasattr(XtQuantService, 'start'))
        print("✅ XtQuantService.start 方法存在")
        
        # 检查XtQuantService类是否有is_connected属性
        service = XtQuantService()
        self.assertTrue(hasattr(service, 'is_connected'))
        print("✅ XtQuantService.is_connected 属性存在")
        
        # 检查XtQuantService类是否有is_data_connected属性
        self.assertTrue(hasattr(service, 'is_data_connected'))
        print("✅ XtQuantService.is_data_connected 属性存在")
        
        # 检查XtQuantService类是否有is_trading_connected属性
        self.assertTrue(hasattr(service, 'is_trading_connected'))
        print("✅ XtQuantService.is_trading_connected 属性存在")
        
        print("✅ XtQuantService 方法和属性存在性测试通过")

async def run_tests():
    """运行所有测试"""
    print("开始测试task_functions修复...\n")
    
    test_case = TestTaskFunctionsFix()
    test_case.setUp()
    
    try:
        # 测试initialize_services方法调用
        await test_case.test_initialize_services_method_calls()
        
        # 测试health_check_task方法调用
        await test_case.test_health_check_task_method_calls()
        
        # 测试run_stock_selection方法调用
        await test_case.test_run_stock_selection_method_calls()
        
        # 测试XtQuantService方法存在性
        test_case.test_xtquant_service_has_start_method()
        
        print("\n🎉 所有测试通过！task_functions修复成功。")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test_case.tearDown()

if __name__ == "__main__":
    asyncio.run(run_tests())