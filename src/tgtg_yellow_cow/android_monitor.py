"""ADB-based monitor for the official Too Good To Go Android app UI."""

from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Callable, Sequence


DEFAULT_POSITIVE_KEYWORDS = (
    "available",
    "left",
    "reserve",
    "buy",
    "add",
    "magic bag",
    "surprise bag",
)
DEFAULT_NEGATIVE_KEYWORDS = (
    "sold out",
    "nothing available",
    "unavailable",
    "fully booked",
    "check again later",
)


class ADBError(RuntimeError):
    """Raised when an ADB command fails."""


@dataclass(frozen=True)
class AndroidMonitorConfig:
    """Settings for watching the currently visible official Android app screen."""

    adb_path: str = "adb"
    serial: str = ""
    package_name: str = "com.app.tgtg"
    poll_seconds: int = 30
    positive_keywords: tuple[str, ...] = field(default_factory=lambda: DEFAULT_POSITIVE_KEYWORDS)
    negative_keywords: tuple[str, ...] = field(default_factory=lambda: DEFAULT_NEGATIVE_KEYWORDS)


@dataclass(frozen=True)
class DetectionResult:
    """Result of checking one UI snapshot for availability words."""

    is_available: bool
    matched_positive: tuple[str, ...]
    matched_negative: tuple[str, ...]
    screen_text: str


CommandRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]


class AndroidMonitor:
    """Small ADB/uiautomator wrapper used by the Android monitor UI."""

    def __init__(self, config: AndroidMonitorConfig, runner: CommandRunner | None = None) -> None:
        self.config = config
        self.runner = runner or self._default_runner

    def adb_command(self, *args: str) -> list[str]:
        """Build an adb command, including a device serial when provided."""

        command = [self.config.adb_path]
        if self.config.serial.strip():
            command.extend(["-s", self.config.serial.strip()])
        command.extend(args)
        return command

    def launch_app(self) -> None:
        """Launch the official app package in the emulator/device."""

        self._run("shell", "monkey", "-p", self.config.package_name, "1")

    def ensure_device(self) -> str:
        """Return adb devices output or raise when no device/emulator is connected."""

        result = self._run("devices")
        connected = [line for line in result.stdout.splitlines() if line.endswith("\tdevice")]
        if not connected:
            raise ADBError(
                "No Android device/emulator is connected. Start your emulator, log into the official TGTG app, "
                "then confirm `adb devices` shows a device."
            )
        return result.stdout

    def dump_ui_xml(self) -> str:
        """Dump and return the current Android UI hierarchy XML."""

        self._run("shell", "uiautomator", "dump", "/sdcard/window.xml")
        result = self._run("exec-out", "cat", "/sdcard/window.xml")
        if not result.stdout.strip():
            raise ADBError("ADB returned an empty UI dump. Make sure the emulator screen is awake and unlocked.")
        return result.stdout

    def read_screen_text(self) -> str:
        """Read visible/accessibility text from the current Android screen."""

        return extract_visible_text(self.dump_ui_xml())

    def detect_current_screen(self) -> DetectionResult:
        """Detect whether the current app screen appears to show an available bag."""

        return detect_availability(
            self.read_screen_text(),
            self.config.positive_keywords,
            self.config.negative_keywords,
        )

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        command = self.adb_command(*args)
        result = self.runner(command)
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip() or "unknown adb error"
            raise ADBError(f"ADB command failed: {' '.join(command)}\n{stderr}")
        return result

    @staticmethod
    def _default_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, capture_output=True, text=True, check=False)


def parse_keywords(value: str) -> tuple[str, ...]:
    """Parse comma/newline separated keywords from a UI entry field."""

    return tuple(keyword.strip().lower() for keyword in value.replace("\n", ",").split(",") if keyword.strip())


def extract_visible_text(ui_xml: str) -> str:
    """Extract visible text/content descriptions from a uiautomator XML dump."""

    try:
        root = ET.fromstring(ui_xml)
    except ET.ParseError as exc:
        raise ADBError(f"Could not parse Android UI XML: {exc}") from exc

    values: list[str] = []
    for node in root.iter():
        for attribute in ("text", "content-desc"):
            value = node.attrib.get(attribute, "").strip()
            if value:
                values.append(value)
    return "\n".join(dict.fromkeys(values))


def detect_availability(
    screen_text: str,
    positive_keywords: Sequence[str] = DEFAULT_POSITIVE_KEYWORDS,
    negative_keywords: Sequence[str] = DEFAULT_NEGATIVE_KEYWORDS,
) -> DetectionResult:
    """Detect availability from screen text without automating purchase actions."""

    normalized = screen_text.lower()
    positives = tuple(keyword for keyword in positive_keywords if keyword and keyword.lower() in normalized)
    negatives = tuple(keyword for keyword in negative_keywords if keyword and keyword.lower() in normalized)
    return DetectionResult(
        is_available=bool(positives) and not negatives,
        matched_positive=positives,
        matched_negative=negatives,
        screen_text=screen_text,
    )
