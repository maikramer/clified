# Bootstrap Clified (PyPI) — wrapper fino sobre scripts/_bootstrap.ps1.
# Dot-sourced por install.ps1 dos projectos consumidores.
#
# Uso (no install.ps1 do projecto):
#   . "$PSScriptRoot\scripts\install-bootstrap.ps1"
#   Invoke-ClifiedBootstrap -ToolName cissapi @args

#Requires -Version 5.1

. "$PSScriptRoot\_bootstrap.ps1"

function Invoke-ClifiedBootstrap {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ToolName,
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$ClifiedArgs
    )

    $py = Get-ClifiedPython
    Add-PythonUserScriptsToPath -PythonExe $py
    $minVer = if ($env:CLIFIED_MIN_VERSION) { $env:CLIFIED_MIN_VERSION } else { "0.4.1" }

    if (Get-Command clified-install -ErrorAction SilentlyContinue) {
        Invoke-ClifiedExec -PythonExe $py -ToolName $ToolName -ClifiedArgs $ClifiedArgs
    }
    if (Test-ClifiedInstalled -PythonExe $py) {
        Invoke-ClifiedExec -PythonExe $py -ToolName $ToolName -ClifiedArgs $ClifiedArgs
    }

    Install-ClifiedPackage -PythonExe $py -MinVersion $minVer
    Invoke-ClifiedExec -PythonExe $py -ToolName $ToolName -ClifiedArgs $ClifiedArgs
}
