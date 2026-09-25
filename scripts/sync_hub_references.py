"""Check/export canonical Hub references to the self-contained compatibility skill."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hub-skill', type=Path, required=True)
    parser.add_argument('--write', action='store_true', help='Copy manifest files; default only checks')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'scripts/hub-references.json').read_text(encoding='utf-8'))
    destination = args.hub_skill.resolve() / 'references'
    if not (args.hub_skill.resolve() / 'SKILL.md').is_file():
        parser.error('--hub-skill must point to an existing skill directory')
    mismatches = []
    for name in manifest:
        if Path(name).name != name or not name.endswith('.md'):
            parser.error('Manifest must contain Markdown basenames only')
        source = root / 'references/hub' / name
        target = destination / name
        data = source.read_bytes()
        if args.write:
            destination.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        elif not target.is_file() or target.read_bytes() != data:
            mismatches.append(name)
    if mismatches:
        parser.exit(1, 'Hub reference drift: ' + ', '.join(mismatches) + '\n')
    print(f'{len(manifest)} Hub references {"exported" if args.write else "verified"}')


if __name__ == '__main__':
    main()
