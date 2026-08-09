[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = (Split-Path -Parent $PSScriptRoot).TrimEnd('\', '/')
$files = @(
    Get-Item -LiteralPath (Join-Path $repoRoot 'README.md')
    Get-ChildItem -LiteralPath (Join-Path $repoRoot 'docs') -Recurse -File -Filter '*.md' |
        Where-Object { $_.Name -notlike '*Zone.Identifier*' }
)

$errors = [System.Collections.Generic.List[string]]::new()
$pattern = '!?(?:\[[^\]]*\])\((?<target>[^)]+)\)'

foreach ($file in $files) {
    $content = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
    foreach ($match in [regex]::Matches($content, $pattern)) {
        $target = $match.Groups['target'].Value.Trim().Trim('<', '>')
        if ([string]::IsNullOrWhiteSpace($target) -or
            $target.StartsWith('#') -or
            $target -match '^(?i:https?|mailto|tel|data):') {
            continue
        }

        $pathOnly = ($target -split '#', 2)[0]
        if ([string]::IsNullOrWhiteSpace($pathOnly)) { continue }
        $pathOnly = [System.Uri]::UnescapeDataString($pathOnly)
        $candidate = Join-Path $file.DirectoryName $pathOnly
        if (-not (Test-Path -LiteralPath $candidate)) {
            $relativeFile = $file.FullName.Substring($repoRoot.Length + 1).Replace('\', '/')
            $errors.Add(($relativeFile + ": missing local link target '" + $target + "'"))
        }
    }
}

if ($errors.Count -gt 0) {
    $errors | Sort-Object | ForEach-Object { Write-Error $_ }
    throw ("Markdown link validation failed with {0} error(s)." -f $errors.Count)
}

Write-Output ("Markdown link validation passed for {0} files." -f $files.Count)
