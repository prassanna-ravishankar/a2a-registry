/**
 * A2A Protocol Client for Browser-based Agent Communication
 * Implements the A2A protocol specification for HTTP+JSON/REST transport
 */

/**
 * Fetches the agent card from the wellKnownURI
 * @param {string} wellKnownURI - URL to the agent's .well-known/agent-card.json
 * @returns {Promise<Object>} - The agent card object
 */
export async function fetchAgentCard(wellKnownURI) {
    try {
        const response = await fetch(wellKnownURI, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Failed to fetch agent card: HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error fetching agent card:', error);
        throw error;
    }
}

/**
 * Extracts the communication endpoint URL and transport from the agent card
 * @param {Object} agentCard - The agent card object
 * @returns {{url: string, transport: string}} - The base URL and transport protocol
 */
export function getAgentEndpoint(agentCard) {
    let url, transport;

    // Try interfaces first (newer spec)
    if (agentCard.interfaces && agentCard.interfaces.length > 0) {
        // Prefer REST/HTTP+JSON transport
        const restInterface = agentCard.interfaces.find(i =>
            i.transport === 'HTTP+JSON' || i.transport === 'REST'
        );

        if (restInterface) {
            url = restInterface.url;
            transport = restInterface.transport;
        } else {
            // Use first available interface
            url = agentCard.interfaces[0].url;
            transport = agentCard.interfaces[0].transport;
        }
    } else if (agentCard.url) {
        // Fallback to url field (older spec)
        url = agentCard.url;
        // Use preferredTransport or default to JSONRPC per A2A spec
        transport = agentCard.preferredTransport || 'JSONRPC';
    } else {
        throw new Error('No communication endpoint found in agent card');
    }

    return { url, transport };
}

/**
 * Generates a unique message ID
 * @returns {string} - UUID v4
 */
function generateMessageId() {
    return crypto.randomUUID();
}

/**
 * Sends a message to an A2A agent
 * @param {string} agentEndpoint - Base URL of the agent
 * @param {string} userMessage - The message text to send
 * @param {Object} options - Additional options
 * @param {boolean} options.streaming - Whether to request streaming response
 * @param {string[]} options.acceptedOutputModes - Accepted output MIME types
 * @param {string} options.transport - Transport protocol ('JSONRPC', 'REST', 'HTTP+JSON')
 * @param {string} options.contextId - Context ID for maintaining conversation continuity
 * @returns {Promise<Object>} - The response (Task or Message object)
 */
export async function sendMessage(agentEndpoint, userMessage, options = {}) {
    const {
        streaming = false,
        acceptedOutputModes = ['text/plain', 'application/json'],
        transport = 'REST',
        contextId = generateMessageId() // Generate new context if not provided
    } = options;

    const messagePayload = {
        kind: 'message',
        messageId: generateMessageId(),
        contextId: contextId, // Use provided contextId for session continuity
        role: 'user',
        parts: [{ kind: 'text', text: userMessage }]
    };

    const requestParams = {
        message: messagePayload,
        configuration: {
            acceptedOutputModes
        }
    };

    // Determine endpoint and payload based on transport
    let endpoint, payload, contentType;

    if (transport === 'JSONRPC') {
        // JSON-RPC 2.0 format
        endpoint = agentEndpoint;
        const method = streaming ? 'message/stream' : 'message/send';
        payload = {
            jsonrpc: '2.0',
            method: method,
            params: requestParams,
            id: generateMessageId()
        };
        contentType = 'application/json';
    } else {
        // REST/HTTP+JSON format
        endpoint = streaming
            ? `${agentEndpoint}/v1/message:stream`
            : `${agentEndpoint}/v1/message:send`;
        payload = requestParams;
        contentType = 'application/json';
    }

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': contentType,
                'Accept': streaming ? 'text/event-stream' : 'application/json',
                'A2A-Version': '0.3'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            // Try to parse error details
            const contentType = response.headers.get('content-type');
            if (contentType?.includes('application/problem+json') || contentType?.includes('application/json')) {
                const errorDetails = await response.json();
                throw new Error(errorDetails.detail || errorDetails.title || errorDetails.error?.message || `HTTP ${response.status}`);
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        // Handle streaming response
        if (streaming && response.headers.get('content-type')?.includes('text/event-stream')) {
            return response; // Return response object for SSE parsing
        }

        // Handle non-streaming response
        const result = await response.json();

        // Unwrap JSON-RPC response if needed
        if (transport === 'JSONRPC' && result.result) {
            return result.result;
        }

        return result;
    } catch (error) {
        console.error('Error sending A2A message:', error);
        throw error;
    }
}

/**
 * Parse Server-Sent Events stream from a streaming response
 * @param {Response} response - The fetch Response object with SSE stream
 * @param {Function} onEvent - Callback for each event (receives parsed JSON)
 * @param {Function} onError - Callback for errors
 * @param {Function} onComplete - Callback when stream completes
 */
export async function parseSSEStream(response, onEvent, onError, onComplete) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
        while (true) {
            const { done, value } = await reader.read();

            if (done) {
                onComplete?.();
                break;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // Keep incomplete line in buffer

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        onEvent(data);
                    } catch (parseError) {
                        console.error('Failed to parse SSE data:', parseError);
                    }
                }
            }
        }
    } catch (error) {
        onError?.(error);
    }
}

/**
 * Extracts text content from an A2A Message object
 * @param {Object} message - A2A Message object
 * @returns {string} - Extracted text
 */
export function extractMessageText(message) {
    if (!message || !message.parts) return '';

    return message.parts
        .filter(part => part.text)
        .map(part => part.text)
        .join('');
}

/**
 * Polls a task until it reaches a terminal state
 * @param {string} agentEndpoint - Base URL of the agent
 * @param {string} taskId - Task ID to poll
 * @param {string} transport - Transport protocol
 * @param {Function} onUpdate - Callback for task updates
 * @returns {Promise<Object>} - Final task object
 */
export async function pollTask(agentEndpoint, taskId, transport, onUpdate) {
    const maxAttempts = 60; // 60 seconds max
    const pollInterval = 1000; // Poll every second

    for (let i = 0; i < maxAttempts; i++) {
        const taskParams = { id: taskId };

        let endpoint, payload;

        if (transport === 'JSONRPC') {
            endpoint = agentEndpoint;
            payload = {
                jsonrpc: '2.0',
                method: 'tasks/get',
                params: taskParams,
                id: generateMessageId()
            };
        } else {
            endpoint = `${agentEndpoint}/v1/tasks/${taskId}`;
            payload = null; // GET request
        }

        const response = await fetch(endpoint, {
            method: transport === 'JSONRPC' ? 'POST' : 'GET',
            headers: {
                'Content-Type': 'application/json',
                'A2A-Version': '0.3'
            },
            body: payload ? JSON.stringify(payload) : null
        });

        if (!response.ok) {
            throw new Error(`Failed to poll task: HTTP ${response.status}`);
        }

        const result = await response.json();
        const task = transport === 'JSONRPC' && result.result ? result.result : result;

        // Call update callback
        if (onUpdate) {
            onUpdate(task);
        }

        // Check if task is in terminal state
        const state = task.status?.state;
        if (state === 'completed' || state === 'failed' || state === 'cancelled' || state === 'rejected') {
            return task;
        }

        // Wait before next poll
        await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    throw new Error('Task polling timed out');
}

/**
 * Extracts text from an A2A Task response
 * @param {Object} task - A2A Task object
 * @returns {string} - Extracted text or status info
 */
export function extractTaskText(task) {
    if (!task) return '';

    // Check for artifacts with text content
    if (task.artifacts && task.artifacts.length > 0) {
        const textArtifact = task.artifacts.find(a => a.parts);
        if (textArtifact) {
            return textArtifact.parts
                .filter(part => part.text)
                .map(part => part.text)
                .join('');
        }
    }

    // Fallback to status description
    if (task.status) {
        return `Task ${task.status.state || 'unknown'}`;
    }

    return 'Processing...';
}
