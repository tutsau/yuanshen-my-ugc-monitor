import os
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import datetime

# 配置
URL = "https://act.miyoushe.com/ys/ugc_community/mx/#/pages/level-detail/index?id=105949017109&region=cn_gf01"
DATA_FILE = "previous_data.json"

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
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587') or '587')

def fetch_page():
    """获取网页内容"""
    try:
        response = requests.get(URL, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching page: {e}")
        return None

def parse_content(html):
    """解析taro-text-core标签内容"""
    soup = BeautifulSoup(html, 'html.parser')
    taro_texts = soup.find_all('taro-text-core')
    
    if len(taro_texts) < 8:
        print(f"Not enough taro-text-core tags found: {len(taro_texts)}")
        return None
    
    try:
        title = taro_texts[4].get_text(strip=True)
        value1 = taro_texts[6].get_text(strip=True)
        value2 = taro_texts[7].get_text(strip=True)
        
        return {
            'title': title,
            'value1': value1,
            'value2': value2,
            'timestamp': datetime.datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error parsing content: {e}")
        return None

def load_previous_data():
    """加载上次查询的数据"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading previous data: {e}")
    return None

def save_data(data):
    """保存数据"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Data saved successfully")
    except Exception as e:
        print(f"Error saving data: {e}")

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
        msg['Subject'] = f"【千星奇域】{data['title']}数据更新 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 生成HTML内容
        html_content = generate_html_content(data, previous_data)
        
        # 添加邮件正文
        part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part)
        
        # 发送邮件
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print("Email sent successfully")
    except Exception as e:
        print(f"Error sending email: {e}")

def generate_html_content(data, previous_data):
    """生成邮件HTML内容，高亮变更值"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .highlight {{ background-color: #ffffcc; padding: 2px 4px; border-radius: 2px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h2>UGC Monitor Update</h2>
        <p>Monitoring URL: {URL}</p>
        <p>Timestamp: {data['timestamp']}</p>
        <table>
            <tr>
                <th>Field</th>
                <th>Current Value</th>
                <th>Previous Value</th>
            </tr>
    """
    
    # 处理标题
    title_html = data['title']
    prev_title = previous_data['title'] if previous_data else "N/A"
    if previous_data and data['title'] != previous_data['title']:
        title_html = f"<span class='highlight'>{data['title']}</span>"
    
    html += f"""
            <tr>
                <td>Title</td>
                <td>{title_html}</td>
                <td>{prev_title}</td>
            </tr>
    """
    
    # 处理第一个值
    value1_html = data['value1']
    prev_value1 = previous_data['value1'] if previous_data else "N/A"
    if previous_data and data['value1'] != previous_data['value1']:
        value1_html = f"<span class='highlight'>{data['value1']}</span>"
    
    html += f"""
            <tr>
                <td>Value 1</td>
                <td>{value1_html}</td>
                <td>{prev_value1}</td>
            </tr>
    """
    
    # 处理第二个值
    value2_html = data['value2']
    prev_value2 = previous_data['value2'] if previous_data else "N/A"
    if previous_data and data['value2'] != previous_data['value2']:
        value2_html = f"<span class='highlight'>{data['value2']}</span>"
    
    html += f"""
            <tr>
                <td>Value 2</td>
                <td>{value2_html}</td>
                <td>{prev_value2}</td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    return html

def main():
    """主函数"""
    print(f"Starting monitor at {datetime.datetime.now()}")
    
    # 获取网页内容
    html = fetch_page()
    if not html:
        print("Failed to fetch page")
        return
    
    # 解析内容
    current_data = parse_content(html)
    if not current_data:
        print("Failed to parse content")
        return
    
    # 加载上次数据
    previous_data = load_previous_data()
    
    # 检查是否有变更
    has_changed = not previous_data or (
        current_data['title'] != previous_data['title'] or
        current_data['value1'] != previous_data['value1'] or
        current_data['value2'] != previous_data['value2']
    )
    
    if has_changed:
        print("Data has changed, sending email...")
        # 发送邮件
        send_email(current_data, previous_data)
        # 保存当前数据
        save_data(current_data)
    else:
        print("No changes detected")

if __name__ == "__main__":
    main()