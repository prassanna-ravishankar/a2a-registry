/**
 * Hello World A2A Agent - All-in-One Cloudflare Worker
 * 
 * Handles everything:
 * - Serves agent card at /.well-known/agent.json
 * - Serves landing page at /
 * - Handles A2A protocol at /a2a
 * - Provides streaming at /a2a/tasks/{id}/stream
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return handleCORS();
    }

    // Route requests
    switch (url.pathname) {
      case '/':
        return serveLandingPage();
      
      case '/.well-known/agent.json':
        return serveAgentCard();
      
      case '/a2a':
      case '/a2a/':
        return handleA2ARequest(request);
      
      case '/icon.png':
        return serveIcon();
      
      default:
        // Handle streaming endpoints
        if (url.pathname.startsWith('/a2a/tasks/') && url.pathname.endsWith('/stream')) {
          return handleStreamingRequest(request, url);
        }
        return new Response('Not Found', { status: 404 });
    }
  },
};

/**
 * Serve the landing page
 */
function serveLandingPage() {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌍 Hello World A2A Agent</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container {
            background: white;
            border-radius: 10px;
            padding: 2rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }
        h1 { color: #667eea; margin-bottom: 0.5rem; }
        .subtitle { color: #666; margin-bottom: 2rem; font-size: 1.1rem; }
        .endpoint { 
            background: #f8f9fa; 
            padding: 1rem; 
            border-radius: 8px;
            margin: 1rem 0;
            border-left: 4px solid #667eea;
        }
        code {
            background: #f1f3f4;
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-family: 'Monaco', 'Consolas', monospace;
        }
        pre {
            background: #2d3748;
            color: #e2e8f0;
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
            font-size: 0.9rem;
        }
        a { color: #667eea; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .status {
            display: inline-block;
            background: #10b981;
            color: white;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.8rem;
            margin-bottom: 1rem;
        }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }
        .feature {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
        }
        .test-button {
            background: #667eea;
            color: white;
            border: none;
            padding: 0.8rem 1.5rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1rem;
        }
        .test-button:hover {
            background: #5a67d8;
        }
        #testResult {
            margin-top: 1rem;
            padding: 1rem;
            background: #f8f9fa;
            border-radius: 8px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="status">🟢 ONLINE</div>
        <h1>🌍 Hello World A2A Agent</h1>
        <p class="subtitle">A simple A2A Protocol compliant agent that always responds with "Hello, World!"</p>
        
        <h2>🔗 Endpoints</h2>
        
        <div class="endpoint">
            <strong>Agent Card (A2A Discovery):</strong><br>
            <code>GET ${new URL(request.url).origin}/.well-known/agent.json</code>
        </div>
        
        <div class="endpoint">
            <strong>A2A Protocol Endpoint:</strong><br>
            <code>POST ${new URL(request.url).origin}/a2a</code>
        </div>
        
        <h2>🧪 Quick Test</h2>
        
        <button class="test-button" onclick="testAgent()">Test Agent Now</button>
        <div id="testResult"></div>
        
        <h3>Or test with curl:</h3>
        <pre>curl -X POST ${new URL(request.url).origin}/a2a \\
  -H "Content-Type: application/json" \\
  -d '{
    "jsonrpc": "2.0",
    "method": "a2a.sendMessage",
    "params": {
      "taskUuid": "test-123",
      "messages": [{
        "role": "user",
        "content": {"type": "text", "text": "Say hello!"}
      }]
    },
    "id": "1"
  }'</pre>
        
        <h2>✨ Features</h2>
        <div class="features">
            <div class="feature">
                <h3>A2A Protocol v0.3.0</h3>
                <p>Fully compliant with official specification</p>
            </div>
            <div class="feature">
                <h3>JSON-RPC 2.0</h3>
                <p>Standard remote procedure calls</p>
            </div>
            <div class="feature">
                <h3>Streaming Support</h3>
                <p>Server-Sent Events (SSE) streaming</p>
            </div>
            <div class="feature">
                <h3>CORS Enabled</h3>
                <p>Works from any web application</p>
            </div>
        </div>
        
        <h2>📚 Resources</h2>
        <ul>
            <li><a href="https://a2aregistry.org">A2A Registry</a></li>
            <li><a href="https://a2a-protocol.org">A2A Protocol Specification</a></li>
            <li><a href="/.well-known/agent.json">View Agent Card</a></li>
        </ul>
    </div>

    <script>
        async function testAgent() {
            const button = document.querySelector('.test-button');
            const result = document.getElementById('testResult');
            
            button.textContent = 'Testing...';
            button.disabled = true;
            result.style.display = 'block';
            result.innerHTML = 'Sending request to agent...';
            
            try {
                const response = await fetch('/a2a', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'a2a.sendMessage',
                        params: {
                            taskUuid: 'web-test-' + Date.now(),
                            messages: [{
                                role: 'user',
                                content: { type: 'text', text: 'Test from web interface!' }
                            }]
                        },
                        id: Date.now()
                    })
                });
                
                const data = await response.json();
                
                if (data.result && data.result.result && data.result.result.messages) {
                    const message = data.result.result.messages[0].content.text;
                    result.innerHTML = \`
                        <strong>✅ Success!</strong><br>
                        Agent responded: <strong>"\${message}"</strong><br>
                        <small>Task UUID: \${data.result.taskUuid}</small>
                    \`;
                } else {
                    result.innerHTML = \`<strong>❌ Unexpected response:</strong><br><pre>\${JSON.stringify(data, null, 2)}</pre>\`;
                }
            } catch (error) {
                result.innerHTML = \`<strong>❌ Error:</strong> \${error.message}\`;
            }
            
            button.textContent = 'Test Agent Now';
            button.disabled = false;
        }
    </script>
</body>
</html>`;

  return new Response(html, {
    headers: {
      'Content-Type': 'text/html',
      'Cache-Control': 'public, max-age=300'
    }
  });
}

/**
 * Serve the A2A Protocol Agent Card
 */
function serveAgentCard() {
  const agentCard = {
    protocolVersion: '0.3.0',
    name: 'Hello World Agent',
    description: 'A simple A2A agent that always responds with Hello, World! Perfect for testing and learning.',
    url: 'https://hello.a2aregistry.org/a2a',
    version: '1.0.0',
    capabilities: {
      streaming: true,
      pushNotifications: false,
      stateTransitionHistory: false,
    },
    skills: [
      {
        id: 'hello',
        name: 'Say Hello',
        description: 'Responds with a friendly Hello, World! message regardless of input',
        tags: ['greeting', 'hello', 'test', 'demo', 'example'],
        examples: [
          'Say hello',
          'Hi there',
          'Greet me',
          'Hello',
          'Test message',
          'Anything at all'
        ],
        inputModes: ['text/plain', 'application/json'],
        outputModes: ['text/plain', 'application/json'],
      },
    ],
    defaultInputModes: ['text/plain', 'application/json'],
    defaultOutputModes: ['text/plain', 'application/json'],
    provider: {
      organization: 'A2A Registry Community',
      url: 'https://a2aregistry.org',
    },
    preferredTransport: 'JSONRPC',
    documentationUrl: 'https://hello.a2aregistry.org',
    iconUrl: 'https://hello.a2aregistry.org/icon.png',
  };

  return new Response(JSON.stringify(agentCard, null, 2), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=3600',
    },
  });
}

/**
 * Serve a simple icon (emoji as SVG)
 */
function serveIcon() {
  const svg = \`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
    <circle cx="50" cy="50" r="45" fill="#667eea"/>
    <text x="50" y="65" font-size="40" text-anchor="middle" fill="white">🌍</text>
  </svg>\`;

  return new Response(svg, {
    headers: {
      'Content-Type': 'image/svg+xml',
      'Cache-Control': 'public, max-age=86400'
    }
  });
}

/**
 * Handle CORS preflight requests
 */
function handleCORS() {
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Accept',
      'Access-Control-Max-Age': '86400',
    },
  });
}

/**
 * Handle A2A JSON-RPC requests
 */
async function handleA2ARequest(request) {
  if (request.method !== 'POST') {
    return new Response('Method Not Allowed', { 
      status: 405,
      headers: { 'Allow': 'POST' }
    });
  }

  let body;
  try {
    body = await request.json();
  } catch (e) {
    return createErrorResponse(-32700, 'Parse error', null);
  }

  // Validate JSON-RPC structure
  if (!body.jsonrpc || body.jsonrpc !== '2.0' || !body.method || body.id === undefined) {
    return createErrorResponse(-32600, 'Invalid Request', body.id || null);
  }

  // Handle A2A methods
  switch (body.method) {
    case 'a2a.sendMessage':
      return handleSendMessage(body);
    
    case 'a2a.sendStreamingMessage':
      return handleSendStreamingMessage(body);
    
    case 'a2a.getTask':
      return handleGetTask(body);
    
    default:
      return createErrorResponse(-32601, 'Method not found', body.id);
  }
}

/**
 * Handle a2a.sendMessage - the main message handling method
 */
function handleSendMessage(request) {
  const params = request.params || {};
  const taskUuid = params.taskUuid || generateUUID();
  
  const response = {
    jsonrpc: '2.0',
    result: {
      taskUuid: taskUuid,
      status: 'completed',
      result: {
        messages: [
          {
            role: 'assistant',
            content: {
              type: 'text',
              text: 'Hello, World! 👋'
            }
          }
        ]
      }
    },
    id: request.id
  };

  return new Response(JSON.stringify(response), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
  });
}

/**
 * Handle a2a.sendStreamingMessage - streaming version
 */
function handleSendStreamingMessage(request) {
  const params = request.params || {};
  const taskUuid = params.taskUuid || generateUUID();
  
  const response = {
    jsonrpc: '2.0',
    result: {
      taskUuid: taskUuid,
      status: 'streaming',
      streamUrl: \`\${new URL(request.url).origin}/a2a/tasks/\${taskUuid}/stream\`
    },
    id: request.id
  };

  return new Response(JSON.stringify(response), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
  });
}

/**
 * Handle a2a.getTask - get task status
 */
function handleGetTask(request) {
  const params = request.params || {};
  const taskUuid = params.taskUuid;
  
  if (!taskUuid) {
    return createErrorResponse(-32602, 'Invalid params: taskUuid required', request.id);
  }
  
  const response = {
    jsonrpc: '2.0',
    result: {
      taskUuid: taskUuid,
      status: 'completed',
      result: {
        messages: [
          {
            role: 'assistant',
            content: {
              type: 'text',
              text: 'Hello, World! 👋'
            }
          }
        ]
      }
    },
    id: request.id
  };

  return new Response(JSON.stringify(response), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
  });
}

/**
 * Handle Server-Sent Events streaming
 */
function handleStreamingRequest(request, url) {
  const encoder = new TextEncoder();
  
  const stream = new ReadableStream({
    async start(controller) {
      // Send connection established
      controller.enqueue(encoder.encode(': connected\n\n'));
      
      // Stream the hello message word by word
      const words = ['Hello,', ' ', 'World!', ' ', '👋'];
      for (let i = 0; i < words.length; i++) {
        const event = {
          type: 'contentDelta',
          delta: {
            text: words[i]
          }
        };
        controller.enqueue(encoder.encode(\`data: \${JSON.stringify(event)}\n\n\`));
        
        // Small delay between words for streaming effect
        await new Promise(resolve => setTimeout(resolve, 300));
      }
      
      // Send completion event
      const completeEvent = {
        type: 'complete',
        status: 'completed'
      };
      controller.enqueue(encoder.encode(\`data: \${JSON.stringify(completeEvent)}\n\n\`));
      
      controller.close();
    }
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
    },
  });
}

/**
 * Create a JSON-RPC error response
 */
function createErrorResponse(code, message, id) {
  const response = {
    jsonrpc: '2.0',
    error: { code, message },
    id: id,
  };

  return new Response(JSON.stringify(response), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    status: 200,
  });
}

/**
 * Generate a simple UUID v4
 */
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}