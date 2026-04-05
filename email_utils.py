#!/usr/bin/env python3
"""
Email utilities module for UGC Monitor
Handles email subject and content generation
Supports multiple level monitoring
"""

import datetime
from email.mime.image import MIMEImage

# 导入通用工具函数
from utils import parse_hot_score


def get_level_url(level_id, region="cn_gf01"):
    """生成关卡详情页URL
    
    Args:
        level_id: 关卡ID
        region: 区域代码，默认为 cn_gf01
    """
    return f"https://act.miyoushe.com/ys/ugc_community/mx/#/pages/level-detail/index?id={level_id}&region={region}"


def generate_email_subject(data, previous_data=None, monitor_id=None):
    """生成邮件主题，包含关键变化信息
    
    Args:
        data: 当前数据
        previous_data: 之前的数据
        monitor_id: 监控器ID（不显示在主题中）
    """
    # 统一使用【千星奇域】前缀
    prefix = "【千星奇域】"
    
    if previous_data:
        # 计算热度变化值
        try:
            # 获取当前和之前的数值
            curr_hot_num = data.get('value1_num')
            if curr_hot_num is None:
                curr_hot_num = parse_hot_score(data['value1'])
            
            prev_hot_num = previous_data.get('value1_num')
            if prev_hot_num is None:
                prev_hot_num = parse_hot_score(previous_data.get('value1', '0'))
            
            hot_change = curr_hot_num - prev_hot_num
            hot_change_str = f"{hot_change:+d}"
        except Exception as e:
            hot_change_str = "N/A"
        
        # 计算评论变化值
        try:
            reply_change = int(data.get('value3', '0')) - int(previous_data.get('value3', '0'))
            reply_change_str = f"{reply_change:+d}"
        except Exception as e:
            reply_change_str = "N/A"
        
        subject = f"{prefix}{data['title']} 热度{hot_change_str} 评论{reply_change_str}"
    else:
        subject = f"{prefix}{data['title']} 热度{data['value1']} 评论{data.get('value3', '0')}"
    return subject


def generate_email_content(data, previous_data, source=None):
    """生成邮件HTML内容，高亮变更值
    
    Args:
        data: 当前数据
        previous_data: 之前的数据
        source: 邮件来源 ('local-test', 'workflow-schedule', 'workflow-push')
    """
    # 获取关卡URL
    level_id = data.get('level_id', '105949017109')
    url = get_level_url(level_id)
    
    # 来源显示文本
    source_text = {
        'local-test': '本地测试（强制发送）',
        'workflow-schedule': 'GitHub Actions 定时任务',
        'workflow-push': 'GitHub Actions Push 触发'
    }.get(source, '未知来源')
    
    # 初始化前一个值变量
    prev_value1 = previous_data['value1'] if previous_data else "N/A"
    prev_value3 = previous_data['value3'] if previous_data else "N/A"
    
    # 计算热度变化值和评论变化值的纯文本形式（用于摘要）
    hot_score_change_text = "N/A"
    if previous_data and prev_value1 != "N/A":
        try:
            # 获取当前和之前的数值
            curr_num = data.get('value1_num')
            if curr_num is None:
                curr_num = parse_hot_score(data['value1'])
            
            prev_num = previous_data.get('value1_num')
            if prev_num is None:
                prev_num = parse_hot_score(prev_value1)
            
            hot_change = curr_num - prev_num
            hot_score_change_text = f"{hot_change:+d}"
        except Exception as e:
            print(f"Error calculating hot score change: {e}")
            hot_score_change_text = "N/A"
    else:
        hot_score_change_text = "N/A"
    
    # 计算评论变化值的纯文本形式
    reply_count_change_text = "N/A"
    if previous_data and prev_value3 != "N/A":
        try:
            reply_change = int(data.get('value3', '0')) - int(prev_value3)
            reply_count_change_text = f"{reply_change:+d}"
        except:
            reply_count_change_text = "N/A"
    else:
        reply_count_change_text = "N/A"
    
    # 生成摘要HTML
    summary_html = ""
    if previous_data:
        # 热度变化颜色
        hot_color = "red" if hot_score_change_text.startswith('+') else "green" if hot_score_change_text.startswith('-') else "gray"
        # 评论变化颜色
        reply_color = "red" if reply_count_change_text.startswith('+') else "green" if reply_count_change_text.startswith('-') else "gray"
        
        # 获取原始热度值和当前热度值
        prev_hot = previous_data.get('value1', 'N/A')
        current_hot = data.get('value1', 'N/A')
        
        # 获取原始评论数和当前评论数
        prev_reply = previous_data.get('value3', 'N/A')
        current_reply = data.get('value3', 'N/A')
        
        summary_html = f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin-bottom: 20px;">
            <h3 style="margin-top: 0; color: #343a40;">摘要</h3>
            <p style="font-size: 16px; line-height: 1.5;">
                热度总量{prev_hot} -&gt; {current_hot}， <span style="color: {hot_color}; font-weight: bold;">{hot_score_change_text}</span> ｜
                评论总量{prev_reply} -&gt; {current_reply}
            </p>
        </div>
        """
    
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
        {summary_html}
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
    if previous_data and data['value1'] != previous_data['value1']:
        value1_html = f"<span class='highlight'>{data['value1']}</span>"
    
    # 计算热度变化（使用数值）
    hot_score_change = ""
    if previous_data and prev_value1 != "N/A":
        try:
            # 获取当前和之前的数值
            curr_num = data.get('value1_num')
            if curr_num is None:
                curr_num = parse_hot_score(data['value1'])
            
            prev_num = previous_data.get('value1_num')
            if prev_num is None:
                prev_num = parse_hot_score(prev_value1)
            
            change = curr_num - prev_num
            
            if change > 0:
                hot_score_change = f"<span style='color: green; font-weight: bold;'>+{change}</span>"
            elif change < 0:
                hot_score_change = f"<span style='color: red; font-weight: bold;'>{change}</span>"
            else:
                hot_score_change = "<span style='color: gray;'>0</span>"
        except Exception as e:
            print(f"Error calculating hot score change: {e}")
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
        <p>Monitoring URL: <a href="{url}">{url}</a></p>
        <p>Timestamp: {data['timestamp']}</p>
        <p><strong>来源:</strong> {source_text}</p>
    </body>
    </html>
    """
    
    return html


def generate_daily_report_email(data_list, statistics, monitor_id=None):
    """生成每日报告邮件的HTML内容和主题
    
    Args:
        data_list: 数据列表
        statistics: 统计数据
        monitor_id: 监控器ID
    """
    if not data_list:
        return None, None
    
    # 获取最新数据
    latest_data = data_list[-1]
    title = latest_data.get('title', 'UGC Monitor')
    level_id = latest_data.get('level_id', '105949017109')
    
    # 生成主题，统一使用【千星奇域日报】格式
    today = datetime.datetime.now().strftime("%m月%d日")
    prefix = "【千星奇域日报】"
    subject = f"{prefix}{title} - {today}热度报告"
    
    # 获取URL
    url = get_level_url(level_id)
    
    # 计算趋势
    first_data = data_list[0]
    hot_change = latest_data['hot_score'] - first_data['hot_score']
    hot_change_pct = (hot_change / first_data['hot_score'] * 100) if first_data['hot_score'] > 0 else 0
    trend_symbol = "📈" if hot_change > 0 else "📉" if hot_change < 0 else "➡️"
    
    # 生成HTML内容
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; border-bottom: 3px solid #FF6B6B; padding-bottom: 20px; margin-bottom: 30px; }}
            .header h1 {{ color: #FF6B6B; margin: 0; font-size: 28px; }}
            .header p {{ color: #666; margin: 10px 0 0 0; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 30px 0; }}
            .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; }}
            .stat-card.hot {{ background: linear-gradient(135deg, #FF6B6B 0%, #ee5a5a 100%); }}
            .stat-card.trend {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
            .stat-value {{ font-size: 32px; font-weight: bold; margin: 10px 0; }}
            .stat-label {{ font-size: 14px; opacity: 0.9; }}
            .chart-section {{ margin: 30px 0; text-align: center; }}
            .chart-section h3 {{ color: #333; margin-bottom: 20px; }}
            .chart-image {{ max-width: 100%; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
            .details-table {{ width: 100%; border-collapse: collapse; margin: 30px 0; }}
            .details-table th, .details-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
            .details-table th {{ background-color: #f8f9fa; font-weight: 600; color: #555; }}
            .details-table tr:hover {{ background-color: #f8f9fa; }}
            .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #999; font-size: 12px; }}
            .trend-up {{ color: #28a745; font-weight: bold; }}
            .trend-down {{ color: #dc3545; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 UGC监控日报</h1>
                <p>{title} - {today}</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card hot">
                    <div class="stat-label">当前热度</div>
                    <div class="stat-value">{latest_data['hot_score']:,}</div>
                    <div class="stat-label">{trend_symbol} {hot_change:+d} ({hot_change_pct:+.1f}%)</div>
                </div>
                <div class="stat-card trend">
                    <div class="stat-label">数据点</div>
                    <div class="stat-value">{statistics['data_points']}</div>
                    <div class="stat-label">过去24小时</div>
                </div>
            </div>
            
            <div class="chart-section">
                <h3>📈 24小时热度变化趋势</h3>
                <p style="color: #666; margin-bottom: 20px;">
                    最高: {statistics['max_hot_score']:,} | 
                    最低: {statistics['min_hot_score']:,} | 
                    平均: {statistics['avg_hot_score']:,}
                </p>
                <img src="cid:heatmap_chart" alt="热度变化图表" class="chart-image" />
            </div>
            
            <div class="chart-section">
                <h3>📊 24小时热度变化值趋势</h3>
                <p style="color: #666; margin-bottom: 20px;">
                    (每个时间点相对于前一个时间点的热度变化)
                </p>
                <img src="cid:change_chart" alt="热度变化值图表" class="chart-image" />
            </div>
            
            <table class="details-table">
                <thead>
                    <tr>
                        <th>统计项</th>
                        <th>热度值</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>📊 平均值</td>
                        <td>{statistics['avg_hot_score']:,}</td>
                    </tr>
                    <tr>
                        <td>⬆️ 最高值</td>
                        <td>{statistics['max_hot_score']:,}</td>
                    </tr>
                    <tr>
                        <td>⬇️ 最低值</td>
                        <td>{statistics['min_hot_score']:,}</td>
                    </tr>
                </tbody>
            </table>
            
            <div class="chart-section">
                <h3>📋 各时段变化值</h3>
                <table class="details-table">
                    <thead>
                        <tr>
                            <th>时间</th>
                            <th>热度值</th>
                            <th>变化值</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # 生成各时段变化值表格
    for i, data in enumerate(data_list):
        if i == 0:
            # 第一个数据点，没有变化值
            time_str = data['timestamp'].split('T')[1].split('.')[0]
            hot_score = data['hot_score']
            html += f"""
                        <tr>
                            <td>{time_str}</td>
                            <td>{hot_score:,}</td>
                            <td><span style="color: gray;">N/A</span></td>
                        </tr>
            """
        else:
            # 计算变化值
            prev_data = data_list[i-1]
            change = data['hot_score'] - prev_data['hot_score']
            time_str = data['timestamp'].split('T')[1].split('.')[0]
            hot_score = data['hot_score']
            
            if change > 0:
                html += f"""
                        <tr>
                            <td>{time_str}</td>
                            <td>{hot_score:,}</td>
                            <td><span style="color: green; font-weight: bold;">+{change}</span></td>
                        </tr>
                """
            elif change < 0:
                html += f"""
                        <tr>
                            <td>{time_str}</td>
                            <td>{hot_score:,}</td>
                            <td><span style="color: red; font-weight: bold;">{change}</span></td>
                        </tr>
                """
            else:
                html += f"""
                        <tr>
                            <td>{time_str}</td>
                            <td>{hot_score:,}</td>
                            <td><span style="color: gray;">0</span></td>
                        </tr>
                """
    
    html += f"""
                    </tbody>
                </table>
            </div>
            
            <div class="footer">
                <p>监控地址: <a href="{url}">{url}</a></p>
                <p>生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return subject, html


def attach_chart_to_email(msg, chart_path='heatmap_chart.png', cid='heatmap_chart'):
    """将图表附加到邮件中"""
    try:
        with open(chart_path, 'rb') as f:
            img_data = f.read()
        
        image = MIMEImage(img_data)
        image.add_header('Content-ID', f'<{cid}>')
        image.add_header('Content-Disposition', 'inline', filename=chart_path)
        msg.attach(image)
        return True
    except Exception as e:
        print(f"Error attaching chart {chart_path} to email: {e}")
        return False


def attach_all_charts_to_email(msg, chart_paths=None):
    """将所有图表附加到邮件中"""
    if chart_paths is None:
        chart_paths = [
            ('heatmap_chart.png', 'heatmap_chart'),
            ('change_chart.png', 'change_chart')
        ]
    
    all_success = True
    for chart_path, cid in chart_paths:
        if not attach_chart_to_email(msg, chart_path, cid):
            all_success = False
    
    return all_success
