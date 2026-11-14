<#
.SYNOPSIS
    Verifies the Authenticode signature and Publisher identity of a Windows MSIX package.
.PARAMETER MsixPath
    Path to the .msix or .appx package file.
.PARAMETER AllowUntrustedDevelopmentCertificate
    Allows UntrustedRoot status when verifying packages signed with local self-signed development certificates.
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$MsixPath,
    [switch]$AllowUntrustedDevelopmentCertificate
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $MsixPath)) {
    Write-Error "[verify_msix_signature] File not found: $MsixPath"
    exit 1
}

$resolvedPath = Resolve-Path $MsixPath
$signature = Get-AuthenticodeSignature -FilePath $resolvedPath

# 1. Read AppxManifest.xml from MSIX Zip Archive
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::OpenRead($resolvedPath.Path)
try {
    $manifestEntry = $archive.GetEntry("AppxManifest.xml")
    if (-not $manifestEntry) {
        throw "MSIX signature verification failed: AppxManifest.xml is missing from package: $MsixPath"
    }

    $reader = [System.IO.StreamReader]::new($manifestEntry.Open())
    try {
        [xml]$manifest = $reader.ReadToEnd()
    } finally {
        $reader.Dispose()
    }
} finally {
    $archive.Dispose()
}

$manifestPublisher = [string]$manifest.Package.Identity.Publisher
if ([string]::IsNullOrWhiteSpace($manifestPublisher)) {
    throw "MSIX signature verification failed: Package manifest Publisher is missing or empty."
}

# 2. Check Signature Presence
if (-not $signature.SignerCertificate -or $signature.Status -eq [System.Management.Automation.SignatureStatus]::NotSigned) {
    throw "MSIX signature verification failed: Package is not signed."
}

# 3. Check Publisher Alignment
if ($signature.SignerCertificate.Subject -cne $manifestPublisher) {
    throw "MSIX signature verification failed: Signer subject '$($signature.SignerCertificate.Subject)' does not match package Publisher '$manifestPublisher'."
}

# 4. Check Signature Integrity / Hash
if ($signature.Status -eq [System.Management.Automation.SignatureStatus]::HashMismatch) {
    throw "MSIX signature verification failed: Package signature hash mismatch (corrupted or tampered package)."
}

# 5. Check Signature Trust
if ($signature.Status -eq [System.Management.Automation.SignatureStatus]::Valid) {
    Write-Host "✅ [verify_msix_signature] Signature valid: $($signature.SignerCertificate.Subject)" -ForegroundColor Green
    exit 0
}

if ($signature.Status -eq [System.Management.Automation.SignatureStatus]::UntrustedRoot) {
    if ($AllowUntrustedDevelopmentCertificate) {
        Write-Host "⚠️  [verify_msix_signature] Signature untrusted root permitted: $($signature.SignerCertificate.Subject)" -ForegroundColor Yellow
        exit 0
    }
    throw "MSIX signature verification failed: Untrusted root certificate. Install the certificate or use -AllowUntrustedDevelopmentCertificate."
}

throw "MSIX signature verification failed with status: $($signature.Status) ($($signature.StatusMessage))"
