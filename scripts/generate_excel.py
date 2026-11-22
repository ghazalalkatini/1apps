"""Populate the shipped Excel template from reviewed Sprint 1 project JSON."""

import argparse
import io
import json
import math
import re
import textwrap
import xml.etree.ElementTree as ET
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

from validate_records import validate


TEMPLATE = Path(__file__).resolve().parents[1] / 'templates' / 'spec_schedule.xlsx'
NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
ET.register_namespace('x', NS)
UNKNOWN = 'Not verified'
SUPPORTED_EVIDENCE = {'VERIFIED', 'CLIENT-PROVIDED'}


@dataclass(frozen=True)
class Formula:
    expression: str
    cached: Decimal


def tag(name):
    return f'{{{NS}}}{name}'


def number(value):
    return type(value) in (int, float) and (type(value) is int or math.isfinite(value))


def attribute(item, *names):
    for name in names:
        field = item['attributes'].get(name, {})
        if field.get('evidence') in SUPPORTED_EVIDENCE and field.get('value') is not None:
            return field['value']
    return None


def source_text(sources):
    return '\n'.join(dict.fromkeys(source['reference'] for source in sources))


def build_rows(project, final=False):
    products = project.get('products')
    currency = project.get('currency')
    audience = project.get('audience')
    if not isinstance(products, list) or not products:
        raise ValueError('At least one product is required.')
    if audience not in ('B2B', 'B2C') or not re.fullmatch(r'[A-Z]{3}', str(currency)):
        raise ValueError('Specify a B2B or B2C audience and a three-letter project currency.')
    if not isinstance(project.get('project_name'), str) or not project['project_name'].strip():
        raise ValueError('Specify a project name.')
    if final and project.get('approval_state') != 'Approved':
        raise ValueError('Final export requires recorded project approval.')
    issues = validate(project)['issues']
    if issues:
        raise ValueError('\n'.join(issues))

    schedule, shopping, qa = [], [], []
    known_total = Decimal(0)
    excluded = 0
    for row, item in enumerate(products, 2):
        item_id = item['item_id']
        sources = item['sources']
        references = {source['source_id']: source['reference'] for source in sources}
        qty = item['quantity']
        qty = qty if number(qty) and qty > 0 else None
        price = attribute(item, 'unit_price')
        price = price if number(price) and price >= 0 else None
        item_currency = item['currency']
        if not re.fullmatch(r'[A-Z]{3}', str(item_currency)):
            raise ValueError(f'{item_id}: invalid item currency')
        amounts_known = qty is not None and price is not None
        subtotal = Decimal(str(qty)) * Decimal(str(price)) if amounts_known else None
        if subtotal is not None and item_currency == currency:
            known_total += subtotal
        else:
            excluded += 1

        warnings = []
        if qty is None:
            warnings.append('Confirm quantity')
        if price is None:
            warnings.append('Confirm unit price')
        if item_currency != currency:
            warnings.append(f'{item_currency} cost excluded from {currency} subtotal')
        if not any(source['type'] in ('url', 'pdf', 'manufacturer_sheet') for source in sources):
            warnings.append('Confirm manufacturer source')
        if item['approval_status'] != 'Approved':
            warnings.append('Item approval pending')
        if not any(attribute(item, name) is not None for name in
                   ('width', 'width_cm', 'depth', 'depth_cm', 'height', 'height_cm', 'diameter_cm', 'tile_size')):
            warnings.append('Confirm dimensions')
        for warning in warnings:
            qa.append([item_id, warning, 'REVIEW', None, None])

        evidence = item['attributes']
        for field, entry in evidence.items():
            trace = '\n'.join(references[ref] for ref in entry['source_ids'])
            qa.append([item_id, field, entry['evidence'], None, trace or None])
        for source in sources:
            qa.append([item_id, f"Source {source['source_id']}", source['type'], source.get('accessed_on'), source['reference']])

        # Keep category-specific attributes such as diameter and coverage visible.
        notes = list(item.get('notes', []))
        notes.extend(f'{field}: {entry["value"]}' for field, entry in evidence.items()
                     if field in ('diameter_cm', 'tile_size', 'coverage_per_box', 'wattage', 'certification')
                     and entry['evidence'] in SUPPORTED_EVIDENCE)
        missing = [field.replace('_', ' ') for field, entry in evidence.items()
                   if entry['evidence'] in ('MISSING', 'CONFLICT') and field != 'unit_price']
        warnings.extend(f'Confirm {field}' for field in missing)
        urls = [source for source in sources if source['type'] == 'url']
        dimensions = [attribute(item, name, f'{name}_cm') for name in ('width', 'depth', 'height')]
        unit = attribute(item, 'dimension_unit', 'unit')
        if unit is None and any(attribute(item, f'{name}_cm') is not None for name in ('width', 'depth', 'height')):
            unit = 'cm'
        schedule.append([
            item_id, item['room'], item['category'].title(), item['product_name'], attribute(item, 'brand', 'manufacturer'),
            attribute(item, 'sku', 'model'), *dimensions, unit, attribute(item, 'material'), attribute(item, 'finish', 'color'),
            qty, price, item_currency, Formula(f'IF(COUNT(M{row}:N{row})=2,M{row}*N{row},"")', subtotal) if amounts_known else None,
            attribute(item, 'supplier'), source_text(urls) or None,
            '\n'.join(dict.fromkeys(source['accessed_on'] for source in urls if source.get('accessed_on'))) or None,
            attribute(item, 'lead_time'), item['approval_status'], '\n'.join(notes),
            ', '.join(sorted({entry['evidence'] for entry in evidence.values()})) or UNKNOWN,
        ])
        shopping.append([
            item['room'], item['product_name'], qty, price, item_currency,
            Formula(f'IF(COUNT(C{row}:D{row})=2,C{row}*D{row},"")', subtotal) if amounts_known else None,
            source_text(urls) or attribute(item, 'supplier'), '; '.join(warnings),
        ])

    amount = f"SUMIF('B2B Spec Schedule'!O2:O{len(products) + 1},B5,'B2B Spec Schedule'!P2:P{len(products) + 1})"
    brief = [
        ['Project', project['project_name']], ['Audience', audience], ['Brand', 'Ghazal.design'],
        ['Currency', currency], ['Release status', 'Final — approved' if final else 'Draft — for review'],
        ['Revision', project.get('revision', 1)], ['Rooms', ', '.join(dict.fromkeys(item['room'] for item in products))],
        ['Known-cost subtotal', Formula(amount, known_total)],
        ['Cost coverage', f'Partial — {excluded} item(s) excluded' if excluded else 'All item costs included'],
        ['Cost exclusions', 'Taxes, shipping, duties and installation are excluded.'],
    ]
    return schedule, shopping, qa, brief


def fill_sheet(xml, rows, money_columns, wrap_style, qa_sheet):
    sheet = ET.fromstring(xml)
    data = sheet.find(tag('sheetData'))
    if qa_sheet:
        for cell, label in zip(data[0], ('Item ID', 'Field / Review item', 'Evidence / Status', 'Source date', 'Source reference')):
            cell.find(tag('v')).text = label
    widths = [float(column.get('width')) for column in sheet.find(tag('cols'))]
    for row in list(data)[1:]:
        data.remove(row)
    for index, values in enumerate(rows, 2):
        row = ET.SubElement(data, tag('row'), r=str(index))
        lines = 1
        for column, value in enumerate(values):
            if value is None or value == '':
                continue
            cell = ET.SubElement(row, tag('c'), r=f'{chr(65 + column)}{index}')
            if column in money_columns or (index == 9 and isinstance(value, Formula)):
                cell.set('s', '6')
            if isinstance(value, Formula):
                ET.SubElement(cell, tag('f')).text = value.expression
                ET.SubElement(cell, tag('v')).text = str(value.cached)
            elif number(value):
                ET.SubElement(cell, tag('v')).text = str(value)
            else:
                cell.set('t', 'inlineStr')
                cell.set('s', str(wrap_style))
                inline = ET.SubElement(cell, tag('is'))
                literal = str(value)
                if len(literal) > 32767 or re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]', literal):
                    raise ValueError(f"Invalid Excel text at {cell.get('r')}")
                ET.SubElement(inline, tag('t'), {'{http://www.w3.org/XML/1998/namespace}space': 'preserve'}).text = literal
                width = max(8, int(widths[column] * 0.85))
                lines = max(lines, sum(max(1, len(textwrap.wrap(line, width))) for line in literal.split('\n')))
        row.set('ht', str(min(408, 16 * lines + 4)))
        row.set('customHeight', '1')
    for rule in sheet.iter(tag('dataValidation')):
        if rule.get('sqref', '').startswith('W2:'):
            # The export can show multiple evidence states in a single row.
            validations = sheet.find(tag('dataValidations'))
            validations.remove(rule)
            validations.set('count', str(len(validations)))
            break
        if rule.get('sqref') == 'U2:U101':
            rule.set('sqref', f'U2:U{max(101, len(rows) + 1)}')
    return ET.tostring(sheet, encoding='utf-8', xml_declaration=True)


def generate_excel(project, final=False):
    rows = build_rows(project, final)
    output = io.BytesIO()
    money = ({13, 15}, {3, 5}, set(), set())
    with ZipFile(TEMPLATE) as template, ZipFile(output, 'w') as workbook:
        styles = ET.fromstring(template.read('xl/styles.xml'))
        fills = styles.find(tag('fills'))
        header = fills[2].find(tag('patternFill')).find(tag('fgColor'))
        header.attrib.clear()
        header.set('rgb', 'FF292725')
        formats = styles.find(tag('cellXfs'))
        wrap_style = len(formats)
        wrapped = deepcopy(formats[0])
        wrapped.set('applyAlignment', '1')
        ET.SubElement(wrapped, tag('alignment'), wrapText='1', vertical='top')
        formats.append(wrapped)
        formats.set('count', str(len(formats)))
        sheets = {f'xl/worksheets/sheet{i}.xml': (values, columns)
                  for i, (values, columns) in enumerate(zip(rows, money), 1)}
        for member in template.infolist():
            content = template.read(member)
            if member.filename in sheets:
                content = fill_sheet(content, *sheets[member.filename], wrap_style,
                                     qa_sheet=member.filename == 'xl/worksheets/sheet3.xml')
            elif member.filename == 'xl/styles.xml':
                content = ET.tostring(styles, encoding='utf-8', xml_declaration=True)
            workbook.writestr(member, content)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('records', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--final', action='store_true', help='Require recorded project approval')
    args = parser.parse_args()
    try:
        if args.output.suffix.lower() != '.xlsx':
            raise ValueError('Output filename must end in .xlsx.')
        project = json.loads(args.records.read_text(encoding='utf-8-sig'))
        workbook = generate_excel(project, args.final)
        with args.output.open('xb') as stream:
            stream.write(workbook)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        parser.exit(1, f'Excel export failed: {error}\n')


if __name__ == '__main__':
    main()
