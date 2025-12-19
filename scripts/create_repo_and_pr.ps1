try {
  $body = @{ name='xnor-chat-program'; description='XNOR Chat Service'; private=$false } | ConvertTo-Json -Depth 4
  Write-Host "Creating repo..."
  $resp = Invoke-RestMethod -Uri 'https://api.github.com/user/repos' -Method Post -Headers @{ Authorization = "token $env:GITHUB_TOKEN"; Accept = 'application/vnd.github+json' } -Body $body -ContentType 'application/json' -ErrorAction Stop
  Write-Host "Created repo:" $resp.html_url
  git remote add origin "https://x-access-token:$env:GITHUB_TOKEN@github.com/BOBZERO-afk/xnor-chat-program.git"
  git push -u origin fix/installer-and-style
  git remote set-url origin https://github.com/BOBZERO-afk/xnor-chat-program.git
  Write-Host "Pushed branch."
  Write-Host "Creating PR..."
  $pr_body = Get-Content pr_body.md -Raw
  $json = @{ title='fix: lint/tests/docs & NSIS checksum + installer improvements'; head='fix/installer-and-style'; base='main'; body=$pr_body } | ConvertTo-Json -Depth 6
  $pr = Invoke-RestMethod -Uri 'https://api.github.com/repos/BOBZERO-afk/xnor-chat-program/pulls' -Method Post -Headers @{ Authorization = "token $env:GITHUB_TOKEN"; Accept = 'application/vnd.github+json' } -Body $json -ContentType 'application/json' -ErrorAction Stop
  Write-Host "PR created:" $pr.html_url
} catch {
  Write-Host "Error:" $_.Exception.Message
} finally {
  Remove-Item Env:\GITHUB_TOKEN -ErrorAction SilentlyContinue
  Write-Host "Removed GITHUB_TOKEN from session."
}