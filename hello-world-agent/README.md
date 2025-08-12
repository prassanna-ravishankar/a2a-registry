# Hello World A2A Agent

A simple A2A Protocol compliant agent that always responds with "Hello, World!" - perfect for testing the A2A Registry.

## Quick Deploy to Cloudflare Workers

1. **Create Worker**: Cloudflare Dashboard → Workers → Create Worker
2. **Paste Code**: Copy `worker.js` content into the worker
3. **Add Domain**: Add custom domain `hello.a2aregistry.org`
4. **Test**: Visit your domain and click "Test Agent Now"

## What It Does

- Serves a landing page at `/` with live testing
- Provides A2A Agent Card at `/.well-known/agent.json`
- Handles A2A Protocol requests at `/a2a`
- Supports streaming via Server-Sent Events
- Always responds with "Hello, World! 👋"

## Test Commands

```bash
# Test agent card
curl https://hello.a2aregistry.org/.well-known/agent.json

# Test A2A endpoint
curl -X POST https://hello.a2aregistry.org/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "a2a.sendMessage",
    "params": {
      "messages": [{"role": "user", "content": {"type": "text", "text": "Hi!"}}]
    },
    "id": "1"
  }'
```

## Registry Entry

Once deployed, submit this to the A2A Registry as `agents/hello-world.json`:

```json
{
  "protocolVersion": "0.3.0",
  "name": "Hello World Agent",
  "description": "A simple A2A agent that always responds with Hello, World!",
  "url": "https://hello.a2aregistry.org/a2a",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "stateTransitionHistory": false
  },
  "skills": [{
    "id": "hello",
    "name": "Say Hello",
    "description": "Always responds with Hello, World! regardless of input",
    "tags": ["greeting", "hello", "test", "demo"],
    "inputModes": ["text/plain", "application/json"],
    "outputModes": ["text/plain", "application/json"]
  }],
  "defaultInputModes": ["text/plain", "application/json"],
  "defaultOutputModes": ["text/plain", "application/json"],
  "provider": {
    "organization": "A2A Registry Community",
    "url": "https://a2aregistry.org"
  },
  "author": "A2A Registry Community",
  "wellKnownURI": "https://hello.a2aregistry.org/.well-known/agent.json",
  "homepage": "https://hello.a2aregistry.org",
  "license": "MIT",
  "pricing": { "model": "free" }
}
```

## License

MIT