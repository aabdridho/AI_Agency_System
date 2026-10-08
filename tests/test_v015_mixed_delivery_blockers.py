from app.delivery.models import ReadinessCheck
from app.orchestration.orchestrator import _delivery_allows_auto_resolution


def _check(blocker_class, *, auto=False):
    return ReadinessCheck(
        check_id=blocker_class.lower(),
        title=blocker_class,
        status="blocker",
        detail="test",
        blocker_class=blocker_class,
        auto_resolvable=auto,
    )


def test_auto_only_can_be_resolved_internally():
    checks = [
        _check("AUTO_RESOLVABLE_INTERNAL", auto=True),
    ]

    assert _delivery_allows_auto_resolution(checks) is True


def test_client_input_blocks_internal_auto_resolution():
    checks = [
        _check("AUTO_RESOLVABLE_INTERNAL", auto=True),
        _check("CLIENT_INPUT_REQUIRED"),
    ]

    assert _delivery_allows_auto_resolution(checks) is False


def test_hard_technical_blocker_blocks_internal_auto_resolution():
    checks = [
        _check("AUTO_RESOLVABLE_INTERNAL", auto=True),
        _check("HARD_TECHNICAL_BLOCKER"),
    ]

    assert _delivery_allows_auto_resolution(checks) is False


def test_non_auto_internal_blocker_is_not_auto_resolved():
    checks = [
        _check("AUTO_RESOLVABLE_INTERNAL", auto=False),
    ]

    assert _delivery_allows_auto_resolution(checks) is False
