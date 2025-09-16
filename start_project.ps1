# Voice Authentication System - Start Script
# This script starts both frontend and backend services

Write-Host "🚀 Starting Voice Authentication System..." -ForegroundColor Green
Write-Host ""

# Get the script directory
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Start Backend
Write-Host "📍 Starting Backend Server..." -ForegroundColor Yellow
$BackendProcess = Start-Process -FilePath "python" -ArgumentList "main.py" -WorkingDirectory "$ProjectDir\backend" -PassThru
Write-Host "✅ Backend started on http://127.0.0.1:8000" -ForegroundColor Green

# Wait a moment for backend to initialize
Start-Sleep -Seconds 3

# Start Frontend
Write-Host "📍 Starting Frontend Server..." -ForegroundColor Yellow
$FrontendProcess = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory "$ProjectDir\frontend" -PassThru
Write-Host "✅ Frontend started on http://localhost:5174" -ForegroundColor Green

Write-Host ""
Write-Host "🎉 Voice Authentication System is running!" -ForegroundColor Green
Write-Host "   Frontend: http://localhost:5174" -ForegroundColor Cyan
Write-Host "   Backend:  http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "   API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to stop both services..." -ForegroundColor Yellow

# Wait for user input
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Stop processes
Write-Host ""
Write-Host "🔴 Stopping services..." -ForegroundColor Red
if ($BackendProcess -and !$BackendProcess.HasExited) {
    Stop-Process -Id $BackendProcess.Id -Force -ErrorAction SilentlyContinue
}
if ($FrontendProcess -and !$FrontendProcess.HasExited) {
    Stop-Process -Id $FrontendProcess.Id -Force -ErrorAction SilentlyContinue
}
Write-Host "✅ All services stopped." -ForegroundColor Green
