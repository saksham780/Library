/* ═══════════════════════════════════════════════════════
   Library Management System — Library Management Frontend
   All API interactions with Flask/SQLAlchemy backend
   ═══════════════════════════════════════════════════════ */

const API = '';  // same origin; set to https://library-management-l921.onrender.com/api/books ://localhost:5000 for dev

// ── Utils ────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const el = (tag, cls, html) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
};

async function apiFetch(path, opts = {}) {
  const defaults = { headers: { 'Content-Type': 'application/json' } };
  const res = await fetch(API + path, { ...defaults, ...opts });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw data;
  return data;
}

function toast(msg, type = 'info') {
  const tc = $('toastContainer');
  const t = el('div', `toast ${type}`,
    `<i class="fa-solid fa-${type === 'success' ? 'circle-check' : type === 'error' ? 'circle-xmark' : 'circle-info'}"></i>
     <span class="toast-msg">${msg}</span>`);
  tc.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateX(20px)'; t.style.transition = '.3s'; setTimeout(() => t.remove(), 300); }, 3200);
}

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function daysLeft(dueDateIso) {
  const due = new Date(dueDateIso);
  const now = new Date(); now.setHours(0,0,0,0);
  const diff = Math.round((due - now) / 86400000);
  if (diff < 0) return `<span style="color:#e05060">${Math.abs(diff)}d overdue</span>`;
  if (diff === 0) return `<span style="color:#d4a843">Due today</span>`;
  return `<span style="color:#4daa88">${diff}d left</span>`;
}

function statusBadge(status) {
  const map = {
    borrowed: 'badge-borrowed',
    returned: 'badge-returned',
    overdue:  'badge-overdue',
  };
  const icons = { borrowed: 'book-open', returned: 'check', overdue: 'triangle-exclamation' };
  return `<span class="badge ${map[status]||''}"><i class="fa-solid fa-${icons[status]||'circle'}"></i>${status}</span>`;
}

// ── Navigation ───────────────────────────────────────────
const pages = {
  dashboard:    $('pageDashboard'),
  books:        $('pageBooks'),
  members:      $('pageMembers'),
  transactions: $('pageTransactions'),
  issue:        $('pageIssue'),
};

const navItems = document.querySelectorAll('.nav-item');
let currentPage = 'dashboard';

function navigate(page) {
  currentPage = page;
  Object.values(pages).forEach(p => p.classList.remove('active'));
  navItems.forEach(n => n.classList.remove('active'));

  if (pages[page]) pages[page].classList.add('active');
  const nav = document.querySelector(`[data-page="${page}"]`);
  if (nav) nav.classList.add('active');

  $('topbarTitle').textContent = {
    dashboard: 'Dashboard',
    books: 'Book Catalogue',
    members: 'Members',
    transactions: 'Transactions',
    issue: 'Issue a Book',
  }[page] || '';

  // Update browser URL so back button works
  history.pushState({ page }, '', `#${page}`);

  // Load data for the page
  if (page === 'dashboard')    loadDashboard();
  else if (page === 'books')        loadBooks();
  else if (page === 'members')      loadMembers();
  else if (page === 'transactions') loadTransactions();
  else if (page === 'issue')        loadIssueForm();
}

// Navigate to transactions with a pre-set status filter
window.navigateWithTxFilter = function(status) {
  txStatus = status;
  txPage = 1;
  navigate('transactions');
  // Sync the filter buttons UI
  setTimeout(() => {
    document.querySelectorAll('.tx-filter-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.status === status);
    });
  }, 50);
};

// Navigate to books filtered by genre
window.navigateWithGenre = function(genre) {
  booksGenre = genre;
  booksPage = 1;
  navigate('books');
  setTimeout(() => {
    const sel = $('genreFilter');
    if (sel) sel.value = genre;
  }, 50);
};

navItems.forEach(n => {
  n.addEventListener('click', () => {
    const p = n.dataset.page;
    if (p) navigate(p);
    if (window.innerWidth <= 860) $('sidebar').classList.remove('open');
  });
});

$('hamburger').addEventListener('click', () => $('sidebar').classList.toggle('open'));

// ══════════════════════════════════════════════════════════
// DASHBOARD
// ══════════════════════════════════════════════════════════
async function loadDashboard() {
  try {
    const d = await apiFetch('/api/dashboard');
    const s = d.stats;

    $('statBooks').textContent   = s.total_books;
    $('statMembers').textContent = s.total_members;
    $('statBorrowed').textContent = s.borrowed;
    $('statOverdue').textContent = s.overdue;

    renderBarChart(d.chart);
    renderGenres(d.genres);
    renderRecentActivity(d.recent);
    renderCategoryGrid();
    loadTrending();

    // overdue badge in sidebar
    const badge = $('overdueBadge');
    if (badge) badge.textContent = s.overdue > 0 ? s.overdue : '';
  } catch (e) { console.error(e); }
}

function renderBarChart(chartData) {
  const max = Math.max(...chartData.map(d => d.count), 1);
  const html = chartData.map(d => {
    const pct = Math.round((d.count / max) * 100);
    const label = new Date(d.date).toLocaleDateString('en-IN', { weekday: 'short' });
    return `<div class="bar-wrap">
      <div class="bar" style="height:${Math.max(pct,4)}%" title="${d.count} borrows"></div>
      <div class="bar-label">${label}</div>
    </div>`;
  }).join('');
  $('barChart').innerHTML = html;
}

function renderGenres(genres) {
  const max = Math.max(...genres.map(g => g.count), 1);
  const html = genres.length ? genres.map(g => `
    <div class="genre-item">
      <span class="genre-name">${g.genre}</span>
      <div class="genre-bar-bg"><div class="genre-bar-fill" style="width:${Math.round(g.count/max*100)}%"></div></div>
      <span class="genre-count">${g.count}</span>
    </div>`).join('') : '<p style="color:var(--text-muted);font-size:13px">No genre data yet</p>';
  $('genreList').innerHTML = html;
}

function renderRecentActivity(txns) {
  if (!txns.length) {
    $('recentList').innerHTML = '<p style="color:var(--text-muted);font-size:13px;padding:10px 0">No activity yet</p>';
    return;
  }
  $('recentList').innerHTML = txns.map(t => {
    const status = t.status;
    const action = status === 'returned' ? 'returned' : status === 'overdue' ? 'overdue on' : 'borrowed';
    return `<div class="activity-item">
      <div class="activity-dot ${status}"></div>
      <div>
        <div class="activity-text"><strong>${t.member_name}</strong> ${action} <strong>${t.book_title}</strong></div>
        <div class="activity-meta">${fmtDate(t.borrow_date)} · due ${fmtDate(t.due_date)}</div>
      </div>
    </div>`;
  }).join('');
}

// Genre icon/color map
const GENRE_META = {
  'Fiction':        { icon: '📖', color: '#4a7c6a' },
  'Dystopian':      { icon: '🏙️', color: '#2c3e50' },
  'Romance':        { icon: '💕', color: '#c0392b' },
  'Fantasy':        { icon: '🧙', color: '#8e44ad' },
  'History':        { icon: '🏛️', color: '#e67e22' },
  'Self-Help':      { icon: '🚀', color: '#1abc9c' },
  'Sci-Fi':         { icon: '🛸', color: '#3461a8' },
  'Mystery':        { icon: '🔍', color: '#7f8c8d' },
  'Thriller':       { icon: '⚡', color: '#e74c3c' },
  'Biography':      { icon: '👤', color: '#8b6914' },
  'Philosophy':     { icon: '🦉', color: '#6c5ce7' },
  'Science':        { icon: '🔬', color: '#00b894' },
  'Business':       { icon: '💼', color: '#0984e3' },
  'Poetry':         { icon: '🪶', color: '#fd79a8' },
  'Horror':         { icon: '👻', color: '#636e72' },
  'Children':       { icon: '🌈', color: '#fdcb6e' },
  'Classics':       { icon: '📜', color: '#b2bec3' },
  'Travel':         { icon: '✈️', color: '#00cec9' },
  'Psychology':     { icon: '🧠', color: '#a29bfe' },
  'Cooking':        { icon: '🍳', color: '#ff7675' },
  'Art':            { icon: '🎨', color: '#e17055' },
  'Religion':       { icon: '☮️', color: '#74b9ff' },
  'Comics':         { icon: '💥', color: '#fab1a0' },
};

async function renderCategoryGrid() {
  const grid = $('categoryGrid');
  if (!grid) return;
  try {
    const genres = await apiFetch('/api/genres');
    if (!genres.length) { grid.innerHTML = '<p style="color:var(--text-muted);font-size:13px">No genres yet</p>'; return; }
    grid.innerHTML = genres.map(g => {
      const meta = GENRE_META[g] || { icon: '📚', color: '#c9a84c' };
      return `<div class="category-chip" onclick="navigateWithGenre('${escHtml(g)}')" style="border-color:${meta.color}22">
        <div class="cat-icon">${meta.icon}</div>
        <div class="cat-name" style="color:${meta.color}">${escHtml(g)}</div>
      </div>`;
    }).join('');
  } catch { grid.innerHTML = '<p style="color:var(--text-muted);font-size:13px">Could not load categories</p>'; }
}

// ══════════════════════════════════════════════════════════
// BOOKS
// ══════════════════════════════════════════════════════════
let booksPage = 1, booksQuery = '', booksGenre = '', booksAvail = '';

async function loadBooks() {
  const tbody = $('booksBody');
  tbody.innerHTML = `<tr class="loading-row"><td colspan="7"><span class="spinner"></span></td></tr>`;

  const params = new URLSearchParams({
    q: booksQuery, genre: booksGenre,
    available: booksAvail, page: booksPage, per_page: 15
  });

  try {
    const d = await apiFetch('/api/books?' + params);
    renderBooksTable(d.books);
    renderPagination('booksPag', d.total, booksPage, 15, p => { booksPage = p; loadBooks(); });
    $('booksCount').textContent = `${d.total} book${d.total!==1?'s':''}`;
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:#e05060;padding:30px">Error loading books</td></tr>`;
  }
}

function renderStars(rating) {
  if (!rating) return '<span style="color:var(--text-muted);font-size:12px">—</span>';
  const full = Math.floor(rating);
  const half = rating - full >= 0.5 ? 1 : 0;
  const empty = 5 - full - half;
  return '<span style="color:#f5c518;font-size:13px;letter-spacing:1px">'
    + '★'.repeat(full) + (half ? '½' : '') + '<span style="color:#555">' + '★'.repeat(empty) + '</span></span>'
    + ' <span style="font-size:11px;color:var(--text-muted)">(' + rating.toFixed(1) + ')</span>';
}

function renderBooksTable(books) {
  const tbody = $('booksBody');
  if (!books.length) {
    tbody.innerHTML = `<tr><td colspan="8"><div class="empty"><i class="fa-solid fa-book-open"></i><h3>No books found</h3><p>Try adjusting your search or add a new book.</p></div></td></tr>`;
    return;
  }

  tbody.innerHTML = books.map(b => `
    <tr onclick="viewBook(${b.id});" style="cursor: pointer;">
      <td>
        <div style="display:flex;align-items:center;gap:10px">
          <div class="book-spine" style="background:${b.cover_color}"></div>
          <div>
            <div class="td-title">${escHtml(b.title)}${b.is_bestseller ? ' <span style="background:#c9a84c20;color:#c9a84c;border:1px solid #c9a84c60;border-radius:4px;font-size:10px;padding:1px 5px;font-weight:600">★ BESTSELLER</span>' : ''}</div>
            <div class="td-sub">${escHtml(b.author)}</div>
          </div>
        </div>
      </td>
      <td><span style="font-family:'DM Mono',monospace;font-size:12px;color:var(--text-muted)">${b.isbn||'—'}</span></td>
      <td>${b.genre ? `<span class="badge" style="background:rgba(212,168,67,.1);color:var(--gold);border:1px solid rgba(212,168,67,.25)">${b.genre}</span>` : '—'}</td>
      <td>${b.year||'—'}</td>
      <td>${renderStars(b.rating)}</td>
      <td><span style="font-family:'DM Mono',monospace">${b.avail_copies}/${b.total_copies}</span></td>
      <td>${b.avail_copies > 0
        ? '<span class="badge badge-available"><i class="fa-solid fa-circle" style="font-size:7px"></i>Available</span>'
        : '<span class="badge badge-unavailable"><i class="fa-solid fa-circle" style="font-size:7px"></i>Out</span>'}</td>
      <td>
        <div class="actions">
          <button class="btn btn-ghost btn-xs" onclick="event.stopPropagation(); viewBook(${b.id})"><i class="fa-solid fa-eye"></i></button>
          <button class="btn btn-ghost btn-xs" onclick="event.stopPropagation(); editBook(${b.id})"><i class="fa-solid fa-pen"></i></button>
          <button class="btn btn-danger btn-xs" onclick="event.stopPropagation(); deleteBook(${b.id},'${escHtml(b.title)}')"><i class="fa-solid fa-trash"></i></button>
        </div>
      </td>
    </tr>
  `).join('');
}

// Book search/filter wiring
$('bookSearch').addEventListener('input', debounce(() => { booksQuery = $('bookSearch').value; booksPage = 1; loadBooks(); }, 350));
$('genreFilter').addEventListener('change', () => { booksGenre = $('genreFilter').value; booksPage = 1; loadBooks(); });
$('availFilter').addEventListener('change', () => { booksAvail = $('availFilter').value; booksPage = 1; loadBooks(); });

// Populate genre filter
async function populateGenreFilter() {
  try {
    const genres = await apiFetch('/api/genres');
    const sel = $('genreFilter');
    while (sel.options.length > 1) sel.remove(1); // keep the "All Genres" placeholder
    genres.forEach(g => {
      const o = document.createElement('option');
      o.value = g; o.textContent = g;
      sel.appendChild(o);
    });
  } catch {}
}

// ── Add / Edit Book modal ─────────────────────────────────
const COLORS = ['#c9a84c','#8b2635','#4a7c6a','#3461a8','#8e44ad','#27ae60','#d35400','#2c3e50','#c0392b','#1abc9c'];
let editingBookId = null;

function openBookModal(book = null) {
  editingBookId = book ? book.id : null;
  $('bookModalTitle').textContent = book ? 'Edit Book' : 'Add New Book';
  $('bookForm').reset();

  if (book) {
    $('bTitle').value         = book.title;
    $('bAuthor').value        = book.author;
    $('bIsbn').value          = book.isbn || '';
    $('bGenre').value         = book.genre || '';
    $('bPublisher').value     = book.publisher || '';
    $('bYear').value          = book.year || '';
    $('bCopies').value        = book.total_copies;
    $('bDesc').value          = book.description || '';
    $('bRating').value        = book.rating != null ? book.rating : '';
    $('bBestseller').checked  = !!book.is_bestseller;
    $('bEditions').value      = book.editions != null ? book.editions : '';
    selectedColor = book.cover_color;
  } else {
    $('bRating').value       = '';
    $('bBestseller').checked = false;
    $('bEditions').value     = '';
    $('bCopies').value       = 1;
    selectedColor = COLORS[0];
  }
  renderColorPicker();
  $('bookModal').classList.add('open');
}

let selectedColor = COLORS[0];

function renderColorPicker() {
  $('colorPicker').innerHTML = COLORS.map(c =>
    `<div class="color-swatch ${c === selectedColor ? 'selected' : ''}"
      style="background:${c}" onclick="selectColor('${c}')"></div>`
  ).join('');
}

window.selectColor = c => { selectedColor = c; renderColorPicker(); };

$('addBookBtn').addEventListener('click', () => openBookModal());
$('closeBookModal').addEventListener('click', () => $('bookModal').classList.remove('open'));
$('cancelBookModal').addEventListener('click', () => $('bookModal').classList.remove('open'));

$('bookForm').addEventListener('submit', async e => {
  e.preventDefault();
  const payload = {
    title:         $('bTitle').value.trim(),
    author:        $('bAuthor').value.trim(),
    isbn:          $('bIsbn').value.trim(),
    genre:         $('bGenre').value.trim(),
    publisher:     $('bPublisher').value.trim(),
    year:          $('bYear').value,
    total_copies:  $('bCopies').value,
    description:   $('bDesc').value.trim(),
    cover_color:   selectedColor,
    rating:        $('bRating').value !== '' ? parseFloat($('bRating').value) : null,
    is_bestseller: $('bBestseller').checked,
    editions:      $('bEditions').value !== '' ? parseInt($('bEditions').value) : null,
  };
  const btn = $('saveBookBtn');
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
  try {
    if (editingBookId) {
      await apiFetch(`/api/books/${editingBookId}`, { method: 'PUT', body: JSON.stringify(payload) });
      toast('Book updated successfully', 'success');
    } else {
      await apiFetch('/api/books', { method: 'POST', body: JSON.stringify(payload) });
      toast('Book added to catalogue', 'success');
    }
    $('bookModal').classList.remove('open');
    loadBooks(); populateGenreFilter();
    if (currentPage === 'dashboard') loadDashboard();
  } catch (err) {
    const msg = err.errors ? Object.values(err.errors).join(', ') : (err.error || 'Failed to save book');
    toast(msg, 'error');
  } finally { btn.disabled = false; btn.textContent = 'Save Book'; }
});

window.editBook = async id => {
  try {
    const b = await apiFetch(`/api/books/${id}`);
    openBookModal(b);
  } catch { toast('Failed to load book', 'error'); }
};

// ── BOOK DETAIL MODAL ─────────────────────────────────────
// ══════════════════════════════════════════════════════════
// BOOK DETAIL — Netflix-style panel
// ══════════════════════════════════════════════════════════

let _bdCurrentBook = null;   // cache for the currently open book
let _bdTabsReady   = false;  // prevent re-binding tab listeners

function bdOpenModal()  { $('viewBookModal').classList.add('open');  document.body.style.overflow = 'hidden'; }
function bdCloseModal() { $('viewBookModal').classList.remove('open'); document.body.style.overflow = ''; }

// ── Tab switching ─────────────────────────────────────────
function bdInitTabs() {
  if (_bdTabsReady) return;
  _bdTabsReady = true;
  document.querySelectorAll('.bd-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.bd-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.bd-tab-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const panel = $('tab' + tab.dataset.tab.charAt(0).toUpperCase() + tab.dataset.tab.slice(1));
      if (panel) panel.classList.add('active');
      if (tab.dataset.tab === 'chapters' && _bdCurrentBook) bdLoadChapters(_bdCurrentBook.id);
    });
  });
  $('closeViewBookModal').addEventListener('click', bdCloseModal);
  $('viewBookModal').addEventListener('click', e => { if (e.target === $('viewBookModal')) bdCloseModal(); });
}

// ── Hero population ───────────────────────────────────────
function bdPopulateHero(b) {
  // Animated gradient background from cover color
  const heroBg = $('bdHeroBg');
  heroBg.style.background = `radial-gradient(ellipse at 20% 50%, ${b.cover_color}55 0%, transparent 60%),
    radial-gradient(ellipse at 80% 20%, ${b.cover_color}33 0%, transparent 50%)`;

  // 3D book
  const front = $('bdBookFront');
  front.style.background = `linear-gradient(160deg, ${lightenColor(b.cover_color, 20)}, ${b.cover_color} 60%, ${darkenColor(b.cover_color, 20)})`;
  $('bdBook3d').querySelector('.bd-book-side').style.background = darkenColor(b.cover_color, 30);
  $('bdSpineTitle').textContent  = b.title;
  $('bdSpineAuthor').textContent = b.author;
  const textClr = isLightColor(b.cover_color) ? '#1a1a1a' : '#ffffff';
  $('bdSpineTitle').style.color  = textClr;
  $('bdSpineAuthor').style.color = textClr + 'bb';

  // Badges
  const badges = [];
  if (b.is_bestseller) badges.push(`<span class="bd-badge bd-badge-gold"><i class="fa-solid fa-fire"></i> Bestseller</span>`);
  if (b.genre) badges.push(`<span class="bd-badge bd-badge-genre">${escHtml(b.genre)}</span>`);
  if (b.avail_copies > 0) badges.push(`<span class="bd-badge bd-badge-avail"><i class="fa-solid fa-circle" style="font-size:7px"></i> Available</span>`);
  else                     badges.push(`<span class="bd-badge bd-badge-out"><i class="fa-solid fa-circle" style="font-size:7px"></i> Out</span>`);
  $('bdBadgeRow').innerHTML = badges.join('');

  // Title & author
  $('bdTitle').textContent = b.title;
  $('bdAuthorLine').innerHTML = `by <span class="bd-author-name">${escHtml(b.author)}</span>`;

  // Rating
  if (b.rating) {
    const full = Math.floor(b.rating);
    const stars = '★'.repeat(full) + (b.rating - full >= 0.5 ? '½' : '') + '<span style="color:#333">' + '★'.repeat(5 - full - (b.rating - full >= 0.5 ? 1 : 0)) + '</span>';
    $('bdRatingRow').innerHTML = `<span class="bd-stars">${stars}</span><span class="bd-rating-num">${b.rating.toFixed(1)}</span><span class="bd-rating-label">/ 5.0</span>`;
  } else {
    $('bdRatingRow').innerHTML = `<span style="color:var(--text-muted);font-size:13px">No rating yet</span>`;
  }

  // Quick stat pills (will update when chapters load)
  $('bdQuickStats').innerHTML = `
    <div class="bd-stat-pill" id="bdStatYear"><i class="fa-solid fa-calendar"></i> ${b.year || 'Unknown'}</div>
    <div class="bd-stat-pill" id="bdStatCopies"><i class="fa-solid fa-copy"></i> ${b.avail_copies}/${b.total_copies} copies</div>
    <div class="bd-stat-pill" id="bdStatPages"><i class="fa-solid fa-file-lines"></i> <span class="spinner" style="width:14px;height:14px;border-width:2px"></span></div>
    <div class="bd-stat-pill" id="bdStatChaps"><i class="fa-solid fa-list-ol"></i> <span class="spinner" style="width:14px;height:14px;border-width:2px"></span></div>`;

  // Action buttons
  const borrowBtn = $('bdBorrowBtn');
  if (b.avail_copies > 0) {
    borrowBtn.disabled = false;
    borrowBtn.style.opacity = '1';
    borrowBtn.onclick = () => { bdCloseModal(); navigate('issue'); };
  } else {
    borrowBtn.disabled = true;
    borrowBtn.style.opacity = '0.45';
    borrowBtn.innerHTML = '<i class="fa-solid fa-ban"></i> Unavailable';
  }
  $('bdEditBtn').onclick = () => { bdCloseModal(); editBook(b.id); };
}

// ── Overview tab ──────────────────────────────────────────
function bdPopulateOverview(b) {
  $('bdDescText').textContent = b.description || 'No description available for this book.';

  // Genre section
  if (b.genre) {
    const meta = (typeof GENRE_META !== 'undefined' && GENRE_META[b.genre]) || { icon: '📚', color: '#c9a84c' };
    $('bdGenreSection').innerHTML = `
      <div class="bd-genre-card" style="border-color:${meta.color}44;background:${meta.color}0d">
        <span class="bd-genre-icon">${meta.icon}</span>
        <div>
          <div class="bd-genre-label">Genre</div>
          <div class="bd-genre-name" style="color:${meta.color}">${escHtml(b.genre)}</div>
        </div>
      </div>`;
  }

  // Wikipedia link
  if (b.wikipedia_url) {
    $('bdWikiRow').innerHTML = `<a href="${b.wikipedia_url}" target="_blank" rel="noopener noreferrer" class="bd-wiki-link">
      <i class="fa-brands fa-wikipedia-w"></i> Learn more about ${escHtml(b.author)} on Wikipedia
    </a>`;
  }
}

// ── Details tab ───────────────────────────────────────────
function bdPopulateDetails(b) {
  const fields = [
    { label: 'ISBN',          icon: 'barcode',          value: b.isbn        || '—' },
    { label: 'Publisher',     icon: 'building-columns', value: b.publisher   || '—' },
    { label: 'Year',          icon: 'calendar',         value: b.year        || '—' },
    { label: 'Editions',      icon: 'layer-group',      value: b.editions    || '—' },
    { label: 'Total Copies',  icon: 'copy',             value: b.total_copies },
    { label: 'Avail. Copies', icon: 'book-open',        value: b.avail_copies + ' / ' + b.total_copies },
    { label: 'Genre',         icon: 'tag',              value: b.genre       || '—' },
    { label: 'Status',        icon: 'circle-dot',       value: b.avail_copies > 0 ? 'Available' : 'Out of stock' },
  ];
  $('bdDetailsGrid').innerHTML = fields.map(f => `
    <div class="bd-detail-field">
      <div class="bd-detail-label"><i class="fa-solid fa-${f.icon}"></i> ${f.label}</div>
      <div class="bd-detail-value">${f.value}</div>
    </div>`).join('');
}

// ── Chapters tab ──────────────────────────────────────────
let _chaptersCache = {};

async function bdLoadChapters(bookId) {
  const list = $('bdChaptersList');
  if (_chaptersCache[bookId]) {
    bdRenderChapters(_chaptersCache[bookId]);
    return;
  }
  list.innerHTML = '<div style="text-align:center;padding:40px 0"><span class="spinner"></span></div>';
  try {
    const data = await apiFetch(`/api/books/${bookId}/chapters`);
    _chaptersCache[bookId] = data;
    // Update quick-stat pills
    $('bdStatPages').innerHTML = `<i class="fa-solid fa-file-lines"></i> ${data.pages.toLocaleString()} pages`;
    $('bdStatChaps').innerHTML = `<i class="fa-solid fa-list-ol"></i> ${data.chapter_count} chapters`;
    bdRenderChapters(data);
  } catch {
    list.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:40px 0">Could not load chapter data.</p>';
  }
}

function bdRenderChapters(data) {
  const list = $('bdChaptersList');
  $('bdChaptersMeta').innerHTML = `
    <span class="bd-chap-meta-pill"><i class="fa-solid fa-file-lines"></i> ${data.pages.toLocaleString()} pages</span>
    <span class="bd-chap-meta-pill"><i class="fa-solid fa-list-ol"></i> ${data.chapter_count} chapters</span>
    <span class="bd-chap-meta-pill"><i class="fa-solid fa-clock"></i> ~${Math.round(data.pages / 40)} hr read</span>`;

  list.innerHTML = data.chapters.map((ch, i) => `
    <div class="bd-chapter-item" style="animation-delay:${i * 30}ms">
      <div class="bd-chapter-num">${i + 1}</div>
      <div class="bd-chapter-name">${escHtml(ch)}</div>
      <div class="bd-chapter-progress">
        <div class="bd-chapter-progress-bar" style="width:${Math.round((i / data.chapters.length) * 100)}%"></div>
      </div>
    </div>`).join('');
}

// ── Main entry point ──────────────────────────────────────
window.viewBook = async id => {
  bdInitTabs();
  _bdCurrentBook = null;
  _chaptersCache = {};   // reset on each new book open

  // Reset to Overview tab
  document.querySelectorAll('.bd-tab').forEach((t, i) => t.classList.toggle('active', i === 0));
  document.querySelectorAll('.bd-tab-panel').forEach((p, i) => p.classList.toggle('active', i === 0));
  // Reset hero title while loading
  $('bdTitle').textContent = 'Loading…';
  $('bdAuthorLine').innerHTML = '';
  $('bdBadgeRow').innerHTML = '';
  $('bdRatingRow').innerHTML = '';
  $('bdQuickStats').innerHTML = '';
  $('bdChaptersList').innerHTML = '<div style="text-align:center;padding:40px 0"><span class="spinner"></span></div>';
  $('bdChaptersMeta').innerHTML = '';

  bdOpenModal();

  try {
    const b = await apiFetch(`/api/books/${id}`);
    _bdCurrentBook = b;

    bdPopulateHero(b);
    bdPopulateOverview(b);
    bdPopulateDetails(b);

    // Pre-fetch chapters in background (updates stat pills)
    bdLoadChapters(id);
  } catch (err) {
    toast('Failed to load book details', 'error');
    bdCloseModal();
  }
};

// ── Color helpers ──────────────────────────────────────────
function hexToRgb(hex) {
  let c = hex.replace('#', '');
  if (c.length === 3) c = c.split('').map(x => x+x).join('');
  return { r: parseInt(c.substr(0,2),16), g: parseInt(c.substr(2,2),16), b: parseInt(c.substr(4,2),16) };
}
function rgbToHex(r, g, b) {
  return '#' + [r,g,b].map(x => Math.max(0,Math.min(255,Math.round(x))).toString(16).padStart(2,'0')).join('');
}
function lightenColor(hex, pct) {
  const {r,g,b} = hexToRgb(hex);
  return rgbToHex(r + (255-r)*pct/100, g + (255-g)*pct/100, b + (255-b)*pct/100);
}
function darkenColor(hex, pct) {
  const {r,g,b} = hexToRgb(hex);
  return rgbToHex(r*(1-pct/100), g*(1-pct/100), b*(1-pct/100));
}

window.deleteBook = async (id, title) => {
  if (!confirm(`Delete "${title}"? This cannot be undone.`)) return;
  try {
    await apiFetch(`/api/books/${id}`, { method: 'DELETE' });
    toast('Book deleted', 'success');
    loadBooks();
    if (currentPage === 'dashboard') loadDashboard();
  } catch (err) {
    toast(err.error || 'Cannot delete this book', 'error');
  }
};

// ══════════════════════════════════════════════════════════
// MEMBERS
// ══════════════════════════════════════════════════════════
let membersPage = 1, membersQuery = '';
let editingMemberId = null;

async function loadMembers() {
  const tbody = $('membersBody');
  tbody.innerHTML = `<tr class="loading-row"><td colspan="6"><span class="spinner"></span></td></tr>`;

  const params = new URLSearchParams({ q: membersQuery, page: membersPage, per_page: 15 });

  try {
    const d = await apiFetch('/api/members?' + params);
    renderMembersTable(d.members);
    renderPagination('membersPag', d.total, membersPage, 15, p => { membersPage = p; loadMembers(); });
    $('membersCount').textContent = `${d.total} member${d.total!==1?'s':''}`;
  } catch { tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#e05060;padding:30px">Error loading members</td></tr>`; }
}

function renderMembersTable(members) {
  const tbody = $('membersBody');
  if (!members.length) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="empty"><i class="fa-solid fa-users"></i><h3>No members found</h3><p>Add a new member to get started.</p></div></td></tr>`;
    return;
  }
  tbody.innerHTML = members.map(m => `
    <tr>
      <td><div style="display:flex;align-items:center;gap:10px">
        <div class="avatar" style="width:30px;height:30px;font-size:11px">${m.name.charAt(0)}</div>
        <div><div class="td-title">${escHtml(m.name)}</div><div class="td-sub">${escHtml(m.email)}</div></div>
      </div></td>
      <td>${m.phone||'—'}</td>
      <td>${fmtDate(m.membership_date)}</td>
      <td><span class="badge ${m.is_active?'badge-active':'badge-inactive'}">${m.is_active?'Active':'Inactive'}</span></td>
      <td><span style="font-family:'DM Mono',monospace">${m.active_borrows}</span></td>
      <td><div class="actions">
        <button class="btn btn-ghost btn-xs" onclick="viewMember(${m.id})"><i class="fa-solid fa-eye"></i></button>
        <button class="btn btn-ghost btn-xs" onclick="editMember(${m.id})"><i class="fa-solid fa-pen"></i></button>
        <button class="btn btn-danger btn-xs" onclick="deleteMember(${m.id},'${escHtml(m.name)}')"><i class="fa-solid fa-trash"></i></button>
      </div></td>
    </tr>`).join('');
}

$('memberSearch').addEventListener('input', debounce(() => { membersQuery = $('memberSearch').value; membersPage = 1; loadMembers(); }, 350));

$('addMemberBtn').addEventListener('click', () => { editingMemberId = null; $('memberModalTitle').textContent = 'Add New Member'; $('memberForm').reset(); $('memberModal').classList.add('open'); });
$('closeMemberModal').addEventListener('click', () => $('memberModal').classList.remove('open'));
$('cancelMemberModal').addEventListener('click', () => $('memberModal').classList.remove('open'));

$('memberForm').addEventListener('submit', async e => {
  e.preventDefault();
  const payload = {
    name:    $('mName').value.trim(),
    email:   $('mEmail').value.trim(),
    phone:   $('mPhone').value.trim(),
    address: $('mAddress').value.trim(),
  };
  const btn = $('saveMemberBtn');
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
  try {
    if (editingMemberId) {
      await apiFetch(`/api/members/${editingMemberId}`, { method: 'PUT', body: JSON.stringify(payload) });
      toast('Member updated', 'success');
    } else {
      await apiFetch('/api/members', { method: 'POST', body: JSON.stringify(payload) });
      toast('Member registered', 'success');
    }
    $('memberModal').classList.remove('open');
    loadMembers();
    if (currentPage === 'dashboard') loadDashboard();
  } catch (err) {
    const msg = err.errors ? Object.values(err.errors).join(', ') : (err.error || 'Failed to save');
    toast(msg, 'error');
  } finally { btn.disabled = false; btn.textContent = 'Save Member'; }
});

window.editMember = async id => {
  try {
    const m = await apiFetch(`/api/members/${id}`);
    editingMemberId = id;
    $('memberModalTitle').textContent = 'Edit Member';
    $('mName').value    = m.name;
    $('mEmail').value   = m.email;
    $('mPhone').value   = m.phone || '';
    $('mAddress').value = m.address || '';
    $('memberModal').classList.add('open');
  } catch { toast('Failed to load member', 'error'); }
};

window.viewMember = async id => {
  try {
    const m = await apiFetch(`/api/members/${id}`);
    $('viewMemberContent').innerHTML = `
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:18px">
        <div class="avatar" style="width:48px;height:48px;font-size:18px">${m.name.charAt(0)}</div>
        <div>
          <h3 style="font-family:'Playfair Display',serif;font-size:18px">${escHtml(m.name)}</h3>
          <p style="color:var(--text-sub)">${escHtml(m.email)}</p>
        </div>
        <div style="margin-left:auto">${m.is_active?'<span class="badge badge-active">Active</span>':'<span class="badge badge-inactive">Inactive</span>'}</div>
      </div>
      <div class="detail-meta">
        <div class="detail-field"><label>Phone</label><span>${m.phone||'—'}</span></div>
        <div class="detail-field"><label>Member Since</label><span>${fmtDate(m.membership_date)}</span></div>
        <div class="detail-field"><label>Active Borrows</label><span>${m.active_borrows}</span></div>
        <div class="detail-field"><label>Address</label><span>${m.address||'—'}</span></div>
      </div>
      ${m.transactions.length ? `
        <h4 style="font-family:'Playfair Display',serif;font-size:14px;margin:14px 0 10px;color:var(--text-sub)">Borrow History</h4>
        ${m.transactions.slice(0,5).map(t=>`
          <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);font-size:13px">
            <span>${escHtml(t.book_title)}</span>
            <div style="display:flex;gap:8px;align-items:center">${statusBadge(t.status)}<span style="color:var(--text-muted)">${fmtDate(t.borrow_date)}</span></div>
          </div>`).join('')}` : ''}`;
    $('viewMemberModal').classList.add('open');
  } catch { toast('Failed to load member', 'error'); }
};

$('closeViewMemberModal').addEventListener('click', () => $('viewMemberModal').classList.remove('open'));

window.deleteMember = async (id, name) => {
  if (!confirm(`Remove member "${name}"?`)) return;
  try {
    await apiFetch(`/api/members/${id}`, { method: 'DELETE' });
    toast('Member removed', 'success');
    loadMembers();
    if (currentPage === 'dashboard') loadDashboard();
  } catch (err) {
    toast(err.error || 'Cannot delete member', 'error');
  }
};

// ══════════════════════════════════════════════════════════
// TRANSACTIONS
// ══════════════════════════════════════════════════════════
let txPage = 1, txStatus = '';

async function loadTransactions() {
  const tbody = $('txBody');
  tbody.innerHTML = `<tr class="loading-row"><td colspan="7"><span class="spinner"></span></td></tr>`;

  const params = new URLSearchParams({ status: txStatus, page: txPage, per_page: 15 });

  try {
    const d = await apiFetch('/api/transactions?' + params);
    renderTxTable(d.transactions);
    renderPagination('txPag', d.total, txPage, 15, p => { txPage = p; loadTransactions(); });
    $('txCount').textContent = `${d.total} record${d.total!==1?'s':''}`;
  } catch { tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:#e05060;padding:30px">Error loading transactions</td></tr>`; }
}

function renderTxTable(txns) {
  const tbody = $('txBody');
  if (!txns.length) {
    tbody.innerHTML = `<tr><td colspan="7"><div class="empty"><i class="fa-solid fa-arrows-rotate"></i><h3>No transactions</h3><p>Issue a book to create a transaction.</p></div></td></tr>`;
    return;
  }
  tbody.innerHTML = txns.map(t => `
    <tr>
      <td><span style="font-family:'DM Mono',monospace;font-size:12px;color:var(--text-muted)">#${t.id}</span></td>
      <td><div class="td-title">${escHtml(t.book_title||'')}</div></td>
      <td>${escHtml(t.member_name||'')}</td>
      <td>${fmtDate(t.borrow_date)}</td>
      <td>${fmtDate(t.due_date)}</td>
      <td>${statusBadge(t.status)}
        ${t.status==='borrowed'?`<div style="font-size:11px;margin-top:3px">${daysLeft(t.due_date)}</div>`:''}
        ${t.fine_amount>0?`<div style="font-size:11px;color:#e05060;margin-top:2px">Fine: ₹${t.fine_amount}</div>`:''}
      </td>
      <td><div class="actions">
        ${t.status !== 'returned'
          ? `<button class="btn btn-success btn-xs" onclick="returnBook(${t.id})"><i class="fa-solid fa-rotate-left"></i> Return</button>`
          : `<span style="color:var(--text-muted);font-size:12px">${fmtDate(t.return_date)}</span>`}
        <button class="btn btn-danger btn-xs" onclick="deleteTx(${t.id})"><i class="fa-solid fa-trash"></i></button>
      </div></td>
    </tr>`).join('');
}

document.querySelectorAll('.tx-filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tx-filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    txStatus = btn.dataset.status;
    txPage = 1;
    loadTransactions();
  });
});

window.returnBook = async id => {
  if (!confirm('Mark this book as returned?')) return;
  try {
    const t = await apiFetch(`/api/transactions/${id}/return`, { method: 'POST' });
    const fine = t.fine_amount;
    toast(fine > 0 ? `Book returned. Fine: ₹${fine}` : 'Book returned successfully', fine > 0 ? 'info' : 'success');
    loadTransactions();
    if (currentPage === 'dashboard') loadDashboard();
  } catch (err) { toast(err.error || 'Failed to process return', 'error'); }
};

window.deleteTx = async id => {
  if (!confirm('Delete this transaction record?')) return;
  try {
    await apiFetch(`/api/transactions/${id}`, { method: 'DELETE' });
    toast('Transaction deleted', 'success');
    loadTransactions();
  } catch { toast('Failed to delete transaction', 'error'); }
};

// ══════════════════════════════════════════════════════════
// ISSUE BOOK
// ══════════════════════════════════════════════════════════
async function loadIssueForm() {
  try {
    // Load available books
    const bd = await apiFetch('/api/books?available=true&per_page=200');
    const bSel = $('issueBookSel');
    bSel.innerHTML = '<option value="">— Select a book —</option>';
    bd.books.forEach(b => {
      const o = document.createElement('option');
      o.value = b.id;
      o.textContent = `${b.title} by ${b.author} (${b.avail_copies} left)`;
      bSel.appendChild(o);
    });

    // Load active members
    const md = await apiFetch('/api/members?per_page=200');
    const mSel = $('issueMemberSel');
    mSel.innerHTML = '<option value="">— Select a member —</option>';
    md.members.filter(m => m.is_active).forEach(m => {
      const o = document.createElement('option');
      o.value = m.id;
      o.textContent = `${m.name} (${m.email})`;
      mSel.appendChild(o);
    });
  } catch { toast('Failed to load issue form data', 'error'); }
}

$('issueForm').addEventListener('submit', async e => {
  e.preventDefault();
  const payload = {
    book_id:   parseInt($('issueBookSel').value),
    member_id: parseInt($('issueMemberSel').value),
    days:      parseInt($('issueDays').value) || 14,
    notes:     $('issueNotes').value.trim(),
  };

  if (!payload.book_id || !payload.member_id) {
    toast('Please select both a book and a member', 'error'); return;
  }

  const btn = $('issueSubmitBtn');
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Processing…';

  try {
    await apiFetch('/api/transactions/borrow', { method: 'POST', body: JSON.stringify(payload) });
    toast('Book issued successfully!', 'success');
    $('issueForm').reset();
    loadIssueForm();
    if (currentPage === 'dashboard') loadDashboard();
  } catch (err) {
    toast(err.error || 'Failed to issue book', 'error');
  } finally { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Issue Book'; }
});

// ══════════════════════════════════════════════════════════
// GLOBAL SEARCH
// ══════════════════════════════════════════════════════════
const searchInput = $('globalSearch');
const searchDrop  = $('searchDropdown');

searchInput.addEventListener('input', debounce(async () => {
  const q = searchInput.value.trim();
  if (!q) { searchDrop.style.display = 'none'; return; }
  try {
    const d = await apiFetch(`/api/search?q=${encodeURIComponent(q)}`);
    if (!d.books.length && !d.members.length) { searchDrop.style.display = 'none'; return; }
    let html = '';
    if (d.books.length) {
      html += `<div class="drop-section">Books</div>`;
      html += d.books.map(b => `<div class="drop-item" onclick="goBook(${b.id})"><i class="fa-solid fa-book"></i>${escHtml(b.title)}<span>${escHtml(b.author)}</span></div>`).join('');
    }
    if (d.members.length) {
      html += `<div class="drop-section">Members</div>`;
      html += d.members.map(m => `<div class="drop-item" onclick="goMember(${m.id})"><i class="fa-solid fa-user"></i>${escHtml(m.name)}<span>${escHtml(m.email)}</span></div>`).join('');
    }
    searchDrop.innerHTML = html;
    searchDrop.style.display = 'block';
  } catch {}
}, 300));

document.addEventListener('click', e => {
  if (!searchInput.contains(e.target) && !searchDrop.contains(e.target)) {
    searchDrop.style.display = 'none';
  }
});

window.goBook = id => { searchDrop.style.display = 'none'; searchInput.value = ''; navigate('books'); setTimeout(() => viewBook(id), 300); };
window.goMember = id => { searchDrop.style.display = 'none'; searchInput.value = ''; navigate('members'); setTimeout(() => viewMember(id), 300); };

// ══════════════════════════════════════════════════════════
// PAGINATION helper
// ══════════════════════════════════════════════════════════
function renderPagination(containerId, total, currentPage, perPage, onPageChange) {
  const container = $(containerId);
  if (!container) return;
  const totalPages = Math.ceil(total / perPage);
  if (totalPages <= 1) { container.innerHTML = ''; return; }

  let html = `<button class="page-btn" ${currentPage===1?'disabled':''} onclick="(${onPageChange.toString()})(${currentPage-1})"><i class="fa-solid fa-chevron-left"></i></button>`;
  for (let p = Math.max(1, currentPage-2); p <= Math.min(totalPages, currentPage+2); p++) {
    html += `<button class="page-btn ${p===currentPage?'active':''}" onclick="(${onPageChange.toString()})(${p})">${p}</button>`;
  }
  html += `<button class="page-btn" ${currentPage===totalPages?'disabled':''} onclick="(${onPageChange.toString()})(${currentPage+1})"><i class="fa-solid fa-chevron-right"></i></button>`;
  html += `<span>${currentPage} of ${totalPages}</span>`;
  container.innerHTML = html;
}

// ══════════════════════════════════════════════════════════
// UTILS
// ══════════════════════════════════════════════════════════
function debounce(fn, delay) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
}

function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Close overlays on background click
document.querySelectorAll('.overlay').forEach(o => {
  o.addEventListener('click', e => { if (e.target === o) o.classList.remove('open'); });
});

// ══════════════════════════════════════════════════════════
// CHAT BOT
// ══════════════════════════════════════════════════════════

let chatOpen = false;
let chatInitialized = false;

function toggleChat() {
  // FIX: was document.getElementById('chatbotContainer') — the element had no id in HTML,
  // causing container to be null and crashing here. Now fixed in index.html.
  const container = $('chatbotContainer');
  chatOpen = !chatOpen;
  if (chatOpen) {
    container.classList.add('open');
    if (!chatInitialized) {
      chatInitialized = true;
      showWelcomeMessage();
    }
    setTimeout(() => $('chatInput').focus(), 200);
  } else {
    container.classList.remove('open');
  }
}

function showWelcomeMessage() {
  const welcomeText = `Hello! I'm your **Library Assistant** 📚\n\nI can help you with:\n- Book recommendations\n- Checking availability\n- Finding members\n- Overdue information\n\nWhat would you like to know?`;
  appendBotMessage(welcomeText, true);
}

function formatBotResponse(text) {
  // Convert **bold** to <strong>
  text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Convert *italic* to <em>
  text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');

  const lines = text.split('\n');
  let html = '';
  let inList = false;
  let listItems = [];

  const flushList = () => {
    if (listItems.length) {
      html += '<ul class="bot-list">' + listItems.map(li => `<li>${li}</li>`).join('') + '</ul>';
      listItems = [];
      inList = false;
    }
  };

  lines.forEach(line => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushList();
      html += '<br>';
    } else if (/^[-•*]\s/.test(trimmed)) {
      inList = true;
      listItems.push(trimmed.replace(/^[-•*]\s/, ''));
    } else {
      flushList();
      html += `<span>${trimmed}</span><br>`;
    }
  });
  flushList();

  // Clean up leading/trailing <br>
  return html.replace(/^(<br>)+|(<br>)+$/g, '');
}

function appendBotMessage(text, isWelcome = false) {
  const messages = $('chatMessages');
  const row = document.createElement('div');
  row.className = 'msg-row bot';

  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.textContent = '📚';

  const bubble = document.createElement('div');
  bubble.className = 'message-bot';
  if (isWelcome) {
    bubble.innerHTML = `<span class="bot-label">Assistant</span><br>` + formatBotResponse(text);
  } else {
    bubble.innerHTML = formatBotResponse(text);
  }

  row.appendChild(avatar);
  row.appendChild(bubble);
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
  return row;
}

function appendUserMessage(text) {
  const messages = $('chatMessages');
  const row = document.createElement('div');
  row.className = 'msg-row user';

  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.innerHTML = '<i class="fa-solid fa-user" style="font-size:11px;color:var(--gold)"></i>';

  const bubble = document.createElement('div');
  bubble.className = 'message-user';
  bubble.textContent = text;

  row.appendChild(avatar);
  row.appendChild(bubble);
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
}

function showTypingIndicator() {
  const messages = $('chatMessages');
  const row = document.createElement('div');
  row.className = 'msg-row bot';
  row.id = 'typingRow';

  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.textContent = '📚';

  const indicator = document.createElement('div');
  indicator.className = 'typing-indicator';
  indicator.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';

  row.appendChild(avatar);
  row.appendChild(indicator);
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
}

function removeTypingIndicator() {
  const el = $('typingRow');
  if (el) el.remove();
}

function useSuggestion(text) {
  $('chatInput').value = text;
  // Hide suggestions after first use
  const suggestions = $('chatSuggestions');
  if (suggestions) suggestions.style.display = 'none';
  sendMessage();
}

function sendMessage() {
  const input = $('chatInput');
  const userText = input.value.trim();
  if (!userText) return;

  // Hide suggestions once user starts chatting
  const suggestions = $('chatSuggestions');
  if (suggestions) suggestions.style.display = 'none';

  appendUserMessage(userText);
  input.value = '';

  showTypingIndicator();

  // FIX: was hardcoded "http://127.0.0.1:5000/chatbot" — breaks in any non-local environment.
  // Now uses the API constant (same-origin) like every other fetch call in this file.
  fetch(API + '/chatbot', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: userText })
  })
  .then(response => response.json())
  .then(data => {
    removeTypingIndicator();
    appendBotMessage(data.response);
  })
  .catch(error => {
    removeTypingIndicator();
    appendBotMessage("Sorry, I'm having trouble connecting right now. Please try again shortly.");
    console.error('Chatbot error:', error);
  });
}

$('chatInput').addEventListener('keypress', function(e) {
  if (e.key === 'Enter') sendMessage();
});

// ══════════════════════════════════════════════════════════
// TRENDING SHELVES  (OTT-style)
// ══════════════════════════════════════════════════════════
async function loadTrending() {
  const wrap = $('trendingShelves');
  if (!wrap) return;
  try {
    const data = await apiFetch('/api/trending');
    renderTrendingShelves(data.shelves);
  } catch (e) {
    console.error('Trending load error', e);
    wrap.innerHTML = '';
  }
}

function renderTrendingShelves(shelves) {
  const wrap = $('trendingShelves');
  if (!shelves || !shelves.length) { wrap.innerHTML = ''; return; }

  wrap.innerHTML = shelves.map((shelf, si) => `
    <div class="shelf-section" id="shelf-${shelf.id}">
      <div class="shelf-header">
        <div>
          <div class="shelf-label">${shelf.label}</div>
          <div class="shelf-sublabel">${shelf.sublabel}</div>
        </div>
        <button class="shelf-see-all" onclick="navigateWithGenre(''); navigate('books')">
          See all <i class="fa-solid fa-arrow-right"></i>
        </button>
      </div>
      <div class="shelf-row-wrapper">
        <button class="shelf-arrow left" onclick="shelfScroll('shelf-row-${si}', -1)" aria-label="Scroll left">
          <i class="fa-solid fa-chevron-left"></i>
        </button>
        <div class="shelf-row" id="shelf-row-${si}">
          ${shelf.books.map((book, bi) => renderBookCard(book, bi, shelf.id === 'trending')).join('')}
        </div>
        <button class="shelf-arrow right" onclick="shelfScroll('shelf-row-${si}', 1)" aria-label="Scroll right">
          <i class="fa-solid fa-chevron-right"></i>
        </button>
      </div>
    </div>
  `).join('');
}

function renderBookCard(book, index, showRank) {
  const stars = book.rating
    ? '★'.repeat(Math.round(book.rating)) + '☆'.repeat(5 - Math.round(book.rating))
    : '';
  const availClass = book.avail_copies > 0 ? 'yes' : 'no';
  const availText  = book.avail_copies > 0 ? 'Available' : 'Out';

  // Darken the cover color slightly for text contrast
  const textContrast = isLightColor(book.cover_color) ? '#1a1a1a' : '#ffffff';

  return `
    <div class="book-card" onclick="viewBook(${book.id})" title="${escHtml(book.title)}">
      <div class="book-cover" style="background:${book.cover_color}">
        ${showRank ? `<div class="book-rank">${index + 1}</div>` : ''}
        ${book.is_bestseller ? `<div class="bestseller-flame" title="Bestseller">🔥</div>` : ''}
        <div class="book-cover-spine">
          <div class="book-cover-title" style="color:${textContrast}">${escHtml(book.title)}</div>
          <div class="book-cover-author" style="color:${textContrast}88">${escHtml(book.author)}</div>
        </div>
        <div class="book-cover-overlay"></div>
      </div>
      <div class="book-card-body">
        <div class="book-card-title" title="${escHtml(book.title)}">${escHtml(book.title)}</div>
        <div class="book-card-author">${escHtml(book.author)}</div>
        <div class="book-card-meta">
          <span class="book-card-rating" title="${book.rating ? book.rating + '/5' : 'No rating'}">${
            book.rating
              ? `<span style="color:#f5c518">${stars}</span> <span style="color:var(--text-muted);font-size:10px">${book.rating.toFixed(1)}</span>`
              : '<span style="color:var(--text-muted)">No rating</span>'
          }</span>
          <span class="book-card-avail ${availClass}">${availText}</span>
        </div>
      </div>
    </div>`;
}

function shelfScroll(rowId, dir) {
  const row = $(rowId);
  if (row) row.scrollBy({ left: dir * 600, behavior: 'smooth' });
}

// Simple luminance check to pick text color on covers
function isLightColor(hex) {
  if (!hex || hex.length < 4) return false;
  let c = hex.replace('#', '');
  if (c.length === 3) c = c.split('').map(x => x+x).join('');
  const r = parseInt(c.substr(0,2),16);
  const g = parseInt(c.substr(2,2),16);
  const b = parseInt(c.substr(4,2),16);
  return (r*299 + g*587 + b*114) / 1000 > 140;
}

// Handle browser back/forward button
window.addEventListener('popstate', (e) => {
  const page = e.state?.page || 'dashboard';
  navigate(page);
});

// On first load, check if URL has a hash and navigate to it
window.addEventListener('DOMContentLoaded', () => {
  const hash = window.location.hash.replace('#', '');
  if (hash && pages[hash]) {
    navigate(hash);
  } else {
    navigate('dashboard');
    history.replaceState({ page: 'dashboard' }, '', '#dashboard');
  }
});

// ══════════════════════════════════════════════════════════
// BOOT
// ══════════════════════════════════════════════════════════
(async () => {
  await populateGenreFilter();
  navigate('dashboard');
})();