# Feishu Bots

这个仓库用于集中管理多个飞书机器人。每个机器人放在 `apps/` 下，独立配置、独立运行，方便在同一台服务器上并行部署。

## 目录结构

```
feishu_bot/
├── apps/                 # 各个机器人
│   └── calendar-bot/     # 日程机器人
├── systemd/              # systemd 服务模板
└── packages/             # 可选：共享代码
```

## 现有机器人

- `apps/calendar-bot`（日程机器人）

## 本地运行（以 calendar-bot 为例）

```bash
cd apps/calendar-bot

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
python main.py
```

## systemd 多实例

```bash
sudo cp systemd/feishu-bot@.service /etc/systemd/system/
sudo systemctl daemon-reload

sudo systemctl start feishu-bot@calendar-bot
sudo systemctl enable feishu-bot@calendar-bot
journalctl -u feishu-bot@calendar-bot -f
```

## 新增机器人建议

1. 复制 `apps/calendar-bot` 为 `apps/<new-bot>`
2. 修改入口和业务逻辑
3. 在新目录下创建 `.env`（参考 `.env.example`）
4. 安装依赖并通过 systemd 启动 `feishu-bot@<new-bot>`

更多细节请参考 `apps/calendar-bot/README.md`。
