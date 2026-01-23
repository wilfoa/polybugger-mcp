# VHS Tape: Full polybugger debugging demo
# Run from project root: cd polybugger-mcp && vhs docs/tapes/debug_full_demo.tape

Output docs/debug_full_demo.gif

Set Shell "bash"
Set FontSize 13
Set Width 1300
Set Height 750
Set Theme "Dracula"
Set Padding 15
Set Framerate 12
Set TypingSpeed 40ms

# Wait for shell to initialize
Sleep 2s

# First show the buggy code
Type "echo '=== Buggy Python Script ===' && cat examples/demo/buggy_calculator.py"
Enter
Sleep 4s

# Run it to show it crashes
Type "echo '=== Running the script ===' && python3 examples/demo/buggy_calculator.py 2>&1 || true"
Enter
Sleep 3s

# Now debug with OpenCode + polybugger
Type "opencode run 'Debug examples/demo/buggy_calculator.py using polybugger debug tools. Set a breakpoint in calculate_average, launch it, and find why it crashes.'"
Enter
Sleep 60s
