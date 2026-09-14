from pathlib import Path
import zipfile

root = Path(__file__).resolve().parent.parent
output = root / 'outputs'
target = output / 'library-harness-design-and-code.zip'
paths = [output / 'library-harness-design.md', output / 'architecture.mmd']
paths += [p for p in (output / 'library_harness').rglob('*')
          if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(paths):
        archive.write(path, path.relative_to(output).as_posix())
with zipfile.ZipFile(target) as archive:
    assert archive.testzip() is None
    print(f'{len(archive.namelist())} files in {target}')
