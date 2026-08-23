param(
    [int]$Port = 8787
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $projectRoot

# A named per-user mutex prevents duplicate starts from multiple VS Code windows.
$mutex = [System.Threading.Mutex]::new($false, "AIProviderRouter")
$mutexOwned = $false
$scriptExitCode = 0

try {
    $mutexOwned = $mutex.WaitOne(0)
    if (-not $mutexOwned) {
        Write-Output ('{"status":"already_starting_or_running","base_url":"http://127.0.0.1:' + $Port + '/v1"}')
    } else {
        $healthUri = "http://127.0.0.1:$Port/health"
        $headers = @{}
        if ($env:AI_ROUTER_LOCAL_API_KEY) {
            $headers["Authorization"] = "Bearer $($env:AI_ROUTER_LOCAL_API_KEY)"
        }

        $alreadyHealthy = $false
        try {
            $health = Invoke-RestMethod -Uri $healthUri -Headers $headers -Method Get -TimeoutSec 3
            $alreadyHealthy = ($health.status -eq "ok")
        } catch {
            # No healthy local server is running; start one below.
        }

        if ($alreadyHealthy) {
            Write-Output ('{"status":"listening","base_url":"http://127.0.0.1:' + $Port + '/v1","already_running":true}')
        } else {
            $routerExecutable = Join-Path $projectRoot ".venv\Scripts\ai-router.exe"
            if (-not (Test-Path $routerExecutable)) {
                throw "ai-provider-router executable was not found at $routerExecutable. Create the project virtual environment and install the package first."
            }

            & $routerExecutable --config-dir (Join-Path $projectRoot "config") --state-db (Join-Path $projectRoot "data\ai_router.db") serve --host 127.0.0.1 --port $Port
            $scriptExitCode = $LASTEXITCODE
        }
    }
} finally {
    if ($mutexOwned) {
        $mutex.ReleaseMutex()
    }
    $mutex.Dispose()
}

exit $scriptExitCode
