from pathlib import Path


def test_demo_site_not_in_package_roots() -> None:
    demo_site_dir = Path("demo-site")
    assert demo_site_dir.exists()
    pyproject_text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "demo-site" in pyproject_text
    assert "project.scripts" in pyproject_text
