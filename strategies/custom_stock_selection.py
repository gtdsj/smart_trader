# coding=utf-8
"""
自定义选股策略
基于用户提供的多维度筛选条件进行股票选择
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from core.database import get_db, StockData, Strategy, StrategySignal
from services.data_service import DataService
# from utils.logger import logger  # 使用简单的print替代
# from utils.stock_utils import StockUtils  # 模块不存在，移除导入


class CustomStockSelectionStrategy:
    """
    自定义选股策略
    
    选股条件：
    1. 非科创板（不以688开头）
    2. 非北交所（不以8开头或43开头）
    3. 非ST股（股票名称不包含ST、*ST等）
    4. 非破板股（需要具体定义破板条件）
    5. 3个交易日内每天的收盘价不低于5日均线
    6. 最近一个交易日收盘价涨跌幅在-5%到6.1%之间
    7. 最近两个交易日收盘价都高于开盘价
    8. 连续3个交易日五日均线角度>20且最近一个交易日五日均线角度>50
    9. 连续3个交易日十日均线角度>10
    10. 最近一个交易日主力资金净流入
    11. 最近一个交易日最低股价高于五日均线
    """
    
    def __init__(self, data_service: DataService):
        self.data_service = data_service
        self.name = "自定义多维度选股策略"
        self.description = "基于技术面、资金面等多维度条件的综合选股策略"
        
    async def screen_stocks(self, target_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        执行选股筛选
        
        Args:
            target_date: 目标日期，格式YYYY-MM-DD，默认为最新交易日
            
        Returns:
            符合条件的股票列表
        """
        try:
            print(f"[INFO] 开始执行{self.name}")
            
            # 获取所有股票代码
            all_stocks = await self._get_all_stocks()
            print(f"[INFO] 获取到{len(all_stocks)}只股票")
            
            selected_stocks = []
            
            for stock_code in all_stocks:
                try:
                    # 基础过滤
                    if not self._basic_filter(stock_code):
                        continue
                        
                    # 获取股票历史数据（最近20个交易日）
                    stock_data = await self._get_stock_data(stock_code, days=20)
                    if not stock_data or len(stock_data) < 15:
                        continue
                        
                    # 技术指标筛选
                    if await self._technical_filter(stock_data):
                        # 计算选股评分
                        score = await self._calculate_score(stock_data)
                        
                        selected_stocks.append({
                            'stock_code': stock_code,
                            'stock_name': await self._get_stock_name(stock_code),
                            'score': score,
                            'latest_price': stock_data[0]['close'],
                            'change_pct': stock_data[0]['change_pct'],
                            'volume': stock_data[0]['volume'],
                            'turnover': stock_data[0]['turnover'],
                            'selection_reason': self._get_selection_reason(stock_data),
                            'selection_time': datetime.now().isoformat()
                        })
                        
                except Exception as e:
                    print(f"[WARNING] 处理股票{stock_code}时出错: {e}")
                    continue
                    
            # 按评分排序
            selected_stocks.sort(key=lambda x: x['score'], reverse=True)
            
            print(f"[INFO] {self.name}完成，共筛选出{len(selected_stocks)}只股票")
            return selected_stocks
            
        except Exception as e:
            print(f"[ERROR] {self.name}执行失败: {e}")
            raise
            
    def _basic_filter(self, stock_code: str) -> bool:
        """
        基础过滤条件
        
        Args:
            stock_code: 股票代码
            
        Returns:
            是否通过基础过滤
        """
        # 1. 非科创板（不以688开头）
        if stock_code.startswith('688'):
            return False
            
        # 2. 非北交所（不以8开头或43开头）
        if stock_code.startswith('8') or stock_code.startswith('43'):
            return False
            
        # 3. 非ST股（这里简化处理，实际需要从股票名称判断）
        # TODO: 需要获取股票名称进行ST判断
        
        return True
        
    async def _technical_filter(self, stock_data: List[Dict]) -> bool:
        """
        技术指标过滤
        
        Args:
            stock_data: 股票历史数据，按日期倒序排列
            
        Returns:
            是否通过技术指标过滤
        """
        try:
            # 计算技术指标
            df = pd.DataFrame(stock_data)
            df = df.sort_values('trade_date')
            
            # 计算移动平均线
            df['ma5'] = df['close'].rolling(window=5).mean()
            df['ma10'] = df['close'].rolling(window=10).mean()
            
            # 计算均线角度（斜率）
            df['ma5_angle'] = self._calculate_ma_angle(df['ma5'])
            df['ma10_angle'] = self._calculate_ma_angle(df['ma10'])
            
            # 按日期倒序排列（最新数据在前）
            df = df.sort_values('trade_date', ascending=False)
            
            # 检查各项条件
            
            # 5. 3个交易日内每天的收盘价不低于5日均线
            for i in range(3):
                if i >= len(df) or df.iloc[i]['close'] < df.iloc[i]['ma5']:
                    return False
                    
            # 6. 最近一个交易日收盘价涨跌幅在-5%到6.1%之间
            latest_change = df.iloc[0]['change_pct']
            if latest_change < -5.0 or latest_change > 6.1:
                return False
                
            # 7. 最近两个交易日收盘价都高于开盘价
            for i in range(2):
                if i >= len(df) or df.iloc[i]['close'] <= df.iloc[i]['open']:
                    return False
                    
            # 8. 连续3个交易日五日均线角度>20且最近一个交易日五日均线角度>50
            for i in range(3):
                if i >= len(df) or df.iloc[i]['ma5_angle'] <= 20:
                    return False
            if df.iloc[0]['ma5_angle'] <= 50:
                return False
                
            # 9. 连续3个交易日十日均线角度>10
            for i in range(3):
                if i >= len(df) or df.iloc[i]['ma10_angle'] <= 10:
                    return False
                    
            # 10. 最近一个交易日主力资金净流入
            # TODO: 需要资金流向数据
            
            # 11. 最近一个交易日最低股价高于五日均线
            if df.iloc[0]['low'] <= df.iloc[0]['ma5']:
                return False
                
            return True
            
        except Exception as e:
            print(f"[ERROR] 技术指标过滤失败: {e}")
            return False
            
    def _calculate_ma_angle(self, ma_series: pd.Series, window: int = 3) -> pd.Series:
        """
        计算移动平均线角度（斜率）
        
        Args:
            ma_series: 移动平均线序列
            window: 计算角度的窗口期
            
        Returns:
            角度序列
        """
        angles = []
        for i in range(len(ma_series)):
            if i < window - 1:
                angles.append(np.nan)
            else:
                # 计算最近window期的斜率
                y_values = ma_series.iloc[i-window+1:i+1].values
                x_values = np.arange(window)
                
                if len(y_values) == window and not np.isnan(y_values).any():
                    # 线性回归计算斜率
                    slope = np.polyfit(x_values, y_values, 1)[0]
                    # 转换为角度（度）
                    angle = np.degrees(np.arctan(slope))
                    angles.append(angle)
                else:
                    angles.append(np.nan)
                    
        return pd.Series(angles, index=ma_series.index)
        
    async def _calculate_score(self, stock_data: List[Dict]) -> float:
        """
        计算选股评分
        
        Args:
            stock_data: 股票历史数据
            
        Returns:
            评分（0-100）
        """
        try:
            df = pd.DataFrame(stock_data)
            df = df.sort_values('trade_date', ascending=False)
            
            score = 0.0
            
            # 基础分数
            score += 20
            
            # 涨跌幅评分（-5%到6.1%之间，越接近中位数分数越高）
            change_pct = df.iloc[0]['change_pct']
            optimal_change = 0.55  # 最优涨跌幅
            change_score = max(0, 20 - abs(change_pct - optimal_change) * 2)
            score += change_score
            
            # 成交量评分（相对于平均成交量）
            avg_volume = df['volume'].mean()
            latest_volume = df.iloc[0]['volume']
            volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 1
            volume_score = min(20, volume_ratio * 10)
            score += volume_score
            
            # 技术指标评分
            df['ma5'] = df['close'].rolling(window=5).mean()
            df['ma5_angle'] = self._calculate_ma_angle(df['ma5'])
            
            # 五日均线角度评分
            ma5_angle = df.iloc[0]['ma5_angle']
            if not np.isnan(ma5_angle):
                angle_score = min(20, ma5_angle / 3)  # 角度越大分数越高
                score += angle_score
            
            # 价格位置评分（收盘价相对于5日均线的位置）
            price_position = (df.iloc[0]['close'] - df.iloc[0]['ma5']) / df.iloc[0]['ma5'] * 100
            position_score = min(20, max(0, price_position * 2))
            score += position_score
            
            return min(100, max(0, score))
            
        except Exception as e:
            print(f"[ERROR] 计算评分失败: {e}")
            return 0.0
            
    def _get_selection_reason(self, stock_data: List[Dict]) -> str:
        """
        生成选股理由
        
        Args:
            stock_data: 股票历史数据
            
        Returns:
            选股理由
        """
        try:
            df = pd.DataFrame(stock_data)
            df = df.sort_values('trade_date', ascending=False)
            
            reasons = []
            
            # 涨跌幅
            change_pct = df.iloc[0]['change_pct']
            reasons.append(f"涨跌幅{change_pct:.2f}%")
            
            # 连续阳线
            yang_days = 0
            for i in range(min(5, len(df))):
                if df.iloc[i]['close'] > df.iloc[i]['open']:
                    yang_days += 1
                else:
                    break
            if yang_days >= 2:
                reasons.append(f"连续{yang_days}日阳线")
                
            # 均线支撑
            df['ma5'] = df['close'].rolling(window=5).mean()
            if df.iloc[0]['close'] > df.iloc[0]['ma5']:
                reasons.append("站稳5日均线")
                
            return "; ".join(reasons)
            
        except Exception as e:
            print(f"[ERROR] 生成选股理由失败: {e}")
            return "符合多维度选股条件"
            
    async def _get_all_stocks(self) -> List[str]:
        """
        获取所有股票代码
        
        Returns:
            股票代码列表
        """
        try:
            session = next(get_db())
            try:
                # 获取所有A股代码
                stocks = session.query(StockData.stock_code).distinct().all()
                return [stock[0] for stock in stocks if stock[0]]
            finally:
                session.close()
        except Exception as e:
            print(f"[ERROR] 获取股票列表失败: {e}")
            return []
            
    async def _get_stock_data(self, stock_code: str, days: int = 20) -> List[Dict]:
        """
        获取股票历史数据
        
        Args:
            stock_code: 股票代码
            days: 获取天数
            
        Returns:
            股票数据列表
        """
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')
            
            session = next(get_db())
            try:
                query = session.query(StockData).filter(
                    and_(
                        StockData.stock_code == stock_code,
                        StockData.trade_date >= start_date,
                        StockData.trade_date <= end_date
                    )
                ).order_by(desc(StockData.trade_date)).limit(days)
                
                data = []
                for record in query.all():
                    data.append({
                        'trade_date': record.trade_date,
                        'open': record.open,
                        'high': record.high,
                        'low': record.low,
                        'close': record.close,
                        'volume': record.volume,
                        'turnover': record.turnover,
                        'change_pct': record.change_pct
                    })
                    
                return data
            finally:
                session.close()
                
        except Exception as e:
            print(f"[ERROR] 获取股票{stock_code}数据失败: {e}")
            return []
            
    async def _get_stock_name(self, stock_code: str) -> str:
        """
        获取股票名称
        
        Args:
            stock_code: 股票代码
            
        Returns:
            股票名称
        """
        # TODO: 从数据库或API获取股票名称
        return f"股票{stock_code}"