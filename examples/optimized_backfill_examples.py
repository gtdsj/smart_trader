#coding=utf-8
"""
A股全量数据补全用例示例
展示如何使用优化的批量插入功能高效补全数据
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 导入优化的服务和配置
from services.optimized_backfill_service import OptimizedBackfillService
from configs.optimized_backfill_config import OptimizedBackfillConfig
from utils.logger import get_logger

logger = get_logger(__name__)


class OptimizedBackfillExamples:
    """
    优化数据补全用例集合
    """
    
    def __init__(self):
        self.service = OptimizedBackfillService()
        self.config = OptimizedBackfillConfig()
    
    async def example_1_full_market_backfill(self):
        """
        用例1: 全市场历史数据补全
        适用场景: 系统初始化，需要补全所有A股历史数据
        """
        print("\n" + "="*60)
        print("用例1: 全市场历史数据补全")
        print("="*60)
        
        start_time = time.time()
        
        try:
            # 获取全历史数据范围
            start_date, end_date = self.config.get_full_history_range()
            
            print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"数据范围: {start_date} ~ {end_date}")
            print(f"优化配置:")
            print(f"  - 股票批量大小: {self.config.STOCK_BATCH_SIZE}")
            print(f"  - 数据库批量插入: {self.config.DATA_BATCH_INSERT_SIZE}")
            print(f"  - 并行处理: {self.config.ENABLE_PARALLEL_PROCESSING}")
            print(f"  - 内存限制: {self.config.MEMORY_LIMIT_MB}MB")
            
            # 执行全市场补全
            result = await self.service.full_market_backfill(
                start_date=start_date,
                end_date=end_date,
                market='ALL',
                force_update=False
            )
            
            # 输出结果
            self._print_result("全市场历史数据补全", result, start_time)
            
        except Exception as e:
            print(f"❌ 全市场补全失败: {e}")
    
    async def example_2_incremental_update(self):
        """
        用例2: 增量数据更新
        适用场景: 日常数据维护，补全最近缺失的数据
        """
        print("\n" + "="*60)
        print("用例2: 增量数据更新")
        print("="*60)
        
        start_time = time.time()
        
        try:
            # 补全最近30天数据
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"增量范围: {start_date} ~ {end_date}")
            print(f"优化特性: 启用并行处理 + 智能批量插入")
            
            # 执行增量更新
            result = await self.service.full_market_backfill(
                start_date=start_date,
                end_date=end_date,
                market='ALL',
                force_update=True  # 强制更新确保数据最新
            )
            
            # 输出结果
            self._print_result("增量数据更新", result, start_time)
            
        except Exception as e:
            print(f"❌ 增量更新失败: {e}")
    
    async def example_3_specific_market_backfill(self):
        """
        用例3: 特定市场数据补全
        适用场景: 只需要补全沪市或深市数据
        """
        print("\n" + "="*60)
        print("用例3: 特定市场数据补全")
        print("="*60)
        
        # 补全沪市数据
        await self._market_backfill_demo('SH', '沪市')
        
        # 补全深市数据
        await self._market_backfill_demo('SZ', '深市')
    
    async def _market_backfill_demo(self, market: str, market_name: str):
        """
        市场补全演示
        """
        start_time = time.time()
        
        try:
            # 获取最近1年数据
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            print(f"\n📊 {market_name}数据补全:")
            print(f"  市场代码: {market}")
            print(f"  日期范围: {start_date} ~ {end_date}")
            
            # 执行市场补全
            result = await self.service.full_market_backfill(
                start_date=start_date,
                end_date=end_date,
                market=market,
                force_update=False
            )
            
            # 输出结果
            self._print_result(f"{market_name}数据补全", result, start_time)
            
        except Exception as e:
            print(f"❌ {market_name}补全失败: {e}")
    
    async def example_4_performance_comparison(self):
        """
        用例4: 性能对比测试
        对比优化前后的性能差异
        """
        print("\n" + "="*60)
        print("用例4: 性能对比测试")
        print("="*60)
        
        # 测试数据集
        test_stocks = ['600000.SH', '600036.SH', '600519.SH', '000001.SZ', '000002.SZ']
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        print(f"测试股票: {test_stocks}")
        print(f"测试范围: {start_date} ~ {end_date}")
        
        # 模拟不同配置的性能测试
        await self._performance_test("小批量处理", test_stocks, start_date, end_date, batch_size=10)
        await self._performance_test("中批量处理", test_stocks, start_date, end_date, batch_size=50)
        await self._performance_test("大批量处理", test_stocks, start_date, end_date, batch_size=100)
    
    async def _performance_test(self, test_name: str, stocks: List[str], 
                              start_date: str, end_date: str, batch_size: int):
        """
        性能测试
        """
        start_time = time.time()
        
        try:
            print(f"\n🚀 {test_name} (批量大小: {batch_size}):")
            
            # 这里可以调用不同的处理方法进行对比
            # 简化演示，使用统一的服务
            result = await self.service.full_market_backfill(
                start_date=start_date,
                end_date=end_date,
                market='ALL',
                force_update=False
            )
            
            duration = time.time() - start_time
            total_records = result.get('total_records', 0)
            speed = total_records / duration if duration > 0 else 0
            
            print(f"  ⏱️  耗时: {duration:.2f}秒")
            print(f"  📊 记录数: {total_records}")
            print(f"  🚄 速度: {speed:.0f}条/秒")
            print(f"  ✅ 成功率: {result.get('success_rate', 0)}%")
            
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
    
    async def example_5_batch_insert_strategies(self):
        """
        用例5: 批量插入策略演示
        展示不同数据量下的最优插入策略
        """
        print("\n" + "="*60)
        print("用例5: 批量插入策略演示")
        print("="*60)
        
        # 模拟不同数据量的插入测试
        test_cases = [
            {"name": "小批量数据", "count": 500, "expected_method": "executemany"},
            {"name": "中批量数据", "count": 1500, "expected_method": "COPY"},
            {"name": "大批量数据", "count": 5000, "expected_method": "Optimized COPY"},
            {"name": "超大批量数据", "count": 10000, "expected_method": "Ultra COPY"}
        ]
        
        for test_case in test_cases:
            await self._batch_insert_demo(test_case)
    
    async def _batch_insert_demo(self, test_case: Dict[str, Any]):
        """
        批量插入演示
        """
        print(f"\n📦 {test_case['name']} ({test_case['count']}条):")
        print(f"  预期策略: {test_case['expected_method']}")
        
        # 生成测试数据
        test_data = self._generate_test_data(test_case['count'])
        
        start_time = time.time()
        
        try:
            # 调用批量插入方法
            inserted_count = await self.service._ultra_fast_batch_insert(test_data)
            
            duration = time.time() - start_time
            speed = inserted_count / duration if duration > 0 else 0
            
            print(f"  ✅ 插入成功: {inserted_count}条")
            print(f"  ⏱️  耗时: {duration:.3f}秒")
            print(f"  🚄 速度: {speed:.0f}条/秒")
            
            # 性能评级
            performance_level = self._get_performance_level(speed)
            print(f"  🏆 性能等级: {performance_level}")
            
        except Exception as e:
            print(f"  ❌ 插入失败: {e}")
    
    def _generate_test_data(self, count: int) -> List[Dict]:
        """
        生成测试数据
        """
        test_data = []
        base_date = datetime.now() - timedelta(days=count)
        
        for i in range(count):
            test_data.append({
                'stock_code': f'60000{i % 10}.SH',
                'trade_date': (base_date + timedelta(days=i)).strftime('%Y-%m-%d'),
                'open_price': 10.0 + (i % 100) * 0.1,
                'high_price': 10.5 + (i % 100) * 0.1,
                'low_price': 9.5 + (i % 100) * 0.1,
                'close_price': 10.2 + (i % 100) * 0.1,
                'volume': 1000000 + i * 1000,
                'amount': 10000000.0 + i * 10000,
                'turnover_rate': 1.5 + (i % 10) * 0.1,
                'pe_ratio': 15.0 + (i % 20) * 0.5,
                'pb_ratio': 2.0 + (i % 10) * 0.2
            })
        
        return test_data
    
    def _print_result(self, operation: str, result: Dict[str, Any], start_time: float):
        """
        打印结果
        """
        duration = time.time() - start_time
        
        print(f"\n📋 {operation}结果:")
        print(f"  ✅ 成功: {result.get('success', False)}")
        print(f"  📊 总股票数: {result.get('total_stocks', 0)}")
        print(f"  ✅ 成功数量: {result.get('success_count', 0)}")
        print(f"  ❌ 失败数量: {result.get('failed_count', 0)}")
        print(f"  📈 总记录数: {result.get('total_records', 0)}")
        print(f"  📊 成功率: {result.get('success_rate', 0)}%")
        print(f"  ⏱️  总耗时: {duration:.2f}秒")
        
        if 'average_speed_per_second' in result:
            print(f"  🚄 平均速度: {result['average_speed_per_second']}条/秒")
        
        if 'performance_summary' in result:
            perf = result['performance_summary']
            print(f"  🏆 效率等级: {perf.get('efficiency_level', 'N/A')}")
        
        if result.get('failed_count', 0) > 0:
            failed_stocks = result.get('failed_stocks', [])
            print(f"  ⚠️  失败股票: {failed_stocks[:5]}{'...' if len(failed_stocks) > 5 else ''}")
    
    def _get_performance_level(self, speed: float) -> str:
        """
        获取性能等级
        """
        if speed >= 10000:
            return "🏆 极高"
        elif speed >= 5000:
            return "🥇 高"
        elif speed >= 1000:
            return "🥈 中等"
        else:
            return "🥉 低"
    
    async def run_all_examples(self):
        """
        运行所有用例
        """
        print("🚀 开始运行A股全量数据补全优化用例")
        print("="*80)
        
        examples = [
            self.example_1_full_market_backfill,
            self.example_2_incremental_update,
            self.example_3_specific_market_backfill,
            self.example_4_performance_comparison,
            self.example_5_batch_insert_strategies
        ]
        
        total_start_time = time.time()
        
        for i, example in enumerate(examples, 1):
            try:
                print(f"\n🔄 执行用例 {i}/{len(examples)}: {example.__name__}")
                await example()
                print(f"✅ 用例 {i} 执行完成")
            except Exception as e:
                print(f"❌ 用例 {i} 执行失败: {e}")
        
        total_duration = time.time() - total_start_time
        print(f"\n🎉 所有用例执行完成，总耗时: {total_duration:.2f}秒")
        print("="*80)


async def main():
    """
    主函数 - 运行所有优化用例
    """
    examples = OptimizedBackfillExamples()
    await examples.run_all_examples()


if __name__ == "__main__":
    # 运行用例
    asyncio.run(main())