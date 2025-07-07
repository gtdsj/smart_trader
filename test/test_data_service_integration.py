# -*- coding: utf-8 -*-
"""
DataService单例模式集成测试
验证其他服务是否正确使用DataService单例
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.data_service import DataService
from services.stock_screener import StockScreener
from api.dependencies import get_data_service


def test_stock_screener_uses_singleton():
    """测试StockScreener是否使用DataService单例"""
    print("测试1: 验证StockScreener使用DataService单例")
    
    # 重置单例
    DataService.reset_instance()
    
    # 创建DataService实例
    data_service1 = DataService()
    
    # 创建StockScreener实例（不传入data_service参数）
    screener = StockScreener()
    
    # 验证StockScreener使用的是同一个DataService实例
    assert screener.data_service is data_service1, "StockScreener应该使用DataService单例"
    
    print(f"✓ DataService实例ID: {id(data_service1)}")
    print(f"✓ StockScreener中DataService实例ID: {id(screener.data_service)}")
    print("✓ StockScreener正确使用DataService单例")


def test_api_dependencies_use_singleton():
    """测试API依赖注入是否使用DataService单例"""
    print("\n测试2: 验证API依赖注入使用DataService单例")
    
    # 重置单例
    DataService.reset_instance()
    
    # 创建DataService实例
    data_service1 = DataService()
    
    # 通过API依赖注入获取DataService
    data_service2 = get_data_service()
    
    # 验证是同一个实例
    assert data_service1 is data_service2, "API依赖注入应该返回DataService单例"
    
    print(f"✓ 直接创建的DataService实例ID: {id(data_service1)}")
    print(f"✓ API依赖注入的DataService实例ID: {id(data_service2)}")
    print("✓ API依赖注入正确使用DataService单例")


def test_multiple_services_share_singleton():
    """测试多个服务共享DataService单例"""
    print("\n测试3: 验证多个服务共享DataService单例")
    
    # 重置单例
    DataService.reset_instance()
    
    # 创建多个服务实例
    screener1 = StockScreener()
    screener2 = StockScreener()
    api_data_service = get_data_service()
    direct_data_service = DataService.get_instance()
    
    # 验证所有服务使用的是同一个DataService实例
    assert screener1.data_service is screener2.data_service, "不同StockScreener实例应该共享DataService单例"
    assert screener1.data_service is api_data_service, "StockScreener和API依赖注入应该共享DataService单例"
    assert screener1.data_service is direct_data_service, "所有获取方式应该返回同一个DataService单例"
    
    instance_id = id(screener1.data_service)
    print(f"✓ 所有服务共享的DataService实例ID: {instance_id}")
    print("✓ 多个服务正确共享DataService单例")


def test_singleton_state_persistence():
    """测试单例状态持久性"""
    print("\n测试4: 验证单例状态持久性")
    
    # 重置单例
    DataService.reset_instance()
    
    # 创建DataService实例并修改状态
    data_service1 = DataService()
    data_service1.test_attribute = "test_value"
    data_service1.is_running = True
    
    # 通过不同方式获取DataService实例
    data_service2 = DataService.get_instance()
    screener = StockScreener()
    api_data_service = get_data_service()
    
    # 验证状态在所有实例中保持一致
    assert hasattr(data_service2, 'test_attribute'), "状态应该在单例中持久化"
    assert data_service2.test_attribute == "test_value", "自定义属性值应该保持一致"
    assert data_service2.is_running is True, "运行状态应该保持一致"
    
    assert hasattr(screener.data_service, 'test_attribute'), "StockScreener中的DataService应该保持状态"
    assert screener.data_service.test_attribute == "test_value", "StockScreener中的状态应该一致"
    
    assert hasattr(api_data_service, 'test_attribute'), "API依赖注入的DataService应该保持状态"
    assert api_data_service.test_attribute == "test_value", "API依赖注入的状态应该一致"
    
    print("✓ 单例状态在所有访问方式中保持一致")
    print("✓ 状态持久性验证通过")


def test_explicit_data_service_injection():
    """测试显式DataService注入"""
    print("\n测试5: 验证显式DataService注入")
    
    # 重置单例
    DataService.reset_instance()
    
    # 创建DataService实例
    data_service = DataService()
    data_service.injected_marker = "explicitly_injected"
    
    # 显式注入DataService到StockScreener
    screener = StockScreener(data_service=data_service)
    
    # 验证StockScreener使用的是注入的实例
    assert screener.data_service is data_service, "StockScreener应该使用显式注入的DataService实例"
    assert hasattr(screener.data_service, 'injected_marker'), "注入的DataService应该保持自定义属性"
    assert screener.data_service.injected_marker == "explicitly_injected", "注入的属性值应该正确"
    
    # 验证其他获取方式仍然返回同一个实例（因为是单例）
    other_instance = DataService.get_instance()
    assert other_instance is data_service, "其他获取方式应该返回同一个单例实例"
    
    print("✓ 显式DataService注入功能正常")
    print("✓ 注入的实例与单例保持一致")


if __name__ == "__main__":
    print("开始DataService单例模式集成测试...\n")
    
    try:
        test_stock_screener_uses_singleton()
        test_api_dependencies_use_singleton()
        test_multiple_services_share_singleton()
        test_singleton_state_persistence()
        test_explicit_data_service_injection()
        
        print("\n🎉 所有集成测试通过！DataService单例模式在整个系统中正确工作。")
        
    except Exception as e:
        print(f"\n❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理：重置单例状态
        DataService.reset_instance()
        print("\n测试完成，已清理单例状态。")