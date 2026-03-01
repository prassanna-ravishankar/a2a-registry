import os
import uuid

import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps.rest.fastapi_app import A2ARESTFastAPIApplication
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, Message, Part, Role, TaskState, TextPart
from a2a.utils.task import new_task

AGENT_URL = os.environ.get('AGENT_URL', 'http://localhost:8080')
PORT = int(os.environ.get('PORT', '8080'))
GITHUB_URL = 'https://github.com/prassanna-ravishankar/a2a-registry'


AGENT_CARD = AgentCard(
    name='Hello World Agent',
    description="A simple A2A agent that responds with 'Hello World' to any request",
    url=AGENT_URL,
    version='1.0.0',
    protocol_version='0.3.0',
    capabilities=AgentCapabilities(streaming=False, push_notifications=False, state_transition_history=False),
    default_input_modes=['text/plain', 'application/json'],
    default_output_modes=['text/plain', 'application/json'],
    skills=[AgentSkill(
        id='hello',
        name='Say Hello',
        description="Responds with a friendly 'Hello World' message",
        tags=['greeting', 'hello', 'simple'],
        examples=['Say hello', 'Greet me', 'Hello'],
    )],
    preferred_transport='HTTP+JSON',
    provider={'organization': 'A2A Registry Team', 'url': GITHUB_URL},
)


class HelloWorldExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        parts = context.message.parts if context.message else []
        user_text = ' '.join(p.root.text for p in parts if isinstance(p.root, TextPart)) or 'Hello'

        reply = Message(
            role=Role.agent,
            message_id=str(uuid.uuid4()),
            parts=[Part(root=TextPart(text=f'Hello World! You said: "{user_text}"'))],
            task_id=task.id,
            context_id=task.context_id,
        )
        await updater.update_status(TaskState.completed, message=reply)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


app = A2ARESTFastAPIApplication(
    agent_card=AGENT_CARD,
    http_handler=DefaultRequestHandler(
        agent_executor=HelloWorldExecutor(),
        task_store=InMemoryTaskStore(),
    ),
).build()


@app.get('/health')
def health():
    return {'status': 'ok'}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=PORT)
