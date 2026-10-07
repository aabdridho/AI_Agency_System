from app.routing.classifier import TaskClassifier

def test_configuring_quality_rules_is_setup():
    category, _ = TaskClassifier().classify(
        "Apply repository quality rules (formatter, linting, tests where applicable)"
    )
    assert category == "setup"

def test_running_quality_checks_is_qa():
    category, _ = TaskClassifier().classify(
        "Run deterministic validation/lint/tests"
    )
    assert category == "qa"
