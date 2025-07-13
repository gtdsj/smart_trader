#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票筛选器股票名称字段测试
测试股票筛选API和服务中股票名称字段的添加功能
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.stock_screener_routes import MatchedStock
from services.stock_screener import StockScreener
import pandas as pd
from datetime import datetime


class TestStockScreenerNameField(unittest.TestCase):
    """测试股票筛选器股票名称字段功能"""
    
    def test_matched_stock_model_has_name_field(self):
        """测试MatchedStock模型包含name字段"""
        # 创建MatchedStock实例
        matched_stock = MatchedStock(
            symbol="000001",
            name="平安银行",
            price=12.50,
            reason="符合策略条件",
            indicators={"ma5": 12.3, "ma20": 12.1}
        )
        
        # 验证字段存在
        self.assertEqual(matched_stock.symbol, "000001")
        self.assertEqual(matched_stock.name, "平安银行")
        self.assertEqual(matched_stock.price, 12.50)
        self.assertEqual(matched_stock.reason, "符合策略条件")
        self.assertIsInstance(matched_stock.indicators, dict)
    
    def test_matched_stock_model_serialization(self):
        """测试MatchedStock模型序列化"""
        matched_stock = MatchedStock(
            symbol="000002",
            name="万科A",
            price=15.80,
            reason="符合表达式条件",
            indicators={"rsi": 65.5}
        )
        
        # 测试转换为字典
        stock_dict = matched_stock.model_dump()
        expected_keys = {"symbol", "name", "price", "reason", "indicators"}
        self.assertEqual(set(stock_dict.keys()), expected_keys)
        self.assertEqual(stock_dict["name"], "万科A")
    
    @patch('services.stock_screener.StockInfoCacheService')
    @patch('services.stock_screener.DataService')
    def test_check_single_stock_strategy_returns_name(self, mock_data_service, mock_stock_cache_service):
        """测试_check_single_stock_strategy方法返回股票名称"""
        # 模拟股票缓存服务
        mock_cache_instance = Mock()
        mock_cache_instance.get_stock_info.return_value = {
            'stock_name': '平安银行',
            'stock_code': '000001'
        }
        mock_stock_cache_service.return_value = mock_cache_instance
        
        # 模拟数据服务
        mock_data_instance = Mock()
        mock_data_service.return_value = mock_data_instance
        
        # 创建股票筛选器实例
        screener = StockScreener()
        
        # 模拟股票数据
        stock_data = pd.DataFrame({
            'close': [12.0, 12.1, 12.2, 12.3, 12.5],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        stock_data.attrs = {'stock_code': '000001'}
        
        # 模拟策略
        strategy = {
            "condition_details": [
                {
                    "condition_type": "technical",
                    "indicator": "ma5",
                    "operator": ">",
                    "value": 12.0
                }
            ]
        }
        
        # 模拟相关方法
        with patch.object(screener, '_calculate_indicators_for_conditions') as mock_calc_indicators, \
             patch.object(screener, '_evaluate_condition') as mock_eval_condition, \
             patch.object(screener, '_combine_condition_results') as mock_combine_results, \
             patch('asyncio.new_event_loop') as mock_loop_new, \
             patch('asyncio.set_event_loop') as mock_loop_set:
            
            # 设置模拟返回值
            mock_calc_indicators.return_value = {'ma5': 12.3}
            mock_eval_condition.return_value = True
            mock_combine_results.return_value = True
            
            # 模拟事件循环
            mock_loop = Mock()
            mock_loop_new.return_value = mock_loop
            mock_loop.run_until_complete.return_value = stock_data
            
            # 执行测试
            result = screener._check_single_stock_strategy(
                symbol="000001",
                strategy=strategy,
                screen_date="2024-01-15"
            )
            
            # 验证结果
            self.assertTrue(result["matched"])
            self.assertEqual(result["symbol"], "000001")
            self.assertEqual(result["name"], "平安银行")
            self.assertEqual(result["price"], 12.5)
            self.assertEqual(result["reason"], "符合策略条件")
            self.assertIn("indicators", result)
            
            # 验证股票缓存服务被调用
            mock_cache_instance.get_stock_info.assert_called_with("000001")
    
    @patch('services.stock_screener.StockInfoCacheService')
    @patch('services.stock_screener.DataService')
    def test_check_single_stock_expression_returns_name(self, mock_data_service, mock_stock_cache_service):
        """测试_check_single_stock_expression方法返回股票名称"""
        # 模拟股票缓存服务
        mock_cache_instance = Mock()
        mock_cache_instance.get_stock_info.return_value = {
            'stock_name': '万科A',
            'stock_code': '000002'
        }
        mock_stock_cache_service.return_value = mock_cache_instance
        
        # 模拟数据服务
        mock_data_instance = Mock()
        mock_data_service.return_value = mock_data_instance
        
        # 创建股票筛选器实例
        screener = StockScreener()
        
        # 模拟股票数据
        stock_data = pd.DataFrame({
            'close': [15.0, 15.2, 15.5, 15.7, 15.8],
            'volume': [2000, 2100, 2200, 2300, 2400]
        })
        
        # 模拟策略管理器评估结果
        evaluation_result = {
            "success": True,
            "result": True,
            "indicators": {"rsi": 65.5, "macd": 0.12}
        }
        
        # 模拟相关方法
        with patch('asyncio.new_event_loop') as mock_loop_new, \
             patch('asyncio.set_event_loop') as mock_loop_set:
            
            # 模拟事件循环
            mock_loop = Mock()
            mock_loop_new.return_value = mock_loop
            mock_loop.run_until_complete.side_effect = [stock_data, evaluation_result]
            
            # 执行测试
            result = screener._check_single_stock_expression(
                symbol="000002",
                expression="close > ma(close, 20)",
                screen_date="2024-01-15"
            )
            
            # 验证结果
            self.assertTrue(result["matched"])
            self.assertEqual(result["symbol"], "000002")
            self.assertEqual(result["name"], "万科A")
            self.assertEqual(result["price"], 15.8)
            self.assertEqual(result["reason"], "符合表达式条件")
            self.assertIn("indicators", result)
            
            # 验证股票缓存服务被调用
            mock_cache_instance.get_stock_info.assert_called_with("000002")
    
    @patch('services.stock_screener.StockInfoCacheService')
    def test_filter_matched_stocks_vectorized_includes_name(self, mock_stock_cache_service):
        """测试_filter_matched_stocks_vectorized方法包含股票名称"""
        # 模拟股票缓存服务
        mock_cache_instance = Mock()
        mock_cache_instance.get_stock_info.side_effect = [
            {'stock_name': '平安银行', 'stock_code': '000001'},
            {'stock_name': '万科A', 'stock_code': '000002'}
        ]
        mock_stock_cache_service.return_value = mock_cache_instance
        
        # 创建股票筛选器实例
        screener = StockScreener()
        
        # 模拟输入数据
        stock_matrices = {
            'close_prices': {
                '000001': pd.Series([12.0, 12.1, 12.2]),
                '000002': pd.Series([15.0, 15.2, 15.5])
            },
            'high_prices': {
                '000001': pd.Series([12.1, 12.2, 12.3]),
                '000002': pd.Series([15.1, 15.3, 15.6])
            },
            'low_prices': {
                '000001': pd.Series([11.9, 12.0, 12.1]),
                '000002': pd.Series([14.9, 15.1, 15.4])
            },
            'volumes': {
                '000001': pd.Series([1000, 1100, 1200]),
                '000002': pd.Series([2000, 2100, 2200])
            },
            'valid_stocks': ['000001', '000002']
        }
        
        indicator_matrices = {
            '000001': {'ma5': 12.15, 'rsi': 55.0},
            '000002': {'ma5': 15.25, 'rsi': 65.0}
        }
        
        condition_results = {
            '000001': [True],
            '000002': [True]
        }
        
        conditions = [{
            "condition_type": "technical",
            "indicator": "ma5",
            "operator": ">",
            "value": 12.0
        }]
        
        stock_batch = ['000001', '000002']
        
        # 执行测试
        result = screener._filter_matched_stocks_vectorized(
            stock_matrices, indicator_matrices, condition_results, conditions, stock_batch
        )
        
        # 验证结果
        self.assertEqual(len(result), 2)
        
        # 验证第一个股票
        stock1 = result[0]
        self.assertEqual(stock1['symbol'], '000001')
        self.assertEqual(stock1['name'], '平安银行')
        self.assertIn('price', stock1)
        self.assertIn('indicators', stock1)
        
        # 验证第二个股票
        stock2 = result[1]
        self.assertEqual(stock2['symbol'], '000002')
        self.assertEqual(stock2['name'], '万科A')
        self.assertIn('price', stock2)
        self.assertIn('indicators', stock2)
        
        # 验证股票缓存服务被调用
        self.assertEqual(mock_cache_instance.get_stock_info.call_count, 2)
    
    def test_stock_cache_service_fallback(self):
        """测试股票缓存服务获取失败时的回退机制"""
        with patch('services.stock_screener.StockInfoCacheService') as mock_stock_cache_service:
            # 模拟股票缓存服务返回None
            mock_cache_instance = Mock()
            mock_cache_instance.get_stock_info.return_value = None
            mock_stock_cache_service.return_value = mock_cache_instance
            
            # 创建股票筛选器实例
            screener = StockScreener()
            
            # 模拟股票数据
            stock_data = pd.DataFrame({
                'close': [12.0, 12.1, 12.2, 12.3, 12.5]
            })
            stock_data.attrs = {'stock_code': '000001'}
            
            # 模拟策略
            strategy = {
                "condition_details": [
                    {
                        "condition_type": "technical",
                        "indicator": "ma5",
                        "operator": ">",
                        "value": 12.0
                    }
                ]
            }
            
            # 模拟相关方法
            with patch.object(screener, '_calculate_indicators_for_conditions') as mock_calc_indicators, \
                 patch.object(screener, '_evaluate_condition') as mock_eval_condition, \
                 patch.object(screener, '_combine_condition_results') as mock_combine_results, \
                 patch('asyncio.new_event_loop') as mock_loop_new, \
                 patch('asyncio.set_event_loop') as mock_loop_set:
                
                # 设置模拟返回值
                mock_calc_indicators.return_value = {'ma5': 12.3}
                mock_eval_condition.return_value = True
                mock_combine_results.return_value = True
                
                # 模拟事件循环
                mock_loop = Mock()
                mock_loop_new.return_value = mock_loop
                mock_loop.run_until_complete.return_value = stock_data
                
                # 执行测试
                result = screener._check_single_stock_strategy(
                    symbol="000001",
                    strategy=strategy,
                    screen_date="2024-01-15"
                )
                
                # 验证结果 - 当获取股票名称失败时，应该使用股票代码作为名称
                self.assertTrue(result["matched"])
                self.assertEqual(result["symbol"], "000001")
                self.assertEqual(result["name"], "000001")  # 回退到股票代码


if __name__ == '__main__':
    unittest.main()