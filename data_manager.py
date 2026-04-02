#!/usr/bin/env python3
"""
Data management module for UGC Monitor
Handles data loading and saving from/to remote repository
"""

import os
import json
import requests

DATA_FILE_PATH = "previous_data.json"

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

def load_previous_data():
    """从远程仓库加载之前的数据"""
    config = _get_config()
    GITHUB_TOKEN = config['GITHUB_TOKEN']
    
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN not found, cannot load data from remote repo")
        return None
    
    url = f"https://api.github.com/repos/{config['DATA_REPO_OWNER']}/{config['DATA_REPO_NAME']}/contents/{DATA_FILE_PATH}"
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
            print("Data loaded successfully from remote repo")
            return json.loads(decoded_content)
        elif response.status_code == 404:
            print("Data file not found in remote repo, returning None")
            return None
        else:
            print(f"Error loading data from remote repo: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error loading data from remote repo: {e}")
        return None

def save_data(data):
    """将数据保存到远程仓库"""
    config = _get_config()
    GITHUB_TOKEN = config['GITHUB_TOKEN']
    
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN not found, cannot save data to remote repo")
        return
    
    url = f"https://api.github.com/repos/{config['DATA_REPO_OWNER']}/{config['DATA_REPO_NAME']}/contents/{DATA_FILE_PATH}"
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
        "message": "Update monitor data",
        "content": content,
        "sha": sha
    }
    
    try:
        response = requests.put(url, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            print("Data saved successfully to remote repo")
        else:
            print(f"Error saving data to remote repo: {response.status_code}")
            print(response.json())
    except Exception as e:
        print(f"Error saving data to remote repo: {e}")
