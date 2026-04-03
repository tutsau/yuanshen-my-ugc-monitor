#!/usr/bin/env python3
"""
UGC Monitor - All Levels
Main entry point for monitoring multiple levels
"""

import argparse
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_enabled_monitors
from monitor import run_monitor, generate_and_send_daily_report


def monitor_all_levels(force_email=False, source=None):
    """监控所有启用的关卡"""
    monitors = get_enabled_monitors()
    
    if not monitors:
        print("No enabled monitors found in config")
        return
    
    print(f"Found {len(monitors)} enabled monitor(s)")
    print("=" * 60)
    
    for monitor_config in monitors:
        monitor_id = monitor_config.get('id', 'unknown')
        monitor_name = monitor_config.get('name', f'关卡 {monitor_id}')
        
        print(f"\n>>> Processing monitor: {monitor_name} (ID: {monitor_id})")
        print("-" * 60)
        
        try:
            run_monitor(monitor_config=monitor_config, force_email=force_email, source=source)
        except Exception as e:
            print(f"Error processing monitor {monitor_id}: {e}")
            continue
        
        print("-" * 60)
    
    print("\n" + "=" * 60)
    print("All monitors processed")
    print("=" * 60)


def daily_report_all():
    """为所有启用的关卡生成每日报告"""
    monitors = get_enabled_monitors()
    
    if not monitors:
        print("No enabled monitors found in config")
        return
    
    print(f"Found {len(monitors)} enabled monitor(s)")
    print("=" * 60)
    
    for monitor_config in monitors:
        monitor_id = monitor_config.get('id', 'unknown')
        monitor_name = monitor_config.get('name', f'关卡 {monitor_id}')
        
        print(f"\n>>> Generating daily report for: {monitor_name} (ID: {monitor_id})")
        print("-" * 60)
        
        try:
            generate_and_send_daily_report(monitor_id=monitor_id)
        except Exception as e:
            print(f"Error generating daily report for {monitor_id}: {e}")
            continue
        
        print("-" * 60)
    
    print("\n" + "=" * 60)
    print("All daily reports generated")
    print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Monitor multiple UGC levels and send email notifications'
    )
    parser.add_argument(
        '--force-email', 
        action='store_true', 
        help='Force send email regardless of data changes'
    )
    parser.add_argument(
        '--daily-report', 
        action='store_true', 
        help='Generate and send daily reports for all monitors'
    )
    args = parser.parse_args()
    
    # 判断邮件来源
    source = 'local-test'
    github_event_name = os.environ.get('GITHUB_EVENT_NAME')
    if github_event_name == 'schedule':
        source = 'workflow-schedule'
    elif github_event_name == 'push':
        source = 'workflow-push'
    
    # 当由push触发时，强制发送邮件
    force_email = args.force_email
    if github_event_name == 'push':
        force_email = True
        print("Force sending email due to push trigger")
    
    if args.daily_report:
        # 生成所有关卡的每日报告
        daily_report_all()
    else:
        # 监控所有启用的关卡
        monitor_all_levels(force_email=force_email, source=source)


if __name__ == "__main__":
    main()
