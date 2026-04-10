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

# 配置
# 优先从本地配置文件读取，其次从环境变量读取
try:
    import local_config
    EMAIL_USER = local_config.EMAIL_USER
    EMAIL_PASSWORD = local_config.EMAIL_PASSWORD
    EMAIL_RECIPIENT = local_config.EMAIL_RECIPIENT
    SMTP_SERVER = getattr(local_config, 'SMTP_SERVER', 'smtp.qq.com')
    SMTP_PORT = getattr(local_config, 'SMTP_PORT', 587)
    
    # GitHub配置
    GITHUB_TOKEN = getattr(local_config, 'GITHUB_TOKEN', None)
    DATA_REPO_OWNER = getattr(local_config, 'DATA_REPO_OWNER', 'tutsau')
    DATA_REPO_NAME = getattr(local_config, 'DATA_REPO_NAME', 'yuanshen-my-ugc-monitor-data')
    
    # Metrics API配置
    METRICS_COOKIES = getattr(local_config, 'METRICS_COOKIES', {})
    METRICS_HEADERS = getattr(local_config, 'METRICS_HEADERS', {})
except ImportError:
    # 本地配置文件不存在，从环境变量读取
    EMAIL_USER = os.environ.get('EMAIL_USER')
    EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
    EMAIL_RECIPIENT = os.environ.get('EMAIL_RECIPIENT')
    # 支持多种环境变量名称，优先使用 SMTP_SERVER，其次 EMAIL_SMTP_SERVER
    SMTP_SERVER = os.environ.get('SMTP_SERVER', os.environ.get('EMAIL_SMTP_SERVER', 'smtp.qq.com'))
    SMTP_PORT = int(os.environ.get('SMTP_PORT', os.environ.get('EMAIL_SMTP_PORT', '587')))
    
    # GitHub配置
    GITHUB_TOKEN = os.environ.get('MY_GITHUB_TOKEN')
    DATA_REPO_OWNER = os.environ.get('DATA_REPO_OWNER', 'tutsau')
    DATA_REPO_NAME = os.environ.get('DATA_REPO_NAME', 'yuanshen-my-ugc-monitor-data')
    
    # Metrics API配置
    import json
    METRICS_COOKIES = json.loads(os.environ.get('METRICS_COOKIES', '{}'))
    METRICS_HEADERS = json.loads(os.environ.get('METRICS_HEADERS', '{}'))

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


def fetch_metrics_data(level_id, region="cn_gf01", max_retries=3):
    """从metrics API获取真实数据
    
    Args:
        level_id: 关卡ID
        region: 区域代码，默认为 cn_gf01
        max_retries: 最大重试次数
    """
    # 构建API请求
    api_url = f"https://api-micreator.mihoyo.com/kolugc_hch/common/v1/data/get_stage_detail?lang=zh-cn&game_biz=hk4e_cn&uid=249673882&region={region}&stage_id={level_id}"
    
    # 使用配置中的headers和cookies
    headers = METRICS_HEADERS
    cookies = METRICS_COOKIES
    
    print(f"[INFO] Starting to fetch metrics data for level_id={level_id}, region={region}")
    print(f"[INFO] Target API URL: {api_url}")
    
    for retry in range(max_retries):
        try:
            print(f"[INFO] Attempt {retry + 1}/{max_retries}")
            response = requests.get(api_url, headers=headers, cookies=cookies, timeout=30)
            print(f"[INFO] Metrics API response status code: {response.status_code}")
            
            response.raise_for_status()
            
            api_data = response.json()
            print(f"[INFO] Metrics API response received successfully for level_id={level_id}")
            print(f"[INFO] Metrics API response keys: {list(api_data.keys())}")
            
            return api_data
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Error fetching metrics data (attempt {retry + 1}/{max_retries}): {e}")
            if retry < max_retries - 1:
                import time
                wait_time = 1
                print(f"[INFO] Retrying in {wait_time} second(s)...")
                time.sleep(wait_time)
            else:
                print(f"[ERROR] All {max_retries} attempts failed")
                return None


def parse_metrics_content(metrics_data):
    """解析metrics API返回的JSON数据，获取真实热度值和趋势数据"""
    try:
        # 打印完整的API响应，以便查看数据结构
        print(f"[DEBUG] Metrics API response data keys: {list(metrics_data.get('data', {}).keys())}")
        
        # 尝试提取数据
        if 'data' in metrics_data:
            data = metrics_data['data']
            
            # 提取关卡信息
            stage_info = data.get('stage_info', {})
            print(f"[DEBUG] Stage info keys: {list(stage_info.keys())}")
            
            # 提取基本信息
            level_name = stage_info.get('stage_name', 'Unknown')
            level_id = stage_info.get('stage_id', 'Unknown')
            
            # 提取真实热度值
            real_hot_score = None
            
            # 提取趋势数据
            trend_data_processed = {}
            
            # 检查today_stats
            if 'today_stats' in data:
                today_stats = data['today_stats']
                print(f"[DEBUG] Today stats type: {type(today_stats)}")
                # 处理today_stats可能是列表的情况
                if isinstance(today_stats, list):
                    for stat in today_stats:
                        print(f"[DEBUG] Stat in today_stats: {stat}")
                        if isinstance(stat, dict):
                            # 查找热度值指标
                            if stat.get('metric_type') == 'METRIC_STAGE_TYPE_STAGE_HOT_SCORE':
                                real_hot_score = int(stat.get('cur', '0'))
                                print(f"[DEBUG] Found real hot score: {real_hot_score}")
                                break
                else:
                    # 处理today_stats是字典的情况
                    if 'hot_score' in today_stats:
                        real_hot_score = today_stats['hot_score']
                    elif 'METRIC_STAGE_TYPE_STAGE_HOT_SCORE' in today_stats:
                        real_hot_score = today_stats['METRIC_STAGE_TYPE_STAGE_HOT_SCORE']
            
            # 检查trend_data
            if 'trend_data' in data:
                trend_data = data['trend_data']
                print(f"[DEBUG] Trend data type: {type(trend_data)}")
                if isinstance(trend_data, list):
                    print(f"[DEBUG] Trend data length: {len(trend_data)}")
                    for i, trend_item in enumerate(trend_data):
                        print(f"[DEBUG] Trend item {i} keys: {list(trend_item.keys())}")
                        metric_type = trend_item.get('metric_type')
                        
                        # 提取每日统计数据
                        if 'daily_stats' in trend_item and isinstance(trend_item['daily_stats'], list):
                            daily_stats = trend_item['daily_stats']
                            print(f"[DEBUG] Processing trend item {i} with metric_type: {metric_type}")
                            
                            # 存储处理后的趋势数据
                            trend_data_processed[metric_type] = {
                                'delta_7_day': trend_item.get('delta_7_day'),
                                'delta_7_day_invalid': trend_item.get('delta_7_day_invalid'),
                                'delta_30_day': trend_item.get('delta_30_day'),
                                'delta_30_day_invalid': trend_item.get('delta_30_day_invalid'),
                                'value_type': trend_item.get('value_type'),
                                'calculate_type': trend_item.get('calculate_type'),
                                'daily_stats': daily_stats
                            }
            
            # 检查stage_info中的热度值
            if real_hot_score is None and 'hot_score' in stage_info:
                real_hot_score = stage_info['hot_score']
            
            # 提取评论总数
            reply_count = 0
            if 'comment_module_info' in data:
                comment_info = data['comment_module_info']
                print(f"[DEBUG] Comment module info keys: {list(comment_info.keys())}")
                if 'total_comment_num' in comment_info:
                    reply_count = int(comment_info['total_comment_num'])
                elif 'comment_count' in comment_info:
                    reply_count = comment_info['comment_count']
            
            print(f"Extracted metrics data: level_name='{level_name}', level_id='{level_id}', real_hot_score={real_hot_score}, reply_count={reply_count}")
            print(f"Extracted trend data types: {list(trend_data_processed.keys())}")
            
            return {
                'title': level_name,
                'level_id': level_id,
                'real_hot_score': real_hot_score,  # 真实热度值
                'reply_count': reply_count,        # 评论总数
                'trend_data': trend_data_processed,  # 处理后的趋势数据
                'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
            }
        
        print(f"[ERROR] No data found in metrics response")
        return None
    except Exception as e:
        print(f"Error parsing metrics content: {e}")
        import traceback
        traceback.print_exc()
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


def save_trend_data(trend_data, monitor_id=None):
    """保存趋势数据到远程仓库，包括历史数据
    
    Args:
        trend_data: 处理后的趋势数据
        monitor_id: 监控器ID
    """
    # 使用全局配置
    token = GITHUB_TOKEN
    owner = DATA_REPO_OWNER
    repo = DATA_REPO_NAME
    
    # 构建趋势数据文件路径
    trend_data_path = f"data/{monitor_id}/trend_data.json" if monitor_id else "data/trend_data.json"
    
    # 构建API URL
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{trend_data_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 尝试获取现有文件
    response = requests.get(url, headers=headers)
    
    # 准备文件内容
    content = {
        'trend_data': trend_data,
        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
    }
    content_json = json.dumps(content, indent=2, ensure_ascii=False)
    content_encoded = content_json.encode('utf-8')
    import base64
    content_base64 = base64.b64encode(content_encoded).decode('utf-8')
    
    # 准备请求数据
    data = {
        "message": f"Update trend data for {monitor_id or 'default'}",
        "content": content_base64,
        "branch": "main"
    }
    
    # 如果文件存在，添加sha字段
    if response.status_code == 200:
        existing_file = response.json()
        data["sha"] = existing_file["sha"]
    
    # 发送请求
    response = requests.put(url, headers=headers, json=data)
    
    if response.status_code in [200, 201]:
        print(f"Trend data saved successfully to remote repo: {trend_data_path}")
    else:
        print(f"Failed to save trend data: {response.status_code} - {response.text}")
        return False
    
    # 保存历史趋势数据（按日期存储）
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    trend_history_path = f"data/{monitor_id}/trend_history/{today}.json" if monitor_id else f"data/trend_history/{today}.json"
    
    # 构建历史数据API URL
    history_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{trend_history_path}"
    
    # 尝试获取现有历史文件
    history_response = requests.get(history_url, headers=headers)
    
    # 准备历史文件内容
    history_content = {
        'trend_data': trend_data,
        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
    }
    history_json = json.dumps(history_content, indent=2, ensure_ascii=False)
    history_encoded = history_json.encode('utf-8')
    history_base64 = base64.b64encode(history_encoded).decode('utf-8')
    
    # 准备历史数据请求
    history_data = {
        "message": f"Save trend history for {today} - {monitor_id or 'default'}",
        "content": history_base64,
        "branch": "main"
    }
    
    # 如果文件存在，添加sha字段
    if history_response.status_code == 200:
        existing_history = history_response.json()
        history_data["sha"] = existing_history["sha"]
    
    # 发送历史数据请求
    history_response = requests.put(history_url, headers=headers, json=history_data)
    
    if history_response.status_code in [200, 201]:
        print(f"Trend history saved successfully to remote repo: {trend_history_path}")
        return True
    else:
        print(f"Failed to save trend history: {history_response.status_code} - {history_response.text}")
        return False


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
    
    # 获取metrics数据（真实热度值）
    metrics_data = fetch_metrics_data(level_id, region)
    if metrics_data:
        metrics_content = parse_metrics_content(metrics_data)
        if metrics_content and metrics_content.get('real_hot_score'):
            # 添加真实热度值到current_data
            current_data['real_hot_score'] = metrics_content['real_hot_score']
            print(f"[INFO] Added real hot score: {metrics_content['real_hot_score']}")
        
        # 保存趋势数据
        if metrics_content and metrics_content.get('trend_data'):
            print(f"[INFO] Saving trend data...")
            save_trend_data(metrics_content['trend_data'], monitor_id)
        else:
            print(f"[INFO] No trend data to save")
    
    print(f"[INFO] Current data parsed successfully:")
    print(f"[INFO]   Title: {current_data.get('title')}")
    print(f"[INFO]   Level ID: {current_data.get('level_id')}")
    print(f"[INFO]   Hot Score: {current_data.get('value1')} (num: {current_data.get('value1_num')})")
    if 'real_hot_score' in current_data:
        print(f"[INFO]   Real Hot Score: {current_data.get('real_hot_score')}")
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


def check_metrics_auth():
    """检查metrics接口认证信息是否过期
    
    Returns:
        bool: 认证是否有效
    """
    print("=" * 50)
    print("Checking metrics API authentication...")
    print("=" * 50)
    
    # 从配置中获取默认的level_id和region
    from data_manager import _get_config
    config = _get_config()
    
    # 使用默认的level_id和region
    level_id = '105949017109'
    region = 'cn_gf01'
    
    # 尝试获取metrics数据
    metrics_data = fetch_metrics_data(level_id, region)
    
    if not metrics_data:
        print("[ERROR] Failed to fetch metrics data - authentication may be expired")
        # 发送认证过期通知邮件
        send_metrics_auth_expired_email()
        return False
    
    print("[INFO] Metrics API authentication is valid")
    return True


def send_metrics_auth_expired_email():
    """发送metrics接口认证过期通知邮件"""
    if not all([EMAIL_USER, EMAIL_PASSWORD, EMAIL_RECIPIENT]):
        print("Email configuration missing")
        return False
    
    try:
        # 构建邮件
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = "【千星奇域】Metrics API 认证信息过期通知"
        
        # 构建HTML内容
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .info {{ background-color: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h2>Metrics API 认证信息过期通知</h2>
            
            <div class="warning">
                <h3>⚠️ 认证信息已过期</h3>
                <p>系统在尝试访问 Metrics API 时失败，可能是因为认证信息已过期。</p>
            </div>
            
            <div class="info">
                <h3>如何重置认证信息</h3>
                <ol>
                    <li>打开浏览器，访问大屏网页：<a href="https://act.mihoyo.com/miliastra_wonderland/developer#/StageData/stageDetail/105949017109">https://act.mihoyo.com/miliastra_wonderland/developer#/StageData/stageDetail/105949017109</a></li>
                    <li>登录你的米哈游账号</li>
                    <li>打开浏览器开发者工具（按 F12）</li>
                    <li>切换到 Network 标签页</li>
                    <li>刷新页面，找到名为 "get_stage_detail" 的请求</li>
                    <li>复制该请求的完整 cURL 命令</li>
                    <li>更新项目中的 cURL/metrics.txt 文件，替换为新的 cURL 命令</li>
                    <li>确保新的 cURL 命令中包含有效的认证信息（如 Cookie、Authorization 头）</li>
                </ol>
            </div>
            
            <p>请尽快更新认证信息，以确保监控系统能够正常获取趋势数据。</p>
        </body>
        </html>
        """
        
        # 添加HTML内容
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # 发送邮件
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print("[INFO] Metrics auth expired email sent successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Error sending metrics auth expired email: {e}")
        return False


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Monitor webpage data and send email notifications')
    parser.add_argument('--force-email', action='store_true', help='Force send email regardless of data changes')
    parser.add_argument('--daily-report', action='store_true', help='Generate and send daily report')
    parser.add_argument('--check-metrics-auth', action='store_true', help='Check if metrics API authentication is valid')
    args = parser.parse_args()
    
    # 判断邮件来源
    source = 'local-test'
    github_event_name = os.environ.get('GITHUB_EVENT_NAME')
    if github_event_name == 'schedule':
        source = 'workflow-schedule'
    elif github_event_name == 'push':
        source = 'workflow-push'
    
    if args.daily_report:
        # 生成每日报告（使用默认monitor_id）
        generate_and_send_daily_report(monitor_id='default')
    elif args.check_metrics_auth:
        # 检查metrics接口认证
        check_metrics_auth()
    else:
        # 运行正常监控（兼容旧版本）
        run_monitor(force_email=args.force_email, source=source)


if __name__ == "__main__":
    main()
