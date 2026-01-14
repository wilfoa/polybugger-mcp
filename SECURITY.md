# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by opening a GitHub issue with the label "security".

For sensitive issues, please email the maintainer directly.

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- Initial response: Within 48 hours
- Status update: Within 7 days
- Resolution: Depends on severity and complexity

## Security Considerations

This MCP server executes Python code through debugpy. Users should:

1. Only debug trusted code
2. Run in isolated environments when debugging untrusted code
3. Be aware that debug sessions have full access to the debugged process
4. Not expose the HTTP server to untrusted networks

## Best Practices

- Keep dependencies updated
- Use virtual environments
- Review debug session permissions
- Monitor debug server access logs
