# UGC Monitor

一个使用GitHub Actions定时监控原神社区UGC关卡数据变化并发送邮件通知的项目，支持多关卡监控、每日报告和数据可视化。

## 功能特性

- 🎮 支持多关卡监控，每个关卡数据独立存储
- 📊 按日期分片存储历史数据，便于查询和分析
- 📧 智能邮件通知：数据变更时自动发送，或时间跨度超过1小时时发送
- 📈 每日报告：包含过去24小时的热度变化折线图
- 🔒 邮箱隐私保护（使用GitHub Secrets存储敏感信息）
- 🚀 数据持久化：使用独立的GitHub仓库存储数据

## 项目结构

```
.
├── .github/
│   └── workflows/
│       └── monitor.yml          # GitHub Actions workflow配置
├── config/
│   ├── __init__.py              # 配置加载模块
│   └── monitors.json            # 多关卡监控配置
├── monitor.py                   # 单关卡监控入口（兼容旧版本）
├── monitor_all.py               # 多关卡监控主入口
├── data_manager.py              # 数据管理模块
├── email_utils.py               # 邮件工具模块
├── chart_generator.py           # 图表生成模块
├── local_config.py.template     # 本地配置模板
└── README.md                    # 项目说明
```

## 数据存储结构

数据存储在独立的GitHub仓库中，结构如下：

```
/
└── data/
    └── {monitor_id}/
        ├── previous.json        # 最新数据快照（用于快速对比变更）
        ├── 2026-04-01.json     # 历史数据（按日期分片）
        ├── 2026-04-02.json
        └── 2026-04-03.json
```

## 配置说明

### 1. 本地开发配置

复制 `local_config.py.template` 为 `local_config.py` 并配置：

```python
# 邮箱配置
EMAIL_USER = 'your_email@example.com'
EMAIL_PASSWORD = 'your_email_password'
EMAIL_RECIPIENT = 'recipient@example.com'
SMTP_SERVER = 'smtp.qq.com'
SMTP_PORT = 587

# 数据仓库配置
DATA_REPO_OWNER = 'your_github_username'
DATA_REPO_NAME = 'yuanshen-my-ugc-monitor-data'
MY_GITHUB_TOKEN = 'your_github_personal_access_token'
```

### 2. 多关卡配置

编辑 `config/monitors.json` 添加或修改监控关卡：

```json
{
  "monitors": [
    {
      "id": "level_105949017109",
      "name": "猜角色：猜猜我选谁",
      "level_id": "105949017109",
      "region": "cn_gf01",
      "enabled": true
    }
  ]
}
```

### 3. GitHub Secrets配置

在GitHub仓库的 `Settings > Secrets and variables > Actions` 中添加以下Secrets：

- `EMAIL_USER`：发件人邮箱地址
- `EMAIL_PASSWORD`：发件人邮箱密码（或应用专用密码）
- `EMAIL_RECIPIENT`：收件人邮箱地址
- `SMTP_SERVER`：SMTP服务器地址（默认：smtp.qq.com）
- `SMTP_PORT`：SMTP服务器端口（默认：587）
- `MY_GITHUB_TOKEN`：GitHub Personal Access Token
- `DATA_REPO_OWNER`：数据仓库所有者
- `DATA_REPO_NAME`：数据仓库名称

### 4. 定时任务配置

在 `.github/workflows/monitor.yml` 文件中修改定时任务：

```yaml
on:
  schedule:
    - cron: '20,40 * * * *'  # 每小时的20分和40分执行监控
    - cron: '0 8 * * *'       # 每天08:00执行每日报告
```

## 使用方法

### 本地运行

#### 监控所有关卡
```bash
python3 monitor_all.py
```

#### 强制发送邮件（用于测试）
```bash
python3 monitor_all.py --force-email
```

#### 生成每日报告
```bash
python3 monitor_all.py --daily-report
```

#### 兼容旧版本（单关卡）
```bash
python3 monitor.py --force-email
```

### GitHub Actions运行

- 定时自动执行（根据workflow配置）
- 或在GitHub Actions页面手动触发

## 邮件格式

### 变更通知邮件
- 主题：`【千星奇域】{关卡名称} 热度{变化}{值} 评论{变化}{值}`
- 内容：数据对比表格，变更值高亮显示

### 每日报告邮件
- 主题：`【千星奇域日报】{关卡名称} - {日期}热度报告`
- 内容：包含统计数据卡片、热度变化折线图、详细数据表格

## 依赖

- Python 3.10+
- requests
- matplotlib
- smtplib
- email
- json
- datetime
- argparse

## 工作原理

1. GitHub Actions按照设定的定时任务执行
2. 执行 `monitor_all.py` 脚本，遍历所有启用的关卡
3. 调用API获取每个关卡的数据
4. 与 `data/{monitor_id}/previous.json` 对比，检查是否有变更
5. 如果有变更或时间跨度超过1小时：
   - 发送邮件通知
   - 更新 `data/{monitor_id}/previous.json`
   - 追加到历史数据 `data/{monitor_id}/{date}.json`
6. 每日08:00生成包含折线图的日报邮件

## 注意事项

- 确保GitHub Token有读写数据仓库的权限
- 对于QQ邮箱等，需要使用"授权码"而非登录密码
- 数据仓库需要单独创建并配置为私有（如包含敏感信息）
- 网页API变更可能导致解析失败，请定期检查

## 许可证

MIT License
