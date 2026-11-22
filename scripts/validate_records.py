"""Deterministic checks for V1 extraction records. No third-party dependencies."""
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

PREFIX = {'furniture': 'F', 'lighting': 'L', 'material': 'M'}
EVIDENCE = {'VERIFIED', 'CLIENT-PROVIDED', 'MISSING', 'CONFLICT'}
STATUSES = {'Draft', 'Needs Verification', 'Ready for Review', 'Approved'}

def validate(data):
    issues = []
    known_total = Decimal('0')
    incomplete = False
    seen = set()
    for idx, item in enumerate(data.get('products', [])):
        label = item.get('item_id', f'index:{idx}')
        category = item.get('category')
        if category not in PREFIX or not re.fullmatch(r'[FLM]-\d{3,}', str(label)) or not str(label).startswith(PREFIX.get(category, '?') + '-'):
            issues.append(f'{label}: invalid category or item ID')
        if label in seen:
            issues.append(f'{label}: duplicate item ID')
        seen.add(label)
        if item.get('approval_status') not in STATUSES:
            issues.append(f'{label}: invalid approval status')
        source_ids = {s.get('source_id') for s in item.get('sources', [])}
        for field, attr in item.get('attributes', {}).items():
            ev, val, refs = attr.get('evidence'), attr.get('value'), attr.get('source_ids', [])
            if ev not in EVIDENCE:
                issues.append(f'{label}.{field}: invalid evidence state')
            if ev == 'MISSING' and val is not None:
                issues.append(f'{label}.{field}: MISSING must have null value')
            if ev in ('VERIFIED', 'CLIENT-PROVIDED') and (val is None or not refs):
                issues.append(f'{label}.{field}: claimed evidence needs value and source')
            if any(ref not in source_ids for ref in refs):
                issues.append(f'{label}.{field}: unknown source reference')
        attrs = item.get('attributes', {})
        price = attrs.get('unit_price', {}).get('value')
        qty = item.get('quantity')
        if isinstance(price, (int, float)) and not isinstance(price, bool) and isinstance(qty, (int, float)) and not isinstance(qty, bool) and price >= 0 and qty > 0:
            known_total += Decimal(str(price)) * Decimal(str(qty))
        else:
            incomplete = True
        if item.get('approval_status') == 'Approved' and not data.get('human_approval', {}).get(label):
            issues.append(f'{label}: Approved without explicit human signoff')
    return {'issues': issues, 'known_subtotal': str(known_total), 'currency': data.get('currency'), 'total_incomplete': incomplete, 'product_count': len(data.get('products', []))}

if __name__ == '__main__':
    data = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    report = validate(data)
    print(json.dumps(report, indent=2))
    sys.exit(1 if report['issues'] else 0)
