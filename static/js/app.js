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

  // Load data for the page
  if (page === 'dashboard')    loadDashboard();
  if (page === 'books')        loadBooks();
  if (page === 'members')      loadMembers();
  if (page === 'transactions') loadTransactions();
  if (page === 'issue')        loadIssueForm();
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
function sendMessage() {
    let input = document.getElementById("chatInput");
    let messages = document.getElementById("chatMessages");

    let userMsg = document.createElement("div");
    userMsg.className = "message-user";
    userMsg.innerText = input.value;
    messages.appendChild(userMsg);

    fetch("http://127.0.0.1:5000/chatbot", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: input.value})
    })
    .then(res => res.json())
    .then(data => {
        let botMsg = document.createElement("div");
        botMsg.className = "message-bot";
        botMsg.innerText = data.response;
        messages.appendChild(botMsg);
        messages.scrollTop = messages.scrollHeight;
    });

    input.value = "";
}

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
  } catch (e) { tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:#e05060;padding:30px">Error loading books</td></tr>`; }
}

function renderStars(rating) {
  if (!rating) return '<span style="color:var(--text-muted);font-size:12px">—</span>';
  const full = Math.floor(rating);
  const half = rating - full >= 0.5 ? 1 : 0;
  const empty = 5 - full - half;
  return '<span style="color:#f5c518;font-size:13px;letter-spacing:1px">'
    + '★'.repeat(full) + (half ? '½' : '') + '<span style="color:#555">'  + '★'.repeat(empty) + '</span></span>'
    + ' <span style="font-size:11px;color:var(--text-muted)">(' + rating.toFixed(1) + ')</span>';
}

function renderBooksTable(books) {
  const tbody = $('booksBody');
  if (!books.length) {
    tbody.innerHTML = `<tr><td colspan="8"><div class="empty"><i class="fa-solid fa-book-open"></i><h3>No books found</h3><p>Try adjusting your search or add a new book.</p></div></td></tr>`;
    return;
  }
  tbody.innerHTML = books.map(b => `
    <tr>
      <td><div style="display:flex;align-items:center;gap:10px">
        <div class="book-spine" style="background:${b.cover_color}"></div>
        <div>
          <div class="td-title">${escHtml(b.title)}${b.is_bestseller ? ' <span style="background:#c9a84c20;color:#c9a84c;border:1px solid #c9a84c60;border-radius:4px;font-size:10px;padding:1px 5px;font-weight:600">★ BESTSELLER</span>' : ''}</div>
          <div class="td-sub">${escHtml(b.author)}</div>
        </div>
      </div></td>
      <td><span style="font-family:'DM Mono',monospace;font-size:12px;color:var(--text-muted)">${b.isbn||'—'}</span></td>
      <td>${b.genre ? `<span class="badge" style="background:rgba(212,168,67,.1);color:var(--gold);border:1px solid rgba(212,168,67,.25)">${b.genre}</span>` : '—'}</td>
      <td>${b.year||'—'}</td>
      <td>${renderStars(b.rating)}</td>
      <td><span style="font-family:'DM Mono',monospace">${b.avail_copies}/${b.total_copies}</span></td>
      <td>${b.avail_copies > 0
        ? '<span class="badge badge-available"><i class="fa-solid fa-circle" style="font-size:7px"></i>Available</span>'
        : '<span class="badge badge-unavailable"><i class="fa-solid fa-circle" style="font-size:7px"></i>Out</span>'}</td>
      <td><div class="actions">
        <button class="btn btn-ghost btn-xs" onclick="viewBook(${b.id})"><i class="fa-solid fa-eye"></i></button>
        <button class="btn btn-ghost btn-xs" onclick="editBook(${b.id})"><i class="fa-solid fa-pen"></i></button>
        <button class="btn btn-danger btn-xs" onclick="deleteBook(${b.id},'${escHtml(b.title)}')"><i class="fa-solid fa-trash"></i></button>
      </div></td>
    </tr>`).join('');
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

window.viewBook = async id => {
  try {
    const b = await apiFetch(`/api/books/${id}`);
    $('viewBookContent').innerHTML = `
      <div style="display:flex;gap:14px;align-items:flex-start;margin-bottom:18px">
        <div style="width:12px;flex-shrink:0;height:80px;border-radius:4px;background:${b.cover_color}"></div>
        <div>
          <h3 style="font-family:'Playfair Display',serif;font-size:20px;font-weight:700">${escHtml(b.title)}</h3>
          <p style="color:var(--text-sub);margin-top:4px">by ${escHtml(b.author)}</p>
        </div>
      </div>
      <div class="detail-meta">
        <div class="detail-field"><label>ISBN</label><span>${b.isbn||'—'}</span></div>
        <div class="detail-field"><label>Genre</label><span>${b.genre||'—'}</span></div>
        <div class="detail-field"><label>Publisher</label><span>${b.publisher||'—'}</span></div>
        <div class="detail-field"><label>Year</label><span>${b.year||'—'}</span></div>
        <div class="detail-field"><label>Rating</label><span>${renderStars(b.rating)}</span></div>
        <div class="detail-field"><label>Editions</label><span>${b.editions != null ? b.editions + ' edition(s)' : '—'}</span></div>
        <div class="detail-field"><label>Bestseller</label><span>${b.is_bestseller ? '<span style="color:#c9a84c;font-weight:600">★ Yes</span>' : 'No'}</span></div>
        <div class="detail-field"><label>Total Copies</label><span>${b.total_copies}</span></div>
        <div class="detail-field"><label>Available</label><span>${b.avail_copies}</span></div>
      </div>
      <div style="margin-top:12px">
        <a href="${b.wikipedia_url}" target="_blank" rel="noopener noreferrer"
           style="display:inline-flex;align-items:center;gap:6px;color:var(--gold);font-size:13px;text-decoration:none;border:1px solid rgba(212,168,67,.3);padding:5px 12px;border-radius:6px;transition:all .2s"
           onmouseover="this.style.background='rgba(212,168,67,.1)'" onmouseout="this.style.background='transparent'">
          <i class="fa-brands fa-wikipedia-w"></i> View Author on Wikipedia
        </a>
      </div>
      ${b.description ? `<p style="font-size:14px;color:var(--text-sub);line-height:1.7;margin-top:14px">${escHtml(b.description)}</p>` : ''}`;
    $('viewBookModal').classList.add('open');
  } catch { toast('Failed to load book details', 'error'); }
};

$('closeViewBookModal').addEventListener('click', () => $('viewBookModal').classList.remove('open'));

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

// Chat Bot
function sendMessage() {
    const input = document.getElementById("chatInput");
    const messages = document.getElementById("chatMessages");

    const userText = input.value.trim();
    if (!userText) return;

    // Add user message to chat
    const userDiv = document.createElement("div");
    userDiv.className = "message-user";
    userDiv.innerText = userText;
    messages.appendChild(userDiv);

    // Send message to Flask backend
    fetch("http://127.0.0.1:5000/chatbot", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            message: userText
        })
    })
    .then(response => response.json())
    .then(data => {
        const botDiv = document.createElement("div");
        botDiv.className = "message-bot";
        botDiv.innerText = data.response;
        messages.appendChild(botDiv);

        // Auto scroll
        messages.scrollTop = messages.scrollHeight;
    })
    .catch(error => {
        console.error("Error:", error);
    });

    input.value = "";
}

document.getElementById("chatInput").addEventListener("keypress", function(e) {
    if (e.key === "Enter") {
        sendMessage();
    }
});

function toggleChat() {
    const chat = document.querySelector(".chatbot-container");
    chat.style.display = chat.style.display === "none" ? "flex" : "none";
}
// ══════════════════════════════════════════════════════════
// BOOT
// ══════════════════════════════════════════════════════════
(async () => {
  await populateGenreFilter();
  navigate('dashboard');
})();
