#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DuckDB适配器
为Python 3.6提供DuckDB支持
"""
import traceback
import duckdb
import os
from typing import Any, Dict, List, Optional
# 移除loguru以避免Python 3.6兼容性问题
# from loguru import logger

# 简单的日志函数
def log_info(msg):
    print(f"[INFO] {msg}")

def log_error(msg):
    print(f"[ERROR] {msg}")

def log_warning(msg):
    print(f"[WARNING] {msg}")


class DuckDBAdapter:
    """DuckDB数据库适配器"""
    
    def __init__(self, db_path: str = None, connection=None):
        """
        初始化DuckDB连接
        
        Args:
            db_path: 数据库文件路径，None表示内存数据库
            connection: 已存在的数据库连接，如果提供则使用此连接
        """
        self.db_path = db_path
        self.connection = connection
        if self.connection is None:
            self._connect()
    
    def _connect(self):
        """建立数据库连接"""
        try:
            if self.db_path:
                # 确保目录存在
                db_dir = os.path.dirname(self.db_path)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)
                
                # 检查数据库文件是否存在且可能损坏
                if os.path.exists(self.db_path):
                    try:
                        # 尝试连接现有数据库
                        self.connection = duckdb.connect(self.db_path)
                        # 测试连接是否正常
                        self.connection.execute("SELECT 1")
                        log_info(f"DuckDB连接成功: {self.db_path}")
                    except (UnicodeDecodeError, Exception) as e:
                        log_warning(f"现有数据库文件可能损坏: {e}")
                        # 备份损坏的数据库文件
                        backup_path = f"{self.db_path}.backup"
                        if os.path.exists(backup_path):
                            os.remove(backup_path)
                        os.rename(self.db_path, backup_path)
                        log_info(f"已备份损坏的数据库文件到: {backup_path}")
                        # 创建新的数据库连接
                        self.connection = duckdb.connect(self.db_path)
                        log_info(f"DuckDB重新创建连接成功: {self.db_path}")
                else:
                    # 创建新的数据库文件
                    self.connection = duckdb.connect(self.db_path)
                    log_info(f"DuckDB新建连接成功: {self.db_path}")
            else:
                self.connection = duckdb.connect(":memory:")
                log_info("DuckDB内存数据库连接成功")
            
            # 应用性能优化配置
            self._optimize_connection()
            
        except Exception as e:
            log_error(f"DuckDB连接失败: {e}, {traceback.format_exc()}")
            # 如果仍然失败，尝试使用内存数据库作为备选方案
            try:
                log_warning("尝试使用内存数据库作为备选方案")
                self.connection = duckdb.connect(":memory:")
                self._optimize_connection()
                log_info("DuckDB内存数据库备选连接成功")
            except Exception as fallback_e:
                log_error(f"备选连接也失败: {fallback_e}")
                raise
    
    def _optimize_connection(self):
        """优化DuckDB连接性能配置"""
        try:
            # 设置内存限制 (2GB)
            self.connection.execute("SET memory_limit='2GB'")
            
            # 设置线程数为CPU核心数
            import os
            cpu_count = os.cpu_count() or 4
            self.connection.execute(f"SET threads={cpu_count}")
            
            # 启用并行处理
            self.connection.execute("SET enable_progress_bar=false")
            
            # 设置临时目录 - 使用系统临时目录避免中文路径编码问题
            import tempfile
            temp_dir = tempfile.gettempdir()
            # 确保使用英文路径，避免编码问题
            try:
                self.connection.execute(f"SET temp_directory='{temp_dir}'")
            except UnicodeDecodeError:
                # 如果仍有编码问题，使用默认设置
                log_warning("临时目录设置失败，使用默认配置")
                pass
            
            # 优化查询性能
            self.connection.execute("SET enable_optimizer=true")
            
            log_info(f"DuckDB性能优化配置完成: 线程数={cpu_count}, 内存限制=2GB")
            
        except Exception as e:
            log_warning(f"DuckDB性能优化配置失败: {e}")
    
    def execute(self, sql: str, params: tuple = None) -> Any:
        """执行SQL语句
        
        Args:
            sql: SQL语句
            params: 参数
        
        Returns:
            执行结果
        """
        try:
            if params:
                result = self.connection.execute(sql, params)
            else:
                result = self.connection.execute(sql)
            return result
        except Exception as e:
            log_error(f"SQL执行失败: {sql}, 错误: {e}")
            raise
    
    def executemany(self, sql: str, params_list: List[tuple]) -> Any:
        """批量执行SQL语句
        
        Args:
            sql: SQL语句
            params_list: 参数列表
        
        Returns:
            执行结果
        """
        try:
            result = self.connection.executemany(sql, params_list)
            return result
        except Exception as e:
            log_error(f"批量SQL执行失败: {sql}, 错误: {e}")
            raise
    
    def fetchall(self, sql: str, params: tuple = None) -> List[tuple]:
        """查询所有结果
        
        Args:
            sql: SQL语句
            params: 参数
        
        Returns:
            查询结果列表
        """
        try:
            result = self.execute(sql, params)
            return result.fetchall()
        except Exception as e:
            log_error(f"查询失败: {sql}, 错误: {e}")
            return []
    
    def fetchone(self, sql: str, params: tuple = None) -> Optional[tuple]:
        """查询单个结果
        
        Args:
            sql: SQL语句
            params: 参数
        
        Returns:
            查询结果
        """
        try:
            result = self.execute(sql, params)
            return result.fetchone()
        except Exception as e:
            log_error(f"查询失败: {sql}, 错误: {e}")
            return None
    
    def fetchdf(self, sql: str, params: tuple = None):
        """查询结果返回DataFrame
        
        Args:
            sql: SQL语句
            params: 参数
        
        Returns:
            pandas DataFrame
        """
        try:
            if params:
                return self.connection.execute(sql, params).fetchdf()
            else:
                return self.connection.execute(sql).fetchdf()
        except Exception as e:
            log_error(f"查询DataFrame失败: {sql}, 错误: {e}")
            return None
    
    def create_table_from_dict(self, table_name: str, data: List[Dict[str, Any]]):
        """从字典列表创建表
        
        Args:
            table_name: 表名
            data: 数据列表
        """
        try:
            if not data:
                log_warning(f"数据为空，无法创建表: {table_name}")
                return
            
            # 删除已存在的表
            self.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # 从第一行数据推断列类型
            first_row = data[0]
            columns = []
            for key, value in first_row.items():
                if isinstance(value, int):
                    col_type = "INTEGER"
                elif isinstance(value, float):
                    col_type = "DOUBLE"
                elif isinstance(value, bool):
                    col_type = "BOOLEAN"
                else:
                    col_type = "VARCHAR"
                columns.append(f"{key} {col_type}")
            
            # 创建表
            create_sql = f"CREATE TABLE {table_name} ({', '.join(columns)})"
            self.execute(create_sql)
            
            # 插入数据
            if data:
                keys = list(first_row.keys())
                placeholders = ', '.join(['?' for _ in keys])
                insert_sql = f"INSERT INTO {table_name} ({', '.join(keys)}) VALUES ({placeholders})"
                
                for row in data:
                    values = tuple(row[key] for key in keys)
                    self.execute(insert_sql, values)
            
            log_info(f"表 {table_name} 创建成功，插入 {len(data)} 条记录")
            
        except Exception as e:
            log_error(f"创建表失败: {table_name}, 错误: {e}")
            raise
    
    def insert_dict(self, table_name: str, data: Dict[str, Any]):
        """插入字典数据
        
        Args:
            table_name: 表名
            data: 数据字典
        """
        try:
            keys = list(data.keys())
            values = tuple(data.values())
            placeholders = ', '.join(['?' for _ in keys])
            
            sql = f"INSERT INTO {table_name} ({', '.join(keys)}) VALUES ({placeholders})"
            self.execute(sql, values)
            
        except Exception as e:
            log_error(f"插入数据失败: {table_name}, 错误: {e}")
            raise
    
    def update_dict(self, table_name: str, data: Dict[str, Any], where_clause: str, where_params: tuple = None):
        """更新字典数据
        
        Args:
            table_name: 表名
            data: 更新数据字典
            where_clause: WHERE条件
            where_params: WHERE参数
        """
        try:
            set_clauses = [f"{key} = ?" for key in data.keys()]
            values = list(data.values())
            
            if where_params:
                values.extend(where_params)
            
            sql = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {where_clause}"
            self.execute(sql, tuple(values))
            
        except Exception as e:
            log_error(f"更新数据失败: {table_name}, 错误: {e}")
            raise
    
    def delete(self, table_name: str, where_clause: str, where_params: tuple = None):
        """删除数据
        
        Args:
            table_name: 表名
            where_clause: WHERE条件
            where_params: WHERE参数
        """
        try:
            sql = f"DELETE FROM {table_name} WHERE {where_clause}"
            self.execute(sql, where_params)
            
        except Exception as e:
            log_error(f"删除数据失败: {table_name}, 错误: {e}")
            raise
    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在
        
        Args:
            table_name: 表名
        
        Returns:
            bool: 表是否存在
        """
        try:
            result = self.fetchone(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            return result is not None
        except Exception:
            return False
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表结构信息
        
        Args:
            table_name: 表名
        
        Returns:
            表结构信息列表
        """
        try:
            sql = f"PRAGMA table_info({table_name})"
            result = self.fetchall(sql)
            
            columns = []
            for row in result:
                columns.append({
                    'name': row[1],
                    'type': row[2],
                    'not_null': bool(row[3]),
                    'default_value': row[4],
                    'primary_key': bool(row[5])
                })
            
            return columns
        except Exception as e:
            log_error(f"获取表信息失败: {table_name}, 错误: {e}")
            return []
    
    def close(self):
        """关闭数据库连接"""
        try:
            if self.connection:
                self.connection.close()
                log_info("DuckDB连接已关闭")
        except Exception as e:
            log_error(f"关闭DuckDB连接失败: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 全局数据库实例
_db_instance = None


def get_duckdb() -> DuckDBAdapter:
    """获取全局DuckDB实例"""
    global _db_instance
    if _db_instance is None:
        from config import get_settings
        settings = get_settings()
        
        if settings.database.memory:
            _db_instance = DuckDBAdapter()
        else:
            _db_instance = DuckDBAdapter(settings.database.path)
        
        log_info("DuckDB适配器初始化完成")
    
    return _db_instance


def init_duckdb():
    """初始化DuckDB"""
    db = get_duckdb()
    # 表创建已移至统一的 core.database 模块
    log_info("DuckDB服务启动")


def _create_tables(db: DuckDBAdapter):
    """创建数据库表 - 已移除，使用统一的 core.database 模块"""
    # 表创建逻辑已移至 core.database 模块
    # 这里不再重复创建表，避免冲突
    log_info("DuckDB适配器：跳过表创建，使用统一数据库模块")


def close_duckdb():
    """关闭DuckDB"""
    global _db_instance
    if _db_instance:
        _db_instance.close()
        _db_instance = None
        log_info("DuckDB服务关闭")