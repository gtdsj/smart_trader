#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票基本信息API测试
测试新增的股票基本信息更新API接口
"""

import asyncio
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from services.stock_info_updater import StockInfoUpdater

# 创建测试客户端
client = TestClient(app)

class TestStockInfoAPI:
    """股票基本信息API测试类"""
    
    def test_get_stock_info_status(self):
        """测试获取股票信息更新状态接口"""
        print("\n=== 测试获取股票信息更新状态 ===")
        
        # 模拟股票信息更新器的方法
        with patch.object(StockInfoUpdater, '_is_updated_today', new_callable=AsyncMock) as mock_is_updated:
            mock_is_updated.return_value = False
            
            # 发送GET请求
            response = client.get("/api/v1/data/stock-info-status")
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.json()}")
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "scheduler_status" in data["data"]
            assert "update_status" in data["data"]
            assert "next_update" in data["data"]
            
            print("✅ 获取股票信息更新状态测试通过")
    
    def test_update_stock_basic_info_success(self):
        """测试股票基本信息更新接口 - 成功场景"""
        print("\n=== 测试股票基本信息更新 - 成功场景 ===")
        
        # 模拟成功的更新结果
        mock_result = {
            'success': True,
            'total_count': 5000,
            'success_count': 4950,
            'failed_count': 50,
            'duration': 120.5
        }
        
        with patch.object(StockInfoUpdater, 'update_all_stock_basic_info', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = mock_result
            
            # 发送POST请求
            response = client.post("/api/v1/data/update-stock-info")
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.json()}")
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "股票基本信息更新成功"
            assert data["data"]["total_count"] == 5000
            assert data["data"]["success_count"] == 4950
            assert data["data"]["failed_count"] == 50
            assert "duration" in data["data"]
            assert "update_time" in data["data"]
            
            print("✅ 股票基本信息更新成功场景测试通过")
    
    def test_update_stock_basic_info_failure(self):
        """测试股票基本信息更新接口 - 失败场景"""
        print("\n=== 测试股票基本信息更新 - 失败场景 ===")
        
        # 模拟失败的更新结果
        mock_result = {
            'success': False,
            'message': '无法连接到数据源'
        }
        
        with patch.object(StockInfoUpdater, 'update_all_stock_basic_info', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = mock_result
            
            # 发送POST请求
            response = client.post("/api/v1/data/update-stock-info")
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.json()}")
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "股票基本信息更新失败" in data["message"]
            assert "无法连接到数据源" in data["message"]
            
            print("✅ 股票基本信息更新失败场景测试通过")
    
    def test_update_stock_basic_info_exception(self):
        """测试股票基本信息更新接口 - 异常场景"""
        print("\n=== 测试股票基本信息更新 - 异常场景 ===")
        
        # 模拟抛出异常
        with patch.object(StockInfoUpdater, 'update_all_stock_basic_info', new_callable=AsyncMock) as mock_update:
            mock_update.side_effect = Exception("模拟的异常错误")
            
            # 发送POST请求
            response = client.post("/api/v1/data/update-stock-info")
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.json()}")
            
            # 验证响应
            assert response.status_code == 500
            data = response.json()
            assert "更新股票基本信息时发生错误" in data["detail"]
            assert "模拟的异常错误" in data["detail"]
            
            print("✅ 股票基本信息更新异常场景测试通过")

def test_api_integration():
    """API集成测试"""
    print("\n=== API集成测试 ===")
    
    # 测试API路由是否正确注册
    response = client.get("/api/v1/data/")
    print(f"数据概览接口状态: {response.status_code}")
    
    # 检查新接口是否在路由中
    from api.business.data import router
    routes = [route.path for route in router.routes]
    print(f"数据业务路由: {routes}")
    
    # 检查路由是否包含新接口（去掉前缀检查）
    route_paths = [route.path.replace('/data', '') for route in router.routes]
    print(f"处理后的路由: {route_paths}")
    
    assert "/update-stock-info" in route_paths
    assert "/stock-info-status" in route_paths
    
    print("✅ API路由注册正确")
    print("✅ API集成测试通过")

def run_tests():
    """运行所有测试"""
    print("🚀 开始股票基本信息API测试")
    
    test_instance = TestStockInfoAPI()
    
    try:
        # 运行各项测试
        test_instance.test_get_stock_info_status()
        test_instance.test_update_stock_basic_info_success()
        test_instance.test_update_stock_basic_info_failure()
        test_instance.test_update_stock_basic_info_exception()
        test_api_integration()
        
        print("\n🎉 所有测试完成！")
        
        print("\n=== 测试总结 ===")
        print("✅ 股票信息更新状态接口正常")
        print("✅ 股票基本信息更新接口正常")
        print("✅ 成功场景处理正确")
        print("✅ 失败场景处理正确")
        print("✅ 异常场景处理正确")
        print("✅ API路由注册正确")
        print("测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    run_tests()