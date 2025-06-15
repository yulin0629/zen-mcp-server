#!/bin/bash

# Zen MCP Server 啟動腳本 (Bash 版本)
# 使用不同的 .env 檔案啟動不同的實例

# --- 設定預設值 ---
ACTION="menu"
FOLLOW_LOGS=false

# --- 顏色定義 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
GRAY='\033[0;90m' # 深灰色
NC='\033[0m'     # 無顏色

# --- 輔助函數：彩色輸出 ---
write_color_output() {
    local color_code="$1"
    shift
    echo -e "${color_code}$*${NC}"
}

# --- 實例管理函數 ---

# 啟動 WSL 實例
start_wsl_instance() {
    write_color_output "$YELLOW" "🚀 啟動 WSL 實例 (使用 .env.wsl)..."
    docker compose -f docker-compose.multi.yml --env-file .env.wsl -p zen-wsl up -d
    if [ $? -eq 0 ]; then
        write_color_output "$GREEN" "✅ WSL 實例啟動成功！"
        echo "   Redis 容器: zen-wsl-redis-1"
        echo "   MCP 容器: zen-wsl-zen-mcp-1"
        echo "   配置檔案: .env.wsl"
    else
        write_color_output "$RED" "❌ WSL 實例啟動失敗！"
    fi
}

# 停止 WSL 實例
stop_wsl_instance() {
    write_color_output "$YELLOW" "🛑 停止 WSL 實例..."
    
    write_color_output "$GRAY" "   檢查並停止預設實例..."
    docker stop zen-mcp-server zen-mcp-redis zen-mcp-log-monitor 2>/dev/null
    docker rm zen-mcp-server zen-mcp-redis zen-mcp-log-monitor 2>/dev/null
    
    docker compose -p zen-wsl down
    write_color_output "$GREEN" "✅ WSL 實例已停止"
}

# 顯示狀態
show_status() {
    write_color_output "$CYAN" "📊 WSL 實例狀態："
    echo ""
    docker compose -p zen-wsl ps
}

# 顯示日誌
show_logs() {
    if [ "$FOLLOW_LOGS" = true ]; then
        write_color_output "$CYAN" "📜 顯示 WSL 實例實時日誌 (Ctrl+C 返回選單)..."
        # 只停止日誌追蹤，不 exit
        trap 'write_color_output "$YELLOW" "\n🛑 停止日誌追蹤，返回選單..." >&2; kill %1 2>/dev/null; trap - SIGINT SIGTERM; return' SIGINT SIGTERM
        docker compose -p zen-wsl logs -f &
        wait %1
        trap - SIGINT SIGTERM
    else
        write_color_output "$CYAN" "📜 WSL 實例最近的日誌："
        echo ""
        docker compose -p zen-wsl logs --tail 20
    fi
}

# 重啟 WSL 實例
restart_wsl_instance() {
    write_color_output "$YELLOW" "🔄 重啟 WSL 實例..."
    stop_wsl_instance
    sleep 2
    echo ""
    start_wsl_instance
}

# 重啟 zen-mcp 容器
restart_zen_mcp_container() {
    write_color_output "$YELLOW" "🔄 重啟 zen-mcp 容器..."
    docker compose -p zen-wsl restart zen-mcp
    if [ $? -eq 0 ]; then
        write_color_output "$GREEN" "✅ zen-mcp 容器重啟成功！"
    else
        write_color_output "$RED" "❌ zen-mcp 容器重啟失敗！"
    fi
}

# 顯示互動式選單
show_menu() {
    while true; do
        clear
        echo ""
        write_color_output "$CYAN" "╔══════════════════════════════════════╗"
        write_color_output "$CYAN" "║    🤖 Zen MCP Server 管理工具       ║"
        write_color_output "$CYAN" "╚══════════════════════════════════════╝"
        echo ""
        echo "請選擇操作："
        echo ""
        write_color_output "$GREEN" "  [1] 啟動 WSL 實例"
        write_color_output "$CYAN" "  [2] 查看實例狀態"
        write_color_output "$MAGENTA" "  [3] 查看日誌 (最近20行)"
        write_color_output "$MAGENTA" "  [4] 實時追蹤日誌"
        write_color_output "$YELLOW" "  [5] 重啟 WSL 實例"
        write_color_output "$YELLOW" "  [6] 重啟 zen-mcp 容器"
        write_color_output "$RED" "  [7] 停止 WSL 實例"
        echo ""
        write_color_output "$GRAY" "  [Q] 退出"
        echo ""
        
        read -r -p "請輸入選項: " choice
        
        case "$choice" in
            1)
                start_wsl_instance
                echo ""; read -r -p "按 Enter 繼續..."
                ;;
            2)
                show_status
                echo ""; read -r -p "按 Enter 繼續..."
                ;;
            3)
                local_follow_logs_backup=$FOLLOW_LOGS # 備份全局狀態
                FOLLOW_LOGS=false # 確保此選項不追蹤
                show_logs
                FOLLOW_LOGS=$local_follow_logs_backup # 恢復全局狀態
                echo ""; read -r -p "按 Enter 繼續..."
                ;;
            4)
                local_follow_logs_backup=$FOLLOW_LOGS # 備份全局狀態
                FOLLOW_LOGS=true # 確保此選項追蹤
                show_logs # show_logs 將處理 Ctrl+C
                FOLLOW_LOGS=$local_follow_logs_backup # 恢復全局狀態
                # 此處不需要 "按 Enter 繼續..." 因為日誌是互動的
                ;;
            5)
                restart_wsl_instance
                echo ""; read -r -p "按 Enter 繼續..."
                ;;
            6)
                restart_zen_mcp_container
                echo ""; read -r -p "按 Enter 繼續..."
                ;;
            7)
                stop_wsl_instance
                echo ""; read -r -p "按 Enter 繼續..."
                ;;
            [qQ])
                echo ""
                write_color_output "$GREEN" "👋 再見！"
                echo ""
                exit 0
                ;;
            *)
                write_color_output "$RED" "❌ 無效的選項，請重試"
                sleep 1
                ;;
        esac
    done
}

# --- 參數解析 ---
# 儲存非選項參數
POSITIONAL_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --follow|-f|-Follow) # 接受 --follow, -f, 或 PowerShell 風格的 -Follow
            FOLLOW_LOGS=true
            shift # 移向下一個參數
            ;;
        *)
            POSITIONAL_ARGS+=("$1") # 儲存為位置參數
            shift # 移向下一個參數
            ;;
    esac
done
set -- "${POSITIONAL_ARGS[@]}" # 恢復位置參數

# 處理位置參數 (操作指令)
VALID_ACTIONS=("menu" "wsl" "stop" "restart" "restart-zen" "status" "logs")
if [ -n "$1" ]; then
    is_valid_action=false
    for valid_action in "${VALID_ACTIONS[@]}"; do
        if [ "$1" == "$valid_action" ]; then
            ACTION="$1"
            is_valid_action=true
            break
        fi
    done
    if [ "$is_valid_action" = false ]; then
        write_color_output "$RED" "❌ 無效的操作: $1"
        echo "可用操作: ${VALID_ACTIONS[*]}"
        echo "使用範例: $0 logs --follow"
        exit 1
    fi
fi

# --- 主要邏輯 ---
if [ "$ACTION" != "menu" ]; then
    echo ""
    write_color_output "$CYAN" "🤖 Zen MCP Server 管理工具"
    echo ""
fi

case "$ACTION" in
    menu)
        show_menu
        ;;
    wsl)
        start_wsl_instance
        ;;
    restart)
        restart_wsl_instance
        ;;
    restart-zen)
        restart_zen_mcp_container
        ;;
    stop)
        stop_wsl_instance
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs # FOLLOW_LOGS 已在參數解析時設定
        ;;
    *)
        # 理論上不應到達此處，因為參數解析已處理無效操作
        write_color_output "$RED" "內部錯誤：未知的操作 '$ACTION'"
        show_menu # 出錯時預設顯示選單
        ;;
esac

# --- 如果不是選單模式且操作成功，則顯示提示 ---
if [ "$ACTION" != "menu" ] && [ $? -eq 0 ]; then
    # 對於 logs --follow，由於 trap exit，可能不會執行到這裡
    # 但對於其他非選單命令，會顯示提示
    if ! ([ "$ACTION" == "logs" ] && [ "$FOLLOW_LOGS" = true ]); then
        echo ""
        echo "💡 提示："
        echo "   - 互動式選單: $0"
        echo "   - 啟動實例:   $0 wsl"
        echo "   - 重啟實例:   $0 restart"
        echo "   - 查看狀態:   $0 status"
        echo "   - 查看日誌:   $0 logs"
        echo "   - 實時日誌:   $0 logs --follow  (或 -f, -Follow)"
        echo "   - 停止實例:   $0 stop"
        echo ""
    fi
fi

exit 0
