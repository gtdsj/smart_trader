# -*- coding: utf-8 -*-
"""
Config package for smart_trader
"""

# 从根目录的 config.py 重新导出主要的配置函数和类
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import get_settings, SystemConfig, reload_settings, save_settings, create_default_config_file

__all__ = ['get_settings', 'SystemConfig', 'reload_settings', 'save_settings', 'create_default_config_file']