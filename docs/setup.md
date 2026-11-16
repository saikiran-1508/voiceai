# Development setup

Target platform: Windows. The local prototype was checked using Python 3.13.

Create an isolated environment from the repository folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Download `vosk-model-small-en-us-0.15` from the official model list:
https://alphacephei.com/vosk/models

Extract it into `models/vosk-model-small-en-us-0.15/`. The extracted directory
should contain `am/final.mdl`. The environment and model files are excluded from
Git because they can be installed or downloaded separately.

A microphone and Windows permission for desktop apps to access it are required.
The model download and dependency installation need internet access; the local
speech workflow operates offline afterward.

After installing dependencies and extracting the model, check the setup:

```powershell
.\.venv\Scripts\python.exe check_setup.py
.\.venv\Scripts\python.exe -m unittest discover -v
```

Double-click `Start Voice Agent.cmd` to open the assistant. Select your microphone,
press Start listening and say "computer open Notepad", then pause.
Use `Show Workflow Demo.cmd` for a simulated workflow without microphone capture
or application launches. `Start Voice Test.cmd` is a legacy launcher for the same
command-enabled application, not a transcription-only mode.
