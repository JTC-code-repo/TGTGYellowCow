from tgtg_yellow_cow.tgtg_client import StoreBag, fetch_nearby_bags, format_money, refresh_bag, reserve_bag


class FakeClient:
    def __init__(self):
        self.created_orders = []

    def get_items(self, **kwargs):
        self.kwargs = kwargs
        return [sample_item("2", "Beta", 0), sample_item("1", "Alpha", 3)]

    def get_item(self, item_id):
        return sample_item(item_id, "Alpha", 1)

    def create_order(self, item_id, number_of_items):
        self.created_orders.append((item_id, number_of_items))
        return {"id": "order-123", "item_id": item_id, "state": "RESERVED"}


def sample_item(item_id, name, available):
    return {
        "item": {
            "item_id": item_id,
            "price_including_taxes": {"code": "USD", "minor_units": 499, "decimals": 2},
        },
        "store": {
            "store_id": f"store-{item_id}",
            "store_name": name,
            "store_location": {"address": {"address_line": "1 Main St"}},
        },
        "display_name": name,
        "items_available": available,
        "distance": 1500,
        "in_sales_window": True,
        "pickup_interval": {"start": "2026-05-14T10:00:00Z", "end": "2026-05-14T11:00:00Z"},
    }


def test_format_money():
    assert format_money({"code": "USD", "minor_units": 1234, "decimals": 2}) == "12.34 USD"
    assert format_money(None) == "price unknown"


def test_fetch_nearby_bags_sorts_and_normalizes():
    client = FakeClient()
    bags = fetch_nearby_bags(client, 1.0, 2.0, 3.0)

    assert [bag.display_name for bag in bags] == ["Alpha", "Beta"]
    assert bags[0].available is True
    assert bags[0].distance_km == 1.5
    assert client.kwargs == {"favorites_only": False, "latitude": 1.0, "longitude": 2.0, "radius": 3.0}


def test_refresh_and_reserve_bag():
    client = FakeClient()
    bag = StoreBag("1", "store-1", "Alpha", "1 Main St", 0, "4.99 USD", 1.5, "", True, {})

    refreshed = refresh_bag(client, bag)
    order = reserve_bag(client, refreshed)

    assert refreshed.items_available == 1
    assert order["state"] == "RESERVED"
    assert client.created_orders == [("1", 1)]
