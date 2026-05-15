#!/bin/bash
# 安筑AI 部署脚本 — 阿里云 ECS (Ubuntu)

set -e

APP_DIR="/var/www/anzhu-ai"
PYTHON="python3"

echo "=== 安筑AI 部署开始 ==="

# 1. 创建目录
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# 2. 复制文件
cp -r . $APP_DIR/

# 3. 初始化数据库
cd $APP_DIR
$PYTHON -c "from api_server import init_db; init_db(); print('DB initialized')"

# 4. 配置 systemd 服务
sudo tee /etc/systemd/system/anzhu-ai.service > /dev/null <<EOF
[Unit]
Description=安筑AI API Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
ExecStart=$PYTHON $APP_DIR/api_server.py
Restart=always
RestartSec=5
Environment=PORT=8000

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable anzhu-ai
sudo systemctl restart anzhu-ai

echo "=== 部署完成 ==="
echo "API: http://localhost:8000/api/stats"
sudo systemctl status anzhu-ai --no-pager
