$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$requiredFiles = @(
  "SKILL.md",
  "AGENTS.md",
  "brands.json",
  "vis-scoring-config.json",
  "vis-scoring-config-market.json",
  "products/recent.json",
  "brand-pulse-vis.html",
  "index.html"
)

function Fail($message) {
  Write-Host "FAILED: $message" -ForegroundColor Red
  exit 1
}

function Read-Json($path) {
  try {
    return Get-Content -Raw -Path $path -Encoding UTF8 | ConvertFrom-Json
  } catch {
    Fail "Invalid JSON: $path ($($_.Exception.Message))"
  }
}

# Check required files exist
foreach ($file in $requiredFiles) {
  $path = Join-Path $root $file
  if (-not (Test-Path $path)) {
    Fail "Missing required file: $file"
  }
}

# Validate brands.json
$brands = Read-Json (Join-Path $root "brands.json")
if (-not $brands.brands -or $brands.brands.Count -lt 10) {
  Fail "brands.json must contain monitored brands"
}

# Read HTML files
$htmlA = Get-Content -Raw -Path (Join-Path $root "brand-pulse-vis.html") -Encoding UTF8
$htmlB = Get-Content -Raw -Path (Join-Path $root "index.html") -Encoding UTF8

# Check window.lastUpdated consistency
$pattern = "window\.lastUpdated\s*=\s*'([^']+)'"
$matchA = [regex]::Match($htmlA, $pattern)
$matchB = [regex]::Match($htmlB, $pattern)
if (-not $matchA.Success -or -not $matchB.Success) {
  Fail "Both HTML files must define window.lastUpdated"
}
if ($matchA.Groups[1].Value -ne $matchB.Groups[1].Value) {
  Fail "window.lastUpdated mismatch between HTML files"
}

# ==================== FRONTEND SCRIPT SYNTAX CHECK ====================
function Test-HtmlScriptSyntax($htmlContent, $fileName) {
  # Extract all inline <script> blocks
  $scriptPattern = '<script>([\s\S]*?)</script>'
  $scripts = [regex]::Matches($htmlContent, $scriptPattern)

  $allJs = ""
  foreach ($m in $scripts) {
    $allJs += $m.Groups[1].Value + "`n"
  }

  if ([string]::IsNullOrWhiteSpace($allJs)) {
    Fail "No inline scripts found in $fileName"
  }

  # Check Node.js is available
  $nodeCmd = $null
  try {
    $nodeCmd = Get-Command "node" -ErrorAction Stop
  } catch {
    Write-Host "WARNING: Node.js not found in PATH. Skipping JavaScript syntax check for $fileName. Install Node.js to enable this check." -ForegroundColor Yellow
    return
  }

  # Use Node.js --check to validate syntax via temp file
  $tempFile = [System.IO.Path]::GetTempFileName() + ".js"
  try {
    [System.IO.File]::WriteAllText($tempFile, $allJs, [System.Text.Encoding]::UTF8)
    $nodeOutput = & node --check $tempFile 2>&1
    if ($LASTEXITCODE -ne 0) {
      Fail "JavaScript syntax error in $fileName`: $nodeOutput"
    }
  } finally {
    if (Test-Path $tempFile) { Remove-Item $tempFile -Force }
  }

  # Check required functions exist
  $requiredFunctions = @('switchSection', 'initializeDashboard', 'renderBrandList', 'applyViewStateAndRender')
  foreach ($func in $requiredFunctions) {
    if (-not ($allJs -match "function\s+$func\s*\(")) {
      Fail "Required function '$func' not found in $fileName"
    }
  }

  # Check data markers exist (post-refactor requirement)
  $requiredMarkers = @(
    '// <BRANDPULSE-DATA-BRANDS-START>',
    '// <BRANDPULSE-DATA-BRANDS-END>',
    '// <BRANDPULSE-DATA-PRODUCTS-START>',
    '// <BRANDPULSE-DATA-PRODUCTS-END>'
  )
  foreach ($marker in $requiredMarkers) {
    if (-not $htmlContent.Contains($marker)) {
      Fail "Required data marker '$marker' not found in $fileName"
    }
  }
}

# Run syntax checks on both HTML files
Test-HtmlScriptSyntax $htmlA "brand-pulse-vis.html"
Test-HtmlScriptSyntax $htmlB "index.html"
# ==================== END FRONTEND CHECK ====================

$runDate = [datetime]::ParseExact($matchA.Groups[1].Value.Substring(0, 10), "yyyy-MM-dd", $null)
$recent = @(Read-Json (Join-Path $root "products/recent.json") | ForEach-Object { $_ })
if ($recent.Count -eq 0) {
  Fail "products/recent.json must contain at least one entry or a no-signal entry"
}

$ids = @{}
$requiredProductFields = @(
  "id", "brand", "category", "title", "summary", "constraintChange",
  "time", "score", "confidence", "reviewStatus", "visBreakdown",
  "primarySource", "evidence", "tags", "createdAt", "updatedAt", "url",
  "source"
)

foreach ($product in $recent) {
  foreach ($field in $requiredProductFields) {
    if (-not ($product.PSObject.Properties.Name -contains $field)) {
      Fail "Product $($product.id) missing field: $field"
    }
  }

  if ($ids.ContainsKey($product.id)) {
    Fail "Duplicate product id: $($product.id)"
  }
  $ids[$product.id] = $true

  # visBreakdown check — split by source
  $productSource = if ($product.PSObject.Properties.Name -contains 'source') { [string]$product.source } else { 'vis' }
  if ($productSource -eq 'market') {
    # Market chain requires visualDiff in visBreakdown
    if (-not $product.visBreakdown.visualDiff -and $product.score -ne 0) {
      Fail "Product $($product.id) has incomplete visBreakdown (market source requires visualDiff)"
    }
  } else {
    # VIS chain requires recognition and diffusionPotential in visBreakdown (0 is valid)
    if ($null -eq $product.visBreakdown.recognition -and $product.score -ne 0) {
      Fail "Product $($product.id) has incomplete visBreakdown (missing recognition)"
    }
    if ($null -eq $product.visBreakdown.diffusionPotential -and $product.score -ne 0) {
      Fail "Product $($product.id) has incomplete visBreakdown (missing diffusionPotential)"
    }
  }

  [datetime]$created = [datetime]::ParseExact($product.createdAt.Substring(0, 10), "yyyy-MM-dd", $null)
  if ($created -lt $runDate.AddDays(-30)) {
    Fail "Product $($product.id) is older than 30 days; move it to products/archive/archive_$($created.ToString('yyyy-MM')).json"
  }
  if ($created -gt $runDate) {
    Fail "Product $($product.id) is dated after lastUpdated; move future sample data out of recent.json"
  }
}

# ==================== FEATURED COUNT LOGIC CHECK ====================
# Featured criteria must match the frontend:
# 1) keep products whose brand is in the monitored brand pool
# 2) featured if score >= 75 OR visTotal >= 7
$monitoredBrands = @($brands.brands | Where-Object { $_.monitored } | ForEach-Object { $_.name })
$visibleProducts = @($recent | Where-Object {
  $productSource = if ($_.PSObject.Properties.Name -contains 'source') { [string]$_.source } else { 'vis' }
  # Market chain products are always visible (not bound to monitored brand pool)
  if ($productSource -eq 'market') { return $true }
  $productBrand = [string]$_.brand
  foreach ($brand in $monitoredBrands) {
    $brandName = [string]$brand
    if ($productBrand -eq $brandName -or $productBrand.Contains($brandName) -or $brandName.Contains($productBrand)) {
      return $true
    }
  }
  return $false
})
$featuredCount = @($visibleProducts | Where-Object { $_.score -ge 75 -or $_.visTotal -ge 7 }).Count
$allVisibleCount = $visibleProducts.Count

# Cross-check: if no featured products exist and it's not a no-signal day, warn
if ($featuredCount -eq 0 -and $recent.Count -gt 0 -and $recent[0].id -ne 'no-signal') {
  Write-Host "WARNING: No featured products found (score >= 75 OR visTotal >= 7). If today has no signals, add a no-signal entry." -ForegroundColor Yellow
}

# Verify stat elements use placeholder '-' (not hardcoded numbers)
foreach ($html in @($htmlA, $htmlB)) {
  $statIds = @('statTotal', 'statFeatured', 'statBrands', 'statMonitored', 'featuredCount', 'allCount', 'brandCountNav')
  foreach ($sid in $statIds) {
    if ($html -match "id=`"$sid`">(\d)") {
      Fail "Static number found in id='$sid' — must be '-' placeholder for dynamic update"
    }
  }
}
# ==================== END LOGIC CHECK ====================

Write-Host "PASSED: BrandPulse VIS validation OK ($($recent.Count) total products, $allVisibleCount visible products, $($brands.brands.Count) brands, updated $($matchA.Groups[1].Value), $featuredCount featured)" -ForegroundColor Green
