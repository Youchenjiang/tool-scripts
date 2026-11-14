<#
.SYNOPSIS
    Generates a self-signed Code Signing certificate for Windows Desktop / MSIX local development.
.DESCRIPTION
    Creates an X.509 code signing certificate with Enhanced Key Usage (1.3.6.1.5.5.7.3.3),
    exports .pfx and .cer files, and optionally registers the certificate into Trusted People
    to allow local test installations without signing errors.
.PARAMETER Publisher
    The publisher CN string (e.g. "CN=DevTeam" or "DevTeam"). If omitted, reads from AppxManifest.
.PARAMETER Password
    Password protecting the exported PFX file (default: "1234").
.PARAMETER OutDir
    Output directory for generated cert files (default: "packaging/certs").
.PARAMETER Install
    Automatically install the certificate to CurrentUser\TrustedPeople for local MSIX installation testing.
#>
param(
    [string]$Publisher,
    [string]$Password = "1234",
    [string]$OutDir = "packaging/certs",
    [switch]$Install
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path "$PSScriptRoot/.."

# 1. Determine Publisher
if (-not $Publisher) {
    $manifestCandidates = @(
        Join-Path $repoRoot "Package.appxmanifest",
        Join-Path $repoRoot "packaging/msix/AppxManifest.xml",
        Join-Path $repoRoot "packaging/AppxManifest.xml",
        Join-Path $repoRoot "AppxManifest.xml"
    )
    foreach ($cand in $manifestCandidates) {
        if (Test-Path $cand) {
            [xml]$xml = Get-Content $cand
            if ($xml.Package.Identity.Publisher) {
                $Publisher = $xml.Package.Identity.Publisher
                Write-Host "[create_dev_cert] Detected Publisher from manifest: $Publisher" -ForegroundColor Cyan
                break
            }
        }
    }
}

if (-not $Publisher) {
    $Publisher = "CN=LocalDevelopment"
    Write-Host "[create_dev_cert] No manifest found; using default publisher: $Publisher" -ForegroundColor Yellow
}

if (-not $Publisher.StartsWith("CN=", [System.StringComparison]::OrdinalIgnoreCase)) {
    $subject = "CN=$Publisher"
} else {
    $subject = $Publisher
}

$cleanName = ($subject -replace '^CN=', '') -replace '[^a-zA-Z0-9_-]', '_'

# 2. Prepare Output Directory
$targetDir = Join-Path $repoRoot $OutDir
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

$pfxPath = Join-Path $targetDir "$cleanName.pfx"
$cerPath = Join-Path $targetDir "$cleanName.cer"

Write-Host "🚀 Creating self-signed code signing certificate: $subject" -ForegroundColor Cyan

# 3. Create Self-Signed Certificate
$securePassword = ConvertTo-SecureString $Password -AsPlainText -Force
$cert = New-SelfSignedCertificate `
    -Type Custom `
    -Subject $subject `
    -KeyUsage DigitalSignature `
    -FriendlyName "Development Code Signing Certificate ($cleanName)" `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -TextExtension @(
        "2.5.29.37={text}1.3.6.1.5.5.7.3.3",  # Code Signing EKU
        "2.5.29.19={text}"                   # Subject Type=End Entity
    )

# 4. Export Certificates
Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $securePassword | Out-Null
Export-Certificate -Cert $cert -FilePath $cerPath | Out-Null

Write-Host "✅ Exported PFX : $pfxPath (Password: $Password)" -ForegroundColor Green
Write-Host "✅ Exported CER : $cerPath" -ForegroundColor Green

# 5. Install to Trusted People if requested
if ($Install) {
    Write-Host "🔐 Installing certificate to CurrentUser\TrustedPeople for local MSIX installation..." -ForegroundColor Cyan
    Import-Certificate -FilePath $cerPath -CertStoreLocation "Cert:\CurrentUser\TrustedPeople" | Out-Null
    Write-Host "✅ Certificate installed to CurrentUser\TrustedPeople!" -ForegroundColor Green
} else {
    Write-Host "💡 To trust this certificate for local MSIX testing, run:" -ForegroundColor Gray
    Write-Host "   Import-Certificate -FilePath `"$cerPath`" -CertStoreLocation `"Cert:\CurrentUser\TrustedPeople`"" -ForegroundColor Gray
}
