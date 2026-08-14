# Generate Code Signing Certificate
$cert = New-SelfSignedCertificate -CertStoreLocation Cert:\CurrentUser\My -Subject "CN=UnifAI Enterprise Security" -Type CodeSigningCert

# Trust the certificate in Root & TrustedPublisher store
$rootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser")
$rootStore.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
$rootStore.Add($cert)
$rootStore.Close()

$pubStore = New-Object System.Security.Cryptography.X509Certificates.X509Store("TrustedPublisher", "CurrentUser")
$pubStore.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
$pubStore.Add($cert)
$pubStore.Close()

# Sign the EXE
$signResult = Set-AuthenticodeSignature -FilePath "dist\UnifAI_Guard.exe" -Certificate $cert
Write-Host "Signing Result: " $signResult.Status
