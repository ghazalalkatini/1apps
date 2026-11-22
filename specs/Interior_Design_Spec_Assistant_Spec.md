# Interior Design Spec Assistant — Spec

## D1 — Dream

**Pain Point:** Interior designers and small design studios spend time manually collecting furniture, lighting, and material specifications from disparate sources, and risk missing or unsupported details. Homeowners also need simplified product lists.

**Objective:** Build a reusable AI-powered specification skill that produces traceable, reviewable schedules and shopping summaries. Focus initial sales on B2B design studios while supporting B2C homeowners. Start with paid services, then package the skill as a digital product, and later add AI-agent workflows.

**User Stories:**
- As an interior designer, I want to submit product links and manufacturer files so that I receive a structured specification schedule for review.
- As a studio owner, I want missing or conflicting product details clearly flagged so that my team can verify them before procurement.
- As a homeowner, I want a readable shopping list with known costs and missing-price warnings so that I can plan purchases.
- As the business owner, I want reusable templates and repeatable quality checks so that I can deliver a consistent paid service.

## D2 — Design

**Confirmed:** Guided Assistant delivered first inside ChatGPT; six conversational stages; B2B-first sales with B2C support; web application deferred.

**Status:** D2 confirmed by user on 2026-11-20: six stages, feature mapping, flows and Ghazal.interior warm visual direction.

### Pages & Screens

These are **conversation stages**, not actual web pages in the first release. Future web UI can map each stage to a page or stepper.

#### 01 — Project Setup
- [MVP] Collect project name, B2B/B2C audience, room(s), currency, desired schedule types; ask only for missing essentials.
- [MVP] Apply B2B detailed-output or B2C simplified-output defaults, with ability to override.
- [Later] Accounts, saved projects, client profiles, shared team workspace.

#### 02 — Product Input
- [MVP] Accept product URLs, uploaded photos, PDFs and manual text; support multiple items per project.
- [MVP] Assign a stable item ID, room, category, quantity and source reference to each item.
- [Later] CSV import, reusable product library, supplier integrations, bulk ingestion.

#### 03 — AI Specification Extraction
- [MVP] Extract only evidenced product name, brand/manufacturer, SKU, dimensions and units, material, finish, color, unit price, currency and source.
- [MVP] Preserve original units and note conversions; mark unsupported fields Not Verified; never invent values.
- [MVP] Keep source links/file references per product and distinguish supplied facts from inferred categorization.
- [Later] Supplier comparisons, monitored price updates, large-scale batch extraction.

#### 04 — Review & Validation
- [MVP] Flag missing values, conflicting sources, unclear product variants, stale or inaccessible links and mismatched units.
- [MVP] Display editable review table; request approval before final export; retain unknowns visibly.
- [MVP] Require manual confirmation for purchasing-critical dimensions, prices and quantities.
- [Later] Multi-reviewer approval, audit log, version history.

#### 05 — Specification Schedule
- [MVP] Produce furniture, lighting and material schedules as applicable, or B2C shopping list.
- [MVP] Compute line totals only where unit price and quantity are both known; display known subtotal and unknown-cost items separately.
- [MVP] Include item ID, room, source, validation status and notes.
- [Later] Budget alternatives, procurement comparisons, supplier substitution, advanced takeoffs.

#### 06 — Export & Delivery
- [MVP] Export formatted Excel workbook and a concise validation/exception summary; verify file creation before sharing.
- [MVP] Allow revisions to selected products/quantities without silently changing approved fields; regenerate calculations and exports.
- [Later] Branded PDF, automated delivery, client portal and payment integration.

### User Flows

**A — New project:** User requests schedule → Assistant gathers missing setup details → User supplies items → Extraction with source attribution → Validation → User reviews/approves → Schedule generation → Excel export.

**B — Missing/conflicting information:** Extraction flags missing/conflicting field → Assistant presents source evidence and specific question → User corrects or retains Not Verified → Review status updated → Export may proceed with conspicuous warnings; purchasing-critical facts remain unapproved until verified.

**C — Revision after export:** User names item ID and field to change → Assistant shows change and recalculated totals → User confirms → Revised workbook exported with version label.

**D — B2B/B2C branch:** Setup selects audience → Same underlying verified product records → B2B detailed technical schedules or B2C simplified shopping list → User may request alternate view without re-entering products.

**E — Unavailable source:** URL/PDF cannot be read → Assistant reports access limitation, requests file/text or manual input → Never claims a field was verified from an unreadable source.

### Visual Design

**Approved direction:** Ghazal.interior warm, minimal, professional visual identity. Palette: warm ivory `#F7F3ED`, sand `#D8C6B4`, muted terracotta `#A87560`, warm gray `#746F67`, charcoal `#292725`. Use clear readable typography, generous whitespace, compact tables, and visible status text plus icons (never color alone). ChatGPT MVP uses conversation stages and document templates, not custom screens. Future web UI may use a six-step progress indicator, project navigation, product grid, and source/validation panel. Typography specifics remain an implementation choice, not an approved font.

## D3 — Develop

**Status:** Portable SKILL.md execution target confirmed by user on 2026-11-20. D3 architecture recorded; Sprint 1 implemented and tested. Remaining sprints not yet implemented.

**Database / Data Model:** No hosted database for ChatGPT MVP. Each project has project_id, project_name, audience (B2B/B2C), currency, rooms, revision and approval state. Each product has stable item_id, room, category, product name, brand, SKU, dimensions and original units, material, finish, quantity, unit price/currency, supplier, source references, per-field evidence status, review notes and approval state. Source records include source type, URL or file reference, date accessed/provided, and exact supporting evidence. Unknown values remain null; do not confuse missing with zero. Keep a local structured intermediate file per project/export as needed; future web app can migrate to a relational database.

**Tools & Integrations:** ChatGPT skill instructions (`SKILL.md`), user-uploaded product images/PDFs, available browsing for accessible product URLs, and local spreadsheet export tools. No guaranteed live vendor API, stock feed, payments, email sending or automatic client outreach in MVP. Product links that cannot be accessed require user-provided evidence.

**Tech Stack:** Markdown-based skill with deterministic validation rules and a structured JSON/CSV intermediate representation; Excel template + generator script for XLSX; manual user approval before final export. ChatGPT is the conversational interface. Future web stack and authentication provider are deferred until demand is validated.

**Constraints & Security:** Do not fabricate product specs, pricing, certification or availability. Clearly distinguish source-verified, client-provided, missing and conflicting values. Human verification for purchasing-critical fields and code/electrical compliance. Do not share private client materials, send messages, purchase goods, or publish results without explicit permission. Avoid persistent storage promises within ChatGPT; export project data for continuity. Costs exclude taxes/shipping/installation unless evidenced.

**Agile Loop (proposed):** Sprint 1 — extraction schema and synthetic fixtures; Sprint 2 — XLSX export and QA; Sprint 3 — six-stage conversational prompts and approval/revision loop; Sprint 4 — B2B/B2C acceptance tests; Sprint 5 — one real-product pilot with human review. Each sprint ends with test evidence and a go/no-go decision.

**Effort Review:** Defer live supplier integrations, bulk crawling, accounts, payments, web UI, automated PDF design and agents. Human fallback: manually paste inaccessible product pages and verify critical measurements/prices. Experiments: test 10 varied products for extraction accuracy, source traceability, missing-field handling, and export correctness; compare time against manual preparation.

**Confirmed CTO decision:** Portable `SKILL.md` package first. A compatible agent runtime is required; ChatGPT interfaces do not universally support direct `.skill` installation.

### Sprint 1 implementation evidence
- `schemas/product.schema.json`: per-product JSON Schema with source-backed attributes and explicit evidence states.
- `scripts/validate_records.py`: deterministic source-reference, approval and subtotal checks; unknown prices never counted as zero.
- `tests/demo_records.json`: synthetic B2B demo with sofa, pendant, and wall tile.
- `tests/test_validator.py`: five automated tests, all passing on 2026-11-20.
- **Known subtotal:** CAD 1,610; total incomplete because tile unit price is missing.
- **Limit:** no real-world product extraction or workbook export was tested in Sprint 1.
- **Next:** Sprint 2 XLSX exporter and template integration, followed by actual agent-runtime extraction trials.

### Sprint 2 implementation — 2026-11-21

- `scripts/generate_excel.py` populates the original XLSX template from Sprint 1 project JSON. It includes a B2B schedule, B2C shopping list, QA and source log, and project brief branded Ghazal.design.
- Draft export supports review. Final export requires recorded project approval and keeps unresolved fields visible. Costs in a different currency are excluded from the project subtotal.
- Synthetic acceptance case: CAD 1,610 known subtotal, with the wall tile cost unresolved. The six-stage runtime and real-product extraction trials remain future sprint work.
- GitHub, Supabase, and Vercel are the selected web stack. Sprint 2 runs locally as part of the portable skill.
