# VHS Tape: Call chain / stack trace demo with polybugger
# Run from project root: cd polybugger-mcp && vhs docs/tapes/call_chain_demo.tape

Output docs/call_chain_demo.gif

Set Shell "bash"
Set FontSize 13
Set Width 1400
Set Height 800
Set Theme "Dracula"
Set Padding 15
Set Framerate 12
Set TypingSpeed 35ms

# Show the demo script structure
Type "echo '=== Call Chain Demo Script ==='"
Enter
Sleep 1s

Type "cat examples/demo/call_chain_demo.py"
Enter
Sleep 4s

# Use OpenCode with polybugger to debug and show call chain
Type "echo '=== Debugging with polybugger - Call Stack Navigation ==='"
Enter
Sleep 1s

Type `opencode run "Debug the script at examples/demo/call_chain_demo.py using polybugger. Set a breakpoint at line 8 (inside level_3 function), launch the script, and when it stops show me the full call stack using debug_get_stacktrace. I want to see how main() calls level_1() calls level_2() calls level_3()."`
Enter
Sleep 60s
