from pathlib import Path


def test_adapters_use_utf8_with_replacement():
    source = Path("app/execution/adapters.py").read_text(encoding="utf-8")
    assert 'encoding="utf-8"' in source
    assert 'errors="replace"' in source
