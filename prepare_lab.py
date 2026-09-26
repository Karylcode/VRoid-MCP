"""Copy a locally installed, supported VRoid into a NEW lab. Never modifies the source."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

TESTED_SHA256='793eb5fcff3093f344ee930fbfa0c0796ed7780ac91c45bdb7ce6bd34d62fd3c'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--lab',required=True,type=Path)
    args=parser.parse_args()
    source=args.source.resolve();lab=args.lab.resolve()
    if lab==source or lab.is_relative_to(source) or source.is_relative_to(lab):
        raise ValueError('Source and lab must be separate directories')
    if lab.exists():raise FileExistsError('Choose a new lab; existing directories are never replaced')
    assembly=source/'GameAssembly.dll'
    if not (source/'VRoidStudio.exe').is_file() or not assembly.is_file():
        raise FileNotFoundError('Source is not a VRoid Studio install')
    if hashlib.sha256(assembly.read_bytes()).hexdigest()!=TESTED_SHA256:
        raise ValueError('Untested VRoid binary; this release requires the verified 2.14.0 build')
    files=sorted(p for p in source.rglob('*') if p.is_file())
    if any(p.resolve()!=p for p in source.rglob('*')):
        raise ValueError('Source contains links/junctions; inspect them before copying')
    manifest=[{'path':str(p.relative_to(source)),'size':p.stat().st_size,
               'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    lab.mkdir(parents=True,exist_ok=False)
    shutil.copytree(source,lab/'app',copy_function=shutil.copy2)
    for entry in manifest:
        if hashlib.sha256((lab/'app'/entry['path']).read_bytes()).hexdigest()!=entry['sha256']:
            raise RuntimeError('Copy hash mismatch: '+entry['path'])
    (lab/'source-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    print(f'Copied and verified {len(manifest)} files into {lab}')


if __name__=='__main__':main()
