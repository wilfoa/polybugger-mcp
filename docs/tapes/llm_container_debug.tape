# VHS Tape: LLM debugs inside Docker container
# Run: vhs docs/tapes/llm_container_debug.tape
# Requires: ANTHROPIC_API_KEY environment variable and Docker running

Output docs/llm_container_debug.gif

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 700
Set Theme "Dracula"
Set Padding 20
Set Framerate 10

# Title
Type "# LLM Debugging: Attaching to a Docker Container"
Enter
Sleep 1s

Type "# Claude will autonomously attach to and debug a Python process in Docker"
Enter
Sleep 1s

Type "poetry run pytest tests/e2e/test_container_debugging.py::TestLLMContainerDebugging::test_llm_attaches_to_docker_container -v -s 2>&1 | head -120"
Enter

# Wait for test to complete (may take up to 2 minutes)
Sleep 150s
