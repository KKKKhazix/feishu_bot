# 飞书日程机器人

一个智能的飞书机器人，可以从文字、图片或语音消息中自动识别日程信息，并在你的飞书日历上创建日程。

## 功能特性

- 📝 **文字识别**：发送"明天下午3点开会"，自动创建日程
- 🖼️ **图片识别**：发送微信聊天截图，OCR识别后创建日程
- 🎤 **语音识别**：发送语音消息，自动转文字并创建日程（需额外配置）
- 📅 **智能提取**：使用豆包大模型智能提取日期、时间、标题、地点

## 快速开始

### 环境要求

- Python 3.10+
- pip

### 本地运行

```bash
# 克隆代码
git clone https://github.com/KKKKhazix/feishu_bot.git
cd feishu_bot/apps/calendar-bot

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 复制配置文件
cp .env.example .env

# 编辑配置文件，填入你的密钥
# Windows: notepad .env
# Linux: nano .env

# 运行机器人
python main.py
```

## 服务器部署指南（Ubuntu）

### 1. 连接服务器

```bash
ssh root@你的服务器IP
# 或
ssh ubuntu@你的服务器IP
```

### 2. 安装依赖

```bash
# 更新系统
sudo apt update

# 安装 Python 和 Git
sudo apt install -y python3 python3-pip python3-venv git
```

### 3. 克隆代码

```bash
cd ~
git clone https://github.com/KKKKhazix/feishu_bot.git
cd feishu_bot/apps/calendar-bot
```

### 4. 配置环境

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 创建配置文件
cp .env.example .env
nano .env  # 编辑配置
```

### 5. 配置文件说明 (.env)

```
# 飞书应用凭证（必填）
FEISHU_APP_ID=你的App_ID
FEISHU_APP_SECRET=你的App_Secret

# 豆包大模型（必填）
DOUBAO_API_KEY=你的API_Key
DOUBAO_MODEL_ID=doubao-1-5-pro-32k-250115

# 火山引擎凭证（语音识别需要，可选）
VOLCANO_ACCESS_KEY=
VOLCANO_SECRET_KEY=

# 日志级别
LOG_LEVEL=INFO
```

### 6. 测试运行

```bash
python main.py
```

看到以下输出表示成功：
```
==================================================
Starting Feishu Calendar Bot...
==================================================
Bot is running! Press Ctrl+C to stop.
```

### 7. 安装为系统服务（可选）

```bash
# 在仓库根目录执行
cd ~/feishu_bot

# 复制服务文件
sudo cp systemd/feishu-bot@.service /etc/systemd/system/

# 根据你的实际路径编辑服务文件
sudo nano /etc/systemd/system/feishu-bot@.service

# 重新加载服务
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start feishu-bot@calendar-bot

# 设置开机自启
sudo systemctl enable feishu-bot@calendar-bot

# 查看状态
sudo systemctl status feishu-bot@calendar-bot

# 查看日志
journalctl -u feishu-bot@calendar-bot -f
```

## 飞书应用配置

### 1. 创建应用

1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 点击「创建企业自建应用」
3. 填写应用名称和描述

### 2. 获取凭证

在应用的「凭证与基础信息」页面获取：
- App ID
- App Secret

### 3. 配置权限

在「权限管理」页面添加以下权限：
- `im:message` - 获取与发送消息
- `im:message:send_as_bot` - 以应用身份发送消息
- `im:resource` - 获取消息中的资源文件
- `calendar:calendar` - 读写日历

### 4. 启用长连接

1. 进入「事件与回调」页面
2. 选择「使用长连接接收事件」
3. **注意：必须先运行机器人代码，再保存此设置**

### 5. 添加事件订阅

保存长连接设置后，添加事件：
- `im.message.receive_v1` - 接收消息

### 6. 发布应用

1. 进入「版本管理与发布」
2. 创建版本并发布

## 使用方法

### 发送文字创建日程

直接发送包含日程信息的文字：
```
明天下午3点开会
1月31号上午10点和张三吃饭
后天下午2点半在会议室A讨论项目
```

### 发送图片创建日程

发送包含日程信息的截图，机器人会：
1. 识别图片中的文字
2. 提取日程信息
3. 自动创建日历事件

### 发送语音创建日程

发送语音消息（需要配置火山引擎语音识别服务）

## 常见问题

### Q: 机器人没有回复？

1. 检查机器人是否在运行（`python main.py`）
2. 检查飞书后台是否添加了 `im.message.receive_v1` 事件
3. 检查应用是否已发布

### Q: 飞书后台无法保存长连接设置？

确保你的机器人代码正在运行。飞书会验证 WebSocket 连接是否存在。

### Q: 创建日程失败？

1. 检查是否添加了 `calendar:calendar` 权限
2. 检查权限是否已审批通过

### Q: 图片识别不准确？

- 确保图片清晰
- 尽量发送截图而非拍照

## 项目结构

```
apps/calendar-bot/
├── main.py              # 主入口
├── handlers/            # 消息处理器
│   ├── text_handler.py  # 文字消息
│   ├── image_handler.py # 图片消息
│   └── voice_handler.py # 语音消息
├── services/            # 外部服务
│   ├── feishu_client.py # 飞书API
│   ├── volcano_ai.py    # OCR/ASR
│   └── doubao_llm.py    # 日程提取
├── utils/               # 工具
│   ├── config.py        # 配置
│   └── logger.py        # 日志
├── .env.example         # 配置模板
└── requirements.txt     # 依赖
```

## License

MIT
