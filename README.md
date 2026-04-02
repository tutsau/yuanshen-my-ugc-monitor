# UGC Monitor

一个使用GitHub Actions定时监控网页内容变更并发送邮件通知的项目。

## 功能

- 每3分钟执行一次对指定网页的查询
- 解析网页中的taro-text-core标签内容
- 对比数据变更，只在有变更时发送邮件
- 邮件中高亮显示变更值
- 确保邮箱隐私（使用GitHub Secrets存储邮箱信息）

## 监控内容

监控 `https://act.miyoushe.com/ys/ugc_community/mx/#/pages/level-detail/index?id=105949017109&region=cn_gf01` 网页中的以下内容：

- taro-text-core标签数组中索引为4的内容（标题）
- taro-text-core标签数组中索引为6的内容（数值1）
- taro-text-core标签数组中索引为7的内容（数值2）

## 项目结构

```
.
├── .github/
│   └── workflows/
│       └── monitor.yml  # GitHub Actions workflow配置
├── monitor.py           # 监控脚本
└── README.md            # 项目说明
```

## 配置

### 1. 设置GitHub Secrets

在GitHub仓库的 `Settings > Secrets and variables > Actions` 中添加以下Secrets：

- `EMAIL_USER`：发件人邮箱地址
- `EMAIL_PASSWORD`：发件人邮箱密码（或应用专用密码）
- `EMAIL_RECIPIENT`：收件人邮箱地址
- `SMTP_SERVER`：SMTP服务器地址（默认：smtp.gmail.com）
- `SMTP_PORT`：SMTP服务器端口（默认：587）
- `GIST_ID`：GitHub Gist ID（用于存储监控数据）
- `GITHUB_TOKEN`：GitHub个人访问令牌（需要gist权限）

### 2. 配置定时任务

在 `.github/workflows/monitor.yml` 文件中，你可以修改定时任务的执行频率：

```yaml
on:
  schedule:
    - cron: '*/3 * * * *'  # 每3分钟执行一次
```

## 运行原理

1. GitHub Actions按照设定的定时任务执行
2. 执行 `monitor.py` 脚本，获取网页内容并解析
3. 与上次存储的数据进行对比
4. 如果有变更，发送邮件通知并更新存储的数据
5. 将更新的数据提交并推送到仓库，解决无状态问题

## 邮件格式

邮件采用HTML格式，包含以下内容：

- 监控URL
- 时间戳
- 数据表格（包含当前值和之前值）
- 变更值会高亮显示

## 依赖

- Python 3.10+
- requests
- beautifulsoup4
- smtplib
- email
- json
- datetime

## 手动触发

除了定时执行外，你还可以在GitHub Actions页面手动触发工作流。

## 注意事项

- 确保设置了正确的GitHub Secrets
- 对于Gmail等邮箱，可能需要开启"允许不够安全的应用"或使用应用专用密码
- 由于GitHub Actions的限制，过于频繁的执行可能会被限制
- 网页结构变更可能导致解析失败，请定期检查脚本是否正常工作