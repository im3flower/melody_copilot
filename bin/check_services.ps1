# Melody Copilot - 启动所有服务的帮助脚本
# 使用说明：在 3 个终端中分别运行这些命令

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Melody Copilot - Service Startup Guide" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "You need to start these services in separate terminals:" -ForegroundColor Yellow
Write-Host ""

Write-Host "Terminal 1 - Backend (FastAPI):" -ForegroundColor Green
Write-Host "  cd c:\Users\18200\Desktop\gen_ai\melody_copilot" -ForegroundColor White
Write-Host "  python main.py" -ForegroundColor White
Write-Host ""

Write-Host "Terminal 2 - Bridge (UDP Listener):" -ForegroundColor Green
Write-Host "  cd c:\Users\18200\Desktop\gen_ai\melody_copilot" -ForegroundColor White
Write-Host "  python midi_track_ctrl\bridge.py" -ForegroundColor White
Write-Host ""

Write-Host "Terminal 3 - Frontend (React/Vite):" -ForegroundColor Green
Write-Host "  cd c:\Users\18200\Desktop\gen_ai\melody_copilot\UI" -ForegroundColor White
Write-Host "  npm run dev" -ForegroundColor White
Write-Host ""

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "After starting all services, test with:" -ForegroundColor Yellow
Write-Host "  python test_udp_send.py" -ForegroundColor White
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Current Status Check:" -ForegroundColor Cyan
Write-Host ""

# Check if backend is running
Write-Host "Checking Backend (port 8000)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/bridge/latest" -UseBasicParsing -TimeoutSec 2
    Write-Host "  ✅ Backend is running" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Backend is NOT running" -ForegroundColor Red
    Write-Host "     Start it with: python main.py" -ForegroundColor White
}

Write-Host ""

# Check if frontend is running
Write-Host "Checking Frontend (port 5173)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -TimeoutSec 2
    Write-Host "  ✅ Frontend is running" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Frontend is NOT running" -ForegroundColor Red
    Write-Host "     Start it with: cd UI; npm run dev" -ForegroundColor White
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
