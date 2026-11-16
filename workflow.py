"""Local LangGraph workflow: parse -> validate -> execute/reject -> report."""
import os
from typing import TypedDict

# This local prototype must not send voice transcripts to hosted tracing.
os.environ['LANGSMITH_TRACING'] = 'false'
os.environ['LANGCHAIN_TRACING_V2'] = 'false'

from langgraph.graph import StateGraph, START, END
from commands import CommandRunner, parse_command


class CommandState(TypedDict, total=False):
    text: str
    action: str | None
    allowed: bool
    result: str
    stop_requested: bool
    detail: str


def build_workflow(runner=None, cancelled=lambda: False, dry_run=False):
    runner = runner if runner is not None else CommandRunner()

    def interpret(state):
        action = parse_command(state['text'])
        return {'action': action, 'stop_requested': False,
                'detail': f'Matched action: {action}' if action else 'No supported command matched.'}

    def validate(state):
        allowed = state['action'] is not None and not cancelled()
        return {'allowed': allowed, 'detail': 'Supported command; session active.' if allowed else 'Unknown command or listening has stopped.'}

    def reject(state):
        return {'result': 'No action taken: unknown command or session stopped.', 'detail': 'Skipped execution.'}

    def execute(state):
        if cancelled():
            return {'result': 'Cancelled before execution.', 'detail': 'No action taken.'}
        if state['action'] == 'stop':
            return {'result': 'Stopping listening.', 'stop_requested': True, 'detail': 'Requested microphone stop.'}
        if dry_run:
            return {'result': f'Demo only: would run {state["action"]}. No application opened.', 'detail': 'Simulated action; no side effects.'}
        try:
            result = runner.run(state['text'])
        except Exception as exc:
            result = f'Action failed: {exc}'
        return {'result': result, 'detail': result}

    def report(state):
        return {'detail': state['result']}

    builder = StateGraph(CommandState)
    for name, node in [('interpret', interpret), ('validate', validate), ('execute', execute), ('reject', reject), ('report', report)]:
        builder.add_node(name, node)
    builder.add_edge(START, 'interpret')
    builder.add_edge('interpret', 'validate')
    builder.add_conditional_edges('validate', lambda state: 'execute' if state['allowed'] else 'reject', {'execute': 'execute', 'reject': 'reject'})
    builder.add_edge('execute', 'report')
    builder.add_edge('reject', 'report')
    builder.add_edge('report', END)
    return builder.compile()


if __name__ == '__main__':
    graph = build_workflow(dry_run=True)
    for phrase in ['computer open notepad', 'computer delete files', 'computer stop listening']:
        print(f'\nYou said: {phrase}')
        for update in graph.stream({'text': phrase}, stream_mode='updates'):
            for node, state in update.items():
                print(f'  {node.upper()}: {state["detail"]}')
