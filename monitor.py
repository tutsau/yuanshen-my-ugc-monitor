#!/usr/bin/env python3
"""
UGC Monitor - Main script
Monitors webpage data and sends email notifications
Supports daily report generation with heatmap charts
Supports multiple level monitoring
"""

import os
import json
import datetime
import smtplib
import argparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests

# 导入数据管理模块
from data_manager import (
    load_previous_data, 
    save_data, 
    append_history_data,
    get_last_24h_data,
    calculate_statistics,
    get_last_record
)
# 导入邮件工具模块
from email_utils import (
    generate_email_subject, 
    generate_email_content,
    generate_daily_report_email,
    attach_all_charts_to_email
)
# 导入图表生成模块
from chart_generator import generate_heatmap_chart, generate_change_chart, cleanup_chart_files
# 导入通用工具函数
from utils import parse_hot_score

# 邮件配置
# 优先从本地配置文件读取，其次从环境变量读取
try:
    import local_config
    EMAIL_USER = local_config.EMAIL_USER
    EMAIL_PASSWORD = local_config.EMAIL_PASSWORD
    EMAIL_RECIPIENT = local_config.EMAIL_RECIPIENT
    SMTP_SERVER = getattr(local_config, 'SMTP_SERVER', 'smtp.qq.com')
    SMTP_PORT = getattr(local_config, 'SMTP_PORT', 587)
except ImportError:
    # 本地配置文件不存在，从环境变量读取
    EMAIL_USER = os.environ.get('EMAIL_USER')
    EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
    EMAIL_RECIPIENT = os.environ.get('EMAIL_RECIPIENT')
    # 支持多种环境变量名称，优先使用 SMTP_SERVER，其次 EMAIL_SMTP_SERVER
    SMTP_SERVER = os.environ.get('SMTP_SERVER', os.environ.get('EMAIL_SMTP_SERVER', 'smtp.qq.com'))
    SMTP_PORT = int(os.environ.get('SMTP_PORT', os.environ.get('EMAIL_SMTP_PORT', '587')))

# 打印邮件配置信息（不包含密码）
print(f"Email configuration:")
print(f"EMAIL_USER: {EMAIL_USER}")
print(f"EMAIL_RECIPIENT: {EMAIL_RECIPIENT}")
print(f"SMTP_SERVER: {SMTP_SERVER}")
print(f"SMTP_PORT: {SMTP_PORT}")


def fetch_page(level_id, region="cn_gf01", monitor_config=None, max_retries=3):
    """获取页面数据
    
    Args:
        level_id: 关卡ID
        region: 区域代码，默认为 cn_gf01
        monitor_config: 监控器配置
        max_retries: 最大重试次数
    """
    # 获取关卡名称，优先使用监控器配置中的名称
    level_name = f"关卡 {level_id}"
    if monitor_config and monitor_config.get('name'):
        level_name = monitor_config['name']
    
    api_url = "https://bbs-api.miyoushe.com/community/ugc_community/web/api/level/full/info"
    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'content-type': 'application/json',
        'origin': 'https://act.miyoushe.com',
        'priority': 'u=1, i',
        'referer': 'https://act.miyoushe.com/',
        'sec-ch-ua': '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
        'x-rpc-client_type': '4',
        'x-rpc-language': 'zh-cn'
    }
    data = {
        "level_id": level_id,
        "region": region,
        "uid": "",
        "agg_req_list": [
            {"api_name": "level_detail"},
            {"api_name": "reply_card"}
        ]
    }
    
    print(f"[INFO] Starting to fetch API data for level_id={level_id}, region={region}")
    print(f"[INFO] Target API URL: {api_url}")
    
    for retry in range(max_retries):
        try:
            print(f"[INFO] Attempt {retry + 1}/{max_retries}")
            response = requests.post(api_url, headers=headers, json=data, timeout=30)
            print(f"[INFO] API response status code: {response.status_code}")
            
            response.raise_for_status()
            
            api_data = response.json()
            print(f"[INFO] API response received successfully for level_id={level_id}")
            print(f"[INFO] API response keys: {list(api_data.keys())}")
            if 'data' in api_data and 'resp_map' in api_data['data']:
                print(f"[INFO] resp_map keys: {list(api_data['data']['resp_map'].keys())}")
            
            return api_data
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Error fetching API data (attempt {retry + 1}/{max_retries}): {e}")
            if retry < max_retries - 1:
                import time
                wait_time = 1
                print(f"[INFO] Retrying in {wait_time} second(s)...")
                time.sleep(wait_time)
            else:
                print(f"[ERROR] All {max_retries} attempts failed")
                return None


def parse_content(api_data):
    """解析API返回的JSON数据"""
    try:
        # 提取数据
        level_info = api_data['data']['resp_map']['level_detail']['data']['level_detail_response']['level_info']
        level_name = level_info['level_name']
        level_id = level_info['level_id']
        hot_score_raw = level_info['hot_score']
        hot_score = parse_hot_score(hot_score_raw)
        good_rate = level_info['good_rate']
        
        # 提取评论总数
        reply_count = api_data['data']['resp_map']['reply_card']['data']['reply_card_response']['reply_count']
        
        print(f"Extracted data: level_name='{level_name}', level_id='{level_id}', hot_score_raw={hot_score_raw}, hot_score={hot_score}, good_rate='{good_rate}', reply_count={reply_count}")
        
        return {
            'title': level_name,
            'level_id': level_id,
            'value1': str(hot_score_raw),  # 热度值（原始格式，用于显示）
            'value1_num': hot_score,        # 热度值（数字格式，用于对比）
            'value2': good_rate,      # 好评率
            'value3': str(reply_count),  # 评论总数
            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
        }
    except Exception as e:
        print(f"Error parsing content: {e}")
        return None


def send_email(data, previous_data=None, monitor_id=None, source=None):
    """发送变更通知邮件
    
    Args:
        data: 当前数据
        previous_data: 之前的数据
        monitor_id: 监控器ID，用于区分不同关卡
        source: 邮件来源 ('local-test', 'workflow-schedule', 'workflow-push')
    """
    if not all([EMAIL_USER, EMAIL_PASSWORD, EMAIL_RECIPIENT]):
        print("Email configuration missing")
        print(f"EMAIL_USER: {EMAIL_USER}")
        print(f"EMAIL_RECIPIENT: {EMAIL_RECIPIENT}")
        print(f"SMTP_SERVER: {SMTP_SERVER}")
        print(f"SMTP_PORT: {SMTP_PORT}")
        return
    
    try:
        # 构建邮件内容
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_RECIPIENT
        
        # 生成邮件标题
        subject = generate_email_subject(data, previous_data, monitor_id)
        msg['Subject'] = subject
        
        # 生成HTML内容
        html_content = generate_email_content(data, previous_data, source)
        
        # 添加邮件正文
        part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part)
        
        # 发送邮件
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        try:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
            print(f"Email sent successfully from {EMAIL_USER} to {EMAIL_RECIPIENT}")
        finally:
            server.quit()
    except Exception as e:
        print(f"Error sending email: {e}")


def send_daily_report_email(data_list, statistics, monitor_id=None):
    """发送每日报告邮件
    
    Args:
        data_list: 数据列表
        statistics: 统计数据
        monitor_id: 监控器ID
    """
    if not all([EMAIL_USER, EMAIL_PASSWORD, EMAIL_RECIPIENT]):
        print("Email configuration missing")
        print(f"EMAIL_USER: {EMAIL_USER}")
        print(f"EMAIL_RECIPIENT: {EMAIL_RECIPIENT}")
        print(f"SMTP_SERVER: {SMTP_SERVER}")
        print(f"SMTP_PORT: {SMTP_PORT}")
        return False
    
    if not data_list or len(data_list) < 2:
        print("Not enough data to generate daily report")
        return False
    
    chart1_path = 'heatmap_chart.png'
    chart2_path = 'change_chart.png'
    
    try:
        # 生成热度趋势图
        print("Generating heatmap chart...")
        if not generate_heatmap_chart(data_list, chart1_path):
            print("Failed to generate heatmap chart")
            return False
        
        # 生成变化值图
        print("Generating change chart...")
        if not generate_change_chart(data_list, chart2_path):
            print("Failed to generate change chart")
            return False
        
        # 生成邮件内容
        subject, html_content = generate_daily_report_email(data_list, statistics, monitor_id)
        if not subject or not html_content:
            print("Failed to generate email content")
            return False
        
        # 构建邮件
        msg = MIMEMultipart('related')
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = subject
        
        # 添加HTML内容
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # 附加所有图表
        if not attach_all_charts_to_email(msg):
            print("Failed to attach charts to email")
            return False
        
        # 发送邮件
        print("Sending daily report email...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        try:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
            print(f"Daily report email sent successfully from {EMAIL_USER} to {EMAIL_RECIPIENT}")
        finally:
            server.quit()
        
        return True
        
    except Exception as e:
        print(f"Error sending daily report email: {e}")
        return False
    finally:
        # 清理临时图表文件
        cleanup_chart_files()


def generate_and_send_daily_report(monitor_id=None):
    """生成并发送每日报告
    
    Args:
        monitor_id: 监控器ID
    """
    print("=" * 50)
    print(f"Generating daily report for {monitor_id or 'default'}...")
    print("=" * 50)
    
    # 获取过去24小时的数据
    data_list = get_last_24h_data(monitor_id)
    
    if not data_list:
        print("No data available for the last 24 hours")
        return False
    
    print(f"Found {len(data_list)} data points for the last 24 hours")
    
    # 计算统计数据
    statistics = calculate_statistics(data_list)
    print(f"Statistics: max_hot={statistics['max_hot_score']}, min_hot={statistics['min_hot_score']}, avg_hot={statistics['avg_hot_score']}")
    
    # 发送报告邮件
    success = send_daily_report_email(data_list, statistics, monitor_id)
    
    if success:
        print("Daily report generated and sent successfully")
    else:
        print("Failed to generate or send daily report")
    
    return success


def run_monitor(monitor_config=None, force_email=False, source=None):
    """运行监控任务
    
    Args:
        monitor_config: 监控器配置字典，包含 id, name, level_id, region
        force_email: 是否强制发送邮件
        source: 邮件来源 ('local-test', 'workflow-schedule', 'workflow-push')
    """
    # 获取监控器配置
    if monitor_config:
        monitor_id = monitor_config.get('id', 'default')
        level_id = monitor_config.get('level_id')
        region = monitor_config.get('region', 'cn_gf01')
        monitor_name = monitor_config.get('name', f'关卡 {level_id}')
    else:
        # 兼容旧版本：使用默认值
        monitor_id = 'default'
        level_id = '105949017109'
        region = 'cn_gf01'
        monitor_name = '猜角色：猜猜我选谁'
    
    print("=" * 50)
    print(f"Running monitor task for {monitor_name} (ID: {monitor_id})...")
    print("=" * 50)
    
    # 获取API数据
    api_data = fetch_page(level_id, region, monitor_config)
    if not api_data:
        print(f"[ERROR] Failed to fetch API data for {monitor_id} after 3 attempts")
        print(f"[ERROR] 接口调用失败，未取到数据")
        return
    
    # 解析内容
    current_data = parse_content(api_data)
    if not current_data:
        print(f"[ERROR] Failed to parse content for {monitor_id}")
        return
    
    print(f"[INFO] Current data parsed successfully:")
    print(f"[INFO]   Title: {current_data.get('title')}")
    print(f"[INFO]   Level ID: {current_data.get('level_id')}")
    print(f"[INFO]   Hot Score: {current_data.get('value1')} (num: {current_data.get('value1_num')})")
    print(f"[INFO]   Good Rate: {current_data.get('value2')}")
    print(f"[INFO]   Reply Count: {current_data.get('value3')}")
    print(f"[INFO]   Timestamp: {current_data.get('timestamp')}")
    
    # 加载上次数据
    print(f"[INFO] Loading previous data for {monitor_id}...")
    previous_data = load_previous_data(monitor_id)
    
    if previous_data:
        print(f"[INFO] Previous data loaded successfully:")
        print(f"[INFO]   Title: {previous_data.get('title')}")
        print(f"[INFO]   Hot Score: {previous_data.get('value1')} (num: {previous_data.get('value1_num')})")
        print(f"[INFO]   Good Rate: {previous_data.get('value2')}")
        print(f"[INFO]   Reply Count: {previous_data.get('value3')}")
        print(f"[INFO]   Timestamp: {previous_data.get('timestamp')}")
    else:
        print(f"[INFO] No previous data found for {monitor_id}")
    
    # 获取最后一条历史记录
    print(f"[INFO] Getting last record for {monitor_id}...")
    last_record = get_last_record(monitor_id)
    if last_record:
        print(f"[INFO] Last record found: {last_record.get('timestamp')}")
    else:
        print(f"[INFO] No last record found for {monitor_id}")
    
    # 确保 previous_data 有 value1_num（兼容旧数据）
    if previous_data and 'value1_num' not in previous_data:
        # 旧数据没有 value1_num，尝试解析 value1
        prev_value1_num = parse_hot_score(previous_data.get('value1', '0'))
        previous_data['value1_num'] = prev_value1_num
        print(f"[INFO] Added value1_num to previous data: {prev_value1_num}")
    
    # 检查是否有变更（使用数值比较）
    has_changed = not previous_data or (
        current_data['title'] != previous_data['title'] or
        current_data['value1_num'] != previous_data.get('value1_num') or
        current_data['value2'] != previous_data['value2'] or
        current_data['value3'] != previous_data.get('value3')
    )
    
    print(f"[INFO] Data change check: {has_changed}")
    
    # 检查时间跨度是否超过1小时
    time_span_exceeded = False
    current_time = datetime.datetime.utcnow()
    
    # 检查历史记录的时间
    if last_record:
        try:
            timestamp = last_record['timestamp']
            # 处理带Z后缀的UTC时间
            if timestamp.endswith('Z'):
                # 移除Z后缀，使用无时区信息的时间
                last_time = datetime.datetime.fromisoformat(timestamp[:-1])
            else:
                last_time = datetime.datetime.fromisoformat(timestamp)
            time_diff = current_time - last_time
            if time_diff >= datetime.timedelta(hours=1):
                time_span_exceeded = True
                print(f"[INFO] Time span exceeded: last record was {time_diff.total_seconds()/3600:.1f} hours ago")
            else:
                print(f"[INFO] Time span within limit: last record was {time_diff.total_seconds()/3600:.1f} hours ago")
        except Exception as e:
            print(f"[ERROR] Error checking time span from last record: {e}")
    
    # 同时检查previous_data的时间
    if previous_data and 'timestamp' in previous_data:
        try:
            timestamp = previous_data['timestamp']
            # 处理带Z后缀的UTC时间
            if timestamp.endswith('Z'):
                # 移除Z后缀，使用无时区信息的时间
                prev_time = datetime.datetime.fromisoformat(timestamp[:-1])
            else:
                prev_time = datetime.datetime.fromisoformat(timestamp)
            time_diff = current_time - prev_time
            if time_diff >= datetime.timedelta(hours=1):
                time_span_exceeded = True
                print(f"[INFO] Time span exceeded: previous data was {time_diff.total_seconds()/3600:.1f} hours ago")
            else:
                print(f"[INFO] Time span within limit: previous data was {time_diff.total_seconds()/3600:.1f} hours ago")
        except Exception as e:
            print(f"[ERROR] Error checking time span from previous data: {e}")
    
    # 没有任何记录，视为时间跨度超过1小时
    if not last_record and not previous_data:
        time_span_exceeded = True
        print("[INFO] No previous record or data found, treating as time span exceeded")
    
    print(f"[INFO] Time span exceeded check: {time_span_exceeded}")
    
    # 决定是否发送邮件：数据变更、强制发送、或时间跨度超过1小时
    should_send_email = has_changed or force_email or time_span_exceeded
    
    print(f"[INFO] Should send email: {should_send_email}")
    
    if should_send_email:
        if force_email:
            print("[INFO] Forcing email send due to command line argument...")
        elif time_span_exceeded:
            print("[INFO] Sending email due to time span exceeded (more than 1 hour)...")
        else:
            print("[INFO] Sending email due to data changes...")
        # 发送邮件
        print("[INFO] Preparing to send email...")
        send_email(current_data, previous_data, monitor_id, source)
        print("[INFO] Email send process completed")
    else:
        print("[INFO] No changes detected and time span not exceeded, skipping email")
    
    # 保存当前数据
    print("[INFO] Saving current data to remote repo...")
    save_data(current_data, monitor_id)
    print("[INFO] Data save process completed")
    
    # 追加到历史数据：数据变更、或时间跨度超过1小时
    should_append_history = has_changed or time_span_exceeded
    print(f"[INFO] Should append history: {should_append_history}")
    
    if should_append_history:
        print("[INFO] Appending to history data...")
        append_history_data(current_data, monitor_id)
        print("[INFO] History append process completed")
    else:
        print("[INFO] Skipping history append (no changes and time span not exceeded)")
    
    if has_changed:
        print("[INFO] Data has changed")
    else:
        print("[INFO] No changes detected")
    
    print("[INFO] Monitor task completed successfully")


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Monitor webpage data and send email notifications')
    parser.add_argument('--force-email', action='store_true', help='Force send email regardless of data changes')
    parser.add_argument('--daily-report', action='store_true', help='Generate and send daily report')
    args = parser.parse_args()
    
    # 判断邮件来源
    source = 'local-test'
    github_event_name = os.environ.get('GITHUB_EVENT_NAME')
    if github_event_name == 'schedule':
        source = 'workflow-schedule'
    elif github_event_name == 'push':
        source = 'workflow-push'
    
    if args.daily_report:
        # 生成每日报告
        generate_and_send_daily_report()
    else:
        # 运行正常监控（兼容旧版本）
        run_monitor(force_email=args.force_email, source=source)


if __name__ == "__main__":
    main()
