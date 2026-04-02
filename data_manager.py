#!/usr/bin/env python3
"""
Data management module for UGC Monitor
Handles data loading and saving from/to remote repository
Stores data by monitor_id and date: previous_{monitor_id}.json, data/{date}.json
"""

import os
import json
import requests
import datetime


def _get_config():
    """获取配置信息"""
    try:
        import local_config
        return {
            'DATA_REPO_OWNER': local_config.DATA_REPO_OWNER,
            'DATA_REPO_NAME': local_config.DATA_REPO_NAME,
            'GITHUB_TOKEN': local_config.MY_GITHUB_TOKEN
        }
    except ImportError:
        return {
            'DATA_REPO_OWNER': os.environ.get('DATA_REPO_OWNER', 'tutsau'),
            'DATA_REPO_NAME': os.environ.get('DATA_REPO_NAME', 'yuanshen-my-ugc-monitor-data'),
            'GITHUB_TOKEN': os.environ.get('MY_GITHUB_TOKEN')
        }


def _get_previous_data_path(monitor_id=None):
    """获取previous_data文件路径"""
    if monitor_id:
        return f"data/{monitor_id}/previous.json"
    return "previous_data.json"


def _get_date_file_path(dt=None, monitor_id=None):
    """获取日期文件路径"""
    if dt is None:
        dt = datetime.datetime.now()
    
    if monitor_id:
        return f"data/{monitor_id}/{dt.strftime('%Y-%m-%d')}.json"
    return f"data/{dt.strftime('%Y-%m-%d')}.json"


def load_previous_data(monitor_id=None):
    """从远程仓库加载之前的数据
    
    Args:
        monitor_id: 监控器ID，用于隔离不同关卡的数据
    """
    config = _get_config()
    GITHUB_TOKEN = config['GITHUB_TOKEN']
    
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN not found, cannot load data from remote repo")
        return None
    
    file_path = _get_previous_data_path(monitor_id)
    url = f"https://api.github.com/repos/{config['DATA_REPO_OWNER']}/{config['DATA_REPO_NAME']}/contents/{file_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            content = response.json()
            import base64
            decoded_content = base64.b64decode(content["content"]).decode("utf-8")
            print(f"Data loaded successfully from remote repo: {file_path}")
            return json.loads(decoded_content)
        elif response.status_code == 404:
            print(f"Data file not found in remote repo: {file_path}, returning None")
            return None
        else:
            print(f"Error loading data from remote repo: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error loading data from remote repo: {e}")
        return None


def save_data(data, monitor_id=None):
    """将数据保存到远程仓库
    
    Args:
        data: 要保存的数据
        monitor_id: 监控器ID，用于隔离不同关卡的数据
    """
    config = _get_config()
    GITHUB_TOKEN = config['GITHUB_TOKEN']
    
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN not found, cannot save data to remote repo")
        return
    
    file_path = _get_previous_data_path(monitor_id)
    url = f"https://api.github.com/repos/{config['DATA_REPO_OWNER']}/{config['DATA_REPO_NAME']}/contents/{file_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 先获取当前文件的SHA（如果存在）
    response = requests.get(url, headers=headers)
    sha = None
    if response.status_code == 200:
        sha = response.json()["sha"]
    
    # 准备数据
    import base64
    content = base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")).decode("utf-8")
    payload = {
        "message": f"Update monitor data for {monitor_id or 'default'}",
        "content": content,
        "sha": sha
    }
    
    try:
        response = requests.put(url, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            print(f"Data saved successfully to remote repo: {file_path}")
        else:
            print(f"Error saving data to remote repo: {response.status_code}")
            print(response.json())
    except Exception as e:
        print(f"Error saving data to remote repo: {e}")


def load_date_data(dt=None, monitor_id=None):
    """加载指定日期的数据
    
    Args:
        dt: 日期对象
        monitor_id: 监控器ID，用于隔离不同关卡的数据
    """
    config = _get_config()
    GITHUB_TOKEN = config['GITHUB_TOKEN']
    
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN not found, cannot load date data from remote repo")
        return None
    
    file_path = _get_date_file_path(dt, monitor_id)
    url = f"https://api.github.com/repos/{config['DATA_REPO_OWNER']}/{config['DATA_REPO_NAME']}/contents/{file_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            content = response.json()
            import base64
            decoded_content = base64.b64decode(content["content"]).decode("utf-8")
            print(f"Data loaded successfully for date: {file_path}")
            return json.loads(decoded_content)
        elif response.status_code == 404:
            print(f"Data file not found for date: {file_path}, returning None")
            return None
        else:
            print(f"Error loading date data: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error loading date data: {e}")
        return None


def save_date_data(dt=None, data=None, monitor_id=None):
    """保存指定日期的数据
    
    Args:
        dt: 日期对象
        data: 要保存的数据
        monitor_id: 监控器ID，用于隔离不同关卡的数据
    """
    if data is None:
        data = {}
    
    config = _get_config()
    GITHUB_TOKEN = config['GITHUB_TOKEN']
    
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN not found, cannot save date data to remote repo")
        return False
    
    file_path = _get_date_file_path(dt, monitor_id)
    url = f"https://api.github.com/repos/{config['DATA_REPO_OWNER']}/{config['DATA_REPO_NAME']}/contents/{file_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 先获取当前文件的SHA（如果存在）
    response = requests.get(url, headers=headers)
    sha = None
    if response.status_code == 200:
        sha = response.json()["sha"]
    
    # 准备数据
    import base64
    content = base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")).decode("utf-8")
    payload = {
        "message": f"Update data for {file_path.split('/')[-1]}",
        "content": content,
        "sha": sha
    }
    
    try:
        response = requests.put(url, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            print(f"Data saved successfully for date: {file_path}")
            return True
        else:
            print(f"Error saving date data: {response.status_code}")
            print(response.json())
            return False
    except Exception as e:
        print(f"Error saving date data: {e}")
        return False


def append_history_data(current_data, monitor_id=None):
    """追加当前数据到历史记录（按日期分片存储）
    
    Args:
        current_data: 当前数据
        monitor_id: 监控器ID，用于隔离不同关卡的数据
    """
    now = datetime.datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M:%S')
    
    # 加载当天的数据
    date_data = load_date_data(now, monitor_id)
    
    # 初始化日期数据结构
    if date_data is None:
        date_data = {
            "date": date_str,
            "monitor_id": monitor_id,
            "level_id": current_data.get('level_id', ''),
            "title": current_data.get('title', ''),
            "records": []
        }
    
    # 创建新的记录项
    record = {
        "time": time_str,
        "hot_score": int(current_data.get('value1', 0)),
        "reply_count": int(current_data.get('value3', 0)),
        "good_rate": current_data.get('value2', 'N/A')
    }
    
    # 追加到记录列表
    date_data["records"].append(record)
    
    # 保存回远程仓库
    save_date_data(now, date_data, monitor_id)
    
    return date_data


def get_last_24h_data(monitor_id=None):
    """获取过去24小时的历史数据
    
    Args:
        monitor_id: 监控器ID，用于隔离不同关卡的数据
    """
    now = datetime.datetime.now()
    all_records = []
    
    # 检查今天和昨天的数据
    for days_ago in [0, 1]:
        check_date = now - datetime.timedelta(days=days_ago)
        date_data = load_date_data(check_date, monitor_id)
        
        if date_data and "records" in date_data:
            for record in date_data["records"]:
                # 构建完整的时间戳
                record_datetime_str = f"{date_data['date']}T{record['time']}"
                record_datetime = datetime.datetime.fromisoformat(record_datetime_str)
                
                # 只保留最近24小时的数据
                if (now - record_datetime) <= datetime.timedelta(hours=24):
                    # 转换为统一的格式
                    all_records.append({
                        "timestamp": record_datetime.isoformat(),
                        "hot_score": record["hot_score"],
                        "reply_count": record["reply_count"],
                        "good_rate": record["good_rate"],
                        "title": date_data.get("title", ""),
                        "level_id": date_data.get("level_id", "")
                    })
    
    # 按时间排序
    all_records.sort(key=lambda x: x["timestamp"])
    
    return all_records


def calculate_statistics(data_list):
    """计算统计数据"""
    if not data_list:
        return {
            "max_hot_score": 0,
            "min_hot_score": 0,
            "avg_hot_score": 0,
            "max_reply_count": 0,
            "min_reply_count": 0,
            "avg_reply_count": 0,
            "data_points": 0
        }
    
    hot_scores = [item['hot_score'] for item in data_list]
    reply_counts = [item['reply_count'] for item in data_list]
    
    return {
        "max_hot_score": max(hot_scores),
        "min_hot_score": min(hot_scores),
        "avg_hot_score": sum(hot_scores) // len(hot_scores),
        "max_reply_count": max(reply_counts),
        "min_reply_count": min(reply_counts),
        "avg_reply_count": sum(reply_counts) // len(reply_counts),
        "data_points": len(data_list)
    }


def get_last_record(monitor_id=None):
    """获取最后一条记录
    
    Args:
        monitor_id: 监控器ID，用于隔离不同关卡的数据
    """
    now = datetime.datetime.now()
    
    # 先检查今天的数据
    date_data = load_date_data(now, monitor_id)
    if date_data and "records" in date_data and len(date_data["records"]) > 0:
        last_record = date_data["records"][-1]
        return {
            "timestamp": f"{date_data['date']}T{last_record['time']}",
            "hot_score": last_record["hot_score"],
            "reply_count": last_record["reply_count"],
            "good_rate": last_record["good_rate"],
            "title": date_data.get("title", ""),
            "level_id": date_data.get("level_id", "")
        }
    
    # 检查昨天的数据
    yesterday = now - datetime.timedelta(days=1)
    date_data = load_date_data(yesterday, monitor_id)
    if date_data and "records" in date_data and len(date_data["records"]) > 0:
        last_record = date_data["records"][-1]
        return {
            "timestamp": f"{date_data['date']}T{last_record['time']}",
            "hot_score": last_record["hot_score"],
            "reply_count": last_record["reply_count"],
            "good_rate": last_record["good_rate"],
            "title": date_data.get("title", ""),
            "level_id": date_data.get("level_id", "")
        }
    
    return None
