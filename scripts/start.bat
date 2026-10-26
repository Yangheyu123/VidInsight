@echo off
rem VidInsight 一键启动:构建前端 → 单进程托管全栈 → 打开看板
cd /d "D:\个人项目\抖音运营中台"
echo [1/2] 构建前端...
cd frontend && call pnpm build && cd ..
echo [2/2] 启动服务(前端+API 单进程, http://127.0.0.1:8787)...
start "" http://127.0.0.1:8787
".venv\Scripts\python.exe" -m backend.api
