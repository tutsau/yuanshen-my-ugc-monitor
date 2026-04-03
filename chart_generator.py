#!/usr/bin/env python3
"""
Chart generator module for UGC Monitor
Handles generation of heat score trend charts
"""

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os
import platform


def _setup_chinese_font():
    """设置中文字体，解决中文显示问题"""
    # 直接设置matplotlib的全局字体配置
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'sans-serif']
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['axes.unicode_minus'] = False
    
    # 在GitHub Actions环境中，使用更简单的方法确保中文显示
    print("Setting up font for Chinese display")


def generate_heatmap_chart(data_list, output_path='heatmap_chart.png'):
    """
    生成热度变化折线图
    
    Args:
        data_list: 包含历史数据的列表，每项包含 timestamp, hot_score
        output_path: 输出图片路径
    
    Returns:
        bool: 是否成功生成图表
    """
    if not data_list or len(data_list) < 2:
        print("Not enough data points to generate chart")
        return False
    
    try:
        # 设置中文字体
        _setup_chinese_font()
        
        # 准备数据
        timestamps = [datetime.fromisoformat(item['timestamp']) for item in data_list]
        hot_scores = [item['hot_score'] for item in data_list]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 设置标题
        title = data_list[0].get('title', 'UGC Monitor')
        plt.title(f'{title} - 24h Heat Trend', fontsize=16, fontweight='bold', pad=20)
        
        # 绘制热度值折线
        color = '#FF6B6B'
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Heat Score', color=color, fontsize=12)
        line = ax.plot(timestamps, hot_scores, color=color, linewidth=2, 
                         marker='o', markersize=4, label='Heat Score')
        ax.tick_params(axis='y', labelcolor=color)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # 设置X轴格式
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
        plt.xticks(rotation=45, ha='right')
        
        # 显示图例
        ax.legend(loc='upper left', framealpha=0.9)
        
        # 添加统计信息文本框
        stats_text = _generate_stats_text(data_list)
        plt.figtext(0.02, 0.02, stats_text, fontsize=9, 
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # 调整布局
        plt.tight_layout()
        
        # 保存图表
        plt.savefig(output_path, dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        print(f"Chart saved successfully to {output_path}")
        return True
        
    except Exception as e:
        print(f"Error generating chart: {e}")
        return False


def generate_change_chart(data_list, output_path='change_chart.png'):
    """
    生成热度变化值折线图（每个时间点相对于前一个时间点的变化）
    
    Args:
        data_list: 包含历史数据的列表，每项包含 timestamp, hot_score
        output_path: 输出图片路径
    
    Returns:
        bool: 是否成功生成图表
    """
    if not data_list or len(data_list) < 3:
        print("Not enough data points to generate change chart")
        return False
    
    try:
        # 设置中文字体
        _setup_chinese_font()
        
        # 准备数据：计算变化值
        timestamps = [datetime.fromisoformat(item['timestamp']) for item in data_list[1:]]  # 从第二个数据点开始
        hot_scores = [item['hot_score'] for item in data_list]
        changes = []
        for i in range(1, len(hot_scores)):
            change = hot_scores[i] - hot_scores[i-1]
            changes.append(change)
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 设置标题
        title = data_list[0].get('title', 'UGC Monitor')
        plt.title(f'{title} - 24h Heat Change Trend', fontsize=16, fontweight='bold', pad=20)
        
        # 绘制变化值折线
        color = '#9B59B6'
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Heat Change', color=color, fontsize=12)
        
        # 绘制正/负变化的柱状图和连接线
        for i, (ts, change) in enumerate(zip(timestamps, changes)):
            if change > 0:
                bar_color = '#E74C3C'
            elif change < 0:
                bar_color = '#27AE60'
            else:
                bar_color = '#95A5A6'
            ax.bar(ts, change, width=0.03, color=bar_color, alpha=0.7)
        
        # 绘制连接线
        line = ax.plot(timestamps, changes, color=color, linewidth=1.5, 
                         marker='o', markersize=5, label='Change Value')
        
        ax.tick_params(axis='y', labelcolor=color)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # 添加零线
        ax.axhline(y=0, color='#34495E', linestyle='-', linewidth=1, alpha=0.5)
        
        # 设置X轴格式
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
        plt.xticks(rotation=45, ha='right')
        
        # 显示图例
        ax.legend(loc='upper left', framealpha=0.9)
        
        # 添加统计信息文本框
        stats_text = _generate_change_stats_text(changes)
        plt.figtext(0.02, 0.02, stats_text, fontsize=9, 
                   bbox=dict(boxstyle='round', facecolor='lavender', alpha=0.5))
        
        # 调整布局
        plt.tight_layout()
        
        # 保存图表
        plt.savefig(output_path, dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        print(f"Change chart saved successfully to {output_path}")
        return True
        
    except Exception as e:
        print(f"Error generating change chart: {e}")
        return False


def _generate_stats_text(data_list):
    """生成统计信息文本"""
    if not data_list:
        return ""
    
    hot_scores = [item['hot_score'] for item in data_list]
    
    max_hot = max(hot_scores)
    min_hot = min(hot_scores)
    avg_hot = sum(hot_scores) // len(hot_scores)
    
    # 计算变化趋势
    first_hot = hot_scores[0]
    last_hot = hot_scores[-1]
    hot_change = last_hot - first_hot
    hot_change_pct = (hot_change / first_hot * 100) if first_hot > 0 else 0
    
    trend_symbol = "↑" if hot_change > 0 else "↓" if hot_change < 0 else "→"
    
    stats_text = (
        f"Heat Stats: Max {max_hot} | Min {min_hot} | Avg {avg_hot} | "
        f"Change {trend_symbol}{hot_change:+d} ({hot_change_pct:+.1f}%)"
    )
    
    return stats_text


def _generate_change_stats_text(changes):
    """生成变化值统计信息文本"""
    if not changes:
        return ""
    
    max_change = max(changes)
    min_change = min(changes)
    avg_change = sum(changes) // len(changes)
    total_change = sum(changes)
    
    positive_count = sum(1 for c in changes if c > 0)
    negative_count = sum(1 for c in changes if c < 0)
    zero_count = sum(1 for c in changes if c == 0)
    
    stats_text = (
        f"Change Stats: Total {total_change:+d} | Avg {avg_change:+d} | "
        f"Max +{max_change} | Min {min_change} | "
        f"Up {positive_count} times | Down {negative_count} times"
    )
    
    return stats_text


def cleanup_chart_files(chart_paths=None):
    """清理临时图表文件"""
    if chart_paths is None:
        chart_paths = ['heatmap_chart.png', 'change_chart.png']
    
    for chart_path in chart_paths:
        try:
            if os.path.exists(chart_path):
                os.remove(chart_path)
                print(f"Cleaned up chart file: {chart_path}")
        except Exception as e:
            print(f"Error cleaning up chart file {chart_path}: {e}")


if __name__ == "__main__":
    # 测试代码
    test_data = [
        {"timestamp": "2026-04-02T08:00:00", "hot_score": 6000, "title": "测试标题"},
        {"timestamp": "2026-04-02T10:00:00", "hot_score": 6100, "title": "测试标题"},
        {"timestamp": "2026-04-02T12:00:00", "hot_score": 6050, "title": "测试标题"},
        {"timestamp": "2026-04-02T14:00:00", "hot_score": 6200, "title": "测试标题"},
        {"timestamp": "2026-04-02T16:00:00", "hot_score": 6150, "title": "测试标题"},
    ]
    
    success1 = generate_heatmap_chart(test_data, 'test_chart.png')
    success2 = generate_change_chart(test_data, 'test_change_chart.png')
    
    if success1 and success2:
        print("Test charts generated successfully")
    else:
        print("Failed to generate test charts")
