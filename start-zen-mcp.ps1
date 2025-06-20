# Zen MCP Server 啟動腳本
# 使用不同的 .env 檔案啟動不同的實例

param(
    [Parameter(Position=0)]
    [ValidateSet("windows", "stop", "restart", "status", "logs", "build", "menu")]
    [string]$Action = "menu",
    
    [Parameter()]
    [switch]$Follow
)

# 設定顏色輸出
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

# 啟動 Windows 實例
function Start-WindowsInstance {
    Write-ColorOutput Yellow "🚀 啟動 Windows 實例 (使用 .env.windows)..."
    # 使用單一檔案 + project name 方式
    docker compose --env-file .env.windows -p zen-windows up -d
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput Green "✅ Windows 實例啟動成功！"
        Write-Host "   Redis 容器: zen-windows-redis-1"
        Write-Host "   MCP 容器: zen-windows-zen-mcp-1"
        Write-Host "   Log Monitor 容器: zen-windows-log-monitor-1"
        Write-Host "   配置檔案: docker-compose.yml"
        Write-Host "   環境檔案: .env.windows"
        Write-Host "   Project Name: zen-windows"
    } else {
        Write-ColorOutput Red "❌ Windows 實例啟動失敗！"
    }
}

# 停止所有實例
function Stop-AllInstances {
    Write-ColorOutput Yellow "🛑 停止所有實例..."
    
    # 停止專案實例
    docker compose -p zen-windows down
    Write-ColorOutput Green "✅ 所有實例已停止"
}

# 顯示狀態
function Show-Status {
    Write-ColorOutput Cyan "📊 實例狀態："
    Write-Host ""
    Write-Host "Windows 實例:"
    docker compose -p zen-windows ps
}

# 顯示日誌
function Show-Logs {
    if ($Follow) {
        Write-ColorOutput Cyan "📜 顯示實時日誌 (Ctrl+C 退出)..."
        # 顯示實例的日誌
        docker compose -p zen-windows logs -f
    } else {
        Write-ColorOutput Cyan "📜 最近的日誌："
        Write-Host ""
        Write-Host "=== Windows 實例 ==="
        docker compose -p zen-windows logs --tail 20
    }
}

# 重啟實例
function Restart-Instances {
    Write-ColorOutput Yellow "🔄 重啟所有實例..."
    Stop-AllInstances
    Start-Sleep -Seconds 2
    Write-Host ""
    Start-WindowsInstance
}

# 重建 Docker Images
function Build-Images {
    Write-ColorOutput Yellow "🔨 重建 Docker Images (無快取)..."
    docker compose --env-file .env.windows -p zen-windows build --no-cache
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput Green "✅ Docker Images 重建成功！"
        Write-Host ""
        Write-ColorOutput Cyan "💡 提示: 重建完成後，您可能需要重新啟動實例來使用新的映像檔"
    } else {
        Write-ColorOutput Red "❌ Docker Images 重建失敗！"
    }
}

# 顯示互動式選單
function Show-Menu {
    while ($true) {
        Clear-Host
        Write-Host ""
        Write-ColorOutput Cyan "╔══════════════════════════════════════╗"
        Write-ColorOutput Cyan "║    🤖 Zen MCP Server 管理工具       ║"
        Write-ColorOutput Cyan "╚══════════════════════════════════════╝"
        Write-Host ""
        Write-Host "請選擇操作："
        Write-Host ""
        Write-ColorOutput Green "  [1] 啟動 Windows 實例"
        Write-ColorOutput Cyan "  [2] 查看實例狀態"
        Write-ColorOutput Magenta "  [3] 查看日誌"
        Write-ColorOutput Magenta "  [4] 實時追蹤日誌"
        Write-ColorOutput Yellow "  [5] 重啟實例"
        Write-ColorOutput DarkYellow "  [6] 重建 Docker Images"
        Write-ColorOutput Red "  [7] 停止實例"
        Write-Host ""
        Write-ColorOutput Gray "  [Q] 退出"
        Write-Host ""
        
        $choice = Read-Host "請輸入選項"
        
        switch ($choice.ToUpper()) {
            "1" {
                Start-WindowsInstance
                Write-Host ""
                Read-Host "按 Enter 繼續..."
            }
            "2" {
                Show-Status
                Write-Host ""
                Read-Host "按 Enter 繼續..."
            }
            "3" {
                Show-Logs
                Write-Host ""
                Read-Host "按 Enter 繼續..."
            }
            "4" {
                Write-ColorOutput Cyan "📜 顯示實時日誌 (按 Ctrl+C 退出)..."
                Start-Sleep -Seconds 1
                $Follow = $true
                Show-Logs
            }
            "5" {
                Restart-Instances
                Write-Host ""
                Read-Host "按 Enter 繼續..."
            }
            "6" {
                Build-Images
                Write-Host ""
                Read-Host "按 Enter 繼續..."
            }
            "7" {
                Stop-AllInstances
                Write-Host ""
                Read-Host "按 Enter 繼續..."
            }
            "Q" {
                Write-Host ""
                Write-ColorOutput Green "👋 再見！"
                Write-Host ""
                return
            }
            default {
                Write-ColorOutput Red "❌ 無效的選項，請重試"
                Start-Sleep -Seconds 1
            }
        }
    }
}

# 主要邏輯
switch ($Action) {
    "menu" {
        Show-Menu
    }
    "windows" {
        Write-Host ""
        Write-ColorOutput Cyan "🤖 Zen MCP Server 管理工具"
        Write-Host ""
        Start-WindowsInstance
    }
    "restart" {
        Write-Host ""
        Write-ColorOutput Cyan "🤖 Zen MCP Server 管理工具"
        Write-Host ""
        Restart-Instances
    }
    "stop" {
        Write-Host ""
        Write-ColorOutput Cyan "🤖 Zen MCP Server 管理工具"
        Write-Host ""
        Stop-AllInstances
    }
    "status" {
        Write-Host ""
        Write-ColorOutput Cyan "🤖 Zen MCP Server 管理工具"
        Write-Host ""
        Show-Status
    }
    "logs" {
        Write-Host ""
        Write-ColorOutput Cyan "🤖 Zen MCP Server 管理工具"
        Write-Host ""
        Show-Logs
    }
    "build" {
        Write-Host ""
        Write-ColorOutput Cyan "🤖 Zen MCP Server 管理工具"
        Write-Host ""
        Build-Images
    }
}

# 如果不是選單模式，顯示提示
if ($Action -ne "menu") {
    Write-Host ""
    Write-Host "💡 提示："
    Write-Host "   - 互動式選單: .\start-zen-mcp.ps1"
    Write-Host "   - 啟動實例: .\start-zen-mcp.ps1 windows"
    Write-Host "   - 重啟實例: .\start-zen-mcp.ps1 restart"
    Write-Host "   - 查看狀態: .\start-zen-mcp.ps1 status"
    Write-Host "   - 查看日誌: .\start-zen-mcp.ps1 logs"
    Write-Host "   - 實時日誌: .\start-zen-mcp.ps1 logs -Follow"
    Write-Host "   - 重建映像: .\start-zen-mcp.ps1 build"
    Write-Host "   - 停止實例: .\start-zen-mcp.ps1 stop"
    Write-Host ""
}