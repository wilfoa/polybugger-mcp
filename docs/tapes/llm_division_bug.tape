# VHS Tape: LLM finds division by zero bug
# Run: vhs docs/tapes/llm_division_bug.tape
# Requires: ANTHROPIC_API_KEY environment variable

Output docs/llm_division_bug.gif

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 700
Set Theme "Dracula"
Set Padding 20
Set Framerate 10

# Title
Type "# LLM Debugging: Finding a Division by Zero Bug"
Enter
Sleep 1s

Type "# Claude will autonomously debug a Python script with a bug"
Enter
Sleep 1s

Type "poetry run pytest tests/e2e/test_llm_debugging.py::TestLLMDebugging::test_llm_finds_division_by_zero_bug -v -s 2>&1 | head -100"
Enter

# Wait for test to complete (may take up to 2 minutes)
Sleep 120s
