#!/bin/sh
#
# Launch the UDP<->TCP OSC bridge and one or more Open Stage Control instances.
#
# Open Stage Control only speaks UDP; osclive only listens on TCP. The bridge
# (tools/osc-bridge.py) translates between the two:
#
#     osclive (TCP:4301) <--> bridge (UDP:4299) <--> OSC instances (UDP)
#
# Each OSC instance serves an independent web UI (independent tabs/navigation)
# so multiple users can use different surfaces at once.
#
# Usage:
#   ./osc-serve.sh [count]          # launch bridge + N instances (default: 1)
#   ./osc-serve.sh 3                # bridge + 3 instances on ports 8080-8082
#
# Then open in browser(s):
#   http://<host>:8080   (user 1)
#   http://<host>:8081   (user 2)
#   http://<host>:8082   (user 3)
#
# The session JSON must be generated first:
#   python tools/toosc.py -o tools/osclive.json
#
# Override the bridge's UDP port (OSC target) and/or osclive TCP port:
#   OSC_UDP_PORT=4402 OSC_TCP_PORT=4401 ./osc-serve.sh 3
# Override the osclive TCP host:
#   OSC_TCP_HOST=192.168.1.100 ./osc-serve.sh 3

count=${1:-1}
base_port=8080
udp_port="${OSC_UDP_PORT:-4299}"
tcp_host="${OSC_TCP_HOST:-localhost}"
tcp_port="${OSC_TCP_PORT:-4301}"
target="localhost:${udp_port}"
script_dir="$(cd "$(dirname "$0")" && pwd)"
json="$script_dir/osclive.json"
bridge_pid=""
osc_pids=""

cleanup() {
    echo ""
    echo "Stopping..."
    [ -n "$bridge_pid" ] && kill "$bridge_pid" 2>/dev/null
    [ -n "$osc_pids" ] && kill $osc_pids 2>/dev/null
    wait 2>/dev/null
}
trap cleanup INT TERM EXIT

if ! command -v open-stage-control >/dev/null 2>&1; then
    echo "Error: open-stage-control not found in PATH"
    exit 1
fi

# Always regenerate the JSON so the target matches the bridge port.
echo "Generating $json (target=$target)..."
python "$script_dir/toosc.py" -s "$target" -o "$json" || exit 1

# Start the UDP<->TCP bridge.
echo "Starting OSC bridge: UDP :${udp_port} <-> TCP ${tcp_host}:${tcp_port}"
python "$script_dir/osc-bridge.py" \
    --udp-port "$udp_port" \
    --tcp-host "$tcp_host" \
    --tcp-port "$tcp_port" &
bridge_pid=$!

# Give the bridge a moment to bind and attempt the TCP connection.
sleep 1

echo ""
echo "Launching $count Open Stage Control instance(s)..."
echo "  Bridge target: $target"
echo ""

for i in $(seq 0 $((count - 1))); do
    port=$((base_port + i))
    echo "  Instance $i: http://0.0.0.0:$port"
    open-stage-control -l "$json" -p "$port" -s "$target" &
    osc_pids="$osc_pids $!"
done

echo ""
echo "All $count instance(s) started (ports $base_port-$((base_port + count - 1)))"
echo "Bridge: UDP :${udp_port} <-> TCP ${tcp_host}:${tcp_port}"
echo "Press Ctrl-C to stop everything."
wait
