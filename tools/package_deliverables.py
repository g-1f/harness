"""Package the current code, skill graph, and docs; never include local credentials."""

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "node-harness.zip")
    args = parser.parse_args()
    paths = [p for p in ROOT.glob("*.py")]
    paths += [
        ROOT / name
        for name in (
            "README.md",
            "requirements.txt",
            "requirements-lock.txt",
            "requirements-dev.txt",
            "pyproject.toml",
        )
    ]
    paths += [ROOT / ".github/workflows/tests.yml"]
    for folder in ("harness", "tests", "skills", "examples", "docs", "tools"):
        paths += [
            p
            for p in (ROOT / folder).rglob("*")
            if p.is_file()
            and p.suffix in (".py", ".js", ".md", ".mmd")
            and "__pycache__" not in p.parts
        ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.output, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(set(paths)):
            archive.write(path, path.relative_to(ROOT).as_posix())
    with ZipFile(args.output) as archive:
        assert archive.testzip() is None
        print(f"{len(archive.namelist())} files in {args.output}")


if __name__ == "__main__":
    main()
