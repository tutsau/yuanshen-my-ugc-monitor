#!/usr/bin/env python3
"""
Email utilities module for UGC Monitor
Handles email subject and content generation
"""

import datetime

# 监控URL
URL = "https://act.miyoushe.com/ys/ugc_community/mx/#/pages/level-detail/index?id=105949017109&region=cn_gf01"

def generate_email_subject(data, previous_data=None):
    """生成邮件主题，包含关键变化信息"""
    if previous_data:
        hot_score_change = "↑" if data['value1'] > previous_data.get('value1', '0') else "↓" if data['value1'] < previous_data.get('value1', '0') else "-"
        reply_count_change = "↑" if data.get('value3', '0') > previous_data.get('value3', '0') else "↓" if data.get('value3', '0') < previous_data.get('value3', '0') else "-"
        subject = f"【千星奇域】{data['title']} 热度{hot_score_change}{data['value1']} 评论{reply_count_change}{data.get('value3', '0')}"
    else:
        subject = f"【千星奇域】{data['title']} 热度{data['value1']} 评论{data.get('value3', '0')}"
    return subject

def generate_email_content(data, previous_data):
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
        <h3>Key Changes</h3>
        <table>
            <tr>
                <th>Field</th>
                <th>Current Value</th>
                <th>Previous Value</th>
            </tr>
    """
    
    # 处理关卡ID
    level_id_html = data.get('level_id', 'N/A')
    prev_level_id = previous_data.get('level_id', 'N/A') if previous_data else "N/A"
    if previous_data and data.get('level_id') != previous_data.get('level_id'):
        level_id_html = f"<span class='highlight'>{data.get('level_id', 'N/A')}</span>"
    
    html += f"""
            <tr>
                <td>Level ID</td>
                <td>{level_id_html}</td>
                <td>{prev_level_id}</td>
            </tr>
    """
    
    # 处理关卡名称
    title_html = data['title']
    prev_title = previous_data['title'] if previous_data else "N/A"
    if previous_data and data['title'] != previous_data['title']:
        title_html = f"<span class='highlight'>{data['title']}</span>"
    
    html += f"""
            <tr>
                <td>Level Name</td>
                <td>{title_html}</td>
                <td>{prev_title}</td>
            </tr>
    """
    
    # 处理热度值
    value1_html = data['value1']
    prev_value1 = previous_data['value1'] if previous_data else "N/A"
    if previous_data and data['value1'] != previous_data['value1']:
        value1_html = f"<span class='highlight'>{data['value1']}</span>"
    
    # 计算热度变化
    hot_score_change = ""
    if previous_data and prev_value1 != "N/A":
        try:
            change = int(data['value1']) - int(prev_value1)
            if change > 0:
                hot_score_change = f"<span style='color: green; font-weight: bold;'>+{change}</span>"
            elif change < 0:
                hot_score_change = f"<span style='color: red; font-weight: bold;'>{change}</span>"
            else:
                hot_score_change = "<span style='color: gray;'>0</span>"
        except:
            hot_score_change = "<span style='color: gray;'>N/A</span>"
    else:
        hot_score_change = "<span style='color: gray;'>N/A</span>"
    
    html += f"""
            <tr>
                <td>Hot Score</td>
                <td>{value1_html}</td>
                <td>{prev_value1}</td>
            </tr>
            <tr>
                <td>Hot Score Change</td>
                <td colspan='2'>{hot_score_change}</td>
            </tr>
    """
    
    # 处理好评率
    value2_html = data['value2']
    prev_value2 = previous_data['value2'] if previous_data else "N/A"
    if previous_data and data['value2'] != previous_data['value2']:
        value2_html = f"<span class='highlight'>{data['value2']}</span>"
    
    html += f"""
            <tr>
                <td>Good Rate</td>
                <td>{value2_html}</td>
                <td>{prev_value2}</td>
            </tr>
    """
    
    # 处理评论总数
    value3_html = data.get('value3', 'N/A')
    prev_value3 = previous_data.get('value3', 'N/A') if previous_data else "N/A"
    if previous_data and data.get('value3') != previous_data.get('value3'):
        value3_html = f"<span class='highlight'>{data.get('value3', 'N/A')}</span>"
    
    # 计算评论变化
    reply_count_change = ""
    if previous_data and prev_value3 != "N/A":
        try:
            change = int(data.get('value3', '0')) - int(prev_value3)
            if change > 0:
                reply_count_change = f"<span style='color: green; font-weight: bold;'>+{change}</span>"
            elif change < 0:
                reply_count_change = f"<span style='color: red; font-weight: bold;'>{change}</span>"
            else:
                reply_count_change = "<span style='color: gray;'>0</span>"
        except:
            reply_count_change = "<span style='color: gray;'>N/A</span>"
    else:
        reply_count_change = "<span style='color: gray;'>N/A</span>"
    
    html += f"""
            <tr>
                <td>Reply Count</td>
                <td>{value3_html}</td>
                <td>{prev_value3}</td>
            </tr>
            <tr>
                <td>Reply Count Change</td>
                <td colspan='2'>{reply_count_change}</td>
            </tr>
        </table>
        
        <h3>Additional Information</h3>
        <p>Monitoring URL: <a href="{URL}">{URL}</a></p>
        <p>Timestamp: {data['timestamp']}</p>
    </body>
    </html>
    """
    
    return html
