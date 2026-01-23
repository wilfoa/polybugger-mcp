# VHS Tape: Full polybugger debugging demo
# Run: vhs docs/tapes/debug_full_demo.tape

Output docs/debug_full_demo.gif

Set Shell "bash"
Set FontSize 13
Set Width 1300
Set Height 750
Set Theme "Dracula"
Set Padding 15
Set Framerate 12
Set TypingSpeed 40ms

# First show the buggy code
Type "echo '=== Buggy Python Script ===' && cat /tmp/polybugger-demo/buggy_calculator.py"
Enter
Sleep 4s

# Run it to show it crashes
Type "echo '=== Running the script ===' && python /tmp/polybugger-demo/buggy_calculator.py 2>&1 || true"
Enter
Sleep 3s

# Now debug with OpenCode + polybugger
Type "echo '=== Asking AI to debug with polybugger ===' && opencode run 'Debug the script /tmp/polybugger-demo/buggy_calculator.py using the polybugger debug tools. Set a breakpoint in calculate_average, run it, and find why it crashes on empty lists.'"
Enter
Sleep 60s
