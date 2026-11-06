#!/usr/bin/env python3
"""Synchronize the README Complete TODO List with TODO markers.

Baseline: the existing README TODO entries.
Only .py files that differ between origin/main and HEAD (dev) are updated:
their baseline entries are replaced by the TODO markers extracted from dev.
Temporary/helper files are ignored and their entries removed.
All other entries are preserved.
"""
import re
import subprocess
import sys

TODO_RE = re.compile(r'TODO:?\s*(.*)')
ENTRY_RE = re.compile(r'^- \[ \] \*\*(.+?):(\d+)\*\* - (.*)$')
MARKER = '### \U0001f4dd Complete TODO List'
NEXT_SECTION = '## \U0001f91d Contributing'

# Temporary helper files introduced only to run this sync; never part of the
# project's TODO baseline.
IGNORE_PATHS = {
    '.todo_sync_update.py',
    'todo_sync_test.txt',
    '.github/workflows/todo-sync.yml',
}


def is_ignored(path):
    return (
        path in IGNORE_PATHS
        or path.startswith('.github/')
        or path.startswith('.')
    )


def git(*args):
    return subprocess.check_output(['git', *args], text=True, errors='replace')


def extract_todos(path):
    """Return [(lineno, text), ...] for a file at HEAD, or [] if deleted."""
    try:
        content = git('show', f'HEAD:{path}')
    except subprocess.CalledProcessError:
        return []
    todos = []
    for lineno, line in enumerate(content.splitlines(), 1):
        if 'TODO' in line:
            match = TODO_RE.search(line)
            text = match.group(1).strip() if match else line.strip()
            todos.append((lineno, text))
    return todos


def main():
    changed_py = [
        p for p in git('diff', '--name-only', 'origin/main', 'HEAD', '--', '*.py').splitlines()
        if p.strip() and not is_ignored(p)
    ]
    print('Changed .py files between origin/main and HEAD (excluding helpers):')
    for p in changed_py:
        print(f'  {p}')
    if not changed_py:
        print('No relevant .py changes; nothing to do.')
        return

    new_todos = {p: extract_todos(p) for p in changed_py}
    for p, todos in new_todos.items():
        print(f'Extracted {len(todos)} TODO(s) from {p}:')
        for lineno, text in todos:
            print(f'  {lineno}: {text}')

    with open('README.md', encoding='utf-8') as f:
        readme = f.read()

    entries = []
    for line in readme.splitlines():
        match = ENTRY_RE.match(line)
        if match:
            entries.append((match.group(1), int(match.group(2)), match.group(3)))
    print(f'Current entries: {len(entries)}')

    changed_set = set(changed_py)
    kept = [
        e for e in entries
        if e[0] not in changed_set and not is_ignored(e[0])
    ]
    added = [
        (path, lineno, text)
        for path in changed_py
        for lineno, text in new_todos[path]
    ]
    final_entries = sorted(kept + added, key=lambda e: (e[0], e[1]))
    print(f'Final entries: {len(final_entries)} (kept={len(kept)}, added={len(added)})')

    new_block = (
        '\n'
        + '\n'.join(
            f'- [ ] **{path}:{lineno}** - {text}'
            for path, lineno, text in final_entries
        )
        + '\n'
    )

    pattern = re.compile(
        r'(' + re.escape(MARKER) + r'\n)(.*?)(\n' + re.escape(NEXT_SECTION) + r')',
        re.DOTALL,
    )
    if not pattern.search(readme):
        print('ERROR: could not locate TODO section boundaries', file=sys.stderr)
        sys.exit(1)

    updated = pattern.sub(
        lambda m: m.group(1) + new_block + m.group(3), readme, count=1
    )

    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(updated)
    print('README.md updated successfully.')


if __name__ == '__main__':
    main()
