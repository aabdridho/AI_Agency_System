from app.routing.classifier import TaskClassifier

CASES = {
    "Initialize project structure and development environment": "setup",
    "Establish page layout and design system from confirmed visual direction": "frontend",
    "Use approved reference aspects as inspiration without copying unconfirmed details": "frontend",
    "Implement form fields: name, email, company, message": "frontend",
    "Add client-side validation": "frontend",
    "Submit form data to `email`": "backend",
    "Add success and failure states": "frontend",
    "Validate submission flow end-to-end": "qa",
    "Verify implementation against every confirmed requirement": "qa",
    "Run deterministic validation/lint/tests": "qa",
    "Check responsive behavior where applicable": "qa",
    "Confirm no unapproved scope was introduced": "qa",
}

def test_real_project_routing_regression():
    classifier = TaskClassifier()
    for task, expected in CASES.items():
        category, _ = classifier.classify(task)
        assert category == expected, f"{task!r}: expected {expected}, got {category}"
