"""Tkinter user interface for monitoring Too Good To Go bag availability."""

from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable

from .config import AppConfig, load_config, save_config
from .tgtg_client import (
    StoreBag,
    build_client,
    credentials_from_mapping,
    fetch_nearby_bags,
    format_tgtg_error,
    refresh_bag,
    request_credentials,
    reserve_bag,
)

UIEvent = tuple[str, Any]


class TgtgMonitorApp(tk.Tk):
    """Minimal desktop app for listing stores and watching one selected store."""

    def __init__(self) -> None:
        super().__init__()
        self.title("TGTG Yellow Cow")
        self.geometry("900x560")
        self.config_data = load_config()
        self.client = build_client(self.config_data.credentials) if self.config_data.credentials else None
        self.bags: list[StoreBag] = []
        self.selected_bag: StoreBag | None = None
        self.monitor_stop = threading.Event()
        self.monitor_thread: threading.Thread | None = None
        self.events: queue.Queue[UIEvent] = queue.Queue()

        self._build_widgets()
        self._set_monitoring(False)
        self.after(150, self._drain_events)

    def _build_widgets(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        credentials = ttk.LabelFrame(root, text="Account")
        credentials.pack(fill=tk.X)
        ttk.Button(credentials, text="Login / refresh credentials", command=self._login).pack(side=tk.LEFT, padx=4, pady=6)
        ttk.Button(credentials, text="Paste credentials JSON", command=self._paste_credentials).pack(
            side=tk.LEFT, padx=4, pady=6
        )
        self.account_label = ttk.Label(credentials, text=self._account_status())
        self.account_label.pack(side=tk.LEFT, padx=8)

        search = ttk.LabelFrame(root, text="Nearby stores")
        search.pack(fill=tk.X, pady=(10, 0))
        self.lat_var = tk.StringVar(value=str(self.config_data.latitude))
        self.lon_var = tk.StringVar(value=str(self.config_data.longitude))
        self.radius_var = tk.StringVar(value=str(self.config_data.radius_km))
        self.poll_var = tk.StringVar(value=str(self.config_data.poll_seconds))
        self._field(search, "Latitude", self.lat_var)
        self._field(search, "Longitude", self.lon_var)
        self._field(search, "Radius km", self.radius_var)
        self._field(search, "Poll sec", self.poll_var)
        ttk.Button(search, text="Load stores", command=self._load_stores).pack(side=tk.LEFT, padx=4, pady=6)

        body = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, pady=10)

        list_frame = ttk.Frame(body)
        self.store_list = tk.Listbox(list_frame, activestyle="dotbox")
        self.store_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.store_list.bind("<<ListboxSelect>>", self._on_select)
        scrollbar = ttk.Scrollbar(list_frame, command=self.store_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.store_list.configure(yscrollcommand=scrollbar.set)
        body.add(list_frame, weight=3)

        detail = ttk.LabelFrame(body, text="Selected store")
        self.detail_text = tk.Text(detail, height=12, wrap=tk.WORD, state=tk.DISABLED)
        self.detail_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        controls = ttk.Frame(detail)
        controls.pack(fill=tk.X, padx=6, pady=(0, 6))
        self.start_button = ttk.Button(controls, text="Start", command=self._toggle_monitor)
        self.start_button.pack(side=tk.LEFT, padx=3)
        self.stop_button = ttk.Button(controls, text="Stop", command=self._stop_monitor)
        self.stop_button.pack(side=tk.LEFT, padx=3)
        body.add(detail, weight=2)

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(root, textvariable=self.status_var, anchor=tk.W).pack(fill=tk.X)

    def _field(self, parent: ttk.Frame, label: str, var: tk.StringVar) -> None:
        ttk.Label(parent, text=label).pack(side=tk.LEFT, padx=(8, 2))
        ttk.Entry(parent, textvariable=var, width=10).pack(side=tk.LEFT, padx=2)

    def _account_status(self) -> str:
        return "Credentials saved" if self.config_data.credentials else "Not logged in"

    def _login(self) -> None:
        email = simpledialog.askstring("Too Good To Go login", "Enter your Too Good To Go account e-mail:")
        if not email:
            return
        self._run_background(
            lambda: request_credentials(email),
            "Waiting for e-mail login approval...",
            lambda credentials: self._finish_login(credentials),
        )

    def _paste_credentials(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Paste Too Good To Go credentials")
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("760x420")
        dialog.minsize(520, 300)

        instructions = (
            "Paste a JSON object from an existing valid session with access_token, "
            "refresh_token, and cookie. These values will be saved locally and used "
            "instead of starting a new e-mail login."
        )
        ttk.Label(dialog, text=instructions, wraplength=720, justify=tk.LEFT, padding=12).pack(fill=tk.X)
        text = tk.Text(dialog, wrap=tk.WORD, height=12)
        text.insert(
            "1.0",
            '{\n  "access_token": "...",\n  "refresh_token": "...",\n  "cookie": "..."\n}',
        )
        text.pack(fill=tk.BOTH, expand=True, padx=12)
        text.focus_set()
        text.tag_add(tk.SEL, "1.0", tk.END)

        buttons = ttk.Frame(dialog, padding=12)
        buttons.pack(fill=tk.X)

        def save_pasted_credentials() -> None:
            try:
                payload = json.loads(text.get("1.0", tk.END))
                if not isinstance(payload, dict):
                    raise ValueError("Credentials JSON must be an object.")
                credentials = credentials_from_mapping(payload)
            except Exception as exc:
                self._show_selectable_error("Invalid credentials JSON", str(exc))
                return
            dialog.destroy()
            self._finish_login(credentials)

        ttk.Button(buttons, text="Save credentials", command=save_pasted_credentials).pack(side=tk.RIGHT, padx=4)
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=4)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.wait_window()

    def _finish_login(self, credentials: Any) -> None:
        self.config_data.credentials = credentials
        save_config(self.config_data)
        self.client = build_client(credentials)
        self.account_label.configure(text=self._account_status())
        self.status_var.set("Credentials saved locally.")

    def _load_stores(self) -> None:
        if not self._ensure_client():
            return
        config = self._read_search_config()
        if not config:
            return
        self.config_data = config
        save_config(config)
        self._run_background(
            lambda: fetch_nearby_bags(self.client, config.latitude, config.longitude, config.radius_km),
            "Loading nearby stores...",
            self._finish_load_stores,
        )

    def _read_search_config(self) -> AppConfig | None:
        try:
            latitude = float(self.lat_var.get())
            longitude = float(self.lon_var.get())
            radius_km = float(self.radius_var.get())
            poll_seconds = int(self.poll_var.get())
        except ValueError:
            self._show_selectable_error("Invalid settings", "Latitude, longitude, radius, and poll seconds must be numbers.")
            return None
        if poll_seconds < 15:
            self._show_selectable_error("Invalid settings", "Please poll no faster than every 15 seconds.")
            return None
        return AppConfig(self.config_data.credentials, latitude, longitude, radius_km, poll_seconds)

    def _finish_load_stores(self, bags: list[StoreBag]) -> None:
        self.bags = bags
        self.store_list.delete(0, tk.END)
        for bag in bags:
            self.store_list.insert(tk.END, bag.list_label())
        self.status_var.set(f"Loaded {len(bags)} nearby store bags.")

    def _on_select(self, _event: tk.Event[Any]) -> None:
        selection = self.store_list.curselection()
        if not selection:
            return
        self.selected_bag = self.bags[selection[0]]
        self._show_details(self.selected_bag)

    def _show_details(self, bag: StoreBag) -> None:
        lines = [
            bag.display_name,
            f"Address: {bag.address or 'unknown'}",
            f"Available: {bag.items_available}",
            f"Price: {bag.price}",
            f"Pickup: {bag.pickup_window}",
            f"Sales window open: {'yes' if bag.in_sales_window else 'no'}",
            f"Item ID: {bag.item_id}",
        ]
        self.detail_text.configure(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert(tk.END, "\n".join(lines))
        self.detail_text.configure(state=tk.DISABLED)

    def _toggle_monitor(self) -> None:
        if self.monitor_thread and self.monitor_thread.is_alive():
            self._stop_monitor()
            return
        if not self._ensure_client() or not self.selected_bag:
            messagebox.showwarning("Select a store", "Load stores, select one store, then press Start.")
            return
        config = self._read_search_config()
        if not config:
            return
        self.config_data = config
        self.monitor_stop.clear()
        self._set_monitoring(True)
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(self.selected_bag,), daemon=True)
        self.monitor_thread.start()
        self.status_var.set(f"Monitoring {self.selected_bag.display_name} every {config.poll_seconds}s.")

    def _stop_monitor(self) -> None:
        self.monitor_stop.set()
        self._set_monitoring(False)
        self.status_var.set("Monitoring stopped.")

    def _set_monitoring(self, monitoring: bool) -> None:
        self.start_button.configure(text="Stop" if monitoring else "Start")
        self.stop_button.configure(state=tk.NORMAL if monitoring else tk.DISABLED)

    def _monitor_loop(self, bag: StoreBag) -> None:
        while not self.monitor_stop.is_set():
            try:
                latest = refresh_bag(self.client, bag)
                self.events.put(("bag_refreshed", latest))
                if latest.available:
                    self.events.put(("bag_available", latest))
                    self.monitor_stop.set()
                    break
            except Exception as exc:
                self.events.put(("error", exc))
            self.monitor_stop.wait(self.config_data.poll_seconds)
        self.events.put(("monitor_stopped", None))

    def _drain_events(self) -> None:
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "bag_refreshed":
                self.selected_bag = payload
                self._show_details(payload)
                self.status_var.set(f"Last checked {payload.display_name}: {payload.items_available} available.")
            elif event == "bag_available":
                self._prompt_purchase(payload)
            elif event == "monitor_stopped":
                self._set_monitoring(False)
            elif event == "error":
                self.status_var.set(f"Monitor error: {payload}")
            elif event == "background_success":
                callback, result = payload
                callback(result)
            elif event == "background_error":
                error_message = format_tgtg_error(payload)
                self._show_selectable_error("Error", error_message)
                self.status_var.set(f"Error: {error_message}")
        self.after(150, self._drain_events)


    def _show_selectable_error(self, title: str, message: str) -> None:
        """Show an error dialog whose text can be selected and copied."""

        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("640x320")
        dialog.minsize(420, 220)

        ttk.Label(dialog, text=title, padding=(12, 12, 12, 0), font=("TkDefaultFont", 10, "bold")).pack(
            anchor=tk.W
        )
        text_frame = ttk.Frame(dialog, padding=12)
        text_frame.pack(fill=tk.BOTH, expand=True)
        error_text = tk.Text(text_frame, wrap=tk.WORD, height=8, undo=False)
        error_text.insert("1.0", message)
        error_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(text_frame, command=error_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        error_text.configure(yscrollcommand=scrollbar.set)
        error_text.focus_set()
        error_text.tag_add(tk.SEL, "1.0", tk.END)

        buttons = ttk.Frame(dialog, padding=(12, 0, 12, 12))
        buttons.pack(fill=tk.X)

        def copy_message() -> None:
            self.clipboard_clear()
            self.clipboard_append(message)
            self.update_idletasks()
            self.status_var.set("Error copied to clipboard.")

        ttk.Button(buttons, text="Copy error", command=copy_message).pack(side=tk.RIGHT, padx=4)
        ttk.Button(buttons, text="Close", command=dialog.destroy).pack(side=tk.RIGHT, padx=4)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.wait_window()

    def _prompt_purchase(self, bag: StoreBag) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Bag available")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        message = (
            f"{bag.display_name} has {bag.items_available} bag(s) available.\n\n"
            f"Price: {bag.price}\n"
            f"Pickup: {bag.pickup_window}\n\n"
            "Choose Buy to reserve one bag, or Skip to leave it."
        )
        ttk.Label(dialog, text=message, justify=tk.LEFT, padding=12).pack(fill=tk.BOTH)
        buttons = ttk.Frame(dialog, padding=(12, 0, 12, 12))
        buttons.pack(fill=tk.X)

        def buy() -> None:
            dialog.destroy()
            self._run_background(
                lambda: reserve_bag(self.client, bag, 1),
                "Reserving one bag...",
                lambda order: messagebox.showinfo(
                    "Reservation created",
                    "A reservation was created. Complete payment in the Too Good To Go mobile app.\n\n"
                    f"Order: {order.get('id', 'unknown')}",
                ),
            )

        def skip() -> None:
            dialog.destroy()
            self.status_var.set("Availability skipped by user.")

        ttk.Button(buttons, text="Buy", command=buy).pack(side=tk.RIGHT, padx=4)
        ttk.Button(buttons, text="Skip", command=skip).pack(side=tk.RIGHT, padx=4)
        dialog.protocol("WM_DELETE_WINDOW", skip)
        dialog.wait_window()

    def _ensure_client(self) -> bool:
        if self.client:
            return True
        messagebox.showwarning("Login required", "Login first so the app can load Too Good To Go stores.")
        return False

    def _run_background(self, work: Callable[[], Any], busy_message: str, on_success: Callable[[Any], None]) -> None:
        self.status_var.set(busy_message)

        def runner() -> None:
            try:
                result = work()
                self.events.put(("background_success", (on_success, result)))
            except Exception as exc:
                self.events.put(("background_error", exc))

        threading.Thread(target=runner, daemon=True).start()


def main() -> None:
    app = TgtgMonitorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
