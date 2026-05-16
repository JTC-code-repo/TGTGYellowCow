"""Small adapter around the unofficial Too Good To Go Python client."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol


class TgtgLoginBlockedError(RuntimeError):
    """Raised when Too Good To Go blocks e-mail login with bot protection."""


class TgtgClientProtocol(Protocol):
    """Methods used by the app from the upstream client."""

    def get_items(self, **kwargs: Any) -> list[dict[str, Any]]: ...

    def get_item(self, item_id: str) -> dict[str, Any]: ...

    def create_order(self, item_id: str, number_of_items: int) -> dict[str, Any]: ...


@dataclass(frozen=True)
class Credentials:
    """Persistable Too Good To Go credentials."""

    access_token: str
    refresh_token: str
    cookie: str


@dataclass(frozen=True)
class StoreBag:
    """Display-friendly view of a Too Good To Go item/store response."""

    item_id: str
    store_id: str
    display_name: str
    address: str
    items_available: int
    price: str
    distance_km: float | None
    pickup_window: str
    in_sales_window: bool
    raw: dict[str, Any]

    @property
    def available(self) -> bool:
        return self.items_available > 0 and self.in_sales_window

    def list_label(self) -> str:
        stock = f"{self.items_available} available" if self.items_available else "sold out"
        distance = f" · {self.distance_km:.1f} km" if self.distance_km is not None else ""
        return f"{self.display_name} · {stock} · {self.price}{distance}"


def credentials_from_mapping(data: dict[str, Any]) -> Credentials:
    """Build credentials from a saved/exported credentials mapping."""

    missing = [key for key in ("access_token", "refresh_token", "cookie") if not data.get(key)]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(
            "Missing required credential field(s): "
            f"{missing_text}. This version of the tgtg client needs access_token, refresh_token, and cookie; "
            "user_id alone is not enough."
        )
    return Credentials(
        access_token=str(data["access_token"]),
        refresh_token=str(data["refresh_token"]),
        cookie=str(data["cookie"]),
    )


def build_client(credentials: Credentials) -> TgtgClientProtocol:
    """Create the upstream TgtgClient lazily so tests do not need network packages."""

    from tgtg import TgtgClient

    return TgtgClient(
        access_token=credentials.access_token,
        refresh_token=credentials.refresh_token,
        cookie=credentials.cookie,
    )


def request_credentials(email: str) -> Credentials:
    """Run Too Good To Go e-mail login and return credentials after link approval."""

    from tgtg import TgtgClient

    client = TgtgClient(email=email)
    try:
        credentials = client.get_credentials()
    except Exception as exc:
        message = format_tgtg_error(exc)
        if _is_captcha_challenge(exc):
            raise TgtgLoginBlockedError(message) from exc
        raise
    return credentials_from_mapping(credentials)


def format_tgtg_error(exc: Exception) -> str:
    """Return a clearer error message for known Too Good To Go failures."""

    if isinstance(exc, TgtgLoginBlockedError):
        return str(exc)
    if _is_captcha_challenge(exc):
        captcha_url = _extract_captcha_url(exc)
        lines = [
            "Too Good To Go returned HTTP 403 with a captcha/bot-protection challenge during e-mail login.",
            "",
            "This usually means Too Good To Go blocked the unofficial API login from this network, IP, or device before it could send/complete the login e-mail flow.",
            "",
            "What to try:",
            "1. Confirm you can log in normally in the official Too Good To Go mobile app.",
            "2. Close this app, wait a few minutes, then try again from a normal home/mobile network instead of a VPN, proxy, datacenter, or corporate network.",
            "3. If it keeps happening, Too Good To Go may be requiring an in-browser captcha that the unofficial Python client cannot solve automatically.",
            "4. This app will not bypass captcha or bot-protection. Use the official Too Good To Go app for login/purchase if the challenge persists.",
        ]
        if captcha_url:
            lines.extend(["", f"Captcha challenge URL returned by the service: {captcha_url}"])
        lines.extend(["", f"Original error: {exc}"])
        return "\n".join(lines)
    return str(exc)


def _is_captcha_challenge(exc: Exception) -> bool:
    haystack = _exception_text(exc).lower()
    return "403" in haystack and "captcha-delivery.com" in haystack


def _extract_captcha_url(exc: Exception) -> str | None:
    for arg in exc.args:
        parsed = _extract_url_from_json_payload(arg)
        if parsed:
            return parsed
    match = re.search(r"https://geo\.captcha-delivery\.com/[^'\")\s]+", _exception_text(exc))
    return match.group(0) if match else None


def _extract_url_from_json_payload(value: Any) -> str | None:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if not isinstance(value, str):
        return None
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return None
    url = payload.get("url") if isinstance(payload, dict) else None
    if isinstance(url, str) and "captcha-delivery.com" in url:
        return url
    return None


def _exception_text(exc: Exception) -> str:
    parts = [str(exc)]
    for arg in exc.args:
        if isinstance(arg, bytes):
            parts.append(arg.decode("utf-8", errors="replace"))
        else:
            parts.append(str(arg))
    return "\n".join(parts)


def fetch_nearby_bags(
    client: TgtgClientProtocol,
    latitude: float,
    longitude: float,
    radius_km: float,
) -> list[StoreBag]:
    """Fetch nearby non-favorite-only bags and normalize them for the UI."""

    items = client.get_items(
        favorites_only=False,
        latitude=latitude,
        longitude=longitude,
        radius=radius_km,
    )
    return sorted((_normalize_item(item) for item in items), key=lambda bag: bag.display_name.lower())


def refresh_bag(client: TgtgClientProtocol, bag: StoreBag) -> StoreBag:
    """Reload a selected bag by item id."""

    return _normalize_item(client.get_item(item_id=bag.item_id))


def reserve_bag(client: TgtgClientProtocol, bag: StoreBag, quantity: int = 1) -> dict[str, Any]:
    """Reserve one or more available bags; payment still happens in the mobile app."""

    return client.create_order(bag.item_id, quantity)


def format_money(value: dict[str, Any] | None) -> str:
    """Convert the API money shape to a user-readable amount."""

    if not value:
        return "price unknown"
    code = value.get("code", "")
    minor_units = value.get("minor_units")
    decimals = value.get("decimals", 2)
    if minor_units is None:
        return f"{code} price unknown".strip()
    amount = minor_units / (10**decimals)
    return f"{amount:.{decimals}f} {code}".strip()


def _normalize_item(item: dict[str, Any]) -> StoreBag:
    item_info = item.get("item", {})
    store = item.get("store", {})
    location = item.get("pickup_location") or store.get("store_location", {})
    address = (location.get("address") or {}).get("address_line", "")
    pickup_interval = item.get("pickup_interval") or {}
    pickup_window = _format_pickup_window(pickup_interval)
    distance = item.get("distance")
    distance_km = float(distance) / 1000 if distance is not None else None
    return StoreBag(
        item_id=str(item_info.get("item_id", item.get("item_id", ""))),
        store_id=str(store.get("store_id", "")),
        display_name=item.get("display_name") or store.get("store_name") or "Unnamed store",
        address=address,
        items_available=int(item.get("items_available") or 0),
        price=format_money(item_info.get("price_including_taxes") or item_info.get("item_price")),
        distance_km=distance_km,
        pickup_window=pickup_window,
        in_sales_window=bool(item.get("in_sales_window", True)),
        raw=item,
    )


def _format_pickup_window(pickup_interval: dict[str, Any]) -> str:
    start = pickup_interval.get("start")
    end = pickup_interval.get("end")
    if start and end:
        return f"{start} → {end}"
    if start:
        return f"starts {start}"
    if end:
        return f"ends {end}"
    return "pickup window unavailable"
