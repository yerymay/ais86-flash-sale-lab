import uuid
from datetime import datetime, timezone

from app.events import build_order_created_event, validate_cloud_event


def complete_event() -> dict:
    return {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": "/services/orders",
        "type": "pe.unamba.flash.order.created.v1",
        "time": datetime.now(timezone.utc).isoformat(),
        "datacontenttype": "application/json",
        "data": {
            "order_id": str(uuid.uuid4()),
            "items": [
                {"product_id": "nova-headphones", "quantity": 2},
                {"product_id": "arc-mouse", "quantity": 1},
            ],
            "total_cents": 309700,
        },
    }


def test_valid_event_passes() -> None:
    assert validate_cloud_event(complete_event()) == []


def test_order_created_event_includes_required_order_data() -> None:
    order_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)
    event = build_order_created_event(
        order_id,
        [{"product_id": "nova-headphones", "quantity": 2}],
        259800,
        created_at,
    )

    assert event["type"] == "pe.unamba.flash.order.created.v1"
    assert event["data"] == {
        "order_id": str(order_id),
        "items": [{"product_id": "nova-headphones", "quantity": 2}],
        "total_cents": 259800,
    }
    assert validate_cloud_event(event) == []


def test_event_requires_identity_fields() -> None:
    event = complete_event()
    event["id"] = "not-a-uuid"
    event["source"] = "elsewhere"
    event["type"] = "wrong.type"
    errors = validate_cloud_event(event)
    assert any("id" in error for error in errors)
    assert any("source" in error for error in errors)
    assert any("type" in error for error in errors)


def test_event_rejects_non_rfc3339_time_and_noncanonical_uuid() -> None:
    event = complete_event()
    event["time"] = datetime.now().replace(tzinfo=None).isoformat()
    event["id"] = "{" + event["id"] + "}"

    errors = validate_cloud_event(event)

    assert any("id" in error for error in errors)
    assert any("time" in error for error in errors)


def test_event_requires_items_and_integer_quantities() -> None:
    event = complete_event()
    event["data"]["items"] = [{"product_id": "nova-headphones", "quantity": "2"}]
    assert any("quantity" in error for error in validate_cloud_event(event))

    event["data"]["items"] = [{"product_id": "nova-headphones", "quantity": True}]
    assert any("quantity" in error for error in validate_cloud_event(event))

    event["data"]["items"] = []
    assert any("items" in error for error in validate_cloud_event(event))


def test_event_requires_non_negative_total() -> None:
    event = complete_event()
    event["data"]["total_cents"] = -1
    assert any("total_cents" in error for error in validate_cloud_event(event))

    event["data"]["total_cents"] = "100"
    assert any("total_cents" in error for error in validate_cloud_event(event))

    del event["data"]["total_cents"]
    assert any("total_cents" in error for error in validate_cloud_event(event))


def test_event_rejects_missing_required_envelope_fields() -> None:
    for field in ("specversion", "id", "source", "type", "time", "datacontenttype", "data"):
        event = complete_event()
        del event[field]
        assert validate_cloud_event(event)


def test_event_rejects_missing_required_order_fields() -> None:
    event = complete_event()
    del event["data"]["order_id"]
    assert any("order_id" in error for error in validate_cloud_event(event))

    event = complete_event()
    del event["data"]["items"][0]["product_id"]
    assert any("product_id" in error for error in validate_cloud_event(event))

    event = complete_event()
    del event["data"]["items"][0]["quantity"]
    assert any("quantity" in error for error in validate_cloud_event(event))
