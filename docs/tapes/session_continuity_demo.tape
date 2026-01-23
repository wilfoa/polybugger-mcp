# VHS Tape: Session continuity demo with polybugger
# Shows that debug sessions persist across multiple LLM interactions
# Run from project root: cd polybugger-mcp && vhs docs/tapes/session_continuity_demo.tape

Output docs/session_continuity_demo.gif

Set Shell "bash"
Set FontSize 13
Set Width 1400
Set Height 800
Set Theme "Dracula"
Set Padding 15
Set Framerate 12
Set TypingSpeed 35ms

# Show the demo script
Type "echo '=== Session Continuity Demo ==='"
Enter
Sleep 1s

Type "head -30 examples/demo/session_demo.py"
Enter
Sleep 3s

# First interaction: Create session, set breakpoints, launch
Type "echo '=== Interaction 1: Start debugging session ==='"
Enter
Sleep 1s

Type `opencode run "Debug examples/demo/session_demo.py with polybugger. Set breakpoints at lines 36, 39, and 42 (the three stage calls in main). Launch the script. When it stops at the first breakpoint, show me the variables and tell me the session_id."`
Enter
Sleep 50s

# Second interaction: Continue without any setup - session persists!
Type "echo '=== Interaction 2: Continue session (no reconfiguration needed!) ==='"
Enter
Sleep 2s

Type `opencode run "Continue the polybugger debug session. Just use debug_continue to go to the next breakpoint, then show me how the config variable changed. No need to create a new session or set breakpoints again - the session persists."`
Enter
Sleep 45s

Type "echo '=== Session maintained state across interactions! ==='"
Enter
Sleep 2s
