# Feishu Calendar Bot (MVP)

私聊机器人，发文本或图片后自动识别并写入你的个人飞书日历。

## 功能概览

- 订阅私聊消息事件（文本 / 图片）
- 图片消息：下载消息资源 -> OCR -> 文本解析
- 文本解析 -> 创建日程（个人主日历）
- 自动创建（不需要确认）

## 运行前准备

1) 在飞书开放平台创建「自建应用」
2) 启用机器人能力与日历能力
3) 配置事件订阅回调地址
4) 配置 OAuth（用于用户级日历写入）
5) 记录并填写 app_id / app_secret / verification_token / encrypt_key（如启用加密）

## 配置

复制 `config.example.env` 为 `.env` 并填写。

```bash
copy config.example.env .env
```

说明：
- `FEISHU_APP_ID` / `FEISHU_APP_SECRET`：应用凭证
- `FEISHU_VERIFICATION_TOKEN`：事件回调校验 token
- `FEISHU_ENCRYPT_KEY`：若开启加密回调，填写密钥
- `FEISHU_OAUTH_REDIRECT_URI`：OAuth 回调地址
- `FEISHU_OAUTH_SCOPE`：日历相关的用户授权范围（以官方文档为准）
- `FEISHU_OAUTH_AUTHORIZE_URL`：OAuth 授权入口（以官方文档为准）
- `FEISHU_API_BASE`：默认 `https://open.feishu.cn`
- `FEISHU_APP_ACCESS_TOKEN_ENDPOINT`：应用 access_token 端点（默认已填）
- `FEISHU_MESSAGE_RESOURCE_ENDPOINT`：消息资源下载端点（默认已填）
- `FEISHU_CALENDAR_PRIMARY_ENDPOINT` / `FEISHU_CALENDAR_EVENT_CREATE_ENDPOINT`：日历接口路径（以官方文档为准）
- `FEISHU_USER_ACCESS_TOKEN_ENDPOINT`：OAuth code 换 user_access_token 的端点（以官方文档为准）
- `FEISHU_SEND_MESSAGE_ENDPOINT`：回传消息接口（可选）

## 安装依赖

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

可选：OCR（本地 Tesseract）

```bash
pip install -r requirements-ocr.txt
```

并确保系统已安装 Tesseract（Windows 可用安装包）。

## 启动

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

将回调地址配置为：

```
http(s)://你的域名/feishu/event
```

OAuth 回调配置为：

```
http(s)://你的域名/feishu/oauth/callback
```

## 说明

本项目提供可运行的 MVP 骨架。部分接口路径与权限 scope 需要你根据官方文档确认并填入环境变量。
