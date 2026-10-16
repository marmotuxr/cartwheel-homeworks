from __future__ import annotations

import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest

from agent import db
from agent.agent import TOOLS_BY_ROLE
from agent.auth import AuthContext
from agent.tools import check_return_eligibility

SHOPPER_1 = AuthContext(user_id=1, role="shopper")
SHOPPER_2 = AuthContext(user_id=2, role="shopper")


def _set_order_delivery(
    order_id: int, *, store_id: int, delivered_days_ago: int
) -> None:
    with db.connection() as conn:
        delivered_at = db.world_asof(conn) - timedelta(days=delivered_days_ago)
        shipped_at = delivered_at - timedelta(days=3)
        conn.execute(
            """
            UPDATE orders
            SET store_id = ?, status = 'delivered', shipped_at = ?,
                delivered_at = ?
            WHERE id = ?
            """,
            (store_id, shipped_at.isoformat(), delivered_at.isoformat(), order_id),
        )
        conn.commit()


def _database_snapshot(path: Path) -> dict[str, list[tuple]]:
    tables = (
        "stores",
        "users",
        "products",
        "orders",
        "refunds",
        "escalations",
        "meta",
        "data_quality_cases",
    )
    with sqlite3.connect(path) as conn:
        return {
            table: conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in tables
        }


def test_check_return_eligibility_reports_open_platform_window(world_copy: Path) -> None:
    result = check_return_eligibility(SHOPPER_1, 4127)

    assert result == {
        "ok": True,
        "order_id": 4127,
        "status": "delivered",
        "delivered_at": "2026-06-19",
        "return_window_days": 30,
        "policy_id": "cw-returns",
        "assessment": "return_window_open",
        "return_window_open": True,
        "next_step": (
            "If you want to proceed, request a return. This assessment "
            "does not approve or submit a return or issue a refund."
        ),
    }


def test_check_return_eligibility_reports_expired_window(world_copy: Path) -> None:
    result = check_return_eligibility(SHOPPER_1, 3980)

    assert result["ok"] is True
    assert result["assessment"] == "return_window_expired"
    assert result["return_window_open"] is False
    assert result["return_window_days"] == 30
    assert result["policy_id"] == "cw-returns"
    assert "does not submit" in result["next_step"]


def test_check_return_eligibility_waits_for_delivery(world_copy: Path) -> None:
    with db.connection() as conn:
        conn.execute(
            """
            UPDATE orders
            SET status = 'shipped', delivered_at = NULL, refund_eligible = 0
            WHERE id = 4127
            """
        )
        conn.commit()

    result = check_return_eligibility(SHOPPER_1, 4127)

    assert result["ok"] is True
    assert result["status"] == "shipped"
    assert result["delivered_at"] is None
    assert result["assessment"] == "pending_delivery"
    assert result["return_window_open"] is None
    assert "Wait until delivery" in result["next_step"]


@pytest.mark.parametrize(
    ("delivered_days_ago", "expected_assessment", "window_open"),
    [
        (14, "return_window_open", True),
        (15, "return_window_expired", False),
    ],
)
def test_check_return_eligibility_uses_store_override(
    world_copy: Path,
    delivered_days_ago: int,
    expected_assessment: str,
    window_open: bool,
) -> None:
    _set_order_delivery(
        4127, store_id=2, delivered_days_ago=delivered_days_ago
    )

    result = check_return_eligibility(SHOPPER_1, 4127)

    assert result["assessment"] == expected_assessment
    assert result["return_window_open"] is window_open
    assert result["return_window_days"] == 14
    assert result["policy_id"] == "store-juniper-home-goods-policy"


def test_check_return_eligibility_denies_other_shopper(world_copy: Path) -> None:
    result = check_return_eligibility(SHOPPER_2, 4127)

    assert result["ok"] is False
    assert result["error"] == "permission_denied"
    assert "delivered_at" not in result
    assert "status" not in result


def test_check_return_eligibility_reports_missing_order(world_copy: Path) -> None:
    result = check_return_eligibility(SHOPPER_1, 999_999)

    assert result["ok"] is False
    assert result["error"] == "not_found"


def test_check_return_eligibility_does_not_change_database(world_copy: Path) -> None:
    before = _database_snapshot(world_copy)

    result = check_return_eligibility(SHOPPER_1, 4127)

    assert result["ok"] is True
    assert _database_snapshot(world_copy) == before


def test_check_return_eligibility_is_registered_for_all_roles() -> None:
    for role in ("shopper", "merchant", "support"):
        names = [tool.name for tool in TOOLS_BY_ROLE[role]]
        assert "check_return_eligibility" in names
