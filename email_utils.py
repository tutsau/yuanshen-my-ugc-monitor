#!/usr/bin/env python3
"""
Email utilities module for UGC Monitor
Handles email subject and content generation
Supports multiple level monitoring
"""

import datetime
from email.mime.image import MIMEImage


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
        hot_score_change = "↑" if data['value1'] > previous_data.get('value1', '0') else "↓" if data['value1'] < previous_data.get('value1', '0') else "-"
        reply_count_change = "↑" if data.get('value3', '0') > previous_data.get('value3', '0') else "↓" if data.get('value3', '0') < previous_data.get('value3', '0') else "-"
        subject = f"{prefix}{data['title']} 热度{hot_score_change}{data['value1']} 评论{reply_count_change}{data.get('value3', '0')}"
    else:
        subject = f"{prefix}{data['title']} 热度{data['value1']} 评论{data.get('value3', '0')}"
    return subject


def generate_email_content(data, previous_data):
    """生成邮件HTML内容，高亮变更值"""
    # 获取关卡URL
    level_id = data.get('level_id', '105949017109')
    url = get_level_url(level_id)
    
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
    
    # 计算热度变化（使用数值）
    hot_score_change = ""
    if previous_data and prev_value1 != "N/A":
        try:
            # 优先使用 value1_num，如果没有则使用 data_manager 的函数
            # 先尝试导入 data_manager
            try:
                from data_manager import parse_hot_score
            except ImportError:
                # 简单的 parse_hot_score 实现
                def parse_hot_score(hot_score):
                    if isinstance(hot_score, int):
                        return hot_score
                    if isinstance(hot_score, float):
                        return int(hot_score)
                    if isinstance(hot_score, str):
                        hot_score = hot_score.strip()
                        if '万' in hot_score:
                            num_part = hot_score.replace('万', '').strip()
                            try:
                                return int(float(num_part) * 10000)
                            except ValueError:
                                pass
                        try:
                            return int(float(hot_score))
                        except ValueError:
                            pass
                    return 0
            
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
        <p>Monitoring URL: <a href="{url}">{url}</a></p>
        <p>Timestamp: {data['timestamp']}</p>
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
