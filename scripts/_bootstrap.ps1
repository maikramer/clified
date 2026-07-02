# =============================================================================
# Primitivas partilhadas de bootstrap do Clified (Windows PowerShell).
# Dot-sourced por scripts/install-bootstrap.ps1 e por install.ps1 de projectos
# consumidores. NÃO chama exit por si — a orquestração fica no wrapper.
#
#   . "$PSScriptRoot\_bootstrap.ps1"
#   $py = Get-ClifiedPython
#   Install-ClifiedPackage -PythonExe $py -MinVersion "0.4.1"
#   Invoke-ClifiedExec -PythonExe $py -ToolName denv -ClifiedArgs $args
# =============================================================================

#Requires -Version 5.1

function Get-ClifiedPython {
    if ($env:PYTHON_CMD) {
        if (Test-Path -LiteralPath $env:PYTHON_CMD) {
            return $env:PYTHON_CMD
        }
        Write-Error "PYTHON_CMD aponta para caminho invalido: $($env:PYTHON_CMD)"
        exit 1
    }

    foreach ($cmd in @("python3.12", "python3", "python")) {
        $found = Get-Command $cmd -ErrorAction SilentlyContinue
        if (-not $found) { continue }
        $py = $found.Source
        $prev = $ErrorActionPreference
        $ErrorActionPreference = "SilentlyContinue"
        & $py -m pip --version 2>$null | Out-Null
        $hasPip = ($LASTEXITCODE -eq 0)
        $ErrorActionPreference = $prev
        if ($hasPip) { return $py }
    }

    Write-Host "Nenhum Python com pip encontrado. Instale Python 3.10+ ou defina PYTHON_CMD." -ForegroundColor Red
    exit 1
}

function Test-ClifiedInstalled {
    param([string]$PythonExe)

    # Evita stderr do Python virar erro terminante com $ErrorActionPreference = Stop
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    & $PythonExe -c @"
import importlib.util
import sys
sys.exit(0 if importlib.util.find_spec('clified') else 1)
"@ 2>$null | Out-Null
    $ok = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prev
    return $ok
}

function Add-PythonUserScriptsToPath {
    param([string]$PythonExe)

    $pathsToAdd = @()

    $userBase = (& $PythonExe -m site --user-base 2>$null).Trim()
    if ($userBase) {
        $pathsToAdd += (Join-Path $userBase "Scripts")
    }

    # pip --user no Windows (especialmente com Anaconda) costuma usar AppData\Roaming\Python\PythonXY\Scripts
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    $ntUserScripts = (& $PythonExe -c "import sysconfig; print(sysconfig.get_path('scripts', 'nt_user'))" 2>$null).Trim()
    $ErrorActionPreference = $prev
    if ($ntUserScripts) {
        $pathsToAdd += $ntUserScripts
    }

    foreach ($dir in ($pathsToAdd | Select-Object -Unique)) {
        if ((Test-Path -LiteralPath $dir) -and ($env:Path -notlike "*$dir*")) {
            $env:Path = "$dir;$env:Path"
        }
    }
}

function Install-ClifiedPackage {
    param(
        [string]$PythonExe,
        [string]$MinVersion
    )

    Write-Host "A instalar clified>=$MinVersion via pip ($PythonExe)..." -ForegroundColor Cyan
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Stop"
    try {
        & $PythonExe -m pip install --user --upgrade "clified>=$MinVersion"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "A repetir pip com --break-system-packages (PEP 668)..." -ForegroundColor Yellow
            & $PythonExe -m pip install --user --break-system-packages --upgrade "clified>=$MinVersion"
        }
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Falha ao instalar clified." -ForegroundColor Red
            exit $LASTEXITCODE
        }
    }
    finally {
        $ErrorActionPreference = $prev
    }

    Add-PythonUserScriptsToPath -PythonExe $PythonExe
}

function Invoke-ClifiedExec {
    param(
        [string]$PythonExe,
        [string]$ToolName,
        [string[]]$ClifiedArgs
    )

    $clifiedInstall = Get-Command clified-install -ErrorAction SilentlyContinue
    if ($clifiedInstall) {
        & clified-install $ToolName @ClifiedArgs
        exit $LASTEXITCODE
    }
    & $PythonExe -m clified $ToolName @ClifiedArgs
    exit $LASTEXITCODE
}
