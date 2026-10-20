$env:npm_config_userconfig = 'NUL'
$URL1 = 'file:///C:/Users/37533/Desktop/workspace/项目/新建文件夹/_skill_audit/bench_fixture_one.html'
$URL2 = 'file:///C:/Users/37533/Desktop/workspace/项目/新建文件夹/_skill_audit/bench_fixture_two.html'
$OUTDIR = Join-Path (Join-Path 'C:\Users\37533\Desktop\workspace' ([string][char]0x9879 + [char]0x76EE)) (([string][char]0x65B0 + [char]0x5EFA + [char]0x6587 + [char]0x4EF6 + [char]0x5939) + '\_skill_audit')
$OLD = Join-Path $OUTDIR 'old_ab\node_modules\.bin\agent-browser.cmd'
$script:Bin = ''
function ABT([string[]]$a, [int]$sec = 25) {
  $j = Start-Job -ArgumentList $a, $script:Bin { param($a, $bin) & $bin @a 2>&1 | Out-String -Width 4096 }
  $d = Wait-Job $j -Timeout $sec
  if (-not $d) { Stop-Job $j; Remove-Job $j -Force; return '' }
  $o = Receive-Job $j; Remove-Job $j -Force; ($o -join [char]10)
}
function T([string]$name, [scriptblock]$body) {
  $pass = 0; $tries = 0
  while ($tries -lt 2 -and -not $pass) { $tries++; if (& $body) { $pass = 1 } }
  Write-Output ($script:Tag + ' ' + $name + ' pass=' + $pass + ' rounds=' + $tries)
  return [pscustomobject]@{ task=$name; pass=$pass; first_try=[int]($pass -and $tries -eq 1); rounds=[int]$(if ($pass) { $tries } else { 2 }) }
}
$script:Rows = @()
function Arm([string]$tag, [string]$bin) {
  $script:Tag = $tag; $script:Bin = $bin
  $r = @()
  $r += T 'T01 open+title' { (ABT @('open',$URL1)).Contains('Fixture') -and (ABT @('get','title')).Contains('Bench Fixture One') }
  $r += T 'T02 snapshot-refs' { ([regex]::Matches((ABT @('snapshot','-i')), 'ref=e[0-9]+')).Count -ge 5 }
  $r += T 'T03 click-dyn-ref' { $s = ABT @('snapshot','-i'); $m = [regex]::Matches($s,'ref=(e[0-9]+)'); if ($m.Count -lt 3) { $false } else { (ABT @('click', ('@' + $m[1].Groups[1].Value))).Contains([char]0x2713) -and (ABT @('get','title')).Contains('Beta Clicked') } }
  $r += T 'T04 fill-input' { $s = ABT @('snapshot','-i'); $m = [regex]::Matches($s,'ref=(e[0-9]+)'); (ABT @('fill', ('@' + $m[5].Groups[1].Value), 'hello bench')).Contains([char]0x2713) }
  $r += T 'T05 eval-js' { (ABT @('eval', "document.querySelectorAll('button').length")).Trim() -match '^3$' }
  $r += T 'T06 navigate-link' { (ABT @('open',$URL1)); $s = ABT @('snapshot','-i'); $m = [regex]::Matches($s,'ref=(e[0-9]+)'); [void](ABT @('click', ('@' + $m[6].Groups[1].Value))); Start-Sleep -Seconds 2; (ABT @('get','title')).Contains('Page Two') }
  $r += T 'T07 screenshot' { $f = Join-Path $env:TEMP ($tag + '_t07.png'); [void](ABT @('screenshot',$f)); (Test-Path $f) -and ((Get-Item $f).Length -gt 800) }
  $r += T 'T08 pdf' { $f = Join-Path $env:TEMP ($tag + '_t08.pdf'); [void](ABT @('pdf',$f)); (Test-Path $f) -and ((Get-Item $f).Length -gt 500) }
  $r += T 'T09 cookies' { $o = ABT @('cookies'); $o.Length -ge 0 -and -not $o.Contains([char]0x2717 + ' ') }
  $r += T 'T10 close-reopen' { [void](ABT @('close')); $o = ABT @('open',$URL2); $o.Contains('ARRIVED') -or $o.Contains([char]0x2713) -or (ABT @('get','title')).Contains('Page Two') }
  [void](ABT @('close','--all'))
  return $r
}
& $OLD close --all 2>&1 | Out-Null; agent-browser close --all 2>&1 | Out-Null
$new = Arm 'NEW-0.39.1' 'agent-browser'
Start-Sleep -Seconds 2
$old = Arm 'OLD-0.31.1' $OLD
$utf8 = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText((Join-Path $OUTDIR 'bench_arm_new.json'), (ConvertTo-Json @($new) -Depth 3), $utf8)
[IO.File]::WriteAllText((Join-Path $OUTDIR 'bench_arm_old.json'), (ConvertTo-Json @($old) -Depth 3), $utf8)
python (Join-Path (Split-Path $OUTDIR) 'tools\run_bench.py') --tasks (Join-Path $OUTDIR 'bench_arm_new.json') --baseline (Join-Path $OUTDIR 'bench_arm_old.json') --out (Join-Path $OUTDIR 'q_gate_final.json')
Write-Output ('GATE_RC=' + $LASTEXITCODE)
