import unittest
from unittest.mock import MagicMock, patch

import app
from app import MouseGestureApp
from mouse_hook import GlobalRightButtonActionHook, WM_QUIT


class ShutdownTests(unittest.TestCase):
    def _make_application(self) -> MouseGestureApp:
        application = object.__new__(MouseGestureApp)
        application.root = MagicMock()
        application.hook = MagicMock()
        application.hook._hook_thread = None
        application.hook._dispatch_thread = None
        application._closing = False
        application._shutdown_watchdog = None
        return application

    @patch("app.threading.Timer")
    def test_close_is_idempotent_and_arms_watchdog(
        self,
        timer_class: MagicMock,
    ) -> None:
        application = self._make_application()
        timer = timer_class.return_value

        application.close()
        application.close()

        timer_class.assert_called_once_with(
            app.SHUTDOWN_WATCHDOG_SECONDS,
            app._force_exit_current_process,
            args=(0,),
        )
        self.assertTrue(timer.daemon)
        timer.start.assert_called_once_with()
        application.hook.stop.assert_called_once_with()
        application.root.quit.assert_called_once_with()
        application.root.destroy.assert_called_once_with()

    @patch("app.threading.Timer")
    def test_close_destroys_window_when_hook_stop_fails(
        self,
        _timer_class: MagicMock,
    ) -> None:
        application = self._make_application()
        application.hook.stop.side_effect = RuntimeError("hook stop failed")

        application.close()

        application.root.quit.assert_called_once_with()
        application.root.destroy.assert_called_once_with()

    @patch("app.os._exit")
    @patch("app.ctypes.windll")
    def test_force_exit_uses_windows_terminate_process(
        self,
        windll: MagicMock,
        os_exit: MagicMock,
    ) -> None:
        kernel32 = windll.kernel32
        kernel32.GetCurrentProcess.return_value = 123

        app._force_exit_current_process(0)

        kernel32.TerminateProcess.assert_called_once_with(123, 0)
        os_exit.assert_called_once_with(0)

    @patch("app._force_exit_current_process")
    @patch("app.MouseGestureApp")
    @patch("app.tk.Tk")
    @patch("app.acquire_single_instance", return_value=321)
    @patch("app.enable_dpi_awareness")
    @patch("app.ctypes.windll")
    def test_main_forces_exit_after_tk_and_mutex_cleanup(
        self,
        windll: MagicMock,
        _enable_dpi_awareness: MagicMock,
        _acquire_single_instance: MagicMock,
        tk_class: MagicMock,
        application_class: MagicMock,
        force_exit: MagicMock,
    ) -> None:
        root = tk_class.return_value

        app.main()

        application_class.assert_called_once_with(root)
        root.mainloop.assert_called_once_with()
        windll.kernel32.CloseHandle.assert_called_once_with(321)
        force_exit.assert_called_once_with(0)

    def test_hook_stop_unhooks_before_posting_quit(self) -> None:
        hook = object.__new__(GlobalRightButtonActionHook)
        hook.set_enabled = MagicMock()
        hook._hook = 456
        hook._hook_thread_id = 789
        hook._user32 = MagicMock()
        hook._user32.UnhookWindowsHookEx.return_value = True
        hook._user32.PostThreadMessageW.return_value = True
        hook._action_queue = MagicMock()
        hook._hook_thread = MagicMock()
        hook._hook_thread.is_alive.return_value = True
        hook._dispatch_thread = MagicMock()
        hook._dispatch_thread.is_alive.return_value = True

        hook.stop()

        self.assertEqual(
            hook._user32.method_calls[:2],
            [
                unittest.mock.call.UnhookWindowsHookEx(456),
                unittest.mock.call.PostThreadMessageW(789, WM_QUIT, 0, 0),
            ],
        )
        self.assertIsNone(hook._hook)
        hook._hook_thread.join.assert_called_once_with(timeout=2.0)
        hook._dispatch_thread.join.assert_called_once_with(timeout=2.0)


if __name__ == "__main__":
    unittest.main()
