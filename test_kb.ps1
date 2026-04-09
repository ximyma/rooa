$base = 'http://127.0.0.1:5000'
$sv = New-Object Microsoft.PowerShell.Commands.WebRequestSession

# Login first
$loginResp = Invoke-WebRequest -Uri "$base/login" -UseBasicParsing -SessionVariable sv -TimeoutSec 5
# Try to login with admin credentials
$loginData = @{
    username = 'admin'
    password = 'admin123'
}
try {
    $postResp = Invoke-WebRequest -Uri "$base/login" -Method POST -Body $loginData -UseBasicParsing -WebSession $sv -TimeoutSec 5
    Write-Host "Login status: $($postResp.StatusCode)"
} catch {
    Write-Host "Login error: $($_.Exception.Message)"
}

Start-Sleep 1

# Test routes
$routes = @(
    '/knowledge/personal',
    '/knowledge/api/search_page',
    '/knowledge/my_favorites',
    '/knowledge/recent',
    '/knowledge/shared'
)
foreach ($r in $routes) {
    try {
        $code = (Invoke-WebRequest -Uri ($base+$r) -WebSession $sv -TimeoutSec 5 -UseBasicParsing).StatusCode
        Write-Host "$r : $code"
    } catch {
        Write-Host "$r : ERROR"
    }
}
