# -*- coding: utf-8 -*-
"""
股票信息缓存服务集成测试
验证StockInfoCacheService在服务启动时的初始化和股票信息更新后的缓存刷新功能
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# 添加项目根目录到路径
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.stock_info_cache_service import StockInfoCacheService
from api.business.data import router as data_router
from fastapi import FastAPI

class TestStockCacheIntegration:
    """股票信息缓存服务集成测试类"""
    
    def setup_method(self):
        """测试前准备"""
        # 重置单例实例
        if hasattr(StockInfoCacheService, '_instance'):
            StockInfoCacheService._instance = None
        
        self.cache_service = StockInfoCacheService()
    
    def test_cache_service_singleton(self):
        """测试缓存服务单例模式"""
        print("\n=== 测试缓存服务单例模式 ===")
        
        # 创建多个实例
        service1 = StockInfoCacheService()
        service2 = StockInfoCacheService()
        
        # 验证是同一个实例
        assert service1 is service2, "StockInfoCacheService应该是单例模式"
        assert id(service1) == id(service2), "实例ID应该相同"
        
        print(f"✅ 单例模式验证通过，实例ID: {id(service1)}")
    
    @patch('services.stock_info_cache_service.get_db')
    def test_cache_service_initialize(self, mock_get_db):
        """测试缓存服务初始化"""
        print("\n=== 测试缓存服务初始化 ===")
        
        # 模拟数据库数据
        mock_stock_data = [
            Mock(
                stock_code='000001.SZ',
                stock_name='平安银行',
                exchange='SZSE',
                listing_date=datetime(2000, 1, 1),
                is_st=False,
                is_trading=True,
                price_tick=0.01,
                updated_at=datetime.now()
            ),
            Mock(
                stock_code='000002.SZ',
                stock_name='万科A',
                exchange='SZSE',
                listing_date=datetime(1991, 1, 1),
                is_st=False,
                is_trading=True,
                price_tick=0.01,
                updated_at=datetime.now()
            ),
            Mock(
                stock_code='600000.SH',
                stock_name='浦发银行',
                exchange='SSE',
                listing_date=datetime(1999, 11, 10),
                is_st=False,
                is_trading=True,
                price_tick=0.01,
                updated_at=datetime.now()
            )
        ]
        
        # 模拟数据库会话
        mock_db = Mock()
        mock_db.query.return_value.all.return_value = mock_stock_data
        mock_get_db.return_value = iter([mock_db])
        
        # 测试初始化
        result = asyncio.run(self.cache_service.initialize())
        
        # 验证初始化结果
        assert result == True, "初始化应该成功"
        assert self.cache_service._is_initialized == True, "初始化状态应该为True"
        
        # 验证缓存数据
        cached_stocks = self.cache_service.get_all_stocks()
        assert len(cached_stocks) == 3, f"缓存中应该有3只股票，实际: {len(cached_stocks)}"
        
        # 验证具体股票信息
        stock_000001 = self.cache_service.get_stock_info('000001.SZ')
        assert stock_000001 is not None, "应该能找到000001.SZ"
        assert stock_000001['stock_name'] == '平安银行', f"股票名称错误: {stock_000001['stock_name']}"
        assert stock_000001['market'] == 'SZ', f"市场信息错误: {stock_000001['market']}"
        
        stock_600000 = self.cache_service.get_stock_info('600000.SH')
        assert stock_600000 is not None, "应该能找到600000.SH"
        assert stock_600000['stock_name'] == '浦发银行', f"股票名称错误: {stock_600000['stock_name']}"
        assert stock_600000['market'] == 'SH', f"市场信息错误: {stock_600000['market']}"
        
        print(f"✅ 缓存服务初始化成功，缓存了 {len(cached_stocks)} 只股票")
        print(f"✅ 股票信息验证通过")
    
    @patch('services.stock_info_cache_service.get_db')
    def test_cache_refresh(self, mock_get_db):
        """测试缓存刷新功能"""
        print("\n=== 测试缓存刷新功能 ===")
        
        # 初始数据
        initial_data = [
            Mock(
                stock_code='000001.SZ',
                stock_name='平安银行',
                exchange='SZSE',
                listing_date=datetime(2000, 1, 1),
                is_st=False,
                is_trading=True,
                price_tick=0.01,
                updated_at=datetime.now()
            )
        ]
        
        # 更新后的数据（新增一只股票）
        updated_data = [
            Mock(
                stock_code='000001.SZ',
                stock_name='平安银行',
                exchange='SZSE',
                listing_date=datetime(2000, 1, 1),
                is_st=False,
                is_trading=True,
                price_tick=0.01,
                updated_at=datetime.now()
            ),
            Mock(
                stock_code='000002.SZ',
                stock_name='万科A',
                exchange='SZSE',
                listing_date=datetime(1991, 1, 1),
                is_st=False,
                is_trading=True,
                price_tick=0.01,
                updated_at=datetime.now()
            )
        ]
        
        # 模拟数据库会话
        mock_db1 = Mock()
        mock_db2 = Mock()
        
        # 第一次调用返回初始数据
        mock_db1.query.return_value.all.return_value = initial_data
        
        # 第二次调用返回更新后的数据
        mock_db2.query.return_value.all.return_value = updated_data
        
        # 设置mock_get_db的side_effect，每次调用返回不同的数据库会话
        mock_get_db.side_effect = [iter([mock_db1]), iter([mock_db2])]
        
        # 初始化缓存
        result = asyncio.run(self.cache_service.initialize())
        assert result == True, "初始化应该成功"
        
        # 验证初始缓存
        initial_stocks = self.cache_service.get_all_stocks()
        assert len(initial_stocks) == 1, f"初始缓存应该有1只股票，实际: {len(initial_stocks)}"
        
        # 刷新缓存
        refresh_result = asyncio.run(self.cache_service.refresh_cache())
        assert refresh_result == True, "缓存刷新应该成功"
        
        # 验证刷新后的缓存
        refreshed_stocks = self.cache_service.get_all_stocks()
        assert len(refreshed_stocks) == 2, f"刷新后缓存应该有2只股票，实际: {len(refreshed_stocks)}"
        
        # 验证新增的股票
        stock_000002 = self.cache_service.get_stock_info('000002.SZ')
        assert stock_000002 is not None, "应该能找到新增的000002.SZ"
        assert stock_000002['stock_name'] == '万科A', f"新增股票名称错误: {stock_000002['stock_name']}"
        
        print(f"✅ 缓存刷新成功，从 {len(initial_stocks)} 只股票更新到 {len(refreshed_stocks)} 只股票")
        print(f"✅ 新增股票验证通过")
    
    def test_cache_service_methods(self):
        """测试缓存服务的各种查询方法"""
        print("\n=== 测试缓存服务查询方法 ===")
        
        # 手动设置测试数据
        test_data = {
            '000001.SZ': {
                'stock_code': '000001.SZ',
                'stock_name': '平安银行',
                'market': 'SZ',
                'exchange': 'SZSE',
                'is_st': False,
                'is_trading': True
            },
            '000002.SZ': {
                'stock_code': '000002.SZ',
                'stock_name': '万科A',
                'market': 'SZ',
                'exchange': 'SZSE',
                'is_st': False,
                'is_trading': True
            },
            '600000.SH': {
                'stock_code': '600000.SH',
                'stock_name': '浦发银行',
                'market': 'SH',
                'exchange': 'SSE',
                'is_st': False,
                'is_trading': True
            }
        }
        
        # 直接设置缓存数据
        with self.cache_service._cache_lock:
            self.cache_service._stock_cache = test_data
            self.cache_service._is_initialized = True
        
        # 测试单只股票查询
        stock_info = self.cache_service.get_stock_info('000001.SZ')
        assert stock_info is not None, "应该能找到000001.SZ"
        assert stock_info['stock_name'] == '平安银行', "股票名称应该正确"
        print("✅ 单只股票查询测试通过")
        
        # 测试批量股票查询
        batch_codes = ['000001.SZ', '600000.SH', '999999.SZ']  # 包含一个不存在的代码
        batch_info = self.cache_service.get_stocks_info(batch_codes)
        assert len(batch_info) == 2, f"批量查询应该返回2只股票，实际: {len(batch_info)}"
        assert '000001.SZ' in batch_info, "批量查询结果应该包含000001.SZ"
        assert '600000.SH' in batch_info, "批量查询结果应该包含600000.SH"
        assert '999999.SZ' not in batch_info, "批量查询结果不应该包含不存在的股票"
        print("✅ 批量股票查询测试通过")
        
        # 测试获取所有股票
        all_stocks = self.cache_service.get_all_stocks()
        assert len(all_stocks) == 3, f"应该有3只股票，实际: {len(all_stocks)}"
        print("✅ 获取所有股票测试通过")
        
        # 测试条件查询
        sz_stocks = self.cache_service.get_stocks_by_condition(market='SZ')
        assert len(sz_stocks) == 2, f"深圳市场应该有2只股票，实际: {len(sz_stocks)}"
        print("✅ 条件查询测试通过")
        
        # 测试股票搜索
        search_results = self.cache_service.search_stocks('平安')
        assert len(search_results) >= 1, "搜索'平安'应该有结果"
        assert any('平安银行' in stock['stock_name'] for stock in search_results), "搜索结果应该包含平安银行"
        print("✅ 股票搜索测试通过")
        
        # 测试缓存状态
        cache_status = self.cache_service.get_cache_status()
        assert cache_status['is_initialized'] == True, "缓存状态应该显示已初始化"
        assert cache_status['stock_count'] == 3, f"缓存状态应该显示3只股票，实际: {cache_status['stock_count']}"
        print("✅ 缓存状态查询测试通过")
    
    @patch('api.business.data.stock_info_updater')
    @patch('api.business.data.stock_cache_service')
    def test_api_integration(self, mock_cache_service, mock_updater):
        """测试API集成：股票信息更新后缓存刷新"""
        print("\n=== 测试API集成 ===")
        
        # 模拟更新器返回成功结果
        async def mock_update_result():
            return {
                'success': True,
                'total_count': 100,
                'success_count': 95,
                'failed_count': 5,
                'duration': 30.5
            }
        
        mock_updater.update_all_stock_basic_info.return_value = mock_update_result()
        
        # 模拟缓存服务刷新成功
        async def mock_refresh_result():
            return True
            
        mock_cache_service.refresh_cache.return_value = mock_refresh_result()
        
        # 创建测试应用
        app = FastAPI()
        app.include_router(data_router, prefix="/api/v1")
        
        # 创建测试客户端
        with TestClient(app) as client:
            # 调用股票信息更新接口
            response = client.post("/api/v1/data/update-stock-info")
            
            # 验证响应
            assert response.status_code == 200, f"API调用应该成功，状态码: {response.status_code}"
            
            response_data = response.json()
            assert response_data['success'] == True, "API响应应该显示成功"
            assert 'cache_refreshed' in response_data['data'], "响应数据应该包含缓存刷新状态"
            
            # 验证更新器被调用
            mock_updater.update_all_stock_basic_info.assert_called_once()
            
            # 验证缓存服务刷新被调用
            mock_cache_service.refresh_cache.assert_called_once()
            
            print("✅ API集成测试通过")
            print(f"✅ 更新器调用次数: {mock_updater.update_all_stock_basic_info.call_count}")
            print(f"✅ 缓存刷新调用次数: {mock_cache_service.refresh_cache.call_count}")

def run_tests():
    """运行所有测试"""
    print("开始运行股票信息缓存服务集成测试...")
    
    try:
        # 创建测试实例
        test_instance = TestStockCacheIntegration()
        
        # 运行测试
        test_instance.setup_method()
        test_instance.test_cache_service_singleton()
        
        test_instance.setup_method()
        test_instance.test_cache_service_initialize()
        
        test_instance.setup_method()
        test_instance.test_cache_refresh()
        
        test_instance.setup_method()
        test_instance.test_cache_service_methods()
        
        test_instance.setup_method()
        test_instance.test_api_integration()
        
        print("\n🎉 所有测试通过！股票信息缓存服务集成功能正常。")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        print(f"错误详情: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = run_tests()
    if not success:
        sys.exit(1)