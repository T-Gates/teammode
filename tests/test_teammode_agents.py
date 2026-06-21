"""teammode on/off agent-aware 배선 테스트."""
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ENGINE = REPO / "infra" / "teammode.py"
PY = sys.executable


def _run(root: Path, *args: str, home: Path | None = None):
    env = os.environ.copy()
    if home is not None:
        env["HOME"] = str(home)
    return subprocess.run(
        [PY, str(ENGINE), *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def test_on_off_can_target_codex_config(tmp_path):
    root = tmp_path / "team"
    root.mkdir()
    config = tmp_path / "codex" / "config.toml"

    proc = _run(
        root,
        "on", "--root", str(root),
        "--agent", "codex", "--config", str(config),
    )
    assert proc.returncode == 0, proc.stderr
    text = config.read_text()
    assert "# teammode-hooks-start" in text
    assert "[[hooks.PreToolUse]]" in text
    assert "normalize.py" in text
    assert (root / ".teammode-active").exists()

    proc = _run(
        root,
        "off", "--root", str(root),
        "--agent", "codex", "--config", str(config),
    )
    assert proc.returncode == 0, proc.stderr
    text = config.read_text()
    assert "# teammode-hooks-start" in text
    assert "[[hooks.PreToolUse]]" in text
    assert "statusMessage" not in text
    assert not (root / ".teammode-active").exists()


def test_install_mode_targets_detected_claude_and_codex(tmp_path):
    root = tmp_path / "team"
    root.mkdir()
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".codex").mkdir(parents=True)

    proc = _run(root, "on", "--root", str(root), "--install", home=home)
    assert proc.returncode == 0, proc.stderr
    assert (home / ".claude" / "settings.json").is_file()
    codex_config = home / ".codex" / "config.toml"
    assert codex_config.is_file()
    assert "[[hooks.PreToolUse]]" in codex_config.read_text()
