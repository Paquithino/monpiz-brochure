from pathlib import Path

from monpiz_brochure.builder import BuildOptions
from monpiz_brochure.watch import build_command, changed_files, snapshot


def test_changes_are_detected(tmp_path: Path) -> None:
    content = tmp_path / "brochure.yaml"
    content.write_text("a")
    before = snapshot([tmp_path])
    content.write_text("bb")
    (tmp_path / "new.png").write_bytes(b"x")
    after = {**snapshot([tmp_path]), content: before[content] + 1}
    assert changed_files(before, after) == {content, tmp_path / "new.png"}


def test_build_command_passes_the_options() -> None:
    options = BuildOptions(Path("c.yaml"), Path("assets"), Path("out.pdf"), dpi=150, bleed=False, guides=True)
    command = build_command(options)
    assert command[1:4] == ["-m", "monpiz_brochure", "build"]
    assert "--no-bleed" in command and "--guides" in command and "--marks" not in command
