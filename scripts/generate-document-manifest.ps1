[CmdletBinding()]
param(
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Split-Path -Parent $PSScriptRoot).TrimEnd('\', '/')
$manifestPath = Join-Path $repoRoot 'manifest.json'

$documentFiles = @(
    Get-Item -LiteralPath (Join-Path $repoRoot 'README.md')
    Get-ChildItem -LiteralPath (Join-Path $repoRoot 'docs') -Recurse -File -Filter '*.md' |
        Where-Object { $_.Name -notlike '*Zone.Identifier*' }
) | Sort-Object FullName

$documents = foreach ($file in $documentFiles) {
    $relativePath = $file.FullName.Substring($repoRoot.Length + 1).Replace('\', '/')
    [ordered]@{
        path = $relativePath
        bytes = $file.Length
        sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}

$aggregateInput = ($documents | ForEach-Object { '{0}:{1}:{2}' -f $_.path, $_.bytes, $_.sha256 }) -join "`n"
$sha = [System.Security.Cryptography.SHA256]::Create()
try {
    $aggregateBytes = [System.Text.Encoding]::UTF8.GetBytes($aggregateInput)
    $aggregateHash = ([System.BitConverter]::ToString($sha.ComputeHash($aggregateBytes))).Replace('-', '').ToLowerInvariant()
}
finally {
    $sha.Dispose()
}

$manifest = [ordered]@{
    schema_version = 2
    name = 'LMS SaaS Master Architecture and Delivery Plan'
    plan_approval_date = '2026-08-02'
    generated_by = 'scripts/generate-document-manifest.ps1'
    checksum_algorithm = 'SHA-256'
    document_count = $documents.Count
    aggregate_sha256 = $aggregateHash
    documents = $documents
}

$rendered = ($manifest | ConvertTo-Json -Depth 6 -Compress) + "`n"

if ($Check) {
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw 'manifest.json is missing. Run scripts/generate-document-manifest.ps1.'
    }
    $current = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8
    if ($current.Replace("`r`n", "`n") -ne $rendered.Replace("`r`n", "`n")) {
        throw 'manifest.json has drifted. Run scripts/generate-document-manifest.ps1 and commit the result.'
    }
    Write-Output ("Manifest valid: {0} documents, aggregate {1}" -f $documents.Count, $aggregateHash)
    exit 0
}

[System.IO.File]::WriteAllText($manifestPath, $rendered, (New-Object System.Text.UTF8Encoding($false)))
Write-Output ("Generated manifest.json: {0} documents, aggregate {1}" -f $documents.Count, $aggregateHash)
