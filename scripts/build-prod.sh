#!/bin/bash
set -e
cd /home/agentuser/agentnet/apps/web

echo "🧹 清理旧构建..."
rm -rf .next

echo "📦 构建前端..."
NEXT_TELEMETRY_DISABLED=1 npx next build

echo "📋 复制静态文件到 standalone..."
mkdir -p .next/standalone/.next/static
cp -r .next/static/* .next/standalone/.next/static/
if [ -d public ] && [ "$(ls -A public 2>/dev/null)" ]; then
  cp -r public/* .next/standalone/public/ 2>/dev/null || true
fi

echo "🔄 重启 Web 服务..."
sudo systemctl restart kin-web

echo "✅ 部署完成！"
