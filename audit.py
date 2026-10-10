import re
import sys

def audit_html(filename):
    print(f"=== Auditing {filename} ===")
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all inline event handlers
    matches = re.findall(r'\bon[a-zA-Z]+\s*=\s*"([^"]+)"', content)
    script_start = content.rfind('<script>')
    script_part = content[script_start:] if script_start != -1 else ""

    # Check for JSON.stringify in template literal onclick attributes
    for m in re.finditer(r'onclick=[\'"][^\'"]*\${JSON\.stringify[^\'"]*[\'"]', content):
        print("CRITICAL: Broken onclick with JSON.stringify found:", m.group(0))

    # Check for setLang
    if 'setLang(' in content and 'function setLang' not in content:
        print("CRITICAL: setLang is called but not defined!")


    # Check for element IDs accessed via document.getElementById that don't exist
    ids_in_html = set(re.findall(r'\bid\s*=\s*"([^"]+)"', content))
    ids_in_js = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", script_part))
    missing_ids = ids_in_js - ids_in_html
    print("Element IDs referenced in JS but not found in HTML:", missing_ids)

audit_html('index.html')
audit_html('login.html')
