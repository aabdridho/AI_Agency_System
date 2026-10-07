from app.delivery.engine import DeliveryEngine


def test_delivery_report_written(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    output = tmp_path / "runtime"

    class FakeChecker:
        def __init__(self, repo):
            pass
        def all_static_checks(self):
            from app.delivery.models import ReadinessCheck
            return [ReadinessCheck(check_id="x", title="X", status="pass", detail="ok")]
        def run_production_validation(self):
            from app.delivery.models import ReadinessCheck
            return (
                ReadinessCheck(
                    check_id="prod",
                    title="Production validation",
                    status="pass",
                    detail="ok",
                ),
                ["npm.cmd run build"],
            )

    monkeypatch.setattr("app.delivery.engine.DeliveryChecker", FakeChecker)
    report = DeliveryEngine().run(
        project_name="demo",
        project_root=project,
        output_root=output,
    )
    assert report.overall_status == "ready"
    assert (output / "demo" / "delivery_report.json").exists()
    assert (output / "demo" / "delivery_report.md").exists()
