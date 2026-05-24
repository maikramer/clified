# =============================================================================
# Clified — Instalador Universal (Windows PowerShell)
# =============================================================================

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:CLIFIED_ROOT = $ScriptDir

$Cyan = "`e[36m"
$Red = "`e[31m"
$Reset = "`e[0m"

function Prepare-InstallerEnvironment {
    Write-Host "${Cyan}Preparando ambiente Clified...${Reset}"

    $toolsYaml = Join-Path $ScriptDir "tools.yaml"
    if (-not (Test-Path -LiteralPath $toolsYaml)) {
        Write-Host "${Red}tools.yaml nao encontrado em $ScriptDir${Reset}"
        Write-Host "  Copie tools.yaml.example para tools.yaml."
        exit 1
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if (-not $pythonCmd) {
        Write-Host "${Red}Python 3 nao encontrado.${Reset}"
        exit 1
    }

    $py = $pythonCmd.Source
    & $py -c "import sys; assert sys.version_info >= (3, 10)" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "${Red}Python 3.10+ necessario.${Reset}"
        exit 1
    }

    $installerVenv = Join-Path $ScriptDir ".installer-venv"
    $launcherPython = Join-Path $installerVenv "Scripts\\python.exe"

    if ((Test-Path -LiteralPath $launcherPython) -and
        (& $launcherPython -c "import clified, rich, yaml" 2>$null; $LASTEXITCODE -eq 0)) {
        return @{ Launcher = $launcherPython; Projects = $py }
    }

    Write-Host "${Cyan}  -> Ambiente do instalador (venv + clified)...${Reset}"
    if (-not (Test-Path -LiteralPath $launcherPython)) {
        & $py -m venv $installerVenv
        if ($LASTEXITCODE -ne 0) { exit 1 }
    }

    & $launcherPython -m pip install -q --upgrade pip
    & $launcherPython -m pip install -q -e $ScriptDir
    if ($LASTEXITCODE -ne 0) { exit 1 }

    return @{ Launcher = $launcherPython; Projects = $py }
}

$p = Prepare-InstallerEnvironment

$env:UV_VENV_CLEAR = "1"
$env:UV_LINK_MODE = "copy"

Write-Host "${Cyan}Clified - Instalador Universal${Reset}"
Write-Host "================================="

& $p.Launcher -m clified --python $p.Projects @args
exit $LASTEXITCODE
