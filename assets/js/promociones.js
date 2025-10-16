// assets/js/promociones.js
// Adaptado a tu catalogo.json real (datos dentro de variantes[0])

let allProducts = [];
let promoProducts = [];

/* ----------  helpers  ---------- */
function escapeHtml(text) {
  if (text == null) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/* ----------  cargar datos  ---------- */
async function loadPromociones() {
  const loader = document.getElementById('loader');
  loader.style.display = 'block';

  const [catalogo, promos] = await Promise.all([
    fetch('data/catalogo.json').then(r => r.json()),
    fetch('data/promos.json').then(r => r.json())
  ]);

  allProducts = catalogo;
  promoProducts = [];

  promos.forEach(promo => {
    const p = catalogo.find(prod => prod.codigo === promo.codigo);
    if (!p) return;

    // Usamos los datos de la primera variante si no existen a nivel producto
    const v = p.variantes?.[0] || {};
    const productoNormalizado = {
      ...p,
      nombre: p.nombre || v.Modalidad || `Código ${p.codigo}`,
      descripcion: p.descripcion || `Código ${p.codigo}`,
      imagen: p.imagen || 'no-imagen.jpeg',
      precio: parseFloat(v.Precio) || 0
    };

    promoProducts.push({
      ...productoNormalizado,
      precioOferta: promo.precioOferta,
      tipo: promo.tipo,
      _index: allProducts.indexOf(p)
    });
  });

  loader.style.display = 'none';
  renderPromos(promoProducts);
}

/* ----------  render  ---------- */
function renderPromos(products) {
  const container = document.getElementById('promos-container');
  container.innerHTML = '';

  if (!products.length) {
    container.innerHTML = '<p class="text-center text-muted">No hay promociones activas</p>';
    return;
  }

  const frag = document.createDocumentFragment();

  products.forEach(prod => {
    const title = ` ${prod.codigo}`;
    const desc = prod.descripcion || 'Sin descripción';
    let image = prod.imagen || 'no-imagen.jpeg';
    if (image && !/^(https?:)?\/\//i.test(image) && !image.includes('/')) image = 'img/' + image;

    const descHtml = desc.substring(0, 120) + (desc.length > 120 ? '...' : '');

    const col = document.createElement('div');
    col.className = 'col-12 col-md-6 col-lg-4 product-card';

    col.innerHTML = `
      <article class="card card-magazine shadow-sm h-100">
        <div class="img-wrap" style="height:220px;display:flex;align-items:center;justify-content:center;overflow:hidden; position:relative;">
  <span class="badge-oferta">
  <i class="bi bi-fire"></i> OFERTA
</span>
  <img src="${escapeHtml(image)}" alt="${escapeHtml(title)}" class="modal-img-hero">
</div>
        <div class="card-body d-flex flex-column">
          <h6 class="fw-bold">${escapeHtml(title)}</h6>
          <p class="card-text flex-grow-1">${escapeHtml(descHtml)}</p>
          <div class="precio-oferta-box">
  <span class="precio-oferta">S/${Number(prod.precioOferta).toFixed(2)}</span>
  <small class="tipo-oferta">por ${prod.tipo}</small>
</div>
          <button class="btn btn-outline-primary w-100 btn-detail" data-index="${prod._index}">Ver detalle</button>
        </div>
      </article>
    `;
    frag.appendChild(col);
  });

  container.appendChild(frag);
}

/* ----------  modal (copia de main.js)  ---------- */
function showModalByIndex(index) {
  const product = allProducts[index];
  if (!product) return;

  const modalTitle = document.getElementById('modalTitle');
  const modalDesc  = document.getElementById('modalDesc');
  const modalImage = document.getElementById('modalImage');
  const variantsEl = document.getElementById('variants');

  const v = product.variantes?.[0] || {};
  modalTitle.textContent = product.nombre || v.Modalidad || `Código ${product.codigo}`;
  modalDesc.textContent  = product.descripcion || `Código ${product.codigo}`;

  let img = product.imagen || 'no-imagen.jpeg';
  if (img && !/^(https?:)?\/\//i.test(img) && !img.includes('/')) img = 'img/' + img;
  modalImage.src = img;

  modalImage.style.cssText = `
    width:100%;height:clamp(200px,40vw,400px);object-fit:contain;
    border-radius:12px;background:var(--color-claro);padding:clamp(10px,2vw,20px);
  `;

  /* variantes */
  variantsEl.innerHTML = '';
  if (Array.isArray(product.variantes) && product.variantes.length) {
    const grid = document.createElement('div');
    grid.className = 'row g-3 mt-3';
    product.variantes.forEach(v => {
      const col  = document.createElement('div');
      col.className = 'col-12 col-md-6';
      const card = document.createElement('div');
      card.className = 'card border-light shadow-sm h-100';
      const body = document.createElement('div');
      body.className = 'card-body p-3';
      body.innerHTML = Object.entries(v || {})
        .map(([k, val]) => `
          <div class="d-flex justify-content-between align-items-center mb-2">
            <small class="text-muted">${escapeHtml(k)}:</small>
            <span class="fw-semibold">${escapeHtml(String(val))}</span>
          </div>`).join('');
      card.appendChild(body);
      col.appendChild(card);
      grid.appendChild(col);
    });
    variantsEl.appendChild(grid);
  } else {
    variantsEl.innerHTML = '<em class="text-muted">No hay variantes registradas</em>';
  }

  /* botón WhatsApp */
  const texto = `Quiero ésta promo: ${modalTitle.textContent} - ${modalDesc.textContent}`;
  const btnWhats = document.getElementById('btnWhatsApp');
  btnWhats.href = `https://wa.me/51922390279?text=${encodeURIComponent(texto)}`;
  btnWhats.className = 'btn btn-success w-100 mt-3';
  btnWhats.innerHTML = '<i class="bi bi-whatsapp me-2"></i>¡Solicita tu OFERTA aquí!';

  const modal = new bootstrap.Modal(document.getElementById('productModal'));
  modal.show();
}

/* ----------  clicks  ---------- */
document.addEventListener('click', (e) => {
  const btn = e.target.closest('.btn-detail');
  if (btn) {
    const idx = Number(btn.dataset.index);
    if (!isNaN(idx)) showModalByIndex(idx);
  }
});

/* ----------  init  ---------- */
document.addEventListener('DOMContentLoaded', loadPromociones);