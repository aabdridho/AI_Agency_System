from app.delivery.engine import DeliveryEngine


def test_engine_writes_client_input_request(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    output = tmp_path / "runtime"

    class FakeChecker:
        def __init__(self, repo):
            pass

        def all_static_checks(self):
            from app.delivery.models import ReadinessCheck
            return [
                ReadinessCheck(
                    check_id="placeholder_content",
                    title="Placeholder/client content",
                    status="blocker",
                    detail=(
                        "Potential placeholder content found in 1 file(s): "
                        "src/content/hero.ts"
                    ),
                    blocker_class="CLIENT_INPUT_REQUIRED",
                )
            ]

        def run_production_validation(self):
            from app.delivery.models import ReadinessCheck
            return (
                ReadinessCheck(
                    check_id="production_validation",
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

    packet = output / "demo" / "client_input_request.md"
    assert report.overall_status == "blocked"
    assert report.client_input_request == str(packet)
    assert packet.exists()
    assert "Hero" in packet.read_text(encoding="utf-8")
