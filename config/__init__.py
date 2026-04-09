#!/usr/bin/env python3
"""配置模块"""

import json
import os

def load_monitors_config():
    """加载监控器配置"""
    config_path = os.path.join(os.path.dirname(__file__), 'monitors.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('monitors', [])
    except Exception as e:
        print(f"Error loading monitors config: {e}")
        return []

def get_enabled_monitors():
    """获取启用的监控器列表"""
    monitors = load_monitors_config()
    return [m for m in monitors if m.get('enabled', True)]
