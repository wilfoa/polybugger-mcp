# VHS Tape: LLM selects debugging language
# Run: vhs docs/tapes/llm_language_selection.tape
# Requires: ANTHROPIC_API_KEY environment variable

Output docs/llm_language_selection.gif

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 700
Set Theme "Dracula"
Set Padding 20
Set Framerate 10

# Title
Type "# LLM Debugging: Multi-Language Support"
Enter
Sleep 1s

Type "# Claude queries available languages and creates a debug session"
Enter
Sleep 1s

Type "poetry run pytest tests/e2e/test_llm_debugging.py::TestLLMDebugging::test_llm_uses_language_selection -v -s 2>&1 | head -80"
Enter

# Wait for test to complete
Sleep 60s
