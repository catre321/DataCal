import tkinter as tk
from tkinter import ttk
import threading
import traceback


class ProgressDialog:
    """
    Reusable modal progress dialog that runs a task in a background thread.

    Usage:
        def run(progress_cb):
            # progress_cb(current, total, label) to update the bar
            return some_result

        ProgressDialog(root, "Loading...", "Loading files...", "File").run(
            run, on_success=lambda result: ..., on_error=lambda err: ...
        )

    Args:
        root: Parent Tk window.
        title: Dialog window title.
        body_label: Bold heading shown at the top.
        status_prefix: Prefix for the live status line, e.g. "File" → "File: data.csv".
    """

    def __init__(self, root, title, body_label, status_prefix=""):
        self._root = root
        self._status_prefix = status_prefix

        self._dialog = tk.Toplevel(root)
        self._dialog.title(title)
        self._dialog.geometry("400x150")
        self._dialog.resizable(False, False)
        self._dialog.transient(root)
        self._dialog.grab_set()

        tk.Label(self._dialog, text=body_label, font=("Arial", 12, "bold")).pack(pady=10)

        self._status_label = tk.Label(self._dialog, text=f"{status_prefix}: ", fg="blue")
        self._status_label.pack(pady=5)

        self._progress_label = tk.Label(self._dialog, text="", fg="gray")
        self._progress_label.pack(pady=5)

        self._progress_bar = ttk.Progressbar(self._dialog, mode='determinate', length=300)
        self._progress_bar.pack(pady=10, padx=20)

    def run(self, fn, on_success, on_error):
        """
        Execute fn in a background thread, then call on_success or on_error on the main thread.

        Args:
            fn: callable(progress_cb) → result.
                progress_cb: callable(current: int, total: int, label: str).
            on_success: callable(result) invoked on the main thread when fn completes.
            on_error: callable(error_str) invoked on the main thread if fn raises.
        """
        def background():
            try:
                def progress_cb(current, total, label):
                    self._root.after(0, lambda: self._update_ui(current, total, label))

                result = fn(progress_cb)
                self._root.after(0, lambda: self._finish(on_success, result, None, on_error))
            except Exception as e:
                err = str(e)
                print(f"\n[ERROR] {err}")
                traceback.print_exc()
                self._root.after(0, lambda: self._finish(on_success, None, err, on_error))

        threading.Thread(target=background, daemon=True).start()

    def _update_ui(self, current, total, label):
        if self._dialog.winfo_exists():
            self._status_label.config(text=f"{self._status_prefix}: {label}")
            self._progress_label.config(text=f"Tiến độ: {current}/{total}")
            self._progress_bar['value'] = (current / total) * 100

    def _finish(self, on_success, result, error, on_error):
        if self._dialog.winfo_exists():
            self._dialog.destroy()
        if error is not None:
            on_error(error)
        else:
            on_success(result)
