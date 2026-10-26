@echo off
rem 抖音运营中台 · 每日调度 tick(幂等:不到期即空转)
cd /d "D:\个人项目\抖音运营中台"
".venv\Scripts\python.exe" -m backend.tick >> "data\tick.log" 2>&1
