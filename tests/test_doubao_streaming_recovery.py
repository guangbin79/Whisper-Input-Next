import asyncio
import queue
import unittest
from unittest.mock import patch

import main


class _FakeThread:
    def __init__(self, target=None, name=None, daemon=None):
        self.target = target
        self.name = name
        self.daemon = daemon
        self.started = False

    def start(self):
        self.started = True

    def is_alive(self):
        return self.started

    def join(self, timeout=None):
        self.started = False


class _RecorderStub:
    def __init__(self, start_results=None):
        self.start_results = list(start_results or [None])
        self.start_calls = 0
        self.reset_reasons = []
        self.stop_calls = 0

    def start_streaming_recording(self):
        index = min(self.start_calls, len(self.start_results) - 1)
        self.start_calls += 1
        return self.start_results[index]

    def reset_streaming_state(self, reason="", drain_queue=True):
        self.reset_reasons.append(reason)

    def stop_streaming_recording(self):
        self.stop_calls += 1

    async def _empty_audio(self):
        if False:
            yield b""

    def stream_audio_chunks(self, target_sample_rate=16000):
        return self._empty_audio()


class _KeyboardStub:
    def __init__(self):
        self.reset_calls = 0
        self.typed_text = []

    def reset_state(self):
        self.reset_calls += 1

    def type_text(self, text, error_message=None):
        self.typed_text.append((text, error_message))


class _PreviewStub:
    def __init__(self):
        self.show_calls = 0
        self.hide_calls = 0
        self.text_updates = []

    def show(self):
        self.show_calls += 1

    def hide(self):
        self.hide_calls += 1

    def update_text(self, text):
        self.text_updates.append(text)


class _StatusControllerStub:
    def __init__(self):
        self.states = []

    def update_state(self, state, queue_length=0):
        self.states.append((state, queue_length))


class _ProcessorAvailableStub:
    def is_available(self):
        return True

    async def disconnect(self):
        return None


class _ProcessorErrorStub(_ProcessorAvailableStub):
    async def process_audio_stream(
        self,
        audio_chunk_generator,
        on_preview_text,
        on_final_text,
        on_complete,
        on_error,
        sample_rate=16000,
    ):
        on_error("boom")


class DoubaoStreamingRecoveryTests(unittest.TestCase):
    def _make_assistant(self, recorder, processor):
        assistant = main.VoiceAssistant.__new__(main.VoiceAssistant)
        assistant.audio_recorder = recorder
        assistant.doubao_processor = processor
        assistant.keyboard_manager = _KeyboardStub()
        assistant.floating_preview = _PreviewStub()
        assistant.status_controller = _StatusControllerStub()
        assistant.job_queue = queue.Queue()
        assistant._current_state = main.InputState.IDLE
        assistant._streaming_loop = None
        assistant._streaming_thread = None
        return assistant

    def test_start_doubao_streaming_recovers_from_stale_recorder_state(self):
        assistant = self._make_assistant(
            _RecorderStub(start_results=["已经在录音中", None]),
            _ProcessorAvailableStub(),
        )

        with patch.object(main.threading, "Thread", _FakeThread):
            assistant.start_doubao_streaming()

        self.assertEqual(assistant.audio_recorder.start_calls, 2)
        self.assertEqual(len(assistant.audio_recorder.reset_reasons), 1)
        self.assertEqual(assistant.keyboard_manager.reset_calls, 0)
        self.assertIsInstance(assistant._streaming_thread, _FakeThread)
        self.assertTrue(assistant._streaming_thread.started)

    def test_run_doubao_streaming_error_cleans_up_state(self):
        assistant = self._make_assistant(
            _RecorderStub(),
            _ProcessorErrorStub(),
        )

        asyncio.run(assistant._run_doubao_streaming())

        self.assertEqual(assistant.keyboard_manager.reset_calls, 1)
        self.assertEqual(len(assistant.audio_recorder.reset_reasons), 1)
        self.assertEqual(assistant.floating_preview.show_calls, 1)
        self.assertEqual(assistant.floating_preview.hide_calls, 1)


if __name__ == "__main__":
    unittest.main()
