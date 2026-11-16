"""Offline voice input and a small set of fixed laptop commands."""
import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk

import sounddevice as sd
from vosk import KaldiRecognizer, Model, SetLogLevel
from commands import CommandRunner
from workflow import build_workflow

MODEL_PATH = Path(__file__).resolve().parent / 'models' / 'vosk-model-small-en-us-0.15'


class VoiceTest:
    def __init__(self, root):
        self.root = root
        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.worker = None
        self.model = None
        self.closing = False
        self.devices = []
        self.runner = CommandRunner()
        self.graph = build_workflow(self.runner, cancelled=lambda: self.stop_event.is_set() or self.closing)
        root.title('Laptop Voice — LangGraph')
        root.geometry('800x650')
        root.minsize(580, 420)
        root.protocol('WM_DELETE_WINDOW', self.close)
        frame = ttk.Frame(root, padding=22)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Your voice. Your laptop.', font=('Segoe UI', 22, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Say “computer” followed by a supported command. English • Offline').pack(anchor='w', pady=(4, 20))
        ttk.Label(frame, text='Workflow: Interpret → Validate → Execute / Skip → Report').pack(anchor='w', pady=(0, 12))
        ttk.Label(frame, text='Microphone').pack(anchor='w')
        self.device_box = ttk.Combobox(frame, state='readonly')
        self.device_box.pack(fill='x', pady=(5, 12))
        buttons = ttk.Frame(frame)
        buttons.pack(fill='x')
        self.start_button = ttk.Button(buttons, text='Start listening', command=self.start)
        self.start_button.pack(side='left')
        self.stop_button = ttk.Button(buttons, text='Stop', command=self.stop, state='disabled')
        self.stop_button.pack(side='left', padx=8)
        self.refresh_button = ttk.Button(buttons, text='Refresh microphones', command=self.refresh_devices)
        self.refresh_button.pack(side='left')
        ttk.Button(buttons, text='Clear text', command=self.clear).pack(side='right')
        self.status = tk.StringVar(value='Ready. Press Start listening when you want to speak.')
        ttk.Label(frame, textvariable=self.status, wraplength=680).pack(anchor='w', pady=14)
        self.partial = tk.StringVar(value='')
        ttk.Label(frame, textvariable=self.partial, wraplength=680, foreground='#355e88').pack(anchor='w', pady=(0, 12))
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill='both', expand=True)
        self.text = tk.Text(text_frame, wrap='word', font=('Segoe UI', 13), state='disabled', height=8)
        scroll = ttk.Scrollbar(text_frame, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.text.pack(fill='both', expand=True)
        ttk.Label(frame, text='Say one complete command, then pause:\ncomputer open Chrome  •  computer open Visual Studio Code\ncomputer open Notepad  •  computer open Calculator\ncomputer open project folder  •  computer stop listening', wraplength=680).pack(anchor='w', pady=(12, 4))
        ttk.Label(frame, text='Audio is processed in memory, never saved. Closing this window clears the transcript.').pack(anchor='w')
        self.refresh_devices()
        self.root.after(80, self.poll)

    def refresh_devices(self):
        try:
            devices = sd.query_devices()
            default = sd.default.device[0]
            self.devices = [(index, info) for index, info in enumerate(devices) if info['max_input_channels'] > 0]
            self.device_box['values'] = [f"{info['name']} ({sd.query_hostapis(info['hostapi'])['name']})" for _, info in self.devices]
            if not self.devices:
                raise RuntimeError('No microphone found. Connect one, then press Refresh microphones.')
            self.device_box.current(next((i for i, (index, _) in enumerate(self.devices) if index == default), 0))
            self.start_button.configure(state='normal')
            self.status.set('Ready. Press Start listening when you want to speak.')
        except Exception as exc:
            self.status.set(f'Microphone unavailable: {exc}')
            self.start_button.configure(state='disabled')

    def clear(self):
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        self.text.configure(state='disabled')
        self.partial.set('')

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        selection = self.device_box.current()
        if selection < 0:
            return
        device, info = self.devices[selection]
        self.stop_event.clear()
        self.start_button.configure(state='disabled')
        self.refresh_button.configure(state='disabled')
        self.device_box.configure(state='disabled')
        self.stop_button.configure(state='normal')
        self.status.set('Loading speech model…')
        self.worker = threading.Thread(target=self.listen, args=(device, int(info['default_samplerate'])), daemon=True)
        self.worker.start()

    def stop(self):
        self.stop_event.set()
        self.stop_button.configure(state='disabled')
        self.status.set('Stopping microphone…')

    def listen(self, device, rate):
        audio = queue.Queue(maxsize=32)

        def callback(data, frames, timing, status):
            if self.stop_event.is_set():
                return
            if status:
                self.events.put(('warning', f'Audio warning: {status}'))
            try:
                audio.put_nowait(bytes(data))
            except queue.Full:
                self.events.put(('warning', 'Audio processing fell behind. Try speaking in shorter phrases.'))

        try:
            SetLogLevel(-1)
            if self.model is None:
                if not (MODEL_PATH / 'am' / 'final.mdl').is_file():
                    raise RuntimeError('English model is missing. Run the setup check.')
                self.model = Model(str(MODEL_PATH))
            if self.stop_event.is_set():
                return
            recognizer = KaldiRecognizer(self.model, rate)
            last_partial = ''
            with sd.RawInputStream(device=device, samplerate=rate, blocksize=max(1, rate // 5), dtype='int16', channels=1, callback=callback):
                self.events.put(('status', 'Listening — speak now. Press Stop when finished.'))
                while not self.stop_event.is_set():
                    try:
                        block = audio.get(timeout=0.15)
                    except queue.Empty:
                        continue
                    if recognizer.AcceptWaveform(block):
                        self.events.put(('text', json.loads(recognizer.Result()).get('text', '')))
                        last_partial = ''
                    else:
                        partial = json.loads(recognizer.PartialResult()).get('partial', '')
                        if partial != last_partial:
                            self.events.put(('partial', partial))
                            last_partial = partial
            # Complete audio already captured before Stop, with microphone now closed.
            while not audio.empty():
                if recognizer.AcceptWaveform(audio.get_nowait()):
                    self.events.put(('text', json.loads(recognizer.Result()).get('text', '')))
            self.events.put(('text', json.loads(recognizer.FinalResult()).get('text', '')))
        except Exception as exc:
            self.events.put(('error', f'{exc} Check the selected microphone and Windows microphone permissions.'))
        finally:
            self.events.put(('done', None))

    def poll(self):
        while not self.events.empty():
            kind, value = self.events.get_nowait()
            if kind in ('status', 'warning', 'error'):
                if kind != 'status' or not self.stop_event.is_set():
                    self.status.set(value)
            elif kind == 'partial':
                self.partial.set(value)
            elif kind == 'text':
                self.partial.set('')
                if value:
                    self.text.configure(state='normal')
                    self.text.insert('end', value + '\n')
                    # Only completed speech from an active session may trigger actions.
                    # Late results after Stop or Close remain transcript-only.
                    if not self.stop_event.is_set() and not self.closing:
                        try:
                            for update in self.graph.stream({'text': value}, stream_mode='updates'):
                                for node, state in update.items():
                                    self.text.insert('end', f'  [{node}] {state["detail"]}\n')
                                    if state.get('stop_requested'):
                                        self.stop()
                        except Exception as exc:
                            self.text.insert('end', f'  Workflow failed: {exc}\n')
                    self.text.see('end')
                    self.text.configure(state='disabled')
            elif kind == 'done':
                self.start_button.configure(state='normal')
                self.stop_button.configure(state='disabled')
                self.refresh_button.configure(state='normal')
                self.device_box.configure(state='readonly')
                if self.status.get().startswith(('Listening', 'Stopping', 'Loading')):
                    self.status.set('Stopped. Press Start listening to try again.')
        if self.closing and (self.worker is None or not self.worker.is_alive()):
            self.root.destroy()
            return
        self.root.after(80, self.poll)

    def close(self):
        self.closing = True
        self.stop()
        self.root.withdraw()


if __name__ == '__main__':
    root = tk.Tk()
    VoiceTest(root)
    root.mainloop()
