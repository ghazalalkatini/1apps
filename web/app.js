const steps = [
  ['Project setup', 'folder'], ['Product input', 'box'], ['Extraction', 'spark'],
  ['Review & validation', 'check'], ['Spec schedule', 'grid'], ['Excel export', 'download'],
];
const prefixes = { furniture: 'F', lighting: 'L', material: 'M' };
const project = { project_name: '', audience: 'B2B', currency: 'CAD', rooms: [], products: [], human_approval: {} };
const workflow = document.querySelector('#workflow');
const stage = document.querySelector('#stage');
const summary = document.querySelector('#summary');
const notice = document.querySelector('#notice');
let current = 0;
let editing = null;
let noticeTimer;

const icon = name => `<svg aria-hidden="true"><use href="#${name}"/></svg>`;
const safe = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
const money = (value, currency = project.currency) => new Intl.NumberFormat('en-CA', { style: 'currency', currency, currencyDisplay: 'code' }).format(value);
const supported = new Set(['VERIFIED', 'CLIENT-PROVIDED']);
const price = item => {
  const entry = item.attributes.unit_price;
  return supported.has(entry?.evidence) && typeof entry.value === 'number' && entry.value >= 0 ? entry.value : null;
};
const total = item => price(item) !== null && item.quantity > 0 ? price(item) * item.quantity : null;
const title = text => text.replaceAll('_', ' ').replace(/^./, char => char.toUpperCase());
const selected = (value, expected) => value === expected ? ' selected' : '';
const checked = (value, expected) => value === expected ? ' checked' : '';
const field = (label, name, value = '', options = '') => `<label class="field">${label}<input name="${name}" value="${safe(value)}" ${options}></label>`;

function flash(message) {
  notice.textContent = message;
  notice.hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => { notice.hidden = true; }, 5000);
}

function renderSummary() {
  const priced = project.products.filter(item => total(item) !== null && item.currency === project.currency);
  const subtotal = priced.reduce((sum, item) => sum + total(item), 0);
  const excluded = project.products.length - priced.length;
  summary.innerHTML = `<dl>
    <div><dt>Project</dt><dd>${safe(project.project_name || 'Untitled project')}</dd></div>
    <div><dt>Audience</dt><dd>${project.audience === 'B2B' ? 'Design studio' : 'Homeowner'}</dd></div>
    <div><dt>Currency</dt><dd>${safe(project.currency)}</dd></div>
    <div><dt>Products</dt><dd>${project.products.length}</dd></div>
  </dl><div class="summary-total"><span>Known subtotal</span><strong>${priced.length ? money(subtotal) : '—'}</strong></div>
  ${excluded ? `<span class="chip warning">${excluded} ${excluded === 1 ? 'item' : 'items'} excluded from subtotal</span>` : ''}`;
}

function setup() {
  return `<form id="setup-form" class="form-grid">
    ${field('Project name', 'project_name', project.project_name, 'placeholder="e.g. West End residence" required maxlength="160"')}
    ${field('Room or scope', 'rooms', project.rooms.join(', '), 'placeholder="e.g. Living room" maxlength="240"')}
    <fieldset><legend>Audience</legend><div class="choices">
      <label class="choice"><input type="radio" name="audience" value="B2B"${checked(project.audience, 'B2B')}><span>Design studio · B2B</span></label>
      <label class="choice"><input type="radio" name="audience" value="B2C"${checked(project.audience, 'B2C')}><span>Homeowner · B2C</span></label>
    </div></fieldset>
    ${field('Project currency', 'currency', project.currency, 'pattern="[A-Z]{3}" required maxlength="3" title="Three uppercase letters, such as CAD"')}
  </form>`;
}

function productInput() {
  const item = project.products.find(product => product.item_id === editing);
  return `<ul class="item-list">${project.products.map(product => `<li class="item"><div class="item-head"><div>
    <h3>${safe(product.product_name)}</h3><p><code>${safe(product.item_id)}</code> · ${safe(product.room)} · ${title(product.category)}</p></div>
    <button class="button outline" data-edit="${safe(product.item_id)}">Edit</button></div></li>`).join('')}</ul>
    <form id="product-form" class="form-grid">
      ${field('Product name', 'name', item?.product_name, 'placeholder="e.g. Cloudline sofa" required maxlength="160"')}
      <label class="field">Category<select name="category">${Object.keys(prefixes).map(category => `<option value="${category}"${selected(item?.category, category)}>${title(category)}</option>`).join('')}</select></label>
      ${field('Room', 'room', item?.room ?? project.rooms[0], 'required maxlength="120"')}
      ${field('Source link or reference', 'source', item?.sources[0]?.reference, 'placeholder="Product URL or document reference" maxlength="1000"')}
      ${field('Quantity', 'quantity', item?.quantity ?? (item ? '' : 1), 'type="number" min="0" step="any"')}
      ${field('Unit price', 'price', item?.attributes.unit_price?.value, 'type="number" min="0" step="any" placeholder="Leave blank if unknown"')}
      <div class="choices field full"><button class="button outline" type="submit">${icon(item ? 'check' : 'plus')}${item ? 'Save product' : 'Add product'}</button>
      ${item ? `<button class="button danger" type="button" data-remove="${safe(item.item_id)}">Remove product</button><button class="button" type="button" id="cancel-edit">Cancel</button>` : ''}</div>
    </form>`;
}

function review(extraction = false) {
  if (!project.products.length) return '<p>Add a product to begin reviewing its details.</p>';
  return `<ul class="item-list">${project.products.map(item => {
    const details = Object.entries(item.attributes);
    const issues = details.filter(([, entry]) => !supported.has(entry.evidence)).map(([name, entry]) => `${title(name)} · ${title(entry.evidence.toLowerCase())}`);
    if (!item.sources.length) issues.push('Source reference missing');
    if (!(item.quantity > 0)) issues.push('Quantity needs confirmation');
    if (price(item) === null && !issues.some(issue => issue.startsWith('Unit price'))) issues.push('Unit price needs confirmation');
    if (item.currency !== project.currency) issues.push(`Price is in ${item.currency} and excluded from the ${project.currency} subtotal`);
    return `<li class="item"><div class="item-head"><div><h3>${safe(item.product_name)}</h3><code>${safe(item.item_id)}</code></div>
      <span class="chip${issues.length ? ' warning' : ''}">${issues.length ? 'Needs verification' : 'Ready for review'}</span></div>
      ${extraction ? details.map(([name, entry]) => `<p><strong>${safe(title(name))}</strong> · ${safe(entry.value ?? 'Not verified')} · ${safe(entry.evidence)}</p>`).join('') : issues.map(issue => `<p>${safe(issue)}</p>`).join('')}
      ${item.sources.map(source => `<p>Source · ${safe(source.reference)}</p>`).join('')}</li>`;
  }).join('')}</ul>`;
}

function schedule() {
  if (!project.products.length) return '<p>Product rows will appear here as you add them.</p>';
  const studio = project.audience === 'B2B';
  return `<div class="table-scroll" tabindex="0" aria-label="Product schedule"><table><thead><tr>${studio ? '<th>ID</th>' : ''}<th>Product</th><th>Room</th><th>Qty</th><th>Line total</th></tr></thead><tbody>
    ${project.products.map(item => `<tr>${studio ? `<td>${safe(item.item_id)}</td>` : ''}<td>${safe(item.product_name)}</td><td>${safe(item.room)}</td><td>${safe(item.quantity ?? '—')}</td><td>${total(item) === null ? 'Not verified' : money(total(item), item.currency)}</td></tr>`).join('')}</tbody></table></div>`;
}

function exportControls() {
  return `<div class="stack"><p>The workbook includes the B2B schedule, B2C shopping list, QA and source log, and project brief.</p>
    <label class="check-label"><input type="checkbox" id="approval">I’ve reviewed this schedule and approve it for final delivery.</label></div>`;
}

const descriptions = [
  'Set the project scope and choose who the specification is for.',
  'Add products and record the details supplied for each one.',
  'Inspect the structured details from manual entry or the demo fixture.',
  'Check source references, missing details and costs before delivery.',
  'Preview the product rows and known costs for your selected audience.',
  'Download a draft for review or approve the schedule to download a final workbook.',
];
const screens = [setup, productInput, () => review(true), review, schedule, exportControls];

function render(focus = false) {
  workflow.innerHTML = steps.map(([label, glyph], index) => `<button type="button" class="step" data-step="${index}"${index === current ? ' aria-current="step"' : ''}><span class="step-icon">${icon(glyph)}</span>${label}</button>`).join('');
  stage.innerHTML = `<h2 id="stage-heading" tabindex="-1">${steps[current][0]}</h2><p class="intro">${descriptions[current]}</p>${screens[current]()}
    <div class="actions">${current ? '<button type="button" class="button" id="back">Back</button>' : '<span></span>'}
    ${current < 5 ? `<button type="button" class="button primary" id="next">${current === 0 ? 'Continue to products' : 'Continue'}</button>` :
      `<div class="choices"><button class="button outline" data-export="draft"${project.products.length ? '' : ' disabled'}>Download draft</button><button class="button primary" data-export="final" disabled>${icon('download')}Download final</button></div>`}</div>`;
  renderSummary();
  if (focus) stage.querySelector('h2').focus({ preventScroll: true });
}

function navigate(index) {
  current = index;
  render(true);
}

function updateSetup(form) {
  const data = Object.fromEntries(new FormData(form));
  project.project_name = data.project_name.trim();
  project.audience = data.audience;
  project.rooms = data.rooms.split(',').map(room => room.trim()).filter(Boolean);
  if (/^[A-Z]{3}$/.test(data.currency)) project.currency = data.currency;
  renderSummary();
}

function nextId(category) {
  const prefix = prefixes[category];
  const used = project.products.filter(item => item.category === category).map(item => Number(item.item_id.slice(2)));
  return `${prefix}-${String(Math.max(0, ...used) + 1).padStart(3, '0')}`;
}

function saveProduct(form) {
  const data = Object.fromEntries(new FormData(form));
  const existing = project.products.find(item => item.item_id === editing);
  if (!data.name.trim() || !data.room.trim()) return flash('Enter a product name and room.');
  if (data.quantity && Number(data.quantity) <= 0) return flash('Quantity must be greater than zero.');
  const source = data.source.trim();
  const unitPrice = data.price === '' ? null : Number(data.price);
  if (unitPrice !== null && !source) return flash('Add a source reference for the unit price.');
  const sources = [...(existing?.sources ?? [])];
  let priceSource = sources.find(entry => entry.reference === source);
  if (source && !priceSource) {
    let index = 1;
    while (sources.some(entry => entry.source_id === `manual-${index}`)) index += 1;
    priceSource = { source_id: `manual-${index}`, type: /^https?:\/\//i.test(source) ? 'url' : 'client_text', reference: source, accessed_on: null };
    sources.unshift(priceSource);
  }
  const attributes = { ...existing?.attributes };
  if (unitPrice !== existing?.attributes.unit_price?.value) {
    attributes.unit_price = unitPrice === null ? { value: null, evidence: 'MISSING', source_ids: [] } :
      { value: unitPrice, evidence: 'CLIENT-PROVIDED', source_ids: [priceSource.source_id] };
  }
  const item = {
    item_id: existing?.category === data.category ? existing.item_id : nextId(data.category),
    category: data.category, room: data.room.trim(), product_name: data.name.trim(),
    quantity: data.quantity === '' ? null : Number(data.quantity), currency: existing?.currency ?? project.currency,
    attributes, sources, approval_status: 'Needs Verification', notes: existing?.notes ?? [],
  };
  if (existing) {
    project.products[project.products.indexOf(existing)] = item;
    delete project.human_approval[existing.item_id];
  } else project.products.push(item);
  editing = null;
  render();
  flash(existing ? 'Product updated.' : 'Product added.');
}

async function download(button) {
  if (!project.project_name) return flash('Enter a project name in Project setup.');
  const final = button.dataset.export === 'final';
  const approval = stage.querySelector('#approval');
  if (final && !approval.checked) return;
  button.disabled = true;
  try {
    const response = await fetch('/api/export', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ project: { ...project, approval_state: final ? 'Approved' : 'Draft' }, final }) });
    if (!response.ok) throw new Error((await response.json()).error);
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement('a');
    link.href = url;
    link.download = `spec-schedule-${final ? 'final' : 'draft'}.xlsx`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    flash('Workbook downloaded.');
  } catch (error) {
    flash(error.message || 'Excel export failed.');
  } finally {
    button.disabled = final && !approval.checked;
  }
}

workflow.addEventListener('click', event => {
  const step = event.target.closest('[data-step]');
  if (step) navigate(Number(step.dataset.step));
});
stage.addEventListener('input', event => {
  if (event.target.form?.id === 'setup-form') updateSetup(event.target.form);
  if (event.target.id === 'approval') stage.querySelector('[data-export="final"]').disabled = !event.target.checked || !project.products.length;
});
stage.addEventListener('submit', event => {
  event.preventDefault();
  if (event.target.id === 'product-form') saveProduct(event.target);
  if (event.target.id === 'setup-form') stage.querySelector('#next').click();
});
stage.addEventListener('click', event => {
  const button = event.target.closest('button');
  if (!button) return;
  if (button.id === 'next') {
    if (current === 0 && (!stage.querySelector('form').reportValidity() || !project.project_name)) return;
    navigate(current + 1);
  }
  if (button.id === 'back') navigate(current - 1);
  if (button.dataset.edit || button.id === 'cancel-edit') {
    editing = button.dataset.edit ?? null;
    render();
    stage.querySelector('#product-form input').focus();
  }
  if (button.dataset.remove && window.confirm('Remove this product from the schedule?')) {
    project.products = project.products.filter(item => item.item_id !== button.dataset.remove);
    delete project.human_approval[button.dataset.remove];
    editing = null;
    render();
  }
  if (button.dataset.export) download(button);
});
document.querySelector('#load-demo').addEventListener('click', async () => {
  if ((project.project_name || project.products.length) && !window.confirm('Replace the current browser workspace with the fictional demo?')) return;
  try {
    const response = await fetch('/api/demo');
    if (!response.ok) throw new Error('The demo could not load.');
    const demo = await response.json();
    Object.assign(project, demo, { rooms: [...new Set(demo.products.map(item => item.room))] });
    editing = null;
    navigate(0);
    flash('Fictional demo loaded.');
  } catch (error) {
    flash(error.message);
  }
});

render();
