$ErrorActionPreference = "Stop"

$SourceDir = "C:\Users\Devloper\.codex\generated_images\019f55d3-4e52-7630-891f-b9bedfa92655"
$TargetDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$Icon = Join-Path $SourceDir "call_kyLLhajBoPKwZ1rxorWy1Bud.png"
$Banner = Join-Path $SourceDir "call_AnJvbVQnML0MhpYVJtWSyEPh.png"

Copy-Item -LiteralPath $Icon -Destination (Join-Path $TargetDir "icon.png") -Force
Copy-Item -LiteralPath $Banner -Destination (Join-Path $TargetDir "banner.png") -Force
Copy-Item -LiteralPath $Banner -Destination (Join-Path $TargetDir "main_screenshot.png") -Force
Copy-Item -LiteralPath $Banner -Destination (Join-Path $TargetDir "screenshot_builder.png") -Force
Copy-Item -LiteralPath $Banner -Destination (Join-Path $TargetDir "screenshot_properties.png") -Force

Write-Host "Done. PNG files were copied to $TargetDir"
