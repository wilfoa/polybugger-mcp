# VHS Tape: Container debugging demo with polybugger
# Run from project root: cd polybugger-mcp && vhs docs/tapes/container_debug_demo.tape

Output docs/container_debug_demo.gif

Set Shell "bash"
Set FontSize 13
Set Width 1400
Set Height 800
Set Theme "Dracula"
Set Padding 15
Set Framerate 12
Set TypingSpeed 35ms

# Wait for shell to initialize
Sleep 2s

# Clean up any existing container first
Type "docker rm -f debug-demo 2>/dev/null; echo '=== Container Debugging Demo ==='"
Enter
Sleep 2s

# Start a Python container with a long-running script
Type "echo 'Starting a Python container with a long-running process...'"
Enter
Sleep 1s

Type `docker run -d --name debug-demo python:3.11 python -c "import time; exec('while True: time.sleep(1)')"`
Enter
Sleep 5s

# Verify container is running
Type "echo '--- Container Status ---' && docker ps --filter name=debug-demo --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'"
Enter
Sleep 3s

# Now use OpenCode with polybugger to list processes
Type "echo '=== Using polybugger to inspect container ==='"
Enter
Sleep 1s

Type `opencode run "Use the debug_container_list_processes tool to list Python processes running inside the Docker container named 'debug-demo'. Show me what processes are running."`
Enter
Sleep 55s

# Cleanup
Type "echo '=== Demo Complete - Cleaning up ===' && docker rm -f debug-demo"
Enter
Sleep 3s
