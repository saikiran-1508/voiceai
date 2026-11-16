"""Exact voice-command matching and fixed Windows actions. Never execute speech as code."""
import os
from pathlib import Path
import re
import subprocess
import time

PROJECT = Path(__file__).resolve().parent
PHRASES = {
    'computer open chrome': 'chrome',
    'computer open vs code': 'vscode',
    'computer open v s code': 'vscode',
    'computer open visual studio code': 'vscode',
    'computer open notepad': 'notepad',
    'computer open calculator': 'calculator',
    'computer open project folder': 'folder',
    'computer stop listening': 'stop',
}


def parse_command(text):
    normalized = re.sub(r'\s+', ' ', text.lower().strip()).rstrip('.!?')
    return PHRASES.get(normalized)


def find_app(action):
    local = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local')))
    program = Path(os.environ.get('ProgramFiles', 'C:/Program Files'))
    program86 = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)'))
    windows = Path(os.environ.get('SystemRoot', 'C:/Windows'))
    candidates = {
        'chrome': [program / 'Google/Chrome/Application/chrome.exe', local / 'Google/Chrome/Application/chrome.exe', program86 / 'Google/Chrome/Application/chrome.exe'],
        'vscode': [local / 'Programs/Microsoft VS Code/Code.exe', program / 'Microsoft VS Code/Code.exe', program86 / 'Microsoft VS Code/Code.exe'],
        'notepad': [windows / 'System32/notepad.exe'],
        'calculator': [windows / 'System32/calc.exe'],
    }
    # Some launch environments redirect LOCALAPPDATA; also check the user's
    # standard installation directory without changing their environment.
    if action == 'vscode':
        candidates[action].append(Path.home() / 'AppData/Local/Programs/Microsoft VS Code/Code.exe')
    elif action == 'chrome':
        candidates[action].append(Path.home() / 'AppData/Local/Google/Chrome/Application/chrome.exe')
    return next((path for path in candidates.get(action, []) if path.is_file()), None)


class CommandRunner:
    def __init__(self):
        self.last_run = {}

    def run(self, text):
        action = parse_command(text)
        if action is None:
            return 'No action: say one of the listed commands beginning with “computer”.'
        if action == 'stop':
            return 'Stopping listening.'
        now = time.monotonic()
        if now - self.last_run.get(action, -100) < 3:
            return 'Repeated command ignored. Wait a few seconds before trying again.'
        if action == 'folder':
            os.startfile(str(PROJECT))
            result = 'Requested opening of the project folder.'
        else:
            executable = find_app(action)
            if executable is None:
                return f'Could not find {action}. Install it in its standard location, then try again.'
            args = [str(executable)]
            if action == 'vscode':
                args.append(str(PROJECT))
            subprocess.Popen(args, shell=False, cwd=PROJECT)
            result = f'Launch requested: {executable.stem}.'
        self.last_run[action] = now
        return result
