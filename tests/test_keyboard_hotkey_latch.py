import unittest

from pynput.keyboard import Key

from src.keyboard.inputState import InputState
from src.keyboard.listener import KeyboardManager


class KeyboardHotkeyLatchTests(unittest.TestCase):
    def _make_manager(self):
        manager = KeyboardManager.__new__(KeyboardManager)
        manager.ctrl_pressed = False
        manager.f_pressed = False
        manager.i_pressed = False
        manager.temp_text_length = 0
        manager.processing_text = None
        manager.error_message = None
        manager.warning_message = None
        manager.is_recording = False
        manager.last_key_time = 0
        manager.KEY_DEBOUNCE_TIME = 0.3
        manager.hotkey_latched = False
        manager._original_clipboard = None
        manager.transcriptions_button = "f"
        manager.translations_button = Key.ctrl
        manager.state_symbol_enabled = False
        manager.on_record_start = lambda: None
        manager.on_record_stop = lambda: None
        manager.on_translate_start = lambda: None
        manager.on_translate_stop = lambda: None
        manager.on_kimi_start = lambda: None
        manager.on_kimi_stop = lambda: None
        manager.on_reset_state = lambda: None
        manager.on_state_change = None
        manager._state_messages = {
            InputState.IDLE: "",
            InputState.RECORDING: "0",
            InputState.PROCESSING: "1",
            InputState.RECORDING_KIMI: "0",
            InputState.PROCESSING_KIMI: "1",
            InputState.RECORDING_TRANSLATE: "0",
            InputState.TRANSLATING: "1",
            InputState.ERROR: lambda msg: msg,
            InputState.WARNING: lambda msg: msg,
        }
        manager._state = InputState.IDLE
        manager._delete_previous_text = lambda: None
        manager._restore_clipboard = lambda: None
        manager.type_temp_text = lambda text: None
        return manager

    def test_toggle_recording_requires_hotkey_release_before_retrigger(self):
        manager = self._make_manager()

        manager.toggle_recording()
        self.assertTrue(manager.is_recording)
        self.assertTrue(manager.hotkey_latched)

        manager.last_key_time = 0
        manager.toggle_recording()
        self.assertTrue(manager.is_recording)

        manager.ctrl_pressed = False
        manager.f_pressed = False
        manager.i_pressed = False
        manager.on_release(Key.ctrl)
        self.assertFalse(manager.hotkey_latched)

        manager.last_key_time = 0
        manager.toggle_recording()
        self.assertFalse(manager.is_recording)

    def test_reset_state_keeps_hotkey_blocked_until_release(self):
        manager = self._make_manager()
        manager.ctrl_pressed = True
        manager.f_pressed = True
        manager.is_recording = True
        manager._state = InputState.PROCESSING

        manager.reset_state()
        self.assertTrue(manager.hotkey_latched)
        self.assertFalse(manager.is_recording)

        manager.on_release(type("KeyObj", (), {"char": "f"})())
        self.assertFalse(manager.hotkey_latched)


if __name__ == "__main__":
    unittest.main()
