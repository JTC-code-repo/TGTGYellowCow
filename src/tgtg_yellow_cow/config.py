"""Local credential/config storage for the monitor."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from .tgtg_client import Credentials


APP_DIR = Path(os.environ.get("TGTG_YELLOW_COW_HOME", Path.home() / ".tgtg-yellow-cow"))
CONFIG_PATH = APP_DIR / "config.json"


@dataclass
class AppConfig:
    """Settings persisted across UI launches."""

    credentials: Credentials | None = None
    latitude: float = 40.7128
    longitude: float = -74.0060
    radius_km: float = 5.0
    poll_seconds: int = 30


def load_config(path: Path = CONFIG_PATH) -> AppConfig:
    """Load saved settings, returning safe defaults when none exist."""

    if not path.exists():
        return AppConfig()
    data = json.loads(path.read_text(encoding="utf-8"))
    credentials_data = data.get("credentials")
    credentials = Credentials(**credentials_data) if credentials_data else None
    return AppConfig(
        credentials=credentials,
        latitude=float(data.get("latitude", AppConfig.latitude)),
        longitude=float(data.get("longitude", AppConfig.longitude)),
        radius_km=float(data.get("radius_km", AppConfig.radius_km)),
        poll_seconds=int(data.get("poll_seconds", AppConfig.poll_seconds)),
    )


def save_config(config: AppConfig, path: Path = CONFIG_PATH) -> None:
    """Persist settings with private file permissions on POSIX systems."""

    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(config)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.chmod(path, 0o600)
