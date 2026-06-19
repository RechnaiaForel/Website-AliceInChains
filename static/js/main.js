/**
 * AliceInChains Shop — main.js
 *
 * Функции:
 *  - loadCatalog(params)   — загружает и рендерит страницу каталога из API
 *  - addToCartJS(id, qty)  — отправляет POST /api/cart/add/ и показывает Toast
 *  - showToast(msg, ok)    — Bootstrap Toast-уведомление
 */

'use strict';

/* =========================================================
   Утилита: Bootstrap Toast
   ========================================================= */
function showToast(message, success = true) {
  const toastEl = document.getElementById('cartToast');
  if (!toastEl) return;

  const toastBody = document.getElementById('cartToastBody');
  toastBody.textContent = message;

  // Красим фон по типу сообщения
  toastEl.classList.remove('bg-success', 'bg-danger', 'text-white');
  if (success) {
    toastEl.classList.add('bg-success', 'text-white');
  } else {
    toastEl.classList.add('bg-danger', 'text-white');
  }

  const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
  toast.show();
}

/* =========================================================
   Добавление товара в корзину через JS
   POST /api/cart/add/
   ========================================================= */
async function addToCartJS(productId, quantity = 1) {
  if (!window.USER_AUTHENTICATED) {
    // Гостю показываем ссылку на вход вместо ошибки
    showToast('Войдите в аккаунт, чтобы добавить товар в корзину.', false);
    return;
  }

  try {
    const resp = await fetch('/api/cart/add/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.CSRF_TOKEN,
      },
      body: JSON.stringify({ product_id: productId, quantity }),
    });

    const data = await resp.json();

    if (resp.ok) {
      showToast(data.detail || 'Товар добавлен в корзину.', true);
    } else if (resp.status === 400) {
      showToast(data.detail || 'Не удалось добавить товар.', false);
    } else if (resp.status === 401 || resp.status === 403) {
      showToast('Нет доступа. Пожалуйста, войдите в систему.', false);
    } else {
      showToast('Ошибка сервера. Попробуйте ещё раз.', false);
    }
  } catch {
    showToast('Нет соединения с сервером.', false);
  }
}

/* =========================================================
   Рендеринг одной карточки товара
   ========================================================= */
function renderProductCard(product) {
  const price = parseFloat(product.price).toFixed(2);
  const inStock = product.quantity_in_stock > 0;

  const badge = inStock
    ? `<span class="badge badge-in-stock text-white">В наличии: ${product.quantity_in_stock}</span>`
    : `<span class="badge badge-out-of-stock text-white">Нет в наличии</span>`;

  const photo = product.photo
    ? `<a href="/catalog/${product.id}/"><img src="${product.photo}" class="card-img-top" alt="${escHtml(product.name)}"></a>`
    : `<div class="d-flex align-items-center justify-content-center bg-light" style="height:180px;"><i class="bi bi-image text-muted fs-1"></i></div>`;

  const addBtn = inStock
    ? `<button class="btn btn-primary btn-sm w-100 mt-2"
          onclick="addToCartJS(${product.id}, 1)">
          <i class="bi bi-cart-plus me-1"></i>В корзину
       </button>`
    : `<button class="btn btn-secondary btn-sm w-100 mt-2" disabled>Нет в наличии</button>`;

  return `
    <div class="col-sm-6 col-md-4 col-lg-4">
      <div class="card product-card h-100">
        ${photo}
        <div class="card-body d-flex flex-column">
          <p class="small text-muted mb-1">${escHtml(product.category_name || '')}</p>
          <h6 class="card-title mb-1">
            <a href="/catalog/${product.id}/" class="text-decoration-none text-dark">
              ${escHtml(product.name)}
            </a>
          </h6>
          <p class="price mb-1">${price} руб.</p>
          ${badge}
          <div class="mt-auto">
            <a href="/catalog/${product.id}/" class="btn btn-outline-primary btn-sm w-100 mt-2">
              Подробнее
            </a>
            ${addBtn}
          </div>
        </div>
      </div>
    </div>`;
}

/* =========================================================
   Рендеринг пагинации
   ========================================================= */
function renderPagination(apiUrl, currentPage, totalCount, pageSize, onPageClick) {
  const totalPages = Math.ceil(totalCount / pageSize);
  if (totalPages <= 1) return '';

  let items = '';
  for (let p = 1; p <= totalPages; p++) {
    items += `
      <li class="page-item ${p === currentPage ? 'active' : ''}">
        <button class="page-link" data-page="${p}">${p}</button>
      </li>`;
  }

  return `<ul class="pagination justify-content-center">${items}</ul>`;
}

/* =========================================================
   Загрузка каталога из /api/products/
   ========================================================= */
async function loadCatalog(filterParams, page = 1) {
  const grid       = document.getElementById('productGrid');
  const loading    = document.getElementById('catalog-loading');
  const errorBox   = document.getElementById('catalog-error');
  const noProducts = document.getElementById('noProducts');
  const paginNav   = document.getElementById('paginationNav');

  if (!grid) return;   // Не страница каталога — ничего не делаем

  // Показываем спиннер, скрываем остальное
  loading.classList.remove('d-none');
  loading.style.display = '';
  grid.style.setProperty('display', 'none', 'important');
  paginNav.style.display = 'none';
  errorBox.classList.add('d-none');
  noProducts.classList.add('d-none');

  try {
    // Строим query-строку: фильтры + страница
    const params = new URLSearchParams(filterParams);
    params.set('page', page);

    const resp = await fetch(`/api/products/?${params.toString()}`);

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }

    const data = await resp.json();

    // DRF pagination wraps in {count, results}; если пагинации нет — массив
    const products   = data.results ?? data;
    const totalCount = data.count   ?? products.length;
    const PAGE_SIZE  = 9;

    loading.style.display = 'none';

    if (!products.length) {
      noProducts.classList.remove('d-none');
      return;
    }

    // Рендерим карточки
    grid.innerHTML = products.map(renderProductCard).join('');
    grid.style.removeProperty('display');

    // Рендерим пагинацию
    if (data.count) {
      paginNav.innerHTML = renderPagination('/api/products/', page, totalCount, PAGE_SIZE);
      paginNav.style.display = '';

      paginNav.querySelectorAll('.page-link').forEach(btn => {
        btn.addEventListener('click', () => {
          const p = parseInt(btn.dataset.page, 10);
          loadCatalog(filterParams, p);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        });
      });
    }

  } catch (err) {
    loading.style.display = 'none';
    errorBox.classList.remove('d-none');
    console.error('Ошибка загрузки каталога:', err);
  }
}

/* =========================================================
   Экранирование HTML (защита от XSS в JS-рендере)
   ========================================================= */
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/* =========================================================
   Привязка формы фильтров к JS-загрузке
   ========================================================= */
document.addEventListener('DOMContentLoaded', () => {
  const filterForm = document.getElementById('filterForm');
  if (!filterForm) return;

  filterForm.addEventListener('submit', e => {
    e.preventDefault();
    const params = new URLSearchParams(new FormData(filterForm));
    // Убираем пустые значения
    [...params.entries()]
      .filter(([, v]) => !v)
      .forEach(([k]) => params.delete(k));

    // Обновляем URL без перезагрузки страницы
    window.history.pushState({}, '', `?${params}`);
    loadCatalog(params, 1);
  });
});
