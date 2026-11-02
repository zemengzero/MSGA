from unittest import TestCase
from unittest.mock import Mock, patch
from zhiyeteam.galaxy import close_guard


class NativeCloseTests(TestCase):
    def test_js_is_queried_off_the_closing_event_thread(self):
        window = Mock()
        window.evaluate_js.return_value = False
        handler = close_guard(window)
        with patch("zhiyeteam.galaxy.threading.Thread") as thread:
            self.assertFalse(handler())
            window.evaluate_js.assert_not_called()
            target = thread.call_args.kwargs["target"]
            target()
        window.destroy.assert_called_once()
        self.assertTrue(handler())

    def test_cancel_preserves_window_and_can_retry(self):
        window = Mock()
        window.evaluate_js.return_value = True
        window.create_confirmation_dialog.return_value = False
        handler = close_guard(window)
        with patch("zhiyeteam.galaxy.threading.Thread") as thread:
            self.assertFalse(handler())
            thread.call_args.kwargs["target"]()
            window.destroy.assert_not_called()
            self.assertFalse(handler())
            self.assertEqual(thread.call_count, 2)

    def test_failed_js_query_requires_explicit_confirmation(self):
        window = Mock()
        window.evaluate_js.side_effect = RuntimeError("renderer unavailable")
        window.create_confirmation_dialog.return_value = False
        handler = close_guard(window)
        with patch("zhiyeteam.galaxy.threading.Thread") as thread:
            handler()
            thread.call_args.kwargs["target"]()
        window.create_confirmation_dialog.assert_called_once()
        window.destroy.assert_not_called()
