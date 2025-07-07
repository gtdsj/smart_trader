# -*- coding: utf-8 -*-
"""
DataService单例模式测试
"""
import sys
import os
import asyncio
import threading
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.data_service import DataService


def test_singleton_same_instance():
    """测试单例模式 - 确保返回相同实例"""
    print("测试1: 验证单例模式返回相同实例")
    
    # 创建多个实例
    service1 = DataService()
    service2 = DataService()
    service3 = DataService.get_instance()
    
    # 验证是否为同一个实例
    assert service1 is service2, "DataService() 应该返回相同实例"
    assert service1 is service3, "DataService.get_instance() 应该返回相同实例"
    assert service2 is service3, "所有获取方式应该返回相同实例"
    
    print(f"✓ 实例ID一致: {id(service1)} == {id(service2)} == {id(service3)}")
    print("✓ 单例模式验证通过")


def test_singleton_thread_safety():
    """测试单例模式 - 线程安全性"""
    print("\n测试2: 验证线程安全性")
    
    instances = []
    
    def create_instance():
        """在线程中创建实例"""
        time.sleep(0.01)  # 模拟一些延迟
        instance = DataService()
        instances.append(instance)
    
    # 重置单例以确保测试的准确性
    DataService.reset_instance()
    
    # 创建多个线程同时获取实例
    threads = []
    for i in range(10):
        thread = threading.Thread(target=create_instance)
        threads.append(thread)
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    # 验证所有实例都是同一个
    first_instance = instances[0]
    for i, instance in enumerate(instances):
        assert instance is first_instance, f"线程{i}获取的实例不一致"
    
    print(f"✓ 所有{len(instances)}个线程获取的实例ID一致: {id(first_instance)}")
    print("✓ 线程安全性验证通过")


def test_singleton_initialization():
    """测试单例模式 - 初始化状态"""
    print("\n测试3: 验证初始化状态")
    
    # 重置单例
    DataService.reset_instance()
    
    # 创建实例
    service = DataService()
    
    # 验证初始化状态
    assert hasattr(service, '_initialized'), "应该有_initialized属性"
    assert service._initialized is True, "_initialized应该为True"
    assert hasattr(service, 'settings'), "应该有settings属性"
    assert hasattr(service, 'cache_client'), "应该有cache_client属性"
    assert hasattr(service, 'is_running'), "应该有is_running属性"
    assert service.is_running is False, "初始状态is_running应该为False"
    
    print("✓ 初始化状态验证通过")


def test_singleton_reset():
    """测试单例模式 - 重置功能"""
    print("\n测试4: 验证重置功能")
    
    # 创建实例
    service1 = DataService()
    instance_id1 = id(service1)
    
    # 重置单例
    DataService.reset_instance()
    
    # 再次创建实例
    service2 = DataService()
    instance_id2 = id(service2)
    
    # 验证是新的实例
    assert service1 is not service2, "重置后应该创建新实例"
    assert instance_id1 != instance_id2, "重置后实例ID应该不同"
    
    print(f"✓ 重置前实例ID: {instance_id1}")
    print(f"✓ 重置后实例ID: {instance_id2}")
    print("✓ 重置功能验证通过")


def test_singleton_multiple_initialization():
    """测试单例模式 - 多次初始化"""
    print("\n测试5: 验证多次初始化保护")
    
    # 重置单例
    DataService.reset_instance()
    
    # 创建实例并记录初始状态
    service = DataService()
    original_settings = service.settings
    
    # 模拟修改状态
    service.is_running = True
    service.test_attr = "test_value"
    
    # 再次调用__init__（通过创建新实例）
    service2 = DataService()
    
    # 验证状态没有被重置
    assert service is service2, "应该返回相同实例"
    assert service.is_running is True, "状态不应该被重置"
    assert hasattr(service, 'test_attr'), "自定义属性不应该丢失"
    assert service.test_attr == "test_value", "自定义属性值不应该改变"
    
    print("✓ 多次初始化保护验证通过")


if __name__ == "__main__":
    print("开始DataService单例模式测试...\n")
    
    try:
        test_singleton_same_instance()
        test_singleton_thread_safety()
        test_singleton_initialization()
        test_singleton_reset()
        test_singleton_multiple_initialization()
        
        print("\n🎉 所有测试通过！DataService单例模式实现正确。")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理：重置单例状态
        DataService.reset_instance()
        print("\n测试完成，已清理单例状态。")