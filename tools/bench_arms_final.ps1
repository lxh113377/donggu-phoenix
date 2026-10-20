# bench_arms_final.ps1 - fair two-arm benchmark (direct binaries, named sessions, era-common syntax).
# old arm = 0.31.1 local prefix bin (npx cold-parse pitfall removed); new arm = global 0.39.1.
# SERIAL: no other agent-browser activity while running.
$env:npm_config_userconfig = 'NUL'
$OLD = 'C:\Users\37533\Desktop\workspace\' + [char]0x9879 + [char]0x76EE + [char]0x65B0 + [char]0x5EFA + [char]0x6587 + [char]0x4EF6 + [char]0x5939 + '\_skill_audit\old_ab\node_modules\.bin\agent-browser.cmd'
$OUT = Split-Path $OLD | Split-Path | Split-Path
$script:Bin = ''; $script:Sess = ''
function AB { param([string[]]$a) & $script:Bin @a 2>&1 | Out-String -Width 4096 }   # DEFAULT session both arms: fully symmetric command shape (r6: 0.31.1 named session proven non-durable cross-process -> default-session is the fair form)
function RunTask([string]$name, [scriptblock]$body) {
  $pass = 0; $tries = 0
  while ($tries -lt 2 -and $pass -eq 0) {
    $tries++
    $r = & $body
    if ($r) { $pass = 1 }
    Write-Output ($script:Tag + ' ' + $name + ' try' + $tries + ' -> ' + $pass)
  }
  return [pscustomobject]@{ task = $name; pass = $pass; first_try = [int]($pass -eq 1 -and $tries -eq 1); rounds = [int]$(if ($pass -eq 1) { $tries } else { 2 }) }
}
$script:Rows = @()
function Arm([string]$tag, [string]$bin, [string]$sess) {
  $script:Tag = $tag; $script:Bin = $bin; $script:Sess = $sess
  $rows = @()
  $rows += RunTask 'T01 open+title' { (AB @('open','https://lxh113377.github.io')).Contains([char]0x2713) -and (AB @('get','title')).Trim().Length -gt 0 }
  $rows += RunTask 'T02 snapshot-refs' { $s = AB @('snapshot','-i'); ([regex]::Matches($s, 'ref=ed+')).Count -ge 5 }
  $rows += RunTask 'T03 click-dyn-ref' { $s = AB @('snapshot','-i'); $m = [regex]::Matches($s, 'ref=(ed+)'); if ($m.Count -lt 3) { return $false }; $ref = '@' + $m[1].Groups[1].Value; (AB @('click', $ref)).Contains([char]0x2713) }
  $rows += RunTask 'T04 get-url' { (AB @('get','url')).Trim().StartsWith('http') }
  $rows += RunTask 'T05 eval-js' { $o = AB @('eval', "document.querySelectorAll('button').length"); $o.Trim() -match '^d+$' }
  $rows += RunTask 'T06 wiki-navigate' { (AB @('open','https://en.wikipedia.org/wiki/Web_archiving')).Contains([char]0x2713) -and (AB @('get','title')).Contains('archiving') }
  $rows += RunTask 'T07 screenshot' { $f = Join-Path $env:TEMP ($tag + '_t07.png'); [void](AB @('screenshot', $f)); (Test-Path $f) -and ((Get-Item $f).Length -gt 1000) }
  $rows += RunTask 'T08 pdf-export' { $f = Join-Path $env:TEMP ($tag + '_t08.pdf'); [void](AB @('pdf', $f)); (Test-Path $f) -and ((Get-Item $f).Length -gt 1000) }
  $rows += RunTask 'T09 network-requests' { (AB @('network','requests')).Length -ge 0 }
  $rows += RunTask 'T10 cookies' { (AB @('cookies')).Length -ge 0 }
  [void](AB @('close','--all'))
  return $rows
}
agent-browser close --all 2>&1 | Out-Null
[void](& 'agent-browser' 'close' '--all' 2>&1)
$newRows = Arm 'NEW-0.39.1' 'agent-browser' 'unused'
Start-Sleep -Seconds 3
[void](AB @())
& $OLD close --all 2>&1 | Out-Null
$oldRows = Arm 'OLD-0.31.1' $OLD 'unused'
$utf8 = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText((Join-Path $OUT 'bench_arm_new.json'), (ConvertTo-Json @($newRows) -Depth 3), $utf8)
[IO.File]::WriteAllText((Join-Path $OUT 'bench_arm_old.json'), (ConvertTo-Json @($oldRows) -Depth 3), $utf8)
python (Join-Path (Split-Path $OUT) '..\tools\run_bench.py') --tasks (Join-Path $OUT 'bench_arm_new.json') --baseline (Join-Path $OUT 'bench_arm_old.json') --out (Join-Path $OUT 'q_gate_final.json')
Write-Output ('GATE_RC=' + $LASTEXITCODE)
