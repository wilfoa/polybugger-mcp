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

# Start a Python container with a long-running script
Type "echo '=== Starting Docker container with Python ==='"
Enter
Sleep 1s

Type `docker run -d --name debug-demo python:3.11 python -c "import time; print('Running...'); exec('while True: time.sleep(1)')"`
Enter
Sleep 4s

# Verify container is running
Type "docker ps --filter name=debug-demo --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'"
Enter
Sleep 2s

# Now use OpenCode with polybugger to debug the container
Type "echo '=== Using polybugger to debug container ==='"
Enter
Sleep 1s

Type `opencode run "Use polybugger to list Python processes in the 'debug-demo' Docker container. Use debug_container_list_processes with runtime=docker and container=debug-demo"`
Enter
Sleep 45s

# Cleanup
Type "echo '=== Cleanup ===' && docker rm -f debug-demo"
Enter
Sleep 2s
