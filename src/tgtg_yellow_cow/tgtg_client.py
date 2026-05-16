"""Small adapter around the unofficial Too Good To Go Python client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


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
    credentials = client.get_credentials()
    return Credentials(
        access_token=credentials["access_token"],
        refresh_token=credentials["refresh_token"],
        cookie=credentials["cookie"],
    )


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
