# VHS Tape: Quick polybugger demo - shows available tools
# Run from project root: cd polybugger-mcp && vhs docs/tapes/debug_demo.tape

Output docs/debug_demo.gif

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 700
Set Theme "Dracula"
Set Padding 20
Set Framerate 12
Set TypingSpeed 30ms

# Wait for shell to initialize
Sleep 2s

# Title
Type "# polybugger-mcp: AI-powered multi-language debugging"
Enter
Sleep 1s

# Show available tools
Type "opencode run 'What debug tools are available from polybugger? List them briefly.'"
Enter
Sleep 30s
