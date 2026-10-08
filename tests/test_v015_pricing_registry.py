from decimal import Decimal

from app.execution.costs import PRICE_REGISTRY, PRICING_VERSION


def test_pricing_version_is_current_v015_freeze():
    assert PRICING_VERSION == "2026-10-09"


def test_claude_sonnet_55_cache_read_rate_is_current():
    rate = PRICE_REGISTRY["claude-sonnet-5-5"]

    assert rate["provider"] == "anthropic"
    assert rate["input"] == Decimal("2.00")
    assert rate["cached_input"] == Decimal("0.10")
    assert rate["cache_write"] == Decimal("2.50")
    assert rate["output"] == Decimal("10.00")
    assert rate["source"] == "anthropic_standard_list_2026_10_07"
