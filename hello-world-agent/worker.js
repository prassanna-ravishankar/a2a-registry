/**
 * Hello World A2A Agent for Cloudflare Workers
 * Responds with "Hello World" to any A2A request
 */

export default {
  async fetch(request, env) {
    // Get configuration from environment variables/secrets
    // Only AGENT_URL is really needed - everything else has good defaults
    const AGENT_URL = env.AGENT_URL || request.url.split('/')[0] + '//' + request.url.split('/')[2];
    const AUTHOR_NAME = env.AUTHOR_NAME || 'A2A Registry Team';
    const GITHUB_URL = env.GITHUB_URL || 'https://github.com/prassanna-ravishankar/a2a-registry';
    
    // Build Agent Card dynamically
    const AGENT_CARD = {
      protocolVersion: "0.3.0",
      name: "Hello World Agent",
      description: "A simple A2A agent that responds with 'Hello World' to any request",
      url: `${AGENT_URL}/a2a`,
      version: "1.0.0",
      capabilities: {
        streaming: false,
        pushNotifications: false,
        stateTransitionHistory: false
      },
      skills: [
        {
          id: "hello",
          name: "Say Hello",
          description: "Responds with a friendly 'Hello World' message",
          tags: ["greeting", "hello", "simple"],
          inputModes: ["text/plain", "application/json"],
          outputModes: ["text/plain", "application/json"],
          examples: ["Say hello", "Greet me", "Hello"]
        }
      ],
      defaultInputModes: ["text/plain", "application/json"],
      defaultOutputModes: ["text/plain", "application/json"],
      provider: {
        organization: AUTHOR_NAME,
        url: GITHUB_URL
      },
      preferredTransport: "REST",
      documentationUrl: GITHUB_URL,
      author: AUTHOR_NAME,
      homepage: AGENT_URL,
      license: "MIT"
    };
    const url = new URL(request.url);
    
    // CORS headers for all responses
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, A2A-Version, Accept',
    };

    // Handle preflight requests
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: corsHeaders
      });
    }

    // Handle .well-known/agent-card.json endpoint
    if (url.pathname === '/.well-known/agent-card.json' || url.pathname === '/.well-known/agent.json') {
      return new Response(JSON.stringify(AGENT_CARD, null, 2), {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders
        }
      });
    }

    // Handle A2A REST endpoint: POST /v1/message:send
    if (url.pathname === '/a2a/v1/message:send' && request.method === 'POST') {
      try {
        const body = await request.json();

        // Extract user message from A2A SendMessageRequest format (handle multiple text parts)
        const userMessage = body.message?.parts?.filter(part => part.text).map(part => part.text).join('\n') || 'Hello';

        // Return A2A Message response
        const a2aResponse = {
          message: {
            messageId: crypto.randomUUID(),
            role: 'assistant',
            parts: [{
              kind: 'text',
              text: `Hello World! You said: "${userMessage}"`
            }],
            timestamp: new Date().toISOString()
          }
        };

        return new Response(JSON.stringify(a2aResponse, null, 2), {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });

      } catch (error) {
        return new Response(JSON.stringify({
          type: "https://a2a-protocol.org/errors/invalid-request",
          title: "Invalid Request",
          status: 400,
          detail: error.message
        }), {
          status: 400,
          headers: {
            'Content-Type': 'application/problem+json',
            ...corsHeaders
          }
        });
      }
    }

    // Legacy /a2a endpoint for backwards compatibility
    if (url.pathname === '/a2a' && request.method === 'POST') {
      try {
        const contentType = request.headers.get('content-type') || '';
        let input = '';

        if (contentType.includes('application/json')) {
          const body = await request.json();
          input = body.message || body.text || JSON.stringify(body);
        } else {
          input = await request.text();
        }

        // Simple response - always return "Hello World"
        const response = {
          message: "Hello World",
          timestamp: new Date().toISOString(),
          receivedInput: input,
          agentVersion: AGENT_CARD.version
        };

        return new Response(JSON.stringify(response, null, 2), {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });

      } catch (error) {
        return new Response(JSON.stringify({
          error: "Invalid request",
          message: error.message
        }), {
          status: 400,
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }
    }

    // Handle root path - show basic info
    if (url.pathname === '/') {
      const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hello World A2A Agent</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { color: #333; }
        .endpoint {
            background: #f0f0f0;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            margin: 0.5rem 0;
            font-family: monospace;
        }
        a {
            color: #0066cc;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .test-section {
            margin-top: 2rem;
            padding-top: 2rem;
            border-top: 1px solid #e0e0e0;
        }
        textarea {
            width: 100%;
            min-height: 100px;
            margin: 0.5rem 0;
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: monospace;
        }
        button {
            background: #0066cc;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background: #0052a3;
        }
        #response {
            margin-top: 1rem;
            padding: 1rem;
            background: #f9f9f9;
            border-radius: 4px;
            white-space: pre-wrap;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌍 Hello World A2A Agent</h1>
        <p>A simple A2A Protocol compliant agent that responds with "Hello World" to any request.</p>
        
        <h2>Endpoints</h2>
        <div class="endpoint">GET <a href="/.well-known/agent-card.json">/.well-known/agent-card.json</a></div>
        <div class="endpoint">POST /a2a/v1/message:send (A2A Protocol)</div>
        <div class="endpoint">POST /a2a (Legacy)</div>
        
        <h2>Agent Information</h2>
        <ul>
            <li><strong>Protocol Version:</strong> ${AGENT_CARD.protocolVersion}</li>
            <li><strong>Agent Version:</strong> ${AGENT_CARD.version}</li>
            <li><strong>Skills:</strong> ${AGENT_CARD.skills.map(s => s.name).join(', ')}</li>
        </ul>

        <div class="test-section">
            <h2>Test the Agent</h2>
            <p>Send a test message to the A2A endpoint:</p>
            <textarea id="testInput" placeholder='Enter your message or JSON like {"message": "Hello"}'></textarea>
            <button onclick="testAgent()">Send Request</button>
            <div id="response"></div>
        </div>
    </div>

    <script>
        async function testAgent() {
            const input = document.getElementById('testInput').value;
            const responseDiv = document.getElementById('response');
            
            try {
                let body;
                let contentType;
                
                // Try to parse as JSON first
                try {
                    body = JSON.stringify(JSON.parse(input));
                    contentType = 'application/json';
                } catch {
                    // If not JSON, send as plain text
                    body = input;
                    contentType = 'text/plain';
                }
                
                const response = await fetch('/a2a', {
                    method: 'POST',
                    headers: {
                        'Content-Type': contentType
                    },
                    body: body
                });
                
                const result = await response.json();
                responseDiv.textContent = JSON.stringify(result, null, 2);
                responseDiv.style.color = response.ok ? '#008000' : '#cc0000';
            } catch (error) {
                responseDiv.textContent = 'Error: ' + error.message;
                responseDiv.style.color = '#cc0000';
            }
        }
    </script>
</body>
</html>
      `;
      
      return new Response(html, {
        status: 200,
        headers: {
          'Content-Type': 'text/html',
          ...corsHeaders
        }
      });
    }

    // 404 for other paths
    return new Response('Not Found', {
      status: 404,
      headers: corsHeaders
    });
  }
};
