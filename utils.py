#!/usr/bin/env python3
"""
通用工具函数模块
包含项目中多个模块共享的工具函数
"""


def parse_hot_score(hot_score):
    """解析热度值，兼容 'x.x万' 格式
    
    Args:
        hot_score: 可以是数字或字符串（如 "1.2万"）
    
    Returns:
        int: 解析后的数字
    """
    if isinstance(hot_score, int):
        return hot_score
    
    if isinstance(hot_score, float):
        return int(hot_score)
    
    if isinstance(hot_score, str):
        # 处理 "x.x万" 格式
        hot_score = hot_score.strip()
        if '万' in hot_score:
            # 移除 "万" 字，转换为数字，然后乘以 10000
            num_part = hot_score.replace('万', '').strip()
            try:
                return int(float(num_part) * 10000)
            except ValueError:
                pass
        
        # 尝试直接转换为数字
        try:
            return int(float(hot_score))
        except ValueError:
            pass
    
    # 如果都失败，返回 0
    return 0
