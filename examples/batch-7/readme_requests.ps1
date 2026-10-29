param([Parameter(Mandatory=$true)][uri]$BaseUrl, [Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference = 'Stop'
if (-not $BaseUrl.IsLoopback) { throw 'Only loopback verification is allowed' }
if (Test-Path -LiteralPath $Output) { throw 'Choose a new output file to preserve previous evidence' }
$base = $BaseUrl.AbsoluteUri.TrimEnd('/')
$health = Invoke-RestMethod "$base/health"
$session = Invoke-RestMethod -Method Post -Uri "$base/sessions" -ContentType 'application/json' -Body '{}'
$id = $session.session_id
$body = @{ question = '星帆剪辑支持什么导出格式？' } | ConvertTo-Json -Compress
$first = Invoke-RestMethod -Method Post -Uri "$base/sessions/$id/messages" -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
$body = @{ question = '那最高支持多大分辨率？' } | ConvertTo-Json -Compress
$second = Invoke-RestMethod -Method Post -Uri "$base/sessions/$id/messages" -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
$history = Invoke-RestMethod "$base/sessions/$id"
if ($first.status -ne 'answered' -or $second.status -ne 'answered' -or $history.messages.Count -ne 4) { throw 'README request verification failed' }
$invalidStatus = 0
try { Invoke-RestMethod -Method Post -Uri "$base/sessions/$id/messages" -ContentType 'application/json' -Body '{"question":""}' }
catch { $invalidStatus = [int]$_.Exception.Response.StatusCode }
$unknownStatus = 0
try { Invoke-RestMethod "$base/sessions/not-found" }
catch { $unknownStatus = [int]$_.Exception.Response.StatusCode }
if ($invalidStatus -ne 422 -or $unknownStatus -ne 404) { throw 'README error verification failed' }
$report = @{ mode='mock'; transport='PowerShell Invoke-RestMethod with UTF-8 bytes'; health=$health; created_session=$session; first=$first; second=$second; history=$history; invalid_question_status=$invalidStatus; unknown_session_status=$unknownStatus }
[IO.File]::WriteAllText($Output, ($report | ConvertTo-Json -Depth 100), (New-Object Text.UTF8Encoding $false))
Write-Output 'README PowerShell requests: 201/200/422/404 verified'
