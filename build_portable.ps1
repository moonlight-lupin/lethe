# Builds the portable, no-install distribution of the De-identifier.
# Produces dist\DeIdentifier-Portable\ (a self-contained folder with its own
# Python) and dist\DeIdentifier-Portable.zip for distribution.
#
# Run from the project root:   powershell -ExecutionPolicy Bypass -File build_portable.ps1
# Requires internet on THIS machine (to fetch Python + packages). The resulting
# bundle needs no internet, no admin rights, and no Python on the target PC.

# The project standardises on Python 3.13 (spaCy/Presidio have no 3.14 wheels).
# $WithNLP = $true  -> bundle the Presidio + spaCy suggestion engine (~143 MB zip)
# $WithNLP = $false -> lean build, regex suggester only (~102 MB zip), still 3.13
$WithNLP = $true

$ErrorActionPreference = "Stop"
$PyVer   = "3.13.2"
$proj    = $PSScriptRoot
$distRoot= Join-Path $proj "dist"
$dist    = Join-Path $distRoot "DeIdentifier-Portable"
$runtime = Join-Path $dist "runtime"
$appFiles= @("app.py")              # root entry point; engine lives in the lethe\ package

Write-Host "1/6  Resetting build folder..."
if (Test-Path $dist) { Remove-Item -LiteralPath $dist -Recurse -Force }
New-Item -ItemType Directory -Force -Path $runtime | Out-Null

Write-Host "2/6  Downloading embeddable Python $PyVer..."
$arch = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "arm64" } else { "amd64" }
$zip  = Join-Path $distRoot "_embed.zip"
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/$PyVer/python-$PyVer-embed-$arch.zip" -OutFile $zip -UseBasicParsing
Expand-Archive -Path $zip -DestinationPath $runtime -Force
Remove-Item -LiteralPath $zip -Force

Write-Host "3/6  Enabling site-packages + bootstrapping pip..."
$pthName = (Get-ChildItem -LiteralPath $runtime -Filter "python*._pth" | Select-Object -First 1).Name
@"
$($pthName -replace '\._pth$','.zip')
.
Lib\site-packages

import site
"@ | Set-Content -Path (Join-Path $runtime $pthName) -Encoding ASCII
New-Item -ItemType Directory -Force -Path (Join-Path $runtime "Lib\site-packages") | Out-Null
$py = Join-Path $runtime "python.exe"
Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile (Join-Path $runtime "get-pip.py") -UseBasicParsing
& $py (Join-Path $runtime "get-pip.py") --no-warn-script-location | Out-Null

Write-Host "4/6  Installing dependencies into the bundle (this is the slow part)..."
& $py -m pip install --no-warn-script-location -r (Join-Path $proj "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
if ($WithNLP) {
  Write-Host "      + NLP engine (Presidio + spaCy + small model)..."
  & $py -m pip install --no-warn-script-location -r (Join-Path $proj "requirements-nlp.txt")
  if ($LASTEXITCODE -ne 0) { throw "pip install (NLP) failed" }
}

Write-Host "5/6  Copying app code + launcher + config..."
foreach ($f in $appFiles) { Copy-Item (Join-Path $proj $f) (Join-Path $dist $f) -Force }
# Ship the engine package (core, docio, vault, store, nlp_suggester). Tests and
# tools are dev-only and deliberately not bundled.
$pkg = Join-Path $proj "lethe"
if (Test-Path $pkg) {
  Copy-Item $pkg (Join-Path $dist "lethe") -Recurse -Force
  Get-ChildItem -Recurse -Directory -Filter "__pycache__" (Join-Path $dist "lethe") |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}
# Launcher, README and .streamlit\config.toml are kept under dist\_assets so they
# survive a rebuild. If they don't exist yet, this build assumes you've created
# them once (see the originals committed alongside this script).
$assets = Join-Path $distRoot "_assets"
if (Test-Path $assets) { Copy-Item (Join-Path $assets "*") $dist -Recurse -Force }
# Ship the sample test files (docx/pdf/xlsx) so users can try the formats.
$samples = Join-Path $proj "samples"
if (Test-Path $samples) { Copy-Item $samples (Join-Path $dist "samples") -Recurse -Force }
# Ship the web theme assets (Cinzel wordmark font + favicon) so the reskin
# renders identically in the portable build — app.py serves these from /static.
$webStatic = Join-Path $proj "web_static"
if (Test-Path $webStatic) { Copy-Item $webStatic (Join-Path $dist "web_static") -Recurse -Force }
# OPTIONAL: pre-seed the firm's shared counterparty list so every teammate
# starts with it. Drop a prepared entities.json next to this script to include it.
if (Test-Path (Join-Path $proj "entities.shared.json")) {
  Copy-Item (Join-Path $proj "entities.shared.json") (Join-Path $dist "entities.json") -Force
  Write-Host "      (seeded shared entities.json)"
}

Write-Host "6/6  Cleaning + zipping..."
Remove-Item -LiteralPath (Join-Path $runtime "get-pip.py") -Force -ErrorAction SilentlyContinue
Get-ChildItem -LiteralPath $dist -Recurse -Directory -Filter "__pycache__" | ForEach-Object {
  Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
$out = Join-Path $distRoot "DeIdentifier-Portable.zip"
Remove-Item -LiteralPath $out -Force -ErrorAction SilentlyContinue
Compress-Archive -Path $dist -DestinationPath $out -CompressionLevel Optimal

$mb = [math]::Round((Get-Item -LiteralPath $out).Length/1MB)
Write-Host "DONE.  $out  ($mb MB)" -ForegroundColor Green
