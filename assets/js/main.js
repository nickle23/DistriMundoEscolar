// assets/js/main.js
// Catálogo con buscador + modal + paginación profesional

let allProducts = [];
let filteredProducts = [];
let currentPage = 1;
const itemsPerPage = 12;

// ---------- FUNCIONES AUXILIARES ----------
function normalizar(texto) {
  return texto
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function escapeHtml(text) {
  if (text == null) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function resaltarCoincidencias(texto, query) {
  if (!query) return texto;
  const palabras = normalizar(query).split(/\s+/).filter(p => p.length > 2);
  let resultado = texto;
  palabras.forEach(p => {
    const regex = new RegExp(`(${p})`, 'gi');
    resultado = resultado.replace(regex, '<mark class="resaltado">$1</mark>');
  });
  return resultado;
}

// ---------- CARGAR CATÁLOGO ----------
async function loadCatalog() {
  document.getElementById('loader').style.display = 'none';
  const tryPaths = [
    "/data/catalogo.json",
    "/data/products.json", 
    "/assets/data/products.json"
];
  let data = null;

  for (const path of tryPaths) {
    try {
      const res = await fetch(path);
      if (!res.ok) continue;
      data = await res.json();
      console.log('Catálogo cargado desde', path, '->', Array.isArray(data) ? data.length : '?', 'items');
      break;
    } catch (err) {
      console.warn('Error fetch', path, err);
    }
  }

  if (!data || !Array.isArray(data)) {
    document.getElementById('magazine').innerHTML =
      '<p class="text-danger">No se pudo cargar el catálogo. Ejecuta convert_excel.py y asegúrate de abrir con Live Server.</p>';
    return;
  }

  allProducts = data.map((p, idx) => {
    const prod = { ...p };
    const name = (prod.nombre || prod.Nombre || '') + '';
    const desc = (prod.descripcion || prod.Descripcion || '') + '';
    const code = (prod.codigo || prod.Codigo || '') + '';

    let variantesText = '';
    if (Array.isArray(prod.variantes)) {
      variantesText = prod.variantes.map(v => {
        try { return Object.values(v || {}).join(' '); } catch { return ''; }
      }).join(' ');
    }

    prod._searchText = (name + ' ' + desc + ' ' + code + ' ' + variantesText).toLowerCase();
    prod._index = idx;
    return prod;
  });

  filteredProducts = allProducts;
  renderProducts(filteredProducts, currentPage);
  renderPagination(filteredProducts);
}

// ---------- RENDER PRODUCTOS ----------
function renderProducts(products, page = 1) {
  const container = document.getElementById('magazine');
  container.innerHTML = '';

  if (!products || products.length === 0) {
    container.innerHTML = '<p class="text-center text-muted">No se encontraron productos</p>';
    return;
  }

  const start = (page - 1) * itemsPerPage;
  const end = start + itemsPerPage;
  const pageItems = products.slice(start, end);
  const frag = document.createDocumentFragment();

  pageItems.forEach(prod => {
    const title = prod.nombre || prod.Nombre || prod.codigo || `Producto ${prod._index + 1}`;
    const desc = prod.descripcion || prod.Descripcion || 'Sin descripción';
    let image = prod.imagen || prod.Imagen || '';
    if (image && !/^(https?:)?\/\//i.test(image) && !image.includes('/')) image = 'img/catalogo/' + image;
    if (!image) image = 'https://via.placeholder.com/600x400?text=Producto';

    const descHtml = escapeHtml(desc.substring(0, 120)) + (desc.length > 120 ? '...' : '');
    const textoResaltado = resaltarCoincidencias(descHtml, document.getElementById('searchInput')?.value || '');

    const col = document.createElement('div');
    col.className = 'col-12 col-md-6 col-lg-4 product-card';
    col.setAttribute('data-index', prod._index);

    col.innerHTML = `
      <article class="card card-magazine shadow-sm h-100">
        <div class="img-wrap" style="height:220px; display:flex; align-items:center; justify-content:center; overflow:hidden">
          <img src="${escapeHtml(image)}" alt="${escapeHtml(title)}" class="modal-img-hero">
        </div>
        <div class="card-body d-flex flex-column">
          <p class="card-text mb-3">${textoResaltado}</p>
          <div class="mt-auto">
            <button class="btn btn-outline-primary w-100 btn-detail" data-index="${prod._index}">Ver detalle</button>
          </div>
        </div>
      </article>
    `;

    frag.appendChild(col);
  });

  container.appendChild(frag);
}

// ---------- MODAL ----------
function showModalByIndex(index) {
  const product = allProducts[index];
  if (!product) return;

  const modalTitle = document.getElementById('modalTitle');
  const modalDesc = document.getElementById('modalDesc');
  const modalImage = document.getElementById('modalImage');
  const variantsEl = document.getElementById('variants');

  modalTitle.textContent = product.nombre || product.Nombre || product.codigo || 'Producto';
  modalDesc.textContent = product.descripcion || '';

  let img = product.imagen || product.Imagen || '';
  if (img && !/^(https?:)?\/\//i.test(img) && !img.includes('/')) img = 'img/catalogo/' + img;
  modalImage.src = img || 'https://via.placeholder.com/600x400?text=Producto';

  modalImage.style.cssText = `
    width: 100%;
    height: clamp(200px, 40vw, 400px);
    object-fit: contain;
    border-radius: 12px;
    background: var(--color-claro);
    padding: clamp(10px, 2vw, 20px);
  `;

  variantsEl.innerHTML = '';
  if (Array.isArray(product.variantes) && product.variantes.length > 0) {
    const grid = document.createElement('div');
    grid.className = 'row g-3 mt-3';

    product.variantes.forEach(v => {
      const col = document.createElement('div');
      col.className = 'col-12 col-md-6';

      const card = document.createElement('div');
      card.className = 'card border-light shadow-sm h-100';

      const cardBody = document.createElement('div');
      cardBody.className = 'card-body p-3';

      const lines = [];
      for (const [k, val] of Object.entries(v || {})) {
        lines.push(`<div class="d-flex justify-content-between align-items-center mb-2">
                      <small class="text-muted">${escapeHtml(k)}:</small>
                      <span class="fw-semibold">${escapeHtml(String(val))}</span>
                    </div>`);
      }

      cardBody.innerHTML = lines.join('');
      card.appendChild(cardBody);
      col.appendChild(card);
      grid.appendChild(col);
    });

    variantsEl.appendChild(grid);
  } else {
    variantsEl.innerHTML = '<em class="text-muted">No hay variantes registradas</em>';
  }

  const texto = `Hola, quiero éste producto: ${modalTitle.textContent} - ${modalDesc.textContent}`;
  const urlWhatsApp = `https://wa.me/51922390279?text=${encodeURIComponent(texto)}`;
  const btnWhatsApp = document.getElementById('btnWhatsApp');
  btnWhatsApp.href = urlWhatsApp;
  btnWhatsApp.className = 'btn btn-success w-100 mt-3';
  btnWhatsApp.innerHTML = '<i class="bi bi-whatsapp me-2"></i>Pídelo por WhatsApp';

  const modal = new bootstrap.Modal(document.getElementById('productModal'));
  modal.show();
}

// ---------- EVENTOS ----------
document.addEventListener('click', (e) => {
  const btn = e.target.closest('.btn-detail');
  if (btn) {
    const idx = Number(btn.getAttribute('data-index'));
    if (!isNaN(idx)) showModalByIndex(idx);
  }
});

// ---------- BÚSQUEDA ----------
let fuse;
function setupSearch() {
  const input = document.getElementById('searchInput');
  if (!input) return;

  fuse = new Fuse(allProducts, {
    keys: [
      { name: 'nombre', weight: 0.6 },
      { name: 'descripcion', weight: 0.3 },
      { name: 'codigo', weight: 0.1 }
    ],
    threshold: 0.6,
    minMatchCharLength: 3,
    findAllMatches: true,
    ignoreLocation: true,
    ignoreFieldNorm: true
  });

  input.addEventListener('input', () => {
    const q = input.value.trim();
    currentPage = 1;

    if (!q) {
      filteredProducts = allProducts;
    } else {
      const palabras = normalizar(q).split(/\s+/);
      filteredProducts = allProducts.filter(prod => {
        const texto = normalizar(prod._searchText || '');
        return palabras.every(p => texto.includes(p));
      });
    }

    renderProducts(filteredProducts, currentPage);
    renderPagination(filteredProducts);
  });
}

// ---------- PAGINACIÓN ----------
function renderPagination(products) {
  const totalPages = Math.ceil(products.length / itemsPerPage);
  const paginationContainer = document.getElementById('pagination');
  paginationContainer.innerHTML = '';

  if (totalPages <= 1) return;

  const ul = document.createElement('ul');
  ul.className = 'pagination justify-content-center';

  const prevLi = document.createElement('li');
  prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
  prevLi.innerHTML = `<a class="page-link" href="#">Anterior</a>`;
  prevLi.addEventListener('click', (e) => {
    e.preventDefault();
    if (currentPage > 1) {
      currentPage--;
      renderProducts(filteredProducts, currentPage);
      renderPagination(filteredProducts);
    }
  });
  ul.appendChild(prevLi);

  let maxVisible = 5;
  let start = Math.max(1, currentPage - 2);
  let end = Math.min(totalPages, start + maxVisible - 1);
  if (end - start < maxVisible - 1) start = Math.max(1, end - maxVisible + 1);

  if (start > 1) {
    addPageButton(ul, 1);
    if (start > 2) ul.appendChild(createEllipsis());
  }

  for (let i = start; i <= end; i++) addPageButton(ul, i);

  if (end < totalPages) {
    if (end < totalPages - 1) ul.appendChild(createEllipsis());
    addPageButton(ul, totalPages);
  }

  const nextLi = document.createElement('li');
  nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
  nextLi.innerHTML = `<a class="page-link" href="#">Siguiente</a>`;
  nextLi.addEventListener('click', (e) => {
    e.preventDefault();
    if (currentPage < totalPages) {
      currentPage++;
      renderProducts(filteredProducts, currentPage);
      renderPagination(filteredProducts);
    }
  });
  ul.appendChild(nextLi);

  paginationContainer.appendChild(ul);
}

function addPageButton(ul, page) {
  const li = document.createElement('li');
  li.className = `page-item ${page === currentPage ? 'active' : ''}`;
  li.innerHTML = `<a class="page-link" href="#">${page}</a>`;
  li.addEventListener('click', (e) => {
    e.preventDefault();
    currentPage = page;
    renderProducts(filteredProducts, currentPage);
    renderPagination(filteredProducts);
  });
  ul.appendChild(li);
}

function createEllipsis() {
  const li = document.createElement('li');
  li.className = 'page-item disabled';
  li.innerHTML = `<span class="page-link">...</span>`;
  return li;
}

// ---------- INICIALIZAR ----------
document.addEventListener('DOMContentLoaded', () => {
  loadCatalog().then(() => {
    setupSearch();
  }).catch(err => console.error('Error inicializando catálogo', err));
});