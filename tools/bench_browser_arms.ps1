# bench_browser_arms.ps1 - two-arm browser benchmark (new direct-binary named-session vs old pinned npx default session).
# Measured traps encoded: (1) npx eats --session -> old arm uses default session, serial chain.
# (2) PS5.1 Set-Content -Encoding utf8 writes BOM -> use [IO.File]::WriteAllText (UTF8 no BOM).
# (3) keep $rows pure: logs via Write-Host only.
# (4) SERIAL ONLY: never run this while any other agent-browser session is active (measured 2026-10-20: concurrent fair-T03 test poisoned NEW arm T02-T10 pass=0). Close-all before AND between arms.
$ErrorActionPreference = 'Continue'
$env:npm_config_userconfig = 'NUL'
$repo = Join-Path (Join-Path 'C:\Users\37533\Desktop\workspace' ([string][char]0x9879 + [string][char]0x76EE)) ([string][char]0x65B0 + [string][char]0x5EFA + [string][char]0x6587 + [string][char]0x4EF6 + [string][char]0x5939)
$outDir = Join-Path $repo '_skill_audit'

$script:Sid = ''
function Invoke-New([string[]]$a) { $full = @('--session', $script:Sid) + $a; & agent-browser @full 2>&1 | Out-String -Width 4096 }
function Invoke-Old([string[]]$a) { & npx -y -p agent-browser@0.31.1 agent-browser @a 2>&1 | Out-String -Width 4096 }

$taskDefs = @(
  @{ Name='T01 open+title'; Steps=@(@(,'open','https://lxh113377.github.io'), @('get','title')) },
  @{ Name='T02 snapshot';   Steps=@(@('snapshot','-i')) },
  @{ Name='T04 url';        Steps=@(@('get','url')) },
  @{ Name='T05 eval';       Steps=@(@('eval',"document.querySelectorAll('button').length")) },
  @{ Name='T06 wiki';       Steps=@(@(,'open','https://en.wikipedia.org/wiki/Web_archiving'), @('snapshot','-i'), @('get','title')) },
  @{ Name='T07 screenshot'; Steps=@(@('screenshot',(Join-Path $env:TEMP 'arm_shot.png'))) },
  @{ Name='T08 pdf';        Steps=@(@('pdf',(Join-Path $env:TEMP 'arm_doc.pdf'))) },
  @{ Name='T09 network';    Steps=@(@('network','requests')) },
  @{ Name='T10 cookies';    Steps=@(@('cookies')) }
)

function RunArm([string]$label, [scriptblock]$exec) {
  $rows = @()
  foreach ($t in $taskDefs) {
    $pass = 0; $tries = 0
    while ($tries -lt 2 -and $pass -eq 0) {
      $tries++
      $ok = $true; $joined = ''
      foreach ($step in $t.Steps) {
        $o = & $exec $step
        $joined += $o
        if ($LASTEXITCODE -ne 0 -or $o -match 'Unknown cli config|not recognized|✗') { $ok = $false }
      }
      if ($ok -and $joined.Trim().Length -gt 0) { $pass = 1 }
    }
    $rt = [int]$(if ($pass -eq 1) { $tries } else { 2 })
    $rows += [pscustomobject]@{ task = $t.Name; pass = $pass; first_try = [int]($pass -eq 1 -and $tries -eq 1); rounds = $rt }
    Write-Host ($label + ' ' + $t.Name + ' pass=' + $pass + ' rounds=' + $tries)
  }
  return $rows
}

agent-browser close --all 2>&1 | Out-Null
$script:Sid = (agent-browser session id --scope worktree --prefix benchnew).Trim()
$newRows = RunArm 'NEW-0.39.1' { param($a) Invoke-New $a }
agent-browser --session $script:Sid close --all 2>&1 | Out-Null
$oldRows = RunArm 'OLD-0.31.1' { param($a) Invoke-Old $a }
agent-browser close --all 2>&1 | Out-Null

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText((Join-Path $outDir 'bench_arm_new.json'), (ConvertTo-Json @($newRows) -Depth 3), $utf8NoBom)
[IO.File]::WriteAllText((Join-Path $outDir 'bench_arm_old.json'), (ConvertTo-Json @($oldRows) -Depth 3), $utf8NoBom)
python (Join-Path $repo 'tools\run_bench.py') --tasks (Join-Path $outDir 'bench_arm_new.json') --baseline (Join-Path $outDir 'bench_arm_old.json') --out (Join-Path $outDir 'q_gate_fullarm.json')
exit $LASTEXITCODE
