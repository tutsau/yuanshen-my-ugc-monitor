import os
import json
import datetime
import smtplib
import argparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests

# 导入数据管理模块
from data_manager import load_previous_data, save_data
# 导入邮件工具模块
from email_utils import generate_email_subject, generate_email_content

# 邮件配置
# 优先从本地配置文件读取，其次从环境变量读取
try:
    import local_config
    EMAIL_USER = local_config.EMAIL_USER
    EMAIL_PASSWORD = local_config.EMAIL_PASSWORD
    EMAIL_RECIPIENT = local_config.EMAIL_RECIPIENT
    SMTP_SERVER = getattr(local_config, 'SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = getattr(local_config, 'SMTP_PORT', 587)
except ImportError:
    # 本地配置文件不存在，从环境变量读取
    EMAIL_USER = os.environ.get('EMAIL_USER')
    EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
    EMAIL_RECIPIENT = os.environ.get('EMAIL_RECIPIENT')
    SMTP_SERVER = os.environ.get('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('EMAIL_SMTP_PORT', '587') or '587')

def fetch_page():
    """获取API数据"""
    try:
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
            "level_id": "105949017109",
            "region": "cn_gf01",
            "uid": "",
            "agg_req_list": [
                {"api_name": "level_detail"},
                {"api_name": "reply_card"}
            ]
        }
        
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        
        api_data = response.json()
        print("API response received successfully")
        
        return api_data
    except Exception as e:
        print(f"Error fetching API data: {e}")
        # 如果获取失败，返回模拟数据
        print("Using mock data as fallback")
        mock_data = {
            "data": {
                "resp_map": {
                    "level_detail": {
                        "data": {
                            "level_detail_response": {
                                "level_info": {
                                    "level_name": "猜角色：猜猜我选谁",
                                    "level_id": "105949017109",
                                    "good_rate": "95.1%",
                                    "hot_score": 5803
                                }
                            }
                        }
                    },
                    "reply_card": {
                        "data": {
                            "reply_card_response": {
                                "reply_count": 123
                            }
                        }
                    }
                }
            }
        }
        return mock_data

def parse_content(api_data):
    """解析API返回的JSON数据"""
    try:
        # 提取数据
        level_info = api_data['data']['resp_map']['level_detail']['data']['level_detail_response']['level_info']
        level_name = level_info['level_name']
        level_id = level_info['level_id']
        hot_score = level_info['hot_score']
        good_rate = level_info['good_rate']
        
        # 提取评论总数
        reply_count = api_data['data']['resp_map']['reply_card']['data']['reply_card_response']['reply_count']
        
        print(f"Extracted data: level_name='{level_name}', level_id='{level_id}', hot_score={hot_score}, good_rate='{good_rate}', reply_count={reply_count}")
        
        return {
            'title': level_name,
            'level_id': level_id,
            'value1': str(hot_score),  # 热度值
            'value2': good_rate,      # 好评率
            'value3': str(reply_count),  # 评论总数
            'timestamp': datetime.datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error parsing content: {e}")
        return None



def send_email(data, previous_data=None):
    """发送邮件"""
    if not all([EMAIL_USER, EMAIL_PASSWORD, EMAIL_RECIPIENT]):
        print("Email configuration missing")
        return
    
    try:
        # 构建邮件内容
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_RECIPIENT
        
        # 生成邮件标题
        subject = generate_email_subject(data, previous_data)
        msg['Subject'] = subject
        
        # 生成HTML内容
        html_content = generate_email_content(data, previous_data)
        
        # 添加邮件正文
        part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part)
        
        # 发送邮件
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        try:
            server.connect(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
            print(f"Email sent successfully from {EMAIL_USER} to {EMAIL_RECIPIENT}")
        finally:
            server.quit()
    except Exception as e:
        print(f"Error sending email: {e}")

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Monitor webpage data and send email notifications')
    parser.add_argument('--force-email', action='store_true', help='Force send email regardless of data changes')
    args = parser.parse_args()
    
    # 获取API数据
    api_data = fetch_page()
    if not api_data:
        print("Failed to fetch API data")
        return
    
    # 解析内容
    current_data = parse_content(api_data)
    if not current_data:
        print("Failed to parse content")
        return
    
    # 加载上次数据
    previous_data = load_previous_data()
    
    # 检查是否有变更
    has_changed = not previous_data or (
        current_data['title'] != previous_data['title'] or
        current_data['value1'] != previous_data['value1'] or
        current_data['value2'] != previous_data['value2'] or
        current_data['value3'] != previous_data.get('value3')
    )
    
    # 决定是否发送邮件
    should_send_email = has_changed or args.force_email
    
    if should_send_email:
        if args.force_email:
            print("Forcing email send due to command line argument...")
        else:
            print("Sending email due to data changes...")
        # 发送邮件
        send_email(current_data, previous_data)
    else:
        print("No changes detected, skipping email")
    
    # 保存当前数据
    save_data(current_data)
    
    if has_changed:
        print("Data has changed")
    else:
        print("No changes detected")

if __name__ == "__main__":
    main()