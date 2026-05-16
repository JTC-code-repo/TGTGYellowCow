"""Tkinter UI for monitoring the official Android app through ADB."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from .android_monitor import (
    DEFAULT_LOGIN_KEYWORDS,
    DEFAULT_NEGATIVE_KEYWORDS,
    DEFAULT_POSITIVE_KEYWORDS,
    AndroidMonitor,
    AndroidMonitorConfig,
    DetectionResult,
    parse_keywords,
)

UIEvent = tuple[str, Any]


class AndroidMonitorApp(tk.Tk):
    """Minimal ADB monitor for a user-controlled official TGTG Android app session."""

    def __init__(self) -> None:
        super().__init__()
        self.title("TGTG Yellow Cow - Android monitor")
        self.geometry("900x620")
        self.events: queue.Queue[UIEvent] = queue.Queue()
        self.stop_event = threading.Event()
        self.monitor_thread: threading.Thread | None = None
        self._build_widgets()
        self._set_monitoring(False)
        self.after(150, self._drain_events)

    def _build_widgets(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        intro = (
            "Use an Android emulator/device and log in inside the official Too Good To Go app. "
            "This is the real login flow: the official app owns the session in the emulator. "
            "After login, navigate to the store/bag screen you want to watch and start monitoring. "
            "This reads visible UI text through ADB; it does not bypass login/captcha and does not auto-purchase."
        )
        ttk.Label(root, text=intro, wraplength=860, justify=tk.LEFT).pack(fill=tk.X)

        settings = ttk.LabelFrame(root, text="ADB / app settings")
        settings.pack(fill=tk.X, pady=(10, 0))
        self.adb_var = tk.StringVar(value="adb")
        self.serial_var = tk.StringVar(value="")
        self.package_var = tk.StringVar(value="com.app.tgtg")
        self.poll_var = tk.StringVar(value="30")
        self._field(settings, "ADB", self.adb_var, 10)
        self._field(settings, "Serial", self.serial_var, 16)
        self._field(settings, "Package", self.package_var, 16)
        self._field(settings, "Poll sec", self.poll_var, 8)
        ttk.Button(settings, text="Open official app / login", command=self._launch_app).pack(side=tk.LEFT, padx=4, pady=6)
        ttk.Button(settings, text="Check login/screen once", command=self._check_once).pack(side=tk.LEFT, padx=4, pady=6)

        keywords = ttk.LabelFrame(root, text="Detection keywords")
        keywords.pack(fill=tk.X, pady=(10, 0))
        self.positive_var = tk.StringVar(value=", ".join(DEFAULT_POSITIVE_KEYWORDS))
        self.negative_var = tk.StringVar(value=", ".join(DEFAULT_NEGATIVE_KEYWORDS))
        self.login_var = tk.StringVar(value=", ".join(DEFAULT_LOGIN_KEYWORDS))
        ttk.Label(keywords, text="Available words").pack(anchor=tk.W, padx=8, pady=(6, 0))
        ttk.Entry(keywords, textvariable=self.positive_var).pack(fill=tk.X, padx=8)
        ttk.Label(keywords, text="Sold-out/blocking words").pack(anchor=tk.W, padx=8, pady=(6, 0))
        ttk.Entry(keywords, textvariable=self.negative_var).pack(fill=tk.X, padx=8)
        ttk.Label(keywords, text="Login/onboarding words").pack(anchor=tk.W, padx=8, pady=(6, 0))
        ttk.Entry(keywords, textvariable=self.login_var).pack(fill=tk.X, padx=8, pady=(0, 8))

        controls = ttk.Frame(root)
        controls.pack(fill=tk.X, pady=(10, 0))
        self.start_button = ttk.Button(controls, text="Start monitoring current screen", command=self._toggle_monitor)
        self.start_button.pack(side=tk.LEFT, padx=4)
        self.stop_button = ttk.Button(controls, text="Stop", command=self._stop_monitor)
        self.stop_button.pack(side=tk.LEFT, padx=4)

        output = ttk.LabelFrame(root, text="Last visible app text / log")
        output.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self.output_text = tk.Text(output, wrap=tk.WORD, height=15)
        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=8)
        scrollbar = ttk.Scrollbar(output, command=self.output_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=8)
        self.output_text.configure(yscrollcommand=scrollbar.set)

        self.status_var = tk.StringVar(value="Ready. Open the official app in your emulator and navigate to a bag screen.")
        ttk.Label(root, textvariable=self.status_var, anchor=tk.W).pack(fill=tk.X, pady=(8, 0))

    def _field(self, parent: ttk.Frame, label: str, var: tk.StringVar, width: int) -> None:
        ttk.Label(parent, text=label).pack(side=tk.LEFT, padx=(8, 2))
        ttk.Entry(parent, textvariable=var, width=width).pack(side=tk.LEFT, padx=2)

    def _config(self) -> AndroidMonitorConfig | None:
        try:
            poll_seconds = int(self.poll_var.get())
        except ValueError:
            messagebox.showerror("Invalid settings", "Poll seconds must be a number.")
            return None
        if poll_seconds < 15:
            messagebox.showerror("Invalid settings", "Please poll no faster than every 15 seconds.")
            return None
        return AndroidMonitorConfig(
            adb_path=self.adb_var.get().strip() or "adb",
            serial=self.serial_var.get().strip(),
            package_name=self.package_var.get().strip() or "com.app.tgtg",
            poll_seconds=poll_seconds,
            positive_keywords=parse_keywords(self.positive_var.get()),
            negative_keywords=parse_keywords(self.negative_var.get()),
            login_keywords=parse_keywords(self.login_var.get()),
        )

    def _monitor(self) -> AndroidMonitor | None:
        config = self._config()
        return AndroidMonitor(config) if config else None

    def _launch_app(self) -> None:
        monitor = self._monitor()
        if not monitor:
            return
        self._run_background(lambda: self._launch(monitor), "Launching official app...")

    def _launch(self, monitor: AndroidMonitor) -> str:
        monitor.ensure_device()
        monitor.launch_app()
        return "Official app launch command sent. Log in there if needed, then navigate to the store/bag screen to watch."

    def _check_once(self) -> None:
        monitor = self._monitor()
        if not monitor:
            return
        self._run_background(monitor.detect_current_screen, "Checking current Android screen...")

    def _toggle_monitor(self) -> None:
        if self.monitor_thread and self.monitor_thread.is_alive():
            self._stop_monitor()
            return
        monitor = self._monitor()
        if not monitor:
            return
        self.stop_event.clear()
        self._set_monitoring(True)
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(monitor,), daemon=True)
        self.monitor_thread.start()
        self.status_var.set(f"Monitoring current Android screen every {monitor.config.poll_seconds}s.")

    def _stop_monitor(self) -> None:
        self.stop_event.set()
        self._set_monitoring(False)
        self.status_var.set("Monitoring stopped.")

    def _set_monitoring(self, monitoring: bool) -> None:
        self.start_button.configure(text="Stop monitoring" if monitoring else "Start monitoring current screen")
        self.stop_button.configure(state=tk.NORMAL if monitoring else tk.DISABLED)

    def _monitor_loop(self, monitor: AndroidMonitor) -> None:
        while not self.stop_event.is_set():
            try:
                result = monitor.detect_current_screen()
                self.events.put(("android_result", result))
                if result.login_required:
                    self.events.put(("android_login_required", result))
                elif result.is_available:
                    self.events.put(("android_available", result))
                    self.stop_event.set()
                    break
            except Exception as exc:
                self.events.put(("android_error", exc))
            self.stop_event.wait(monitor.config.poll_seconds)
        self.events.put(("android_stopped", None))

    def _run_background(self, work, busy_message: str) -> None:
        self.status_var.set(busy_message)

        def runner() -> None:
            try:
                self.events.put(("android_result", work()))
            except Exception as exc:
                self.events.put(("android_error", exc))

        threading.Thread(target=runner, daemon=True).start()

    def _drain_events(self) -> None:
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "android_result":
                self._show_result(payload)
            elif event == "android_available":
                self._prompt_available(payload)
            elif event == "android_login_required":
                self._show_login_required(payload)
            elif event == "android_error":
                self._append_output(f"ERROR:\n{payload}")
                self.status_var.set(f"Error: {payload}")
            elif event == "android_stopped":
                self._set_monitoring(False)
        self.after(150, self._drain_events)

    def _show_result(self, payload: DetectionResult | str) -> None:
        if isinstance(payload, DetectionResult):
            summary = (
                f"Available: {'yes' if payload.is_available else 'no'}\n"
                f"Matched available words: {', '.join(payload.matched_positive) or '(none)'}\n"
                f"Matched sold-out/blocking words: {', '.join(payload.matched_negative) or '(none)'}\n"
                f"Matched login/onboarding words: {', '.join(payload.matched_login) or '(none)'}\n\n"
                f"Visible text:\n{payload.screen_text}"
            )
            self._append_output(summary)
            if payload.login_required:
                self.status_var.set("Official app still appears to be on login/onboarding. Finish login in the emulator.")
            else:
                self.status_var.set("Bag-like availability detected." if payload.is_available else "Checked screen; no availability detected.")
        else:
            self._append_output(payload)
            self.status_var.set(payload)

    def _append_output(self, text: str) -> None:
        self.output_text.configure(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, text)
        self.output_text.configure(state=tk.NORMAL)

    def _show_login_required(self, result: DetectionResult) -> None:
        self.status_var.set("Finish the real login inside the official Android app, then navigate to a bag screen.")

    def _prompt_available(self, result: DetectionResult) -> None:
        messagebox.showinfo(
            "Possible bag available",
            "The current official app screen matched your availability keywords.\n\n"
            "Review the emulator and complete any reservation manually in the official app.",
        )


def main() -> None:
    app = AndroidMonitorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
