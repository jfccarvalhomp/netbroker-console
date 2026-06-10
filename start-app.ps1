param(
  [int]$Port = 4180
)

$ErrorActionPreference = 'Stop'

$pythonCandidates = @(
  "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
)

$python = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if (-not $python) {
  Write-Host "Python nao encontrado nos caminhos conhecidos." -ForegroundColor Red
  Write-Host "Instalacao esperada: $env:LOCALAPPDATA\Programs\Python\Python314\python.exe"
  exit 1
}

$root = $PSScriptRoot
Write-Host "Servidor da aplicacao iniciado." -ForegroundColor Green
Write-Host "Pasta: $root"
Write-Host "URL:   http://127.0.0.1:$Port/"
Write-Host ""
Write-Host "Para parar, pressione Ctrl+C nesta janela."

& $python "$root\server.py" --host 127.0.0.1 --port $Port --data "$root\data\state.json"
