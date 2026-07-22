@echo off
chcp 65001 >nul
title 桌面宠物

echo ========================================
echo   桌面宠物 - 启动脚本
echo ========================================
echo.

:: 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请确认已安装并加入 PATH。
    pause
    exit /b 1
)

:: 检查 PySide6 是否已安装
python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo [提示] 首次运行，正在安装 PySide6 ...
    pip install PySide6
    if errorlevel 1 (
        echo [错误] PySide6 安装失败，请检查网络或手动执行: pip install PySide6
        pause
        exit /b 1
    )
    echo [完成] PySide6 安装成功。
    echo.
)

:: 确保目录结构存在
if not exist "res" mkdir res
if not exist "config" mkdir config

:: 启动程序
echo [启动] 正在启动桌面宠物...
python src\main.py

:: 如果异常退出，暂停查看错误
if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出，请查看上方错误信息。
    pause
)