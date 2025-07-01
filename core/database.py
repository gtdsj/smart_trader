# -*- coding: utf-8 -*-
"""
数据库连接和管理模块
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Generator
# 移除loguru以避免Python 3.6兼容性问题
# from loguru import logger
import os
import duckdb

from config import get_settings

# 简单的日志函数
def log_info(msg):
    print(f"[INFO] {msg}")

def log_error(msg):
    print(f"[ERROR] {msg}")

def log_warning(msg):
    print(f"[WARNING] {msg}")


Base = declarative_base()

def create_tables_manually(engine):
    """手动创建数据库表，避免SQLAlchemy的SERIAL问题"""
    with engine.connect() as conn:
        # 创建股票数据表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stock_data (
                id INTEGER PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL,
                trade_date TIMESTAMP NOT NULL,
                open_price FLOAT,
                high_price FLOAT,
                low_price FLOAT,
                close_price FLOAT,
                volume FLOAT,
                amount FLOAT,
                turnover_rate FLOAT,
                pe_ratio FLOAT,
                pb_ratio FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # 创建交易订单表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS trading_orders (
                id INTEGER PRIMARY KEY,
                order_id VARCHAR(50) UNIQUE NOT NULL,
                stock_code VARCHAR(20) NOT NULL,
                order_type VARCHAR(10) NOT NULL,
                quantity INTEGER NOT NULL,
                price FLOAT,
                status VARCHAR(20) DEFAULT 'PENDING',
                strategy_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                executed_at TIMESTAMP,
                executed_price FLOAT,
                executed_quantity INTEGER DEFAULT 0,
                commission FLOAT DEFAULT 0.0,
                error_message TEXT
            )
        """))
        
        # 创建持仓表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL,
                quantity INTEGER NOT NULL,
                avg_cost FLOAT NOT NULL,
                current_price FLOAT,
                market_value FLOAT,
                unrealized_pnl FLOAT,
                realized_pnl FLOAT DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # 创建策略表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                strategy_type VARCHAR(50) NOT NULL,
                parameters TEXT,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        log_info("数据库表创建完成")


class StockData(Base):
    """股票数据表"""
    __tablename__ = "stock_data"
    
    id = Column(Integer, primary_key=True)
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
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")


class TradingOrder(Base):
    """交易订单表"""
    __tablename__ = "trading_orders"
    
    id = Column(Integer, primary_key=True)
    order_id = Column(String(50), unique=True, nullable=False, index=True)
    stock_code = Column(String(20), nullable=False, index=True)
    order_type = Column(String(10), nullable=False)  # BUY, SELL
    order_status = Column(String(20), nullable=False, index=True)  # PENDING, FILLED, CANCELLED, REJECTED
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    filled_quantity = Column(Integer, default=0)
    filled_price = Column(Float)
    commission = Column(Float, default=0.0)
    strategy_name = Column(String(100))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Position(Base):
    """持仓表"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True)
    stock_code = Column(String(20), nullable=False, unique=True, index=True)
    quantity = Column(Integer, nullable=False)
    avg_cost = Column(Float, nullable=False)
    current_price = Column(Float)
    market_value = Column(Float)
    profit_loss = Column(Float)
    profit_loss_ratio = Column(Float)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Strategy(Base):
    """策略表"""
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text)
    strategy_type = Column(String(50), nullable=False)
    parameters = Column(Text)  # JSON格式存储策略参数
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class StrategyCondition(Base):
    """策略条件表"""
    __tablename__ = "strategy_conditions"
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=False)
    condition_type = Column(String(50), nullable=False)
    indicator = Column(String(100), nullable=False)
    operator = Column(String(20), nullable=False)
    value = Column(Text)  # 改为Text类型
    logic_operator = Column(String(10), default="AND")
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    # 关系
    strategy = relationship("Strategy", backref="strategy_conditions")


class StrategyExecution(Base):
    """策略执行记录表"""
    __tablename__ = "strategy_executions"
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=False)
    execution_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    total_stocks = Column(Integer, default=0)
    signal_count = Column(Integer, default=0)
    success_rate = Column(Float)
    error_message = Column(Text)
    result_data = Column(Text)  # 改为Text类型
    created_at = Column(DateTime, default=func.now())
    
    # 关系
    strategy = relationship("Strategy", backref="executions")


class StrategySignal(Base):
    """策略信号表"""
    __tablename__ = "strategy_signals"
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=False)
    execution_id = Column(Integer, ForeignKey('strategy_executions.id'))
    stock_code = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(20), nullable=False)
    signal_strength = Column(Float)
    trigger_price = Column(Float)
    target_price = Column(Float)
    stop_loss_price = Column(Float)
    reason = Column(Text)
    confidence = Column(Float)
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    # 关系
    strategy = relationship("Strategy", backref="signals")
    execution = relationship("StrategyExecution", backref="signals")


class BacktestResult(Base):
    """回测结果表"""
    __tablename__ = "backtest_results"
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, nullable=False)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    initial_cash = Column(Float)
    final_cash = Column(Float)
    total_return = Column(Float)
    annual_return = Column(Float)
    max_drawdown = Column(Float)
    sharpe_ratio = Column(Float)
    win_rate = Column(Float)
    trade_count = Column(Integer)
    result_data = Column(Text)  # 改为Text类型
    created_at = Column(DateTime, default=func.now())


class NotificationLog(Base):
    """通知日志表"""
    __tablename__ = "notification_logs"
    
    id = Column(Integer, primary_key=True)
    type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    level = Column(String(20), default='INFO')
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())


# 数据库引擎和会话
engine = None
SessionLocal = None


def init_database():
    """初始化数据库连接"""
    global engine, SessionLocal
    
    try:
        settings = get_settings()
        log_info(f"正在连接数据库: {settings.database.url}")
        
        # 确保数据库目录存在
        if settings.database.url.startswith('duckdb://'):
            db_path = settings.database.url.replace('duckdb:///', '')
            if db_path != ':memory:':
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                log_info(f"数据库路径: {db_path}")
        
        log_info("创建数据库引擎...")
        engine = create_engine(settings.database.url)
        
        log_info("手动创建数据库表...")
        # 使用原生DuckDB SQL创建表，避免SQLAlchemy的SERIAL问题
        create_tables_manually(engine)
        
        log_info("创建会话工厂...")
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        log_info("数据库初始化成功")
        
    except Exception as e:
        log_error(f"数据库初始化失败: {e}")
        import traceback
        log_error(f"错误详情: {traceback.format_exc()}")
        raise


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


def get_duckdb_connection():
    """获取DuckDB连接"""
    global engine
    if engine is None:
        init_database()
    return engine.raw_connection()


def close_database():
    """关闭数据库连接"""
    global engine
    if engine:
        engine.dispose()
        log_info("数据库连接已关闭")