/**
 * OpenCode Python Debugger Plugin
 *
 * Provides custom tools for debugging Python code via the OpenCode Debug Relay Server.
 * The server must be running at http://127.0.0.1:5679 (or configured via OPENCODE_DEBUG_HOST/PORT).
 */

import { type Plugin, tool } from "@opencode-ai/plugin"

const DEBUG_HOST = process.env.OPENCODE_DEBUG_HOST || "127.0.0.1"
const DEBUG_PORT = process.env.OPENCODE_DEBUG_PORT || "5679"
const BASE_URL = `http://${DEBUG_HOST}:${DEBUG_PORT}/api/v1`

async function request(path: string, options?: RequestInit) {
  const url = `${BASE_URL}${path}`
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: response.statusText }))
    throw new Error(`Debug server error: ${error.message || error.detail || response.statusText}`)
  }

  return response.json()
}

export const PythonDebuggerPlugin: Plugin = async (ctx) => {
  // Check if debug server is available
  try {
    await fetch(`${BASE_URL.replace('/api/v1', '')}/health`)
    await ctx.client.app.log({
      service: "python-debugger",
      level: "info",
      message: "Debug server connected",
      extra: { url: BASE_URL },
    })
  } catch {
    await ctx.client.app.log({
      service: "python-debugger",
      level: "warn",
      message: "Debug server not available - debug tools will fail until server is started",
      extra: { url: BASE_URL },
    })
  }

  return {
    tool: {
      /**
       * Create a new debug session
       */
      "debug-session-create": tool({
        description: "Create a new Python debug session for a project. Returns session ID to use with other debug commands.",
        args: {
          project_root: tool.schema.string().describe("Root directory of the project to debug"),
          name: tool.schema.string().optional().describe("Optional session name"),
        },
        async execute(args) {
          const result = await request("/sessions", {
            method: "POST",
            body: JSON.stringify({
              project_root: args.project_root,
              name: args.name,
            }),
          })
          return `Created debug session: ${result.id}\nState: ${result.state}\nProject: ${result.project_root}`
        },
      }),

      /**
       * Launch a Python program for debugging
       */
      "debug-launch": tool({
        description: "Launch a Python program in debug mode. The program will start and stop at the first line if stop_on_entry is true, or run until a breakpoint is hit.",
        args: {
          session_id: tool.schema.string().describe("Debug session ID"),
          program: tool.schema.string().optional().describe("Path to Python script to debug"),
          module: tool.schema.string().optional().describe("Python module to debug (alternative to program)"),
          args: tool.schema.array(tool.schema.string()).optional().describe("Command line arguments for the program"),
          stop_on_entry: tool.schema.boolean().optional().describe("Stop at first line of code (default: false)"),
          stop_on_exception: tool.schema.boolean().optional().describe("Stop on uncaught exceptions (default: true)"),
        },
        async execute(args) {
          const result = await request(`/sessions/${args.session_id}/launch`, {
            method: "POST",
            body: JSON.stringify({
              program: args.program,
              module: args.module,
              args: args.args,
              stop_on_entry: args.stop_on_entry ?? false,
              stop_on_exception: args.stop_on_exception ?? true,
            }),
          })
          return `Launched program\nStatus: ${result.status}`
        },
      }),

      /**
       * Set breakpoints in a source file
       */
      "debug-breakpoints": tool({
        description: "Set breakpoints in a Python source file. Replaces all existing breakpoints for the file.",
        args: {
          session_id: tool.schema.string().describe("Debug session ID"),
          source: tool.schema.string().describe("Path to source file"),
          breakpoints: tool.schema.array(
            tool.schema.object({
              line: tool.schema.number().describe("Line number (1-based)"),
              condition: tool.schema.string().optional().describe("Condition expression (breakpoint only hits when true)"),
              log_message: tool.schema.string().optional().describe("Log message instead of stopping (logpoint)"),
            })
          ).describe("List of breakpoints to set"),
        },
        async execute(args) {
          const result = await request(`/sessions/${args.session_id}/breakpoints`, {
            method: "POST",
            body: JSON.stringify({
              source: args.source,
              breakpoints: args.breakpoints,
            }),
          })
          const bps = result.breakpoints.map((bp: any) =>
            `  Line ${bp.line}: ${bp.verified ? 'verified' : 'pending'}${bp.message ? ` (${bp.message})` : ''}`
          ).join('\n')
          return `Set ${result.breakpoints.length} breakpoint(s) in ${args.source}:\n${bps}`
        },
      }),

      /**
       * Continue execution
       */
      "debug-continue": tool({
        description: "Continue program execution until the next breakpoint or program end.",
        args: {
          session_id: tool.schema.string().describe("Debug session ID"),
          thread_id: tool.schema.number().optional().describe("Thread ID (default: current thread)"),
        },
        async execute(args) {
          const result = await request(`/sessions/${args.session_id}/continue`, {
            method: "POST",
            body: JSON.stringify({ thread_id: args.thread_id }),
          })
          return `Continued execution\nStatus: ${result.status}`
        },
      }),

      /**
       * Step over (next line)
       */
      "debug-step-over": tool({
        description: "Execute the current line and stop at the next line in the same function.",
        args: {
          session_id: tool.schema.string().describe("Debug session ID"),
          thread_id: tool.schema.number().optional().describe("Thread ID"),
        },
        async execute(args) {
          const result = await request(`/sessions/${args.session_id}/step-over`, {
            method: "POST",
            body: JSON.stringify({ thread_id: args.thread_id }),
          })
          return `Stepped over\nStatus: ${result.status}`
        },
      }),

      /**
       * Step into function
       */
      "debug-step-into": tool({
        description: "Step into a function call on the current line.",
        args: {
          session_id: tool.schema.string().describe("Debug session ID"),
          thread_id: tool.schema.number().optional().describe("Thread ID"),
        },
        async execute(args) {
          const result = await request(`/sessions/${args.session_id}/step-into`, {
            method: "POST",
            body: JSON.stringify({ thread_id: args.thread_id }),
          })
          return `Stepped into\nStatus: ${result.status}`
        },
      }),

      /**
       * Step out of function
       */
      "debug-step-out": tool({
        description: "Continue execution until the current function returns.",
        args: {
          session_id: tool.schema.string().describe("Debug session ID"),
          thread_id: tool.schema.number().optional().describe("Thread ID"),
        },
        async execute(args) {
          const result = await request(`/sessions/${args.session_id}/step-out`, {
            method: "POST",
            body: JSON.stringify({ thread_id: args.thread_id }),
          })
          return `Stepped out\nStatus: ${result.status}`
        },
      }),

      /**
       * Get session state and events
       */
      "debug-status": tool({
        description: "Get the current state of a debug session and poll for events.",
        args: {
          session_id: tool.schema.string().describe("Debug session ID"),
          poll_events: tool.schema.boolean().optional().describe("Poll for new events (default: true)"),
          timeout: tool.schema.number().optional().describe("Event poll timeout in seconds (default: 1)"),
        },
        async execute(args) {
          const session = await request(`/sessions/${args.session_id}`)

          let events: any[] = []
          if (args.poll_events !== false) {
            const eventsResult = await request(
              `/sessions/${args.session_id}/events?timeout=${args.timeout ?? 1}`
            )
            events = eventsResult.events || []
          }

          let output = `Session: ${session.id}\nState: ${session.state}`
          if (session.stop_reason) output += `\nStop reason: ${session.stop_reason}`
          if (session.current_thread_id) output += `\nCurrent thread: ${session.current_thread_id}`

          if (events.length > 0) {
            output += `\n\nRecent events:`
            for (const event of events) {
              output += `\n  - ${event.type}`
              if (event.data?.reason) output += ` (${event.data.reason})`
            }
          }

          return output
        },
      }),

      /**
       * Get stack trace
       */
      "debug-stacktrace": tool({
        description: "Get the call stack for a paused thread. Shows the sequence of function calls that led to the current position.",
        args: {
          session_id: tool.schema.string().describe("Debug session ID"),
          thread_id: tool.schema.number().optional().describe("Thread ID (default: 1)"),
        },
        async execute(args) {
          const result = await request(
            `/sessions/${args.session_id}/stacktrace?thread_id=${args.thread_id ?? 1}`
          )

          if (!result.frames || result.frames.length === 0) {
            return "No stack frames available"
          }

          let output = `Stack trace (${result.frames.length} frames):`
          for (const frame of result.frames) {
            const location = frame.source?.path
              ? `${frame.source.path}:${frame.line}`
              : `<unknown>:${frame.line}`
            output += `\n  #${frame.id} ${frame.name} at ${location}`
          }

          return output
        },
      }),

      /**
       * Get variables in scope
       */
      "debug-variables": tool({
        description: "Get variables in the current scope. First get scopes using the frame_id from stacktrace, then get variables using the scope's variables_reference.",
        args: {
          session_id: tool.schema.string().describe("Debug session ID"),
          frame_id: tool.schema.number().optional().describe("Frame ID from stacktrace (to get scopes)"),
          variables_ref: tool.schema.number().optional().describe("Variables reference from scope or expanded variable"),
        },
        async execute(args) {
          if (args.frame_id !== undefined) {
            // Get scopes for a frame
            const result = await request(
              `/sessions/${args.session_id}/scopes?frame_id=${args.frame_id}`
            )

            let output = `Scopes for frame ${args.frame_id}:`
            for (const scope of result.scopes) {
              output += `\n  ${scope.name} (ref: ${scope.variables_reference})`
              if (scope.named_variables) output += ` - ${scope.named_variables} variables`
            }
            output += `\n\nUse debug-variables with variables_ref to inspect a scope`
            return output
          }

          if (args.variables_ref !== undefined) {
            // Get variables for a reference
            const result = await request(
              `/sessions/${args.session_id}/variables?ref=${args.variables_ref}`
            )

            if (!result.variables || result.variables.length === 0) {
              return "No variables in this scope"
            }

            let output = `Variables:`
            for (const v of result.variables) {
              output += `\n  ${v.name}: ${v.value}`
              if (v.type) output += ` (${v.type})`
              if (v.variables_reference > 0) output += ` [expandable, ref: ${v.variables_reference}]`
            }
            return output
          }

          return "Provide either frame_id (to get scopes) or variables_ref (to get variables)"
        },
      }),

      /**
       * Evaluate an expression
       */
      "debug-evaluate": tool({
        description: "Evaluate a Python expression in the context of the current stack frame.",
        args: {
          session_id: tool.schema.string().describe("Debug session ID"),
          expression: tool.schema.string().describe("Python expression to evaluate"),
          frame_id: tool.schema.number().optional().describe("Frame ID for context (default: top frame)"),
        },
        async execute(args) {
          const result = await request(`/sessions/${args.session_id}/evaluate`, {
            method: "POST",
            body: JSON.stringify({
              expression: args.expression,
              frame_id: args.frame_id,
              context: "repl",
            }),
          })

          let output = `${args.expression} = ${result.result}`
          if (result.type) output += `\nType: ${result.type}`
          if (result.variables_reference > 0) {
            output += `\n[Expandable object, ref: ${result.variables_reference}]`
          }
          return output
        },
      }),

      /**
       * Get program output
       */
      "debug-output": tool({
        description: "Get captured stdout/stderr output from the debugged program.",
        args: {
          session_id: tool.schema.string().describe("Debug session ID"),
          lines: tool.schema.number().optional().describe("Number of lines to retrieve (default: 100)"),
        },
        async execute(args) {
          const result = await request(
            `/sessions/${args.session_id}/output?limit=${args.lines ?? 100}`
          )

          if (!result.lines || result.lines.length === 0) {
            return "No output captured"
          }

          let output = `Program output (${result.total} total lines):`
          for (const line of result.lines) {
            const prefix = line.category === "stderr" ? "[err] " : ""
            output += `\n${prefix}${line.content}`
          }

          if (result.has_more) {
            output += `\n... (${result.total - result.lines.length} more lines)`
          }

          return output
        },
      }),

      /**
       * Terminate debug session
       */
      "debug-terminate": tool({
        description: "Terminate a debug session and stop the debugged program.",
        args: {
          session_id: tool.schema.string().describe("Debug session ID"),
        },
        async execute(args) {
          await request(`/sessions/${args.session_id}`, {
            method: "DELETE",
          })
          return `Debug session ${args.session_id} terminated`
        },
      }),

      /**
       * List all debug sessions
       */
      "debug-sessions": tool({
        description: "List all active debug sessions.",
        args: {},
        async execute() {
          const result = await request("/sessions")

          if (!result.sessions || result.sessions.length === 0) {
            return "No active debug sessions"
          }

          let output = `Active debug sessions (${result.total}):`
          for (const session of result.sessions) {
            output += `\n  ${session.id}: ${session.state}`
            if (session.name) output += ` (${session.name})`
            output += ` - ${session.project_root}`
          }

          return output
        },
      }),
    },
  }
}
