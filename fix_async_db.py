#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复所有服务文件中的 async for db in get_db() 错误
"""

import os
import re
from pathlib import Path

def fix_async_db_pattern(file_path: str) -> bool:
    """修复单个文件中的异步数据库模式"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否包含需要修复的模式
        if 'async for db in get_db():' not in content:
            return False
        
        print(f"修复文件: {file_path}")
        
        # 替换模式
        # 匹配: async for db in get_db():
        # 替换为: db_gen = get_db(); db = next(db_gen); try:
        pattern = r'(\s+)async for db in get_db\(\):'
        
        def replace_func(match):
            indent = match.group(1)
            return f"{indent}db_gen = get_db()\n{indent}db = next(db_gen)\n{indent}try:"
        
        new_content = re.sub(pattern, replace_func, content)
        
        # 需要为每个修复的块添加对应的 finally 子句
        # 这需要更复杂的逻辑来匹配代码块
        lines = new_content.split('\n')
        fixed_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            fixed_lines.append(line)
            
            # 如果这行包含 db = next(db_gen)，需要找到对应的代码块结束位置
            if 'db = next(db_gen)' in line and 'try:' in line:
                indent = len(line) - len(line.lstrip())
                base_indent = ' ' * indent
                
                # 找到对应的代码块结束
                j = i + 1
                brace_count = 1
                
                while j < len(lines) and brace_count > 0:
                    next_line = lines[j]
                    
                    # 计算缩进级别
                    if next_line.strip():
                        next_indent = len(next_line) - len(next_line.lstrip())
                        
                        # 如果缩进回到原始级别或更少，说明代码块结束
                        if next_indent <= indent:
                            # 在这里插入 finally 块
                            fixed_lines.append(f"{base_indent}finally:")
                            fixed_lines.append(f"{base_indent}    db.close()")
                            break
                    
                    fixed_lines.append(next_line)
                    j += 1
                
                i = j - 1
            
            i += 1
        
        # 还需要移除 await db.execute 中的 await
        final_content = '\n'.join(fixed_lines)
        final_content = re.sub(r'await db\.execute\(', 'db.execute(', final_content)
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        return True
        
    except Exception as e:
        print(f"修复文件 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    # 需要修复的服务文件
    service_files = [
        'services/trading_service.py',
        'services/strategy_executor.py', 
        'services/backtest_service.py',
        'services/notification_service.py',
        'services/strategy_service.py',
        'services/data_service.py',
        'services/strategy_manager.py'
    ]
    
    base_dir = Path(__file__).parent
    fixed_count = 0
    
    for service_file in service_files:
        file_path = base_dir / service_file
        if file_path.exists():
            if fix_async_db_pattern(str(file_path)):
                fixed_count += 1
        else:
            print(f"文件不存在: {file_path}")
    
    print(f"\n修复完成，共修复 {fixed_count} 个文件")
    print("\n注意：由于代码结构复杂，建议手动检查修复结果")
    print("主要修改：")
    print("1. async for db in get_db(): -> db_gen = get_db(); db = next(db_gen); try:")
    print("2. await db.execute() -> db.execute()")
    print("3. 添加 finally: db.close()")

if __name__ == '__main__':
    main()