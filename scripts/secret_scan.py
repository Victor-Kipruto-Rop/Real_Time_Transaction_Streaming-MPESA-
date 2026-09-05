#!/usr/bin/env python3
"""Simple repo secret scanner for common placeholder patterns."""
import re
from pathlib import Path

def scan(path='.'):
    patterns = [r'set_me_via_env', r'change_me', r'admin123', r'your_secure_token_here', r'secret', r'password']
    compiled = re.compile('|'.join(patterns), re.IGNORECASE)
    results = []
    for p in Path(path).rglob('*'):
        if p.is_file() and p.suffix not in {'.pyc','.png','.jpg','.jpeg','.gif','.svg'}:
            try:
                text = p.read_text(errors='ignore')
            except Exception:
                continue
            for m in compiled.finditer(text):
                line_no = text[:m.start()].count('\n') + 1
                results.append((str(p), line_no, m.group(0)))
    return results

if __name__ == '__main__':
    r = scan('.')
    if not r:
        print('No placeholder secrets found.')
    else:
        for f,l,m in r:
            print(f'{f}:{l}: {m}')
        print(f'Found {len(r)} potential placeholder secrets.')
