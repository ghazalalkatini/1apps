# Interior Design Spec Assistant V1

Contents:
- `SKILL.md`: reusable AI instructions
- `templates/spec_schedule.xlsx`: B2B schedule + B2C shopping list + QA + brief
- `examples/demo_brief.md`: fictional test inputs
- `examples/demo_expected.md`: acceptance criteria

How to use: attach SKILL.md and the template to an AI workspace that supports file instructions. Provide real manufacturer links/PDFs and ask: 'Follow SKILL.md, fill the schedule, label evidence, and report missing details.' Review all outputs before client delivery.

Sales MVP: offer a paid pilot preparing a 10-item schedule for a design studio; share only fictional or permissioned samples. This bundle is an operational prototype, not a deployed autonomous agent.

## Sprint 2 — Excel Generator

Run with Python 3.10+ from the project root. The exporter uses the shipped template and Python standard library.

```powershell
python -B scripts/generate_excel.py tests/demo_records.json demo-spec-schedule.xlsx
```

Use a new output filename for each export. The workbook contains the B2B schedule, B2C shopping list, QA and source log, and project brief. The demo is a draft with a known subtotal of CAD 1,610. The tile has no known price. Costs in another currency remain on their own lines and are excluded from the project subtotal.

Run `python -B -m unittest discover -s tests` and validate product records against `schemas/product.schema.json` before exporting real data. The exporter also runs the Sprint 1 business-rule validator. After the user approves the reviewed schedule for delivery, record `"approval_state": "Approved"` on the project and use `--final`. Record item-level human signoff separately before marking an item Approved. For a revision, update the reviewed JSON, increment `revision`, obtain approval again for final delivery, and export to a new filename.

## Local web preview

```powershell
python -B scripts/serve_app.py
```

Open `http://127.0.0.1:8765/`. Load the fictional demo or enter product details manually. The six-stage workspace runs in the browser and uses the existing Python generator for draft and approved Excel downloads. Project edits are held in the open page. Automated extraction and hosted accounts are outside this preview.
