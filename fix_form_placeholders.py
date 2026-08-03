import os
import re

REPLACEMENTS = [
    (r'empty_label\s*=\s*["\'].*?["\']', "empty_label='Select an option...'"),
    (r'\(\'\'\s*,\s*["\'].*?["\']', "('', 'Select an option...'"),
    (r'\(None\s*,\s*["\'].*?["\']', "(None, 'Select an option...'"),
    (r'<option value="">-+</option>', '<option value="" disabled selected>Select an option...</option>'),
    (r'value="\[\]"', 'placeholder="e.g., vpn, network, email"'),
    (r'initial\s*=\s*["\']\[\]["\']', "initial=''")
]

def scan_and_fix(directory='.'):
    print('Scanning project files...')
    modified = 0
    for root, dirs, files in os.walk(directory):
        if any(ignored in root for ignored in ['.venv', 'venv', 'env', '.git', '__pycache__']):
            continue
        for file in files:
            if file.endswith(('.py', '.html')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    new_content = content
                    for pattern, replacement in REPLACEMENTS:
                        new_content = re.sub(pattern, replacement, new_content)
                    if new_content != content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f'Updated: {filepath}')
                        modified += 1
                except Exception:
                    pass
    print(f'Done! Modified {modified} file(s).')

if __name__ == "__main__":
    scan_and_fix()
