# -*- coding: utf-8 -*-
"""
数据库连接和管理模块
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Generator
# 移除loguru以避免Python 3.6兼容性问题
# from loguru import logger
import os

from config import get_settings

# 简单的日志函数
def log_info(msg):
    print(f"[INFO] {msg}")

def log_error(msg):
    print(f"[ERROR] {msg}")

def log_warning(msg):
    print(f"[WARNING] {msg}")


Base = declarative_base()


class StockData(Base):
    """股票数据表"""
    __tablename__ = "stock_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, index=True, comment="股票代码")
    trade_date = Column(DateTime, nullable=False, index=True, comment="交易日期")
    open_price = Column(Float, comment="开盘价")
    high_price = Column(Float, comment="最高价")
    low_price = Column(Float, comment="最低价")
    close_price = Column(Float, comment="收盘价")
    volume = Column(Float, comment="成交量")
    amount = Column(Float, comment="成交额")
    turnover_rate = Column(Float, comment="换手率")
    pe_ratio = Column(Float, comment="市盈率")
    pb_ratio = Column(Float, comment="市净率")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class TradingOrder(Base):
    """交易订单表"""
    __tablename__ = "trading_orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), unique=True, nullable=False, comment="订单ID")
    stock_code = Column(String(20), nullable=False, index=True, comment="股票代码")
    order_type = Column(String(10), nullable=False, comment="订单类型(BUY/SELL)")
    price_type = Column(String(20), nullable=False, comment="价格类型")
    order_price = Column(Float, comment="委托价格")
    order_volume = Column(Integer, comment="委托数量")
    traded_volume = Column(Integer, default=0, comment="成交数量")
    order_status = Column(String(20), comment="订单状态")
    strategy_name = Column(String(100), comment="策略名称")
    remark = Column(Text, comment="备注")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class Position(Base):
    """持仓表"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String(50), nullable=False, comment="账户ID")
    stock_code = Column(String(20), nullable=False, index=True, comment="股票代码")
    volume = Column(Integer, default=0, comment="持仓数量")
    available_volume = Column(Integer, default=0, comment="可用数量")
    avg_price = Column(Float, comment="平均成本价")
    market_value = Column(Float, comment="市值")
    profit_loss = Column(Float, comment="盈亏")
    profit_loss_ratio = Column(Float, comment="盈亏比例")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class Strategy(Base):
    """策略表"""
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, comment="策略名称")
    description = Column(Text, comment="策略描述")
    strategy_type = Column(String(50), comment="策略类型")
    category = Column(String(50), comment="策略分类(stock_selection/trading/risk_management)")
    parameters = Column(JSON, comment="策略参数")
    conditions = Column(JSON, comment="策略条件配置")
    is_active = Column(Boolean, default=False, comment="是否激活")
    priority = Column(Integer, default=0, comment="优先级")
    created_by = Column(String(100), comment="创建者")
    version = Column(String(20), default="1.0", comment="版本号")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class StrategyCondition(Base):
    """策略条件表"""
    __tablename__ = "strategy_conditions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=False, comment="策略ID")
    condition_type = Column(String(50), nullable=False, comment="条件类型(technical/fundamental/custom)")
    indicator = Column(String(100), nullable=False, comment="指标名称")
    operator = Column(String(20), nullable=False, comment="操作符(>,<,>=,<=,==,!=,between,in)")
    value = Column(JSON, comment="条件值")
    logic_operator = Column(String(10), default="AND", comment="逻辑操作符(AND/OR)")
    order_index = Column(Integer, default=0, comment="条件顺序")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 关系
    strategy = relationship("Strategy", backref="strategy_conditions")


class StrategyExecution(Base):
    """策略执行记录表"""
    __tablename__ = "strategy_executions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=False, comment="策略ID")
    execution_type = Column(String(50), nullable=False, comment="执行类型(scan/backtest/live)")
    status = Column(String(20), nullable=False, comment="执行状态(running/completed/failed)")
    start_time = Column(DateTime, nullable=False, comment="开始时间")
    end_time = Column(DateTime, comment="结束时间")
    total_stocks = Column(Integer, default=0, comment="扫描股票总数")
    signal_count = Column(Integer, default=0, comment="信号数量")
    success_rate = Column(Float, comment="成功率")
    error_message = Column(Text, comment="错误信息")
    result_data = Column(JSON, comment="执行结果数据")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 关系
    strategy = relationship("Strategy", backref="executions")


class StrategySignal(Base):
    """策略信号表"""
    __tablename__ = "strategy_signals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=False, comment="策略ID")
    execution_id = Column(Integer, ForeignKey('strategy_executions.id'), comment="执行记录ID")
    stock_code = Column(String(20), nullable=False, index=True, comment="股票代码")
    signal_type = Column(String(20), nullable=False, comment="信号类型(BUY/SELL/HOLD)")
    signal_strength = Column(Float, comment="信号强度")
    trigger_price = Column(Float, comment="触发价格")
    target_price = Column(Float, comment="目标价格")
    stop_loss_price = Column(Float, comment="止损价格")
    reason = Column(Text, comment="信号原因")
    confidence = Column(Float, comment="置信度")
    is_processed = Column(Boolean, default=False, comment="是否已处理")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 关系
    strategy = relationship("Strategy", backref="signals")
    execution = relationship("StrategyExecution", backref="signals")


class BacktestResult(Base):
    """回测结果表"""
    __tablename__ = "backtest_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, nullable=False, comment="策略ID")
    start_date = Column(DateTime, comment="回测开始日期")
    end_date = Column(DateTime, comment="回测结束日期")
    initial_cash = Column(Float, comment="初始资金")
    final_cash = Column(Float, comment="最终资金")
    total_return = Column(Float, comment="总收益率")
    annual_return = Column(Float, comment="年化收益率")
    max_drawdown = Column(Float, comment="最大回撤")
    sharpe_ratio = Column(Float, comment="夏普比率")
    win_rate = Column(Float, comment="胜率")
    trade_count = Column(Integer, comment="交易次数")
    result_data = Column(JSON, comment="详细结果数据")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


class NotificationLog(Base):
    """通知日志表"""
    __tablename__ = "notification_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    notification_type = Column(String(50), comment="通知类型")
    title = Column(String(200), comment="通知标题")
    content = Column(Text, comment="通知内容")
    recipient = Column(String(100), comment="接收者")
    status = Column(String(20), comment="发送状态")
    error_message = Column(Text, comment="错误信息")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


# 数据库引擎和会话
engine = None
SessionLocal = None


def init_database():
    """初始化数据库"""
    global engine, SessionLocal
    
    settings = get_settings()
    
    # 确保数据目录存在
    if not settings.database.memory:
        db_dir = os.path.dirname(settings.database.path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    
    # 创建DuckDB引擎
    engine = create_engine(
        settings.database.url,
        echo=settings.debug
    )
    
    # 创建会话工厂
    SessionLocal = sessionmaker(
        bind=engine,
        expire_on_commit=False
    )
    
    # 创建表
    Base.metadata.create_all(engine)
    
    log_info(f"DuckDB数据库初始化完成: {settings.database.url}")


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话"""
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def close_database():
    """关闭数据库连接"""
    global engine
    if engine:
        engine.dispose()
        log_info("数据库连接已关闭")