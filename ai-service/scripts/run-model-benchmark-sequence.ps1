param(
    [string]$Endpoint = "http://localhost:8200/v1/inference/fall-detection",
    [int]$WaitSeconds = 180,
    [int]$SamplePerClass = 2000,
    [switch]$ContinueOnError
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Set-EnvValue {
    param(
        [string[]]$Lines,
        [string]$Key,
        [string]$Value
    )

    $updated = $false
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i] -match "^\s*$([regex]::Escape($Key))\s*=") {
            $Lines[$i] = "$Key=$Value"
            $updated = $true
            break
        }
    }

    if (-not $updated) {
        $Lines += "$Key=$Value"
    }

    return ,$Lines
}

function Update-EnvForModel {
    param(
        [string]$EnvPath,
        [hashtable]$Model
    )

    $lines = [System.Collections.Generic.List[string]]::new()
    foreach ($line in [System.IO.File]::ReadAllLines($EnvPath)) {
        [void]$lines.Add($line)
    }

    $linesArray = $lines.ToArray()
    $linesArray = Set-EnvValue -Lines $linesArray -Key "MODEL_NAME" -Value $Model.ModelName
    $linesArray = Set-EnvValue -Lines $linesArray -Key "MODEL_REPO" -Value $Model.ModelRepo
    $linesArray = Set-EnvValue -Lines $linesArray -Key "MODEL_DIR" -Value "/app/model"
    $linesArray = Set-EnvValue -Lines $linesArray -Key "MODEL_FILE" -Value $Model.ModelFile
    $linesArray = Set-EnvValue -Lines $linesArray -Key "MODEL_PATH" -Value "/app/model/$($Model.ModelFile)"
    $linesArray = Set-EnvValue -Lines $linesArray -Key "MMPROJ_FILE" -Value $Model.MMProjFile
    $linesArray = Set-EnvValue -Lines $linesArray -Key "MMPROJ_PATH" -Value "/app/model/$($Model.MMProjFile)"

    [System.IO.File]::WriteAllLines($EnvPath, $linesArray, [System.Text.UTF8Encoding]::new($false))
}

function Invoke-Step {
    param(
        [string]$WorkingDir,
        [hashtable]$Model,
        [string]$Falling0Dir,
        [string]$Falling1Dir
    )

    Write-Host ""
    Write-Host "============================================================"
    Write-Host "Model: $($Model.ModelName)"
    Write-Host "Test : $($Model.TestScript)"
    Write-Host "============================================================"

    $envPath = Join-Path $WorkingDir ".env"
    Update-EnvForModel -EnvPath $envPath -Model $Model
    Write-Host ".env updated."

    Push-Location $WorkingDir
    try {
        Write-Host "docker compose down"
        docker compose down

        Write-Host "docker compose up -d --build"
        docker compose up -d --build

        Wait-ForAiServiceHealth -TimeoutSeconds $WaitSeconds

        Write-Host "Starting Python test..."
        $cmd = @(
            "python",
            $Model.TestScript,
            "--endpoint", $Endpoint,
            "--falling-0-dir", $Falling0Dir,
            "--falling-1-dir", $Falling1Dir
        )
        & $cmd[0] $cmd[1] $cmd[2] $cmd[3] $cmd[4] $cmd[5] $cmd[6] $cmd[7]
        if ($LASTEXITCODE -ne 0) {
            throw "Test failed: $($Model.TestScript) (exit=$LASTEXITCODE)"
        }
    }
    finally {
        Pop-Location
    }
}

function Wait-ForAiServiceHealth {
    param(
        [int]$TimeoutSeconds
    )

    $healthUrl = "http://localhost:8200/health"
    $pollIntervalSeconds = 2
    $startedAt = Get-Date
    $deadline = $startedAt.AddSeconds($TimeoutSeconds)

    Write-Host "Waiting for AI service health (timeout: $TimeoutSeconds sec)..."

    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $healthUrl -Method Get -TimeoutSec 5 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                $elapsedSeconds = [math]::Round(((Get-Date) - $startedAt).TotalSeconds, 1)
                Write-Host "Health OK received ($elapsedSeconds sec). Proceeding to test."
                return
            }
        }
        catch {
            # Service may not be up yet; polling continues.
        }

        Start-Sleep -Seconds $pollIntervalSeconds
    }

    throw "AI service health timeout: 200 OK was not received within $TimeoutSeconds sec ($healthUrl)."
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $repoRoot ".env"
if (-not (Test-Path $envFile)) {
    throw ".env not found: $envFile"
}
if ($SamplePerClass -le 0) {
    throw "SamplePerClass must be greater than 0."
}

$datasetRoot = Join-Path $repoRoot "tests/dataset"
$falling0Source = Join-Path $datasetRoot "falling_0"
$falling1Source = Join-Path $datasetRoot "falling_1"
if (-not (Test-Path $falling0Source)) {
    throw "Dataset not found: $falling0Source"
}
if (-not (Test-Path $falling1Source)) {
    throw "Dataset not found: $falling1Source"
}

$allowedExtensions = @(".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff")
$falling0Files = @(Get-ChildItem -Path $falling0Source -File | Where-Object { $allowedExtensions -contains $_.Extension.ToLowerInvariant() })
$falling1Files = @(Get-ChildItem -Path $falling1Source -File | Where-Object { $allowedExtensions -contains $_.Extension.ToLowerInvariant() })

if ($falling0Files.Count -lt $SamplePerClass) {
    throw "Not enough files for falling_0. Required=$SamplePerClass, available=$($falling0Files.Count)"
}
if ($falling1Files.Count -lt $SamplePerClass) {
    throw "Not enough files for falling_1. Required=$SamplePerClass, available=$($falling1Files.Count)"
}

$selected0 = @($falling0Files | Get-Random -Count $SamplePerClass)
$selected1 = @($falling1Files | Get-Random -Count $SamplePerClass)

$sampleRoot = Join-Path $repoRoot "tests/dataset/_benchmark_random_sample"
$sample0Dir = Join-Path $sampleRoot "falling_0"
$sample1Dir = Join-Path $sampleRoot "falling_1"

if (Test-Path $sampleRoot) {
    Remove-Item -Path $sampleRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $sample0Dir -Force | Out-Null
New-Item -ItemType Directory -Path $sample1Dir -Force | Out-Null

foreach ($file in $selected0) {
    Copy-Item -Path $file.FullName -Destination (Join-Path $sample0Dir $file.Name) -Force
}
foreach ($file in $selected1) {
    Copy-Item -Path $file.FullName -Destination (Join-Path $sample1Dir $file.Name) -Force
}

Write-Host "Random sample created: class0=$($selected0.Count), class1=$($selected1.Count), total=$($selected0.Count + $selected1.Count)"
Write-Host "Sample folder: $sampleRoot"

$sequence = @(
    @{
        ModelName  = "smolvlm2-256m-video-instruct-q8"
        ModelRepo  = "ggml-org/SmolVLM2-256M-Video-Instruct-GGUF"
        ModelFile  = "SmolVLM2-256M-Video-Instruct-Q8_0.gguf"
        MMProjFile = "mmproj-SmolVLM2-256M-Video-Instruct-Q8_0.gguf"
        TestScript = "tests/smolvlm2-256m-video-q8-same_model_test/test_image.py"
    },
    @{
        ModelName  = "smolvlm2-256m-video-instruct-q8"
        ModelRepo  = "ggml-org/SmolVLM2-256M-Video-Instruct-GGUF"
        ModelFile  = "SmolVLM2-256M-Video-Instruct-Q8_0.gguf"
        MMProjFile = "mmproj-SmolVLM2-256M-Video-Instruct-f16.gguf"
        TestScript = "tests/smolvlm2-256m-video-q8-fp16_model_test/test_image.py"
    },
    @{
        ModelName  = "smolvlm2-256m-video-instruct-f16"
        ModelRepo  = "ggml-org/SmolVLM2-256M-Video-Instruct-GGUF"
        ModelFile  = "SmolVLM2-256M-Video-Instruct-f16.gguf"
        MMProjFile = "mmproj-SmolVLM2-256M-Video-Instruct-f16.gguf"
        TestScript = "tests/smolvlm2-256m-video-f16-same_model_test/test_image.py"
    },
    @{
        ModelName  = "smolvlm2-500m-video-instruct-q8"
        ModelRepo  = "ggml-org/SmolVLM2-500M-Video-Instruct-GGUF"
        ModelFile  = "SmolVLM2-500M-Video-Instruct-Q8_0.gguf"
        MMProjFile = "mmproj-SmolVLM2-500M-Video-Instruct-Q8_0.gguf"
        TestScript = "tests/smolvlm2-500m-video-q8-same_model_test/test_image.py"
    },
    @{
        ModelName  = "smolvlm2-500m-video-instruct-q8"
        ModelRepo  = "ggml-org/SmolVLM2-500M-Video-Instruct-GGUF"
        ModelFile  = "SmolVLM2-500M-Video-Instruct-Q8_0.gguf"
        MMProjFile = "mmproj-SmolVLM2-500M-Video-Instruct-f16.gguf"
        TestScript = "tests/smolvlm2-500m-video-q8-fp16_model_test/test_image.py"
    },
    @{
        ModelName  = "smolvlm2-500m-video-instruct-f16"
        ModelRepo  = "ggml-org/SmolVLM2-500M-Video-Instruct-GGUF"
        ModelFile  = "SmolVLM2-500M-Video-Instruct-f16.gguf"
        MMProjFile = "mmproj-SmolVLM2-500M-Video-Instruct-f16.gguf"
        TestScript = "tests/smolvlm2-500m-video-f16-same_model_test/test_image.py"
    }
)

foreach ($model in $sequence) {
    try {
        Invoke-Step -WorkingDir $repoRoot -Model $model -Falling0Dir $sample0Dir -Falling1Dir $sample1Dir
    }
    catch {
        Write-Error $_
        if (-not $ContinueOnError) {
            throw
        }
    }
}

Write-Host ""
Write-Host "All model runs completed."
