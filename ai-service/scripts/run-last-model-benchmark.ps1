param(
    [string]$Endpoint = "http://localhost:8200/v1/inference/fall-detection",
    [int]$WaitSeconds = 300  # Increased timeout for F16
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Set-EnvValue {
    param([string[]]$Lines, [string]$Key, [string]$Value)
    $updated = $false
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i] -match "^\s*$([regex]::Escape($Key))\s*=") {
            $Lines[$i] = "$Key=$Value"
            $updated = $true
            break
        }
    }
    if (-not $updated) { $Lines += "$Key=$Value" }
    return ,$Lines
}

function Update-EnvForModel {
    param([string]$EnvPath, [hashtable]$Model)
    $lines = [System.Collections.Generic.List[string]]::new()
    foreach ($line in [System.IO.File]::ReadAllLines($EnvPath)) { [void]$lines.Add($line) }
    $linesArray = $lines.ToArray()
    $linesArray = Set-EnvValue -Lines $linesArray -Key "MODEL_NAME" -Value $Model.ModelName
    $linesArray = Set-EnvValue -Lines $linesArray -Key "MODEL_REPO" -Value $Model.ModelRepo
    $linesArray = Set-EnvValue -Lines $linesArray -Key "MODEL_FILE" -Value $Model.ModelFile
    $linesArray = Set-EnvValue -Lines $linesArray -Key "MODEL_PATH" -Value "/app/model/$($Model.ModelFile)"
    $linesArray = Set-EnvValue -Lines $linesArray -Key "MMPROJ_FILE" -Value $Model.MMProjFile
    $linesArray = Set-EnvValue -Lines $linesArray -Key "MMPROJ_PATH" -Value "/app/model/$($Model.MMProjFile)"
    [System.IO.File]::WriteAllLines($EnvPath, $linesArray, [System.Text.UTF8Encoding]::new($false))
}

function Wait-ForAiServiceHealth {
    param([int]$TimeoutSeconds)
    $healthUrl = "http://localhost:8200/health"
    $pollIntervalSeconds = 5
    $startedAt = Get-Date
    $deadline = $startedAt.AddSeconds($TimeoutSeconds)
    Write-Host "Waiting for AI service health (timeout: $TimeoutSeconds sec)..."
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $healthUrl -Method Get -TimeoutSec 5 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Host "Health OK received. Proceeding to test."
                return
            }
        } catch { }
        Start-Sleep -Seconds $pollIntervalSeconds
    }
    throw "AI service health timeout: 200 OK was not received within $TimeoutSeconds sec."
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $repoRoot ".env"
$sampleRoot = Join-Path $repoRoot "tests/dataset/_benchmark_random_sample"
$sample0Dir = Join-Path $sampleRoot "falling_0"
$sample1Dir = Join-Path $sampleRoot "falling_1"

if (-not (Test-Path $sampleRoot)) {
    throw "ERROR: Existing sample folder not found: $sampleRoot. Please run the main script at least once."
}

$lastModel = @{
    ModelName  = "smolvlm2-500m-video-instruct-f16"
    ModelRepo  = "ggml-org/SmolVLM2-500M-Video-Instruct-GGUF"
    ModelFile  = "SmolVLM2-500M-Video-Instruct-f16.gguf"
    MMProjFile = "mmproj-SmolVLM2-500M-Video-Instruct-f16.gguf"
    TestScript = "tests/smolvlm2-500m-video-f16-same_model_test/test_image.py"
}

Write-Host "`n>>> RESUME FROM LAST POINT: FINAL MODEL TEST <<<"
Update-EnvForModel -EnvPath $envFile -Model $lastModel

Push-Location $repoRoot
try {
    Write-Host "docker compose down"
    docker compose down
    Write-Host "docker compose up -d --build"
    docker compose up -d --build
    Wait-ForAiServiceHealth -TimeoutSeconds $WaitSeconds
    Write-Host "Starting Python test (Final Model)..."
    python $lastModel.TestScript --endpoint $Endpoint --falling-0-dir $sample0Dir --falling-1-dir $sample1Dir
} finally {
    Pop-Location
}

Write-Host "`nFinal model test completed."
