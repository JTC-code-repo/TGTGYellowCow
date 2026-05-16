import subprocess

from tgtg_yellow_cow.android_monitor import (
    ADBError,
    AndroidMonitor,
    AndroidMonitorConfig,
    detect_availability,
    extract_visible_text,
    parse_keywords,
)


def completed(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(["adb"], returncode, stdout, stderr)


def test_parse_keywords_accepts_commas_and_newlines():
    assert parse_keywords("available, left\nreserve") == ("available", "left", "reserve")


def test_extract_visible_text_reads_text_and_content_description():
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <hierarchy>
      <node text="Store A" content-desc="" />
      <node text="" content-desc="1 surprise bag available" />
      <node text="Store A" content-desc="duplicate ignored" />
    </hierarchy>'''

    text = extract_visible_text(xml)

    assert "Store A" in text
    assert "1 surprise bag available" in text
    assert text.count("Store A") == 1


def test_detect_availability_requires_positive_without_negative():
    available = detect_availability("Store A\n1 magic bag available", ("available",), ("sold out",), ("log in",))
    sold_out = detect_availability("Store A\nSold out", ("available",), ("sold out",), ("log in",))
    login = detect_availability("Log in to continue\n1 bag available", ("available",), ("sold out",), ("log in",))

    assert available.is_available is True
    assert available.matched_positive == ("available",)
    assert sold_out.is_available is False
    assert sold_out.matched_negative == ("sold out",)
    assert login.is_available is False
    assert login.login_required is True
    assert login.matched_login == ("log in",)


def test_android_monitor_builds_serial_command_and_reads_screen():
    calls = []

    def runner(command):
        calls.append(command)
        if command[-1] == "devices":
            return completed("List of devices attached\nemulator-5554\tdevice\n")
        if command[-3:] == ["exec-out", "cat", "/sdcard/window.xml"]:
            return completed('<hierarchy><node text="1 bag available" /></hierarchy>')
        return completed("UI dumped")

    monitor = AndroidMonitor(AndroidMonitorConfig(serial="emulator-5554"), runner=runner)

    assert "emulator-5554\tdevice" in monitor.ensure_device()
    result = monitor.detect_current_screen()

    assert result.is_available is True
    assert result.login_required is False
    assert calls[0][:3] == ["adb", "-s", "emulator-5554"]


def test_android_monitor_raises_when_no_device_connected():
    monitor = AndroidMonitor(AndroidMonitorConfig(), runner=lambda _command: completed("List of devices attached\n"))

    try:
        monitor.ensure_device()
    except ADBError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected ADBError")

    assert "No Android device" in message
