# Smart Office System - Build Package Script
param(
    [switch]$CleanVenv
)

Write-Host "============================================================"
Write-Host "  Build Package Tool"
Write-Host "============================================================"
Write-Host ""

$VenvDir = "venv_build"
$Requirements = "requirements.txt"
$AppDir = $PSScriptRoot
Set-Location $AppDir

# Chinese mirror URL
$MirrorUrl = "https://mirrors.aliyun.com/pypi/simple/"

Write-Host "[INFO] Working directory: $AppDir"
Write-Host "[INFO] Using mirror: $MirrorUrl"
Write-Host ""

# Step 1: Check Python
Write-Host "============================================================"
Write-Host "  Step 1: Check Python Environment"
Write-Host "============================================================"
try {
    $PythonVer = python --version 2>&1
    Write-Host "[OK] Python: $PythonVer"
}
catch {
    Write-Host "[ERROR] Python not found!"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

# Step 2: Prepare Virtual Environment
Write-Host "============================================================"
Write-Host "  Step 2: Prepare Virtual Environment"
Write-Host "============================================================"
if (Test-Path $VenvDir) {
    if ($CleanVenv) {
        Write-Host "[INFO] Removing old virtual environment..."
        Remove-Item -Path $VenvDir -Recurse -Force
        Start-Sleep -Seconds 1
    }
    else {
        Write-Host "[INFO] Virtual environment already exists"
    }
}

if (-not (Test-Path $VenvDir)) {
    Write-Host "[INFO] Creating virtual environment: $VenvDir"
    try {
        python -m venv $VenvDir
        Write-Host "[OK] Virtual environment created"
    }
    catch {
        Write-Host "[ERROR] Failed to create virtual environment!"
        Read-Host "Press Enter to exit"
        exit 1
    }
}
Write-Host ""

# Step 3: Activate Virtual Environment
Write-Host "============================================================"
Write-Host "  Step 3: Activate Virtual Environment"
Write-Host "============================================================"
$VenvActivate = Join-Path $VenvDir "Scripts\Activate.ps1"
if (-not (Test-Path $VenvActivate)) {
    Write-Host "[ERROR] Activation script not found!"
    Read-Host "Press Enter to exit"
    exit 1
}
& $VenvActivate
Write-Host "[OK] Virtual environment activated"
Write-Host ""

# Step 4: Configure pip mirror
Write-Host "============================================================"
Write-Host "  Step 4: Configure pip mirror"
Write-Host "============================================================"
$VenvScripts = Join-Path $VenvDir "Scripts"
$VenvPip = Join-Path $VenvScripts "pip.exe"

# Set pip mirror in pip.conf
$Env:PIP_INDEX_URL = $MirrorUrl
$Env:PIP_TRUSTED_HOST = "mirrors.aliyun.com"

# Also create pip.conf file for permanent settings
$PipConfDir = "$env:APPDATA\pip"
if (-not (Test-Path $PipConfDir)) {
    New-Item -ItemType Directory -Path $PipConfDir -Force | Out-Null
}
$PipConf = Join-Path $PipConfDir "pip.ini"
@"
[global]
index-url = $MirrorUrl
trusted-host = mirrors.aliyun.com
[install]
trusted-host = mirrors.aliyun.com
"@ | Out-File -FilePath $PipConf -Encoding utf8

Write-Host "[OK] Mirror configured: $MirrorUrl"
Write-Host ""

# Step 5: Upgrade pip
Write-Host "============================================================"
Write-Host "  Step 5: Upgrade pip"
Write-Host "============================================================"
& $VenvPip install --upgrade pip
Write-Host ""

# Step 6: Install Dependencies
Write-Host "============================================================"
Write-Host "  Step 6: Install Dependencies"
Write-Host "============================================================"
if (-not (Test-Path $Requirements)) {
    Write-Host "[ERROR] $Requirements not found!"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[INFO] Installing from $Requirements using mirror..."
Write-Host ""
try {
    & $VenvPip install -r $Requirements
    Write-Host ""
    Write-Host "[OK] All dependencies installed"
}
catch {
    Write-Host ""
    Write-Host "[WARNING] Some packages may have failed. Continuing anyway..."
}
Write-Host ""

# Step 7: Check Files
Write-Host "============================================================"
Write-Host "  Step 7: Check Project Files"
Write-Host "============================================================"
$FilesCheck = $true

$CheckList = @("app.py", "init_db_standalone_simple.py", "models.py")
foreach ($File in $CheckList) {
    if (-not (Test-Path $File)) {
        Write-Host "[ERROR] $File not found!"
        $FilesCheck = $false
    }
}

$DirList = @("templates", "static")
foreach ($Dir in $DirList) {
    if (-not (Test-Path $Dir)) {
        Write-Host "[ERROR] $Dir not found!"
        $FilesCheck = $false
    }
}

if (-not $FilesCheck) {
    Write-Host "[ERROR] File check failed!"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[OK] All files checked"
Write-Host ""

# Step 8: Build with PyInstaller
Write-Host "============================================================"
Write-Host "  Step 8: Build with PyInstaller"
Write-Host "============================================================"
Write-Host ""

$VenvPython = Join-Path $VenvScripts "python.exe"

try {
    & $VenvPython build_exe.py
    $BuildExit = $LASTEXITCODE
}
catch {
    $BuildExit = 1
}

if ($BuildExit -ne 0) {
    Write-Host ""
    Write-Host "============================================================"
    Write-Host "  [ERROR] Build failed!"
    Write-Host "============================================================"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "============================================================"
Write-Host "  Build completed!"
Write-Host "============================================================"
Write-Host ""
Write-Host "Output directory: $(Join-Path $AppDir 'dist')"
Write-Host ""
Write-Host "============================================================"
Write-Host "  Next steps:"
Write-Host "============================================================"
Write-Host ""
Write-Host "1. Test the package:"
Write-Host "   Go to dist folder, run: 智能服务办公平台.exe"
Write-Host ""
Write-Host "2. Verify database initialization:"
Write-Host "   Should automatically create oa.db"
Write-Host ""
Write-Host "3. Test login:"
Write-Host "   Username: admin"
Write-Host "   Password: admin123"
Write-Host ""
Write-Host "============================================================"
Write-Host ""

$Answer = Read-Host "Open dist folder? (Y/N)"
if ($Answer -eq "Y" -or $Answer -eq "y") {
    if (Test-Path "dist") {
        explorer dist
    }
}

Write-Host ""
Write-Host "Done!"
Write-Host ""
Read-Host "Press Enter to exit"
