import os
import uuid

import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers.default_request_handler import LegacyRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill, Message, Part, Role, TaskState
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

AGENT_URL = os.environ.get('AGENT_URL', 'http://localhost:8080')
PORT = int(os.environ.get('PORT', '8080'))
GITHUB_URL = 'https://github.com/prassanna-ravishankar/a2a-registry'

AGENT_CARD = AgentCard(
    name='Hello World Agent',
    description="A simple A2A agent that responds with 'Hello World' to any request",
    version='1.0.0',
    supported_interfaces=[AgentInterface(url=AGENT_URL)],
    capabilities=AgentCapabilities(streaming=False, push_notifications=False),
    default_input_modes=['text/plain', 'application/json'],
    default_output_modes=['text/plain', 'application/json'],
    skills=[AgentSkill(
        id='hello',
        name='Say Hello',
        description="Responds with a friendly 'Hello World' message",
        tags=['greeting', 'hello', 'simple'],
        examples=['Say hello', 'Greet me', 'Hello'],
    )],
    provider={'organization': 'A2A Registry Team', 'url': GITHUB_URL},
)


class HelloWorldExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)

        parts = context.message.parts if context.message else []
        user_text = ' '.join(p.text for p in parts if p.text) or 'Hello'

        reply = Message(
            role=Role.ROLE_AGENT,
            message_id=str(uuid.uuid4()),
            parts=[Part(text=f'Hello World! You said: "{user_text}"')],
        )
        await updater.update_status(TaskState.TASK_STATE_COMPLETED, message=reply)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


handler = LegacyRequestHandler(
    agent_executor=HelloWorldExecutor(),
    task_store=InMemoryTaskStore(),
    agent_card=AGENT_CARD,
)

async def health(request):
    return JSONResponse({'status': 'ok'})

routes = [
    *create_agent_card_routes(AGENT_CARD),
    *create_jsonrpc_routes(handler, rpc_url='/', enable_v0_3_compat=True),
    Route('/health', health),
]

app = Starlette(routes=routes)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=PORT)
