# =============================================================================
# Clified — Instalador Universal (Windows PowerShell)
# =============================================================================
#
# One-liner (instala o motor):
#   irm https://raw.githubusercontent.com/maikramer/clified/main/install.ps1 | iex
#
# One-liner com argumentos (instalar ferramenta remota):
#   & ([scriptblock]::Create((irm https://raw.githubusercontent.com/maikramer/clified/main/install.ps1))) --get denv
#
# Local (clone do repo, dev — editable install em .installer-venv):
#   .\install.ps1 [tool] [opções]
#
# Defina $env:CLIFIED_VERSION para uma versão específica (ex.: "clified==0.7.0"
# ou "git+https://github.com/maikramer/clified.git@main" para --edge).
# =============================================================================

$ErrorActionPreference = "Stop"

$ESC = [char]27
$Cyan = "$ESC[36m"; $Red = "$ESC[31m"; $Green = "$ESC[32m"; $Reset = "$ESC[0m"

# --- Detectar modo: dev (clone local) vs remoto (irm | iex / PyPI) ----------
$scriptPath = $MyInvocation.MyCommand.Path
$devMode = $false
$scriptDir = ""
if ($scriptPath -and (Test-Path -LiteralPath $scriptPath)) {
    $scriptDir = Split-Path -Parent $scriptPath
    $pyproject = Join-Path $scriptDir "pyproject.toml"
    if ((Test-Path -LiteralPath $pyproject) -and
        (Select-String -Path $pyproject -Pattern 'name = "clified"' -Quiet)) {
        $devMode = $true
    }
}

# =============================================================================
# Modo dev: editable install no .installer-venv (clone do repo clified)
# =============================================================================
if ($devMode) {
    $env:CLIFIED_ROOT = $scriptDir

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) { $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue }
    if (-not $pythonCmd) { Write-Host "${Red}Python 3 nao encontrado.${Reset}"; exit 1 }
    $py = $pythonCmd.Source

    & $py -c "import sys; assert sys.version_info >= (3, 10)" 2>$null
    if ($LASTEXITCODE -ne 0) { Write-Host "${Red}Python 3.10+ necessario.${Reset}"; exit 1 }

    $toolsYaml = Join-Path $scriptDir "tools.yaml"
    if (-not (Test-Path -LiteralPath $toolsYaml) -and
        (Test-Path -LiteralPath (Join-Path $scriptDir "tools.yaml.example"))) {
        Write-Host "${Cyan}  -> Criando tools.yaml a partir do exemplo...${Reset}"
        Copy-Item (Join-Path $scriptDir "tools.yaml.example") $toolsYaml
    }

    $installerVenv = Join-Path $scriptDir ".installer-venv"
    $launcherPy = Join-Path $installerVenv "Scripts\python.exe"
    $launcherReady = $false
    if (Test-Path -LiteralPath $launcherPy) {
        $prev = $ErrorActionPreference; $ErrorActionPreference = "SilentlyContinue"
        & $launcherPy -c "import clified, rich, yaml" 2>$null | Out-Null
        $launcherReady = ($LASTEXITCODE -eq 0)
        $ErrorActionPreference = $prev
    }
    if (-not $launcherReady) {
        Write-Host "${Cyan}  -> Ambiente do instalador (venv + clified)...${Reset}"
        if (-not (Test-Path -LiteralPath $launcherPy)) { & $py -m venv $installerVenv }
        & $launcherPy -m pip install -q --upgrade pip
        & $launcherPy -m pip install -q -e $scriptDir
        if ($LASTEXITCODE -ne 0) { exit 1 }
    }

    $env:UV_VENV_CLEAR = "1"; $env:UV_LINK_MODE = "copy"
    Write-Host "${Cyan}Clified - Instalador Universal (dev)${Reset}"
    & $launcherPy -m clified @args
    exit $LASTEXITCODE
}

# =============================================================================
# Modo remoto: instalar motor do PyPI e delegar a clified-install
# =============================================================================
function Get-ClifiedPython {
    if ($env:PYTHON_CMD -and (Get-Command $env:PYTHON_CMD -ErrorAction SilentlyContinue)) {
        $py = (Get-Command $env:PYTHON_CMD).Source
        $prev = $ErrorActionPreference; $ErrorActionPreference = "SilentlyContinue"
        & $py -m pip --version 2>$null | Out-Null
        $hasPip = ($LASTEXITCODE -eq 0)
        $ErrorActionPreference = $prev
        if ($hasPip) { return $py }
    }
    foreach ($cmd in @("python3.12", "python3", "python")) {
        $found = Get-Command $cmd -ErrorAction SilentlyContinue
        if (-not $found) { continue }
        $py = $found.Source
        $prev = $ErrorActionPreference; $ErrorActionPreference = "SilentlyContinue"
        & $py -m pip --version 2>$null | Out-Null
        $hasPip = ($LASTEXITCODE -eq 0)
        $ErrorActionPreference = $prev
        if ($hasPip) { return $py }
    }
    Write-Host "${Red}Nenhum Python 3.10+ com pip encontrado. Instale Python ou defina PYTHON_CMD.${Reset}"
    exit 1
}

function Add-PythonUserScriptsToPath {
    param([string]$PythonExe)
    $pathsToAdd = @()
    $userBase = (& $PythonExe -m site --user-base 2>$null).Trim()
    if ($userBase) { $pathsToAdd += (Join-Path $userBase "Scripts") }
    $prev = $ErrorActionPreference; $ErrorActionPreference = "SilentlyContinue"
    $nt = (& $PythonExe -c "import sysconfig; print(sysconfig.get_path('scripts','nt_user'))" 2>$null).Trim()
    $ErrorActionPreference = $prev
    if ($nt) { $pathsToAdd += $nt }
    foreach ($dir in ($pathsToAdd | Select-Object -Unique)) {
        if ((Test-Path -LiteralPath $dir) -and ($env:Path -notlike "*$dir*")) {
            $env:Path = "$dir;$env:Path"
        }
    }
}

$py = Get-ClifiedPython
& $py -c "import sys; assert sys.version_info >= (3, 10)" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "${Red}Python 3.10+ necessario.${Reset}"; exit 1 }
Add-PythonUserScriptsToPath -PythonExe $py

$clifiedInstall = Get-Command clified-install -ErrorAction SilentlyContinue
if (-not $clifiedInstall) {
    $prev = $ErrorActionPreference; $ErrorActionPreference = "SilentlyContinue"
    & $py -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('clified') else 1)" 2>$null | Out-Null
    $already = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prev
    if (-not $already) {
        $spec = if ($env:CLIFIED_VERSION) { $env:CLIFIED_VERSION } else { "clified" }
        Write-Host "${Cyan}A instalar o motor clified via pip ($py)...${Reset}"
        & $py -m pip install --user --upgrade $spec
        if ($LASTEXITCODE -ne 0) {
            Write-Host "${Cyan}  -> repetir com --break-system-packages (PEP 668)...${Reset}"
            & $py -m pip install --user --break-system-packages --upgrade $spec
        }
        if ($LASTEXITCODE -ne 0) { Write-Host "${Red}Falha ao instalar clified.${Reset}"; exit $LASTEXITCODE }
        Add-PythonUserScriptsToPath -PythonExe $py
    }
}

if ($args.Count -eq 0) {
    Write-Host "${Green}Clified instalado.${Reset} Proximos passos:"
    Write-Host "  clified-install --catalog            # listar ferramentas remotas conhecidas"
    Write-Host "  clified-install --get denv           # instalar a ferramenta denv do catalogo"
    Write-Host "  clified-install --get <t> --repo URL # instalar ferramenta de um repo arbitrario"
    Write-Host "  clified-install --list               # ferramentas de um tools.yaml local"
    exit 0
}

$clifiedInstall = Get-Command clified-install -ErrorAction SilentlyContinue
if ($clifiedInstall) {
    & $clifiedInstall.Source @args
    exit $LASTEXITCODE
}
& $py -m clified @args
exit $LASTEXITCODE
