[CmdletBinding()]
param(
    [ValidateSet('onefile', 'onedir')]
    [string]$Mode = 'onefile',

    [string]$Name = 'AutopageMKIIver5.3.0LITE',

    [string]$Entry = 'autopage_MKII_ver5.3.0LITE.py',

    [string]$Python = 'python',

    [string]$DistDir = 'dist',

    [string]$WorkDir = 'build',

    [switch]$Console,

    [switch]$NoSplash,

    [switch]$Upx
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    $version = & $Python -c "import sys; print(sys.version.split()[0])"
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found: $Python"
    }

    & $Python -c "import PyInstaller"
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller is not installed for $Python. Run: $Python -m pip install pyinstaller"
    }

    $excludes = @(
        'torch', 'torchaudio', 'torchvision', 'torchgen',
        'transformers', 'sentencepiece',
        'diffusers', 'accelerate', 'peft', 'optimum', 'timm', 'kornia',
        'onnx', 'onnxruntime',
        'sklearn', 'scipy', 'numba', 'llvmlite',
        'matplotlib', 'sympy',
        'IPython', 'ipykernel', 'ipywidgets',
        'jupyter', 'jupyter_client', 'jupyter_core', 'notebook',
        'yapf', 'jedi', 'parso', 'debugpy', 'comm',
        'pythainlp'
    )

    $assetsDir = Join-Path $ProjectRoot 'assets'
    $tablesDir = Join-Path $ProjectRoot 'tables'
    $iconPath = Join-Path $ProjectRoot 'assets/imgs/kheedluang.ico'
    $splashPath = Join-Path $ProjectRoot 'assets/imgs/5.3_loading_splash.jpg'
    $entryPath = Join-Path $ProjectRoot $Entry
    $upxDir = Join-Path $ProjectRoot 'to_exe_tools/exe_size_reducer/upx-5.0.1-win64'

    $pyArgs = @(
        '-m', 'PyInstaller',
        '--noconfirm',
        '--clean',
        '--name', $Name,
        '--distpath', $DistDir,
        '--workpath', $WorkDir,
        '--specpath', $WorkDir,
        '--icon', $iconPath,
        '--add-data', "$assetsDir;assets",
        '--add-data', "$tablesDir;tables",
        '--hidden-import', 'numpy._core._exceptions'
    )

    if ($Mode -eq 'onefile') {
        $pyArgs += '--onefile'
    }
    else {
        $pyArgs += '--onedir'
    }

    if ($Console) {
        $pyArgs += '--console'
    }
    else {
        $pyArgs += '--windowed'
    }

    if (-not $NoSplash) {
        $pyArgs += @('--splash', $splashPath)
    }

    if ($Upx) {
        $pyArgs += @('--upx-dir', $upxDir)
    }

    foreach ($module in $excludes) {
        $pyArgs += @('--exclude-module', $module)
    }

    $pyArgs += $entryPath

    Write-Host "Python $version | PyInstaller | mode=$Mode | console=$Console | splash=$(-not $NoSplash) | upx=$Upx"
    Write-Host "Entry: $Entry"

    & $Python @pyArgs
    $exitCode = $LASTEXITCODE

    $exePath = if ($Mode -eq 'onefile') {
        Join-Path $DistDir "$Name.exe"
    }
    else {
        Join-Path (Join-Path $DistDir $Name) "$Name.exe"
    }

    if (-not [System.IO.Path]::IsPathRooted($exePath)) {
        $exePath = Join-Path $ProjectRoot $exePath
    }
    $exePath = [System.IO.Path]::GetFullPath($exePath)
    $hasExe = Test-Path -LiteralPath $exePath
}
finally {
    Pop-Location
}

if ($exitCode -ne 0) {
    Write-Error "Build failed with exit code $exitCode"
    exit $exitCode
}

if (-not $hasExe) {
    Write-Error "Build finished but executable was not found: $exePath"
    exit 1
}

$sizeMb = [math]::Round((Get-Item -LiteralPath $exePath).Length / 1MB, 1)
Write-Host "Build complete: $exePath ($sizeMb MB)"
exit 0
