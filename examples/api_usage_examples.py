#coding=utf-8
"""
A股数据补全API使用示例
展示如何通过API接口使用优化的数据补全功能
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any


class BackfillAPIClient:
    """
    数据补全API客户端
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        发送HTTP请求
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ API请求失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_optimization_config(self) -> Dict[str, Any]:
        """
        获取优化配置信息
        """
        return self._make_request('GET', '/api/v1/optimized-backfill/config')
    
    def create_full_market_task(self, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建全市场数据补全任务
        """
        return self._make_request('POST', '/api/v1/optimized-backfill/full-market', json=task_config)
    
    def quick_backfill(self, market: str = 'ALL', days: int = 30, force_update: bool = False) -> Dict[str, Any]:
        """
        快速数据补全
        """
        data = {
            "market": market,
            "days": days,
            "force_update": force_update
        }
        return self._make_request('POST', '/api/v1/optimized-backfill/quick-backfill', json=data)
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        """
        return self._make_request('GET', f'/api/v1/optimized-backfill/task/{task_id}')
    
    def get_task_list(self, status: str = None, limit: int = 20) -> Dict[str, Any]:
        """
        获取任务列表
        """
        params = {'limit': limit}
        if status:
            params['status'] = status
        
        return self._make_request('GET', '/api/v1/optimized-backfill/tasks', params=params)
    
    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """
        取消任务
        """
        return self._make_request('DELETE', f'/api/v1/optimized-backfill/task/{task_id}')
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计
        """
        return self._make_request('GET', '/api/v1/optimized-backfill/performance/stats')
    
    def wait_for_task_completion(self, task_id: str, timeout: int = 3600) -> Dict[str, Any]:
        """
        等待任务完成
        
        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）
            
        Returns:
            Dict: 最终任务状态
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.get_task_status(task_id)
            
            if not result.get('success', False):
                return result
            
            task_info = result.get('data', {})
            status = task_info.get('status', '')
            
            print(f"⏳ 任务状态: {status}, 进度: {task_info.get('progress', 0)}%")
            
            if status in ['completed', 'failed', 'cancelled']:
                return result
            
            time.sleep(10)  # 每10秒检查一次
        
        print(f"⚠️ 任务等待超时 ({timeout}秒)")
        return self.get_task_status(task_id)


def example_1_quick_backfill():
    """
    示例1: 快速数据补全
    适用场景: 补全最近几天的数据
    """
    print("\n" + "="*60)
    print("示例1: 快速数据补全")
    print("="*60)
    
    client = BackfillAPIClient()
    
    # 补全最近30天的全市场数据
    print("🚀 开始快速补全最近30天数据...")
    
    result = client.quick_backfill(
        market='ALL',
        days=30,
        force_update=True
    )
    
    if result.get('success', False):
        data = result.get('data', {})
        summary = data.get('summary', {})
        
        print("✅ 快速补全完成!")
        print(f"📊 处理记录数: {summary.get('total_records', 0)}")
        print(f"📈 成功率: {summary.get('success_rate', 0)}%")
        print(f"⏱️ 耗时: {summary.get('total_time_seconds', 0)}秒")
        print(f"🚄 平均速度: {summary.get('average_speed_per_second', 0)}条/秒")
        
        performance = data.get('performance', {})
        if performance:
            print(f"🏆 效率等级: {performance.get('efficiency_level', 'N/A')}")
    else:
        print(f"❌ 快速补全失败: {result.get('message', '未知错误')}")


def example_2_full_market_task():
    """
    示例2: 创建全市场补全任务
    适用场景: 大规模历史数据补全
    """
    print("\n" + "="*60)
    print("示例2: 全市场补全任务")
    print("="*60)
    
    client = BackfillAPIClient()
    
    # 配置任务参数
    task_config = {
        "task_name": "全市场历史数据补全",
        "market": "ALL",
        "start_date": "2023-01-01",
        "end_date": datetime.now().strftime('%Y-%m-%d'),
        "force_update": False,
        "enable_parallel": True,
        "batch_size": 100,
        "priority": "high",
        "enable_monitoring": True
    }
    
    print("🚀 创建全市场补全任务...")
    print(f"📅 日期范围: {task_config['start_date']} ~ {task_config['end_date']}")
    print(f"⚙️ 批量大小: {task_config['batch_size']}")
    print(f"🔄 并行处理: {task_config['enable_parallel']}")
    
    # 创建任务
    result = client.create_full_market_task(task_config)
    
    if result.get('success', False):
        data = result.get('data', {})
        task_id = data.get('task_id')
        
        print(f"✅ 任务创建成功!")
        print(f"🆔 任务ID: {task_id}")
        print(f"⏱️ 预估时间: {data.get('estimated_time', 'N/A')}")
        print(f"🔧 优化特性: {', '.join(data.get('optimization_features', []))}")
        
        # 等待任务完成（演示用，实际可能需要很长时间）
        print("\n⏳ 等待任务完成...")
        final_result = client.wait_for_task_completion(task_id, timeout=300)  # 5分钟超时
        
        if final_result.get('success', False):
            task_info = final_result.get('data', {})
            task_result = task_info.get('result', {})
            
            print(f"\n📋 任务最终状态: {task_info.get('status', 'unknown')}")
            if task_result:
                print(f"📊 总记录数: {task_result.get('total_records', 0)}")
                print(f"📈 成功率: {task_result.get('success_rate', 0)}%")
                print(f"⏱️ 总耗时: {task_result.get('total_time_seconds', 0)}秒")
    else:
        print(f"❌ 任务创建失败: {result.get('message', '未知错误')}")


def example_3_market_specific_backfill():
    """
    示例3: 特定市场数据补全
    适用场景: 只补全沪市或深市数据
    """
    print("\n" + "="*60)
    print("示例3: 特定市场数据补全")
    print("="*60)
    
    client = BackfillAPIClient()
    
    markets = [
        {"code": "SH", "name": "沪市"},
        {"code": "SZ", "name": "深市"}
    ]
    
    for market in markets:
        print(f"\n📊 补全{market['name']}数据...")
        
        # 补全最近90天数据
        result = client.quick_backfill(
            market=market['code'],
            days=90,
            force_update=False
        )
        
        if result.get('success', False):
            data = result.get('data', {})
            summary = data.get('summary', {})
            
            print(f"✅ {market['name']}补全完成!")
            print(f"📊 记录数: {summary.get('total_records', 0)}")
            print(f"📈 成功率: {summary.get('success_rate', 0)}%")
        else:
            print(f"❌ {market['name']}补全失败: {result.get('message', '未知错误')}")


def example_4_task_management():
    """
    示例4: 任务管理
    展示如何管理补全任务
    """
    print("\n" + "="*60)
    print("示例4: 任务管理")
    print("="*60)
    
    client = BackfillAPIClient()
    
    # 获取任务列表
    print("📋 获取任务列表...")
    result = client.get_task_list(limit=10)
    
    if result.get('success', False):
        data = result.get('data', {})
        tasks = data.get('tasks', [])
        
        print(f"✅ 获取到{len(tasks)}个任务")
        print(f"📊 总任务数: {data.get('total_count', 0)}")
        
        for i, task in enumerate(tasks[:5], 1):  # 显示前5个任务
            print(f"\n{i}. 任务: {task.get('task_name', 'N/A')}")
            print(f"   🆔 ID: {task.get('task_id', 'N/A')}")
            print(f"   📊 状态: {task.get('status', 'N/A')}")
            print(f"   📅 创建时间: {task.get('created_at', 'N/A')}")
            print(f"   📈 进度: {task.get('progress', 0)}%")
    else:
        print(f"❌ 获取任务列表失败: {result.get('message', '未知错误')}")
    
    # 获取运行中的任务
    print("\n🔄 获取运行中的任务...")
    running_result = client.get_task_list(status='running', limit=5)
    
    if running_result.get('success', False):
        running_tasks = running_result.get('data', {}).get('tasks', [])
        print(f"⚡ 运行中任务数: {len(running_tasks)}")
        
        for task in running_tasks:
            print(f"   🔄 {task.get('task_name', 'N/A')} - {task.get('progress', 0)}%")
    
    # 演示取消任务（如果有运行中的任务）
    if running_tasks:
        task_to_cancel = running_tasks[0]
        task_id = task_to_cancel.get('task_id')
        
        print(f"\n⚠️ 演示取消任务: {task_id}")
        cancel_result = client.cancel_task(task_id)
        
        if cancel_result.get('success', False):
            print("✅ 任务取消成功")
        else:
            print(f"❌ 任务取消失败: {cancel_result.get('message', '未知错误')}")


def example_5_performance_monitoring():
    """
    示例5: 性能监控
    展示如何监控补全性能
    """
    print("\n" + "="*60)
    print("示例5: 性能监控")
    print("="*60)
    
    client = BackfillAPIClient()
    
    # 获取优化配置
    print("⚙️ 获取优化配置...")
    config_result = client.get_optimization_config()
    
    if config_result.get('success', False):
        config_data = config_result.get('data', {})
        perf_settings = config_data.get('performance_settings', {})
        
        print("✅ 优化配置:")
        print(f"   📦 股票批量大小: {perf_settings.get('stock_batch_size', 'N/A')}")
        print(f"   💾 数据批量插入: {perf_settings.get('data_batch_insert_size', 'N/A')}")
        print(f"   🔄 最大并发批次: {perf_settings.get('max_concurrent_batches', 'N/A')}")
        print(f"   💻 内存限制: {perf_settings.get('memory_limit_mb', 'N/A')}MB")
        
        optimization_features = config_data.get('optimization_features', {})
        print(f"\n🔧 优化特性:")
        print(f"   🔄 并行处理: {'✅' if optimization_features.get('parallel_processing') else '❌'}")
        print(f"   💾 内存优化: {'✅' if optimization_features.get('memory_optimization') else '❌'}")
        print(f"   📊 性能监控: {'✅' if optimization_features.get('performance_monitoring') else '❌'}")
    
    # 获取性能统计
    print("\n📊 获取性能统计...")
    stats_result = client.get_performance_stats()
    
    if stats_result.get('success', False):
        stats_data = stats_result.get('data', {})
        stats = stats_data.get('stats')
        
        if stats:
            print("✅ 性能统计:")
            print(f"   📋 完成任务数: {stats.get('total_completed_tasks', 0)}")
            print(f"   📊 处理记录数: {stats.get('total_records_processed', 0)}")
            print(f"   ⏱️ 总处理时间: {stats.get('total_processing_time_seconds', 0)}秒")
            print(f"   🚄 平均速度: {stats.get('average_processing_speed', 0)}条/秒")
            print(f"   📈 平均成功率: {stats.get('average_success_rate', 0)}%")
            print(f"   🏆 性能等级: {stats.get('performance_level', 'N/A')}")
        else:
            print("📊 暂无性能统计数据")
    else:
        print(f"❌ 获取性能统计失败: {stats_result.get('message', '未知错误')}")


def main():
    """
    主函数 - 运行所有API使用示例
    """
    print("🚀 A股数据补全API使用示例")
    print("="*80)
    print("📝 注意: 请确保Smart Trader服务已启动 (http://localhost:8000)")
    print("="*80)
    
    examples = [
        example_1_quick_backfill,
        example_2_full_market_task,
        example_3_market_specific_backfill,
        example_4_task_management,
        example_5_performance_monitoring
    ]
    
    for i, example in enumerate(examples, 1):
        try:
            print(f"\n🔄 执行示例 {i}/{len(examples)}: {example.__name__}")
            example()
            print(f"✅ 示例 {i} 执行完成")
        except Exception as e:
            print(f"❌ 示例 {i} 执行失败: {e}")
        
        # 示例间暂停
        if i < len(examples):
            time.sleep(2)
    
    print("\n🎉 所有API示例执行完成!")
    print("="*80)


if __name__ == "__main__":
    main()