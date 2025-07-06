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
        try:
            # 创建序列
            conn.execute(text("CREATE SEQUENCE IF NOT EXISTS stock_data_id_seq"))
            conn.execute(text("CREATE SEQUENCE IF NOT EXISTS trading_orders_id_seq"))
            conn.execute(text("CREATE SEQUENCE IF NOT EXISTS positions_id_seq"))
            conn.execute(text("CREATE SEQUENCE IF NOT EXISTS strategies_id_seq"))
            conn.execute(text("CREATE SEQUENCE IF NOT EXISTS strategy_conditions_id_seq"))
            conn.execute(text("CREATE SEQUENCE IF NOT EXISTS strategy_executions_id_seq"))
            conn.execute(text("CREATE SEQUENCE IF NOT EXISTS strategy_signals_id_seq"))
            conn.execute(text("CREATE SEQUENCE IF NOT EXISTS backtest_results_id_seq"))
            conn.execute(text("CREATE SEQUENCE IF NOT EXISTS notification_logs_id_seq"))
            conn.commit()
            
            # 创建股票数据表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS stock_data (
                    id INTEGER PRIMARY KEY DEFAULT nextval('stock_data_id_seq'),
                    stock_code VARCHAR(20) NOT NULL,
                    trade_date TIMESTAMP NOT NULL,
                    open_price DOUBLE,
                    high_price DOUBLE,
                    low_price DOUBLE,
                    close_price DOUBLE,
                    volume DOUBLE,
                    amount DOUBLE,
                    turnover_rate DOUBLE,
                    pe_ratio DOUBLE,
                    pb_ratio DOUBLE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            
            # 创建交易订单表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS trading_orders (
                    id INTEGER PRIMARY KEY DEFAULT nextval('trading_orders_id_seq'),
                    order_id VARCHAR(50) UNIQUE NOT NULL,
                    stock_code VARCHAR(20) NOT NULL,
                    order_type VARCHAR(10) NOT NULL,
                    quantity INTEGER NOT NULL,
                    price DOUBLE,
                    status VARCHAR(20) DEFAULT 'PENDING',
                    strategy_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    executed_at TIMESTAMP,
                    executed_price DOUBLE,
                    executed_quantity INTEGER DEFAULT 0,
                    commission DOUBLE DEFAULT 0.0,
                    error_message TEXT
                )
            """))
            conn.commit()
            
            # 创建持仓表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY DEFAULT nextval('positions_id_seq'),
                    stock_code VARCHAR(20) NOT NULL,
                    quantity INTEGER NOT NULL,
                    avg_cost DOUBLE NOT NULL,
                    current_price DOUBLE,
                    market_value DOUBLE,
                    unrealized_pnl DOUBLE,
                    realized_pnl DOUBLE DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            
            # 创建策略表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS strategies (
                    id INTEGER PRIMARY KEY DEFAULT nextval('strategies_id_seq'),
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    strategy_type VARCHAR(50) NOT NULL,
                    category VARCHAR(50) NOT NULL DEFAULT 'stock_selection',
                    parameters TEXT,
                    conditions TEXT,
                    priority INTEGER DEFAULT 0,
                    created_by VARCHAR(100) DEFAULT 'system',
                    version VARCHAR(20) DEFAULT '1.0',
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            
            # 创建策略条件表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS strategy_conditions (
                    id INTEGER PRIMARY KEY DEFAULT nextval('strategy_conditions_id_seq'),
                    strategy_id INTEGER NOT NULL,
                    condition_type VARCHAR(50) NOT NULL,
                    indicator VARCHAR(100) NOT NULL,
                    operator VARCHAR(20) NOT NULL,
                    value TEXT,
                    logic_operator VARCHAR(10) DEFAULT 'AND',
                    order_index INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            
            # 创建策略执行记录表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS strategy_executions (
                    id INTEGER PRIMARY KEY DEFAULT nextval('strategy_executions_id_seq'),
                    strategy_id INTEGER NOT NULL,
                    execution_type VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    total_stocks INTEGER DEFAULT 0,
                    signal_count INTEGER DEFAULT 0,
                    success_rate DOUBLE,
                    error_message TEXT,
                    result_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            
            # 创建策略信号表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS strategy_signals (
                    id INTEGER PRIMARY KEY DEFAULT nextval('strategy_signals_id_seq'),
                    strategy_id INTEGER NOT NULL,
                    execution_id INTEGER,
                    stock_code VARCHAR(20) NOT NULL,
                    signal_type VARCHAR(20) NOT NULL,
                    signal_strength DOUBLE,
                    trigger_price DOUBLE,
                    target_price DOUBLE,
                    stop_loss_price DOUBLE,
                    reason TEXT,
                    confidence DOUBLE,
                    is_processed BOOLEAN DEFAULT false,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            
            # 创建回测结果表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS backtest_results (
                    id INTEGER PRIMARY KEY DEFAULT nextval('backtest_results_id_seq'),
                    strategy_id INTEGER NOT NULL,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    initial_cash DOUBLE,
                    final_cash DOUBLE,
                    total_return DOUBLE,
                    annual_return DOUBLE,
                    max_drawdown DOUBLE,
                    sharpe_ratio DOUBLE,
                    win_rate DOUBLE,
                    trade_count INTEGER,
                    result_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            
            # 创建通知日志表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS notification_logs (
                    id INTEGER PRIMARY KEY DEFAULT nextval('notification_logs_id_seq'),
                    type VARCHAR(50) NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    content TEXT,
                    level VARCHAR(20) DEFAULT 'INFO',
                    is_sent BOOLEAN DEFAULT false,
                    sent_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            
            # 创建日线股票数据表（用于数据服务）
            conn.execute(text("""
                CREATE SEQUENCE IF NOT EXISTS daily_stock_data_id_seq
            """))
            conn.commit()
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS daily_stock_data (
                    id INTEGER PRIMARY KEY DEFAULT nextval('daily_stock_data_id_seq'),
                    stock_code VARCHAR(20) NOT NULL,
                    trade_date DATE NOT NULL,
                    open_price DECIMAL(10,3),
                    high_price DECIMAL(10,3),
                    low_price DECIMAL(10,3),
                    close_price DECIMAL(10,3),
                    volume BIGINT,
                    amount DECIMAL(20,2),
                    turnover_rate DECIMAL(8,4),
                    pe_ratio DECIMAL(10,4),
                    pb_ratio DECIMAL(10,4),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_code, trade_date)
                )
            """))
            conn.commit()
            
            # 创建日线数据表索引
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_daily_stock_code ON daily_stock_data(stock_code)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_daily_trade_date ON daily_stock_data(trade_date)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_daily_code_date ON daily_stock_data(stock_code, trade_date)
            """))
            conn.commit()
            
            log_info("数据库表创建完成")
        except Exception as e:
            log_error(f"创建数据库表时出错: {e}")
            import traceback
            log_error(f"错误详情: {traceback.format_exc()}")
            raise


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
    category = Column(String(50), nullable=False, default="stock_selection")
    parameters = Column(Text)  # JSON格式存储策略参数
    conditions = Column(Text)  # JSON格式存储策略条件
    priority = Column(Integer, default=0)
    created_by = Column(String(100), default="system")
    version = Column(String(20), default="1.0")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系映射
    strategy_conditions = relationship("StrategyCondition", back_populates="strategy")
    executions = relationship("StrategyExecution", back_populates="strategy")
    signals = relationship("StrategySignal", back_populates="strategy")


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
    strategy = relationship("Strategy", back_populates="strategy_conditions")


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
    strategy = relationship("Strategy", back_populates="executions")
    signals = relationship("StrategySignal", back_populates="execution")


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
    strategy = relationship("Strategy", back_populates="signals")
    execution = relationship("StrategyExecution", back_populates="signals")


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
_database_initialized = False
_database_initializing = False
_initialization_lock = None


def init_database():
    """初始化数据库连接（单例模式，确保只初始化一次）"""
    global engine, SessionLocal, _database_initialized, _database_initializing, _initialization_lock
    
    # 使用线程锁确保线程安全
    import threading
    if _initialization_lock is None:
        _initialization_lock = threading.Lock()
    
    # 快速检查（无锁）
    if _database_initialized and engine is not None and SessionLocal is not None:
        log_info("数据库已经初始化，跳过重复初始化")
        return
    
    # 如果正在初始化，等待完成
    if _database_initializing:
        log_info("数据库正在初始化中，等待完成...")
        while _database_initializing:
            import time
            time.sleep(0.1)
        # 等待完成后再次检查
        if _database_initialized and engine is not None and SessionLocal is not None:
            log_info("数据库初始化已完成")
            return
    
    # 获取锁进行初始化
    with _initialization_lock:
        # 双重检查锁定模式 - 再次检查状态
        if _database_initialized and engine is not None and SessionLocal is not None:
            log_info("数据库已经初始化（双重检查），跳过重复初始化")
            return
        
        if _database_initializing:
            log_info("其他线程正在初始化，等待完成")
            return
        
        log_info("开始初始化数据库连接...")
        
        # 标记为正在初始化
        _database_initializing = True
        _database_initialized = False
    
    try:
        settings = get_settings()
        log_info(f"正在连接数据库: {settings.database.url}")
        
        # 确保数据库目录存在
        if settings.database.url.startswith('duckdb://'):
            db_path = settings.database.url.replace('duckdb:///', '')
            if db_path != ':memory:':
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                log_info(f"数据库路径: {db_path}")
        
        # 处理DuckDB连接和编码问题
        database_url = settings.database.url
        
        if database_url.startswith('duckdb:///'):
            db_path = database_url.replace('duckdb:///', '')
            
            # 检查数据库文件状态
            if db_path != ':memory:':
                log_info(f"检查数据库文件: {db_path}")
                
                # 如果文件存在但可能损坏，尝试删除重建
                if os.path.exists(db_path):
                    try:
                        # 测试文件是否可读
                        with open(db_path, 'rb') as f:
                            # 读取文件头部检查是否为有效的DuckDB文件
                            header = f.read(16)
                            if len(header) < 16 or header[:4] != b'DUCK':
                                log_warning(f"数据库文件格式无效，删除重建: {db_path}")
                                os.remove(db_path)
                    except (OSError, IOError, UnicodeDecodeError) as e:
                        log_warning(f"数据库文件读取失败，删除重建: {e}")
                        try:
                            os.remove(db_path)
                        except:
                            pass
                
                # 设置环境变量以避免编码问题
                import locale
                try:
                    # 设置系统编码
                    os.environ['PYTHONIOENCODING'] = 'utf-8'
                    os.environ['LC_ALL'] = 'C.UTF-8'
                    locale.setlocale(locale.LC_ALL, 'C.UTF-8')
                except:
                    try:
                        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
                    except:
                        pass
                
                # 尝试使用ASCII安全的路径
                safe_db_path = db_path
                try:
                    # 检查路径是否包含非ASCII字符
                    db_path.encode('ascii')
                except UnicodeEncodeError:
                    # 如果路径包含非ASCII字符，使用临时目录
                    import tempfile
                    temp_dir = tempfile.gettempdir()
                    safe_db_path = os.path.join(temp_dir, 'smart_trader.db')
                    log_warning(f"路径包含非ASCII字符，使用临时路径: {safe_db_path}")
                    database_url = f'duckdb:///{safe_db_path}'
                
                # 尝试创建新的数据库连接
                connection_attempts = [
                    (safe_db_path, "安全路径"),
                    (os.path.join(os.getcwd(), 'temp_smart_trader.db'), "当前目录临时文件"),
                    (':memory:', "内存数据库")
                ]
                
                for attempt_path, attempt_desc in connection_attempts:
                    try:
                        log_info(f"尝试{attempt_desc}连接: {attempt_path}")
                        test_conn = duckdb.connect(attempt_path)
                        # 测试基本操作
                        test_conn.execute("SELECT 1")
                        test_conn.close()
                        log_info(f"{attempt_desc}连接测试成功")
                        
                        # 更新数据库URL
                        if attempt_path == ':memory:':
                            database_url = 'duckdb:///:memory:'
                        else:
                            database_url = f'duckdb:///{attempt_path}'
                        break
                        
                    except Exception as e:
                        log_error(f"{attempt_desc}连接失败: {e}")
                        # 删除可能损坏的文件
                        if attempt_path != ':memory:' and os.path.exists(attempt_path):
                            try:
                                os.remove(attempt_path)
                                log_info(f"已删除损坏的数据库文件: {attempt_path}")
                            except:
                                pass
                        continue
                else:
                    # 所有尝试都失败了
                    log_error("所有数据库连接尝试都失败，强制使用内存数据库")
                    database_url = 'duckdb:///:memory:'
        
        log_info(f"创建数据库引擎: {database_url}")
        engine = create_engine(database_url)
        
        log_info("手动创建数据库表...")
        # 使用原生DuckDB SQL创建表，避免SQLAlchemy的SERIAL问题
        create_tables_manually(engine)
        
        log_info("创建会话工厂...")
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # 标记数据库已初始化
        _database_initialized = True
        _database_initializing = False
        log_info("数据库初始化成功")
        
    except Exception as e:
        # 重置初始化状态
        _database_initializing = False
        _database_initialized = False
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
    global engine, SessionLocal, _database_initialized, _database_initializing
    if engine:
        engine.dispose()
        engine = None
        SessionLocal = None
        _database_initialized = False
        _database_initializing = False
        log_info("数据库连接已关闭")


def reset_database():
    """重置数据库连接（用于测试或重新初始化）"""
    global _database_initialized, _database_initializing, _initialization_lock
    
    log_info("重置数据库连接...")
    close_database()
    
    # 重置初始化锁
    if _initialization_lock:
        with _initialization_lock:
            _database_initialized = False
            _database_initializing = False
    else:
        _database_initialized = False
        _database_initializing = False
    
    log_info("数据库连接已重置")


def is_database_initialized():
    """检查数据库是否已初始化"""
    global engine, SessionLocal, _database_initialized
    return _database_initialized and engine is not None and SessionLocal is not None