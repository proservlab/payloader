# Command and Control Server

This repository contains a Python script (`server.py`) that acts as a command and control (C2) server. It is designed to manage reverse shell connections by queuing incoming sessions and delivering payloads based on the client's request (via the environment variable `TASK`). The server supports both Linux (bash scripts) and Windows (PowerShell scripts) payloads.

## Features

- **Reverse Shell Listener:** Listens for and accepts incoming reverse shell connections.
- **Payload Delivery:** Dynamically delivers payloads based on the client's `TASK` environment variable.
- **Platform Support:** Provides bash scripts for Linux and PowerShell scripts for Windows clients.
- **Session Management:** Queues sessions and processes them with dedicated worker tasks.
- **File Operations:** Offers FastAPI endpoints for file upload and download per session.
- **Command Execution API:** Executes arbitrary tasks on connected clients and returns base64-encoded responses.
- **Keepalive Mechanism:** Periodically sends commands to maintain active sessions.
- **Bootstrap Initialization:** Sends an initial bootstrap payload to configure the client environment.

## Requirements

- Python 3.7+
- [uvicorn](https://www.uvicorn.org/)
- [fastapi](https://fastapi.tiangolo.com/)
- [pydantic](https://pydantic-docs.helpmanual.io/)

You can install the required packages using pip:

```bash
pip install uvicorn fastapi pydantic
```

Or use pipreqs via the reqs.sh

```bash
./reqs.sh
```

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/credibleforce/payloader.git
   cd payloader/server
   ```

2. **(Optional) Create and activate a virtual environment:**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

   - Python 3.7+
   - [uvicorn](https://www.uvicorn.org/)
   - [fastapi](https://fastapi.tiangolo.com/)
   - [pydantic](https://pydantic-docs.helpmanual.io/)

   You can install the required packages using pip:

```bash
pip install uvicorn fastapi pydantic
```

   Or use pipreqs via the reqs.sh

```bash
./reqs.sh
```

## Usage

Run the server with the following command-line options:

```bash
python server.py --port 4444 --host <reverse_shell_host>
```

- `--port`: The port for the reverse shell listener (default is 4444).
- `--host`: The hostname or IP address for the reverse shell. If not specified, the script will attempt to determine the public IP via [icanhazip.com](http://icanhazip.com).

## Payloads

Payload scripts should be stored in a directory named `payloads` in the same directory as `server.py`. The script expects payload files based on the requested task:

- **Linux payloads:** `<task>.sh`
- **Windows payloads:** `<task>.ps1`

A bootstrap payload (named `bootstrap.sh` for Linux or `bootstrap.ps1` for Windows) is required to initialize the client environment. This payload is automatically loaded and sent to the client upon connection.

## API Endpoints

The server runs a FastAPI application in the background (on port 8001) that provides the following endpoints:

### File Download

- **Endpoint:** `GET /files/{session_id}/{filename}`
- **Description:** Downloads a file from the specified session directory.
- **Response:** Returns the requested file or a 404 error if not found.

### File Upload

- **Endpoint:** `POST /files/{session_id}/{filename}`
- **Description:** Uploads a file to the session's directory.
- **Usage:** Send the file as form data.
- **Response:** A JSON confirmation that the file was uploaded successfully.

### Execute Task

- **Endpoint:** `POST /execute`
- **Description:** Executes a command on the client.
- **Request Body:** JSON with the following properties:
  - `session_id`: The identifier for the session.
  - `task`: The task command to be executed.
- **Response:** A JSON object with base64-encoded output and error messages, along with the task and return code.

## Signal Handling and Shutdown

The script registers a signal handler for SIGINT (Ctrl+C) to gracefully shut down the listener and any active worker tasks.