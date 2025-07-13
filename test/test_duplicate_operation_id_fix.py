# -*- coding: utf-8 -*-
"""
重复Operation ID修复验证测试
验证修复后的API路由是否正常工作，确保没有重复的Operation ID
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from fastapi.openapi.utils import get_openapi
import warnings
from io import StringIO
import sys
from contextlib import redirect_stderr

# 导入主应用
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import create_app

class TestDuplicateOperationIdFix:
    """重复Operation ID修复测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.app = create_app()
        self.client = TestClient(self.app)
    
    def test_no_duplicate_operation_id_warnings(self):
        """测试是否还有重复Operation ID警告"""
        print("\n=== 测试重复Operation ID警告修复 ===")
        
        # 捕获警告信息
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            
            # 获取OpenAPI schema，这会触发Operation ID的生成
            openapi_schema = get_openapi(
                title=self.app.title,
                version=self.app.version,
                description=self.app.description,
                routes=self.app.routes,
            )
            
            # 检查是否有重复Operation ID的警告
            duplicate_warnings = [
                w for w in warning_list 
                if "Duplicate Operation ID" in str(w.message)
            ]
            
            print(f"捕获到的重复Operation ID警告数量: {len(duplicate_warnings)}")
            
            if duplicate_warnings:
                print("\n发现的重复Operation ID警告:")
                for warning in duplicate_warnings:
                    print(f"  - {warning.message}")
            else:
                print("✅ 没有发现重复Operation ID警告")
            
            # 断言没有重复Operation ID警告
            assert len(duplicate_warnings) == 0, f"仍然存在 {len(duplicate_warnings)} 个重复Operation ID警告"
    
    def test_api_routes_accessibility(self):
        """测试API路由可访问性"""
        print("\n=== 测试API路由可访问性 ===")
        
        # 测试系统根路径
        response = self.client.get("/")
        print(f"根路径状态码: {response.status_code}")
        assert response.status_code == 200
        
        # 测试健康检查
        response = self.client.get("/health")
        print(f"健康检查状态码: {response.status_code}")
        assert response.status_code == 200
        
        # 测试API文档
        response = self.client.get("/docs")
        print(f"API文档状态码: {response.status_code}")
        assert response.status_code == 200
        
        # 测试OpenAPI schema
        response = self.client.get("/openapi.json")
        print(f"OpenAPI schema状态码: {response.status_code}")
        assert response.status_code == 200
        
        print("✅ 所有基础路由都可正常访问")
    
    def test_business_api_routes(self):
        """测试业务API路由"""
        print("\n=== 测试业务API路由 ===")
        
        # 测试业务API路由是否存在
        business_routes = [
            "/api/v1/data/stocks",
            "/api/v1/data/stock-info-status",
            "/api/v1/trading/",
            "/api/v1/strategy/list",
            "/api/v1/backtest/list",
            "/api/v1/notification/settings"
        ]
        
        accessible_routes = []
        inaccessible_routes = []
        
        for route in business_routes:
            try:
                response = self.client.get(route)
                if response.status_code in [200, 422]:  # 422表示参数错误但路由存在
                    accessible_routes.append(route)
                    print(f"✅ {route} - 状态码: {response.status_code}")
                else:
                    inaccessible_routes.append((route, response.status_code))
                    print(f"❌ {route} - 状态码: {response.status_code}")
            except Exception as e:
                inaccessible_routes.append((route, str(e)))
                print(f"❌ {route} - 错误: {e}")
        
        print(f"\n可访问的路由数量: {len(accessible_routes)}")
        print(f"不可访问的路由数量: {len(inaccessible_routes)}")
        
        # 至少应该有一些路由是可访问的
        assert len(accessible_routes) > 0, "没有可访问的业务API路由"
    
    def test_openapi_schema_structure(self):
        """测试OpenAPI schema结构"""
        print("\n=== 测试OpenAPI Schema结构 ===")
        
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        
        # 检查基本结构
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        
        # 检查路径数量
        paths = schema["paths"]
        print(f"API路径总数: {len(paths)}")
        
        # 检查是否有业务API路径
        business_paths = [path for path in paths.keys() if path.startswith("/api/v1/")]
        print(f"业务API路径数量: {len(business_paths)}")
        
        # 检查Operation ID唯一性
        operation_ids = []
        for path, methods in paths.items():
            for method, operation in methods.items():
                if isinstance(operation, dict) and "operationId" in operation:
                    operation_ids.append(operation["operationId"])
        
        unique_operation_ids = set(operation_ids)
        print(f"Operation ID总数: {len(operation_ids)}")
        print(f"唯一Operation ID数量: {len(unique_operation_ids)}")
        
        # 检查是否有重复的Operation ID
        duplicate_ids = []
        seen_ids = set()
        for op_id in operation_ids:
            if op_id in seen_ids:
                duplicate_ids.append(op_id)
            else:
                seen_ids.add(op_id)
        
        if duplicate_ids:
            print(f"\n发现重复的Operation ID:")
            for dup_id in duplicate_ids:
                print(f"  - {dup_id}")
        else:
            print("✅ 所有Operation ID都是唯一的")
        
        # 断言没有重复的Operation ID
        assert len(duplicate_ids) == 0, f"发现 {len(duplicate_ids)} 个重复的Operation ID"
        assert len(operation_ids) == len(unique_operation_ids), "Operation ID不唯一"
    
    def test_route_tags_organization(self):
        """测试路由标签组织"""
        print("\n=== 测试路由标签组织 ===")
        
        response = self.client.get("/openapi.json")
        schema = response.json()
        
        # 收集所有标签
        all_tags = set()
        for path, methods in schema["paths"].items():
            for method, operation in methods.items():
                if isinstance(operation, dict) and "tags" in operation:
                    all_tags.update(operation["tags"])
        
        print(f"API标签总数: {len(all_tags)}")
        print("API标签列表:")
        for tag in sorted(all_tags):
            print(f"  - {tag}")
        
        # 检查是否有预期的业务标签
        expected_tags = ["数据业务", "交易业务", "策略业务", "回测业务", "通知业务"]
        found_tags = [tag for tag in expected_tags if tag in all_tags]
        
        print(f"\n找到的预期业务标签: {found_tags}")
        print(f"预期标签覆盖率: {len(found_tags)}/{len(expected_tags)}")
        
        # 至少应该有一些业务标签
        assert len(found_tags) > 0, "没有找到预期的业务API标签"

def run_tests():
    """运行所有测试"""
    print("开始运行重复Operation ID修复验证测试...")
    
    try:
        # 创建测试实例
        test_instance = TestDuplicateOperationIdFix()
        test_instance.setup_method()
        
        # 运行测试
        test_instance.test_no_duplicate_operation_id_warnings()
        test_instance.test_api_routes_accessibility()
        test_instance.test_business_api_routes()
        test_instance.test_openapi_schema_structure()
        test_instance.test_route_tags_organization()
        
        print("\n🎉 所有测试通过！重复Operation ID问题已成功修复。")
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