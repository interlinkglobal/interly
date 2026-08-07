$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$InterlySpec = "git+https://github.com/interlinkglobal/Interly.git@main"
$PythonVersion = "3.13.14"

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Refresh-Path {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

function Find-Python {
    $candidates = @(
        @{ Command = "py"; Arguments = @("-3") },
        @{ Command = "python"; Arguments = @() }
    )

    foreach ($candidate in $candidates) {
        $command = Get-Command $candidate.Command -ErrorAction SilentlyContinue
        if (-not $command) {
            continue
        }

        try {
            $candidateArguments = @($candidate.Arguments)
            $version = & $command.Source @candidateArguments -c (
                "import sys; print('.'.join(map(str, sys.version_info[:3])))"
            ) 2>$null
            if ($LASTEXITCODE -eq 0 -and [version]$version -ge [version]"3.11") {
                return [pscustomobject]@{
                    Command = $command.Source
                    Arguments = $candidate.Arguments
                    Version = $version
                }
            }
        }
        catch {
            continue
        }
    }
    return $null
}

function Install-Python {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Step "Installing Python with Windows Package Manager"
        & $winget.Source install --id Python.Python.3.13 --exact --silent `
            --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -eq 0) {
            Refresh-Path
            if (Find-Python) {
                return
            }
        }
        Write-Warning "Windows Package Manager did not complete the install; using python.org."
    }

    Write-Step "Downloading Python from python.org"
    $architecture = [Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
    $installerName = switch ($architecture) {
        "Arm64" { "python-$PythonVersion-arm64.exe" }
        "X86" { "python-$PythonVersion.exe" }
        default { "python-$PythonVersion-amd64.exe" }
    }
    $installerUrl = "https://www.python.org/ftp/python/$PythonVersion/$installerName"
    $installerPath = Join-Path ([IO.Path]::GetTempPath()) $installerName

    try {
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
        $process = Start-Process -FilePath $installerPath -ArgumentList @(
            "/quiet",
            "InstallAllUsers=0",
            "Include_launcher=1",
            "Include_pip=1",
            "PrependPath=1"
        ) -Wait -PassThru
        if ($process.ExitCode -ne 0) {
            throw "Python installer exited with code $($process.ExitCode)."
        }
    }
    finally {
        Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
    }
    Refresh-Path
}

function Find-Git {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) {
        return $null
    }
    & $git.Source --version *> $null
    if ($LASTEXITCODE -eq 0) {
        return $git.Source
    }
    return $null
}

function Install-Git {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Step "Installing Git with Windows Package Manager"
        & $winget.Source install --id Git.Git --exact --silent `
            --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -eq 0) {
            Refresh-Path
            if (Find-Git) {
                return
            }
        }
        Write-Warning "Windows Package Manager did not complete the install; using GitHub."
    }

    Write-Step "Downloading Git for Windows"
    $architecture = [Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
    $assetArchitecture = switch ($architecture) {
        "Arm64" { "arm64" }
        "X64" { "64-bit" }
        default { throw "Automatic Git installation requires 64-bit or ARM64 Windows." }
    }
    $headers = @{ Accept = "application/vnd.github+json"; "User-Agent" = "Interly installer" }
    $release = Invoke-RestMethod `
        -Uri "https://api.github.com/repos/git-for-windows/git/releases/latest" `
        -Headers $headers
    $asset = $release.assets | Where-Object {
        $_.name -match "^Git-.*-$assetArchitecture\.exe$"
    } | Select-Object -First 1
    if (-not $asset) {
        throw "GitHub returned no suitable Git for Windows installer."
    }
    $installerPath = Join-Path ([IO.Path]::GetTempPath()) $asset.name

    try {
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $installerPath -UseBasicParsing
        $process = Start-Process -FilePath $installerPath -ArgumentList @(
            "/VERYSILENT",
            "/NORESTART",
            "/NOCANCEL",
            "/SP-",
            "/CURRENTUSER"
        ) -Wait -PassThru
        if ($process.ExitCode -ne 0) {
            throw "Git installer exited with code $($process.ExitCode)."
        }
    }
    finally {
        Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
    }
    Refresh-Path
}

if ($env:OS -ne "Windows_NT") {
    throw "This installer currently supports Windows only."
}

Write-Host "Interly installer" -ForegroundColor White
$python = Find-Python
if (-not $python) {
    Install-Python
    $python = Find-Python
}
if (-not $python) {
    throw "Python 3.11 or newer could not be installed or found."
}
Write-Host "Using Python $($python.Version)."
$pythonCommand = $python.Command
$pythonArguments = @($python.Arguments)

$git = Find-Git
if (-not $git) {
    Install-Git
    $git = Find-Git
}
if (-not $git) {
    throw "Git could not be installed or found."
}
Write-Host "Git is ready."

Write-Step "Installing pipx"
& $pythonCommand @pythonArguments -m pip install --user --upgrade pipx
if ($LASTEXITCODE -ne 0) {
    throw "pipx installation failed."
}
& $pythonCommand @pythonArguments -m pipx ensurepath
if ($LASTEXITCODE -ne 0) {
    throw "pipx PATH configuration failed."
}

Write-Step "Installing Interly"
& $pythonCommand @pythonArguments -m pipx install --force $InterlySpec
if ($LASTEXITCODE -ne 0) {
    throw "Interly installation failed."
}

$interlyPath = $null
$interly = Get-Command interly -ErrorAction SilentlyContinue
if (-not $interly) {
    $pipxBin = & $pythonCommand @pythonArguments -m pipx environment --value PIPX_BIN_DIR
    $candidate = Join-Path $pipxBin.Trim() "interly.exe"
    if (Test-Path $candidate) {
        $interlyPath = $candidate
    }
}
else {
    $interlyPath = $interly.Source
}
if (-not $interlyPath) {
    throw "Interly installed, but interly.exe could not be found. Open a new terminal and run interly."
}

Write-Step "Installation verified. Launching Interly"
& $interlyPath
