# VHS Tape: Watch expressions demo with polybugger
# Run from project root: cd polybugger-mcp && vhs docs/tapes/watch_expressions_demo.tape

Output docs/watch_expressions_demo.gif

Set Shell "bash"
Set FontSize 13
Set Width 1400
Set Height 800
Set Theme "Dracula"
Set Padding 15
Set Framerate 12
Set TypingSpeed 35ms

# Show the demo script structure
Type "echo '=== Watch Expressions Demo Script ==='"
Enter
Sleep 1s

Type "cat examples/demo/watch_demo.py"
Enter
Sleep 4s

# Use OpenCode with polybugger to debug with watch expressions
Type "echo '=== Debugging with polybugger - Watch Expressions ==='"
Enter
Sleep 1s

Type `opencode run "Debug examples/demo/watch_demo.py using polybugger. Set a breakpoint at line 31 (inside the for loop in process_data). Launch the script and when it hits the breakpoint, use debug_evaluate to watch these expressions: 'processor.total', 'processor.average', 'processor.count', and 'value'. Then continue execution with debug_continue and evaluate the same expressions again to show how they change between iterations."`
Enter
Sleep 75s
