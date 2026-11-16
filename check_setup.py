"""Check local speech requirements without recording or executing commands."""
from pathlib import Path
import sys


def main():
    import sounddevice as sd
    from vosk import Model, KaldiRecognizer, SetLogLevel

    model_path = Path(__file__).resolve().parent / 'models' / 'vosk-model-small-en-us-0.15'
    if not (model_path / 'am' / 'final.mdl').is_file():
        raise RuntimeError('English model is missing or its download is not finished.')
    SetLogLevel(-1)
    model = Model(str(model_path))
    recognizer = KaldiRecognizer(model, 16000)
    recognizer.AcceptWaveform(bytes(32000))
    print('PASS: Offline English model loaded and processed one second of synthetic silence.')
    inputs = [d for d in sd.query_devices() if d['max_input_channels'] > 0]
    print(f'Available microphone/input entries: {len(inputs)}')
    for device in inputs:
        print(f"  - {device['name']}")
    if not inputs:
        raise RuntimeError('No input devices detected. Connect or enable a microphone.')
    default = sd.query_devices(kind='input')
    sd.check_input_settings(channels=1, dtype='int16', samplerate=default['default_samplerate'])
    print(f"PASS: Default input supports recording: {default['name']}")
    print('Setup check complete. No microphone recording was made and no apps were opened.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'SETUP ISSUE: {exc}', file=sys.stderr)
        sys.exit(1)
