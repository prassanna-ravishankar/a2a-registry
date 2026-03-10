---
name: generate-notes
description: Test registered agents and set maintainer notes based on results.
---

# Generate Maintainer Notes

Test all healthy registered agents by sending A2A `message/send` requests and set maintainer notes based on the results.

## Prerequisites

- Admin API key from k8s: `kubectl get secret a2aregistry-secrets -n a2aregistry -o jsonpath='{.data.ADMIN_API_KEY}' | base64 -d`
- The `client-python/examples/send_messages.py` script (or equivalent logic)
- Backend must be deployed with the `maintainer_notes` feature

## Step 1: Fetch All Agents

```bash
curl -s 'https://a2aregistry.org/api/agents?limit=200' | python3 -c "
import json, sys
data = json.load(sys.stdin)
agents = data.get('agents', data)
for a in agents:
    print(f\"{a['id']} | {a['name'][:40]:<40} | healthy={a.get('is_healthy')} | conformance={a.get('conformance')} | notes={a.get('maintainer_notes', '(none)')[:60]}\")
print(f'\nTotal: {len(agents)}')
"
```

## Step 2: Test Healthy Agents

Run the send_messages script from `client-python/`:

```bash
cd client-python && uv run --extra all python examples/send_messages.py
```

This tests all healthy conformant agents with >90% uptime. For broader coverage, modify the filter in the script.

## Step 3: Categorize Results

Classify each agent into one of these categories based on the test output:

| Category | HTTP/Error | Note Template |
|----------|-----------|---------------|
| **Working** | Got a text response | `Verified working. Agent responds to \`message/send\` correctly via A2A SDK.` |
| **404 Not Found** | 404 on message/send | `A2A endpoint returns **404 Not Found** when sending messages. The agent card is served correctly but the \`message/send\` endpoint does not exist at the expected URL.` |
| **405 Method Not Allowed** | 405 on message/send | `Agent card is valid but the A2A endpoint returns **405 Method Not Allowed**. Ensure your server accepts POST requests for \`message/send\` at the URL in your agent card.` |
| **401 Unauthorized (no standard auth)** | 401, no securitySchemes | `Agent requires authentication (returns **401 Unauthorized**) but does not declare \`securitySchemes\` / \`security\` in the agent card. See the A2A spec for the correct format.` |
| **401 Unauthorized (proper auth)** | 401, has securitySchemes | `Agent requires authentication (returns **401 Unauthorized**). The agent card correctly declares \`securitySchemes\` — callers need valid credentials.` |
| **Non-compliant response** | ValidationError from SDK | `Agent responds but the response is missing required A2A fields. The response cannot be parsed by standard A2A SDK clients. Update your response format to match the latest A2A spec.` (include specific missing fields) |
| **No compatible transports** | ValueError: no transports | `Agent card does not declare any compatible A2A transports. The A2A SDK cannot connect.` |
| **DNS failure** | nodename not provided | `Agent card URL fails DNS resolution — the host appears to be down or decommissioned.` |
| **Timeout** | ReadTimeout | `Agent endpoint is reachable but times out when processing \`message/send\` requests.` |

For 401 agents, check if they declare auth properly:
```bash
curl -s "<wellKnownURI>" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('securitySchemes:', d.get('securitySchemes', '(none)'))
print('security:', d.get('security', '(none)'))
# Also check non-standard fields
for k in d:
    if 'auth' in k.lower():
        print(f'{k}:', d[k])
"
```

## Step 4: Set Notes via Admin API

```bash
ADMIN_KEY="<key from step 0>"
API="https://a2aregistry.org/api"

curl -s -X PATCH "$API/agents/<agent-id>/notes" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -d '{"notes": "<markdown note>"}'
```

To clear notes: `{"notes": null}`

## Step 5: Verify

```bash
curl -s 'https://a2aregistry.org/api/agents?limit=200' | python3 -c "
import json, sys
data = json.load(sys.stdin)
agents = data.get('agents', data)
noted = [a for a in agents if a.get('maintainer_notes')]
for a in noted:
    print(f\"  {a['name']}: {a['maintainer_notes'][:100]}...\")
print(f'\n{len(noted)} agents with notes out of {len(agents)} total')
"
```

## Notes

- Only set notes for agents you've actually tested — don't guess
- Include specific error details (HTTP codes, missing fields) so developers can fix issues
- Use markdown formatting: `**bold**` for error codes, backticks for field names
- "Verified working" notes are valuable too — they signal to users which agents are functional
- Re-run periodically as agents may fix their issues or new agents may register
