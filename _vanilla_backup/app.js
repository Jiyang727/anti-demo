/**
 * AI Pulse — Dashboard Application Logic
 * Handles feed loading, filtering, searching, saving, and rendering.
 */

// ═══════════════════════════════════════════════════════════
// State
// ═══════════════════════════════════════════════════════════

const state = {
    articles: [],
    savedIds: new Set(),
    activeSource: 'all',
    searchQuery: '',
    feedMeta: null,
};

const STORAGE_KEY = 'ai-pulse-saved';
const FEED_PATH = '.tmp/feed.json';

// ═══════════════════════════════════════════════════════════
// DOM References
// ═══════════════════════════════════════════════════════════

const $ = (id) => document.getElementById(id);

const dom = {
    grid: $('article-grid'),
    loading: $('loading-state'),
    empty: $('empty-state'),
    searchInput: $('search-input'),
    btnRefresh: $('btn-refresh'),
    statTotal: $('stat-total'),
    statSaved: $('stat-saved'),
    statUpdated: $('stat-updated'),
    countAll: $('count-all'),
    countBens: $('count-bens'),
    countRundown: $('count-rundown'),
    countSaved: $('count-saved'),
    toastContainer: $('toast-container'),
    filterTabs: $('filter-tabs'),
};


// ═══════════════════════════════════════════════════════════
// Data Loading
// ═══════════════════════════════════════════════════════════

async function loadFeed() {
    try {
        showLoading(true);
        const resp = await fetch(FEED_PATH);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        state.articles = data.articles || [];
        state.feedMeta = {
            generatedAt: data.generatedAt,
            totalArticles: data.totalArticles,
            sources: data.sources,
        };

        loadSavedIds();
        updateStats();
        updateCounts();
        renderArticles();
        showLoading(false);

        showToast('✨', `Loaded ${state.articles.length} articles`);
    } catch (err) {
        console.error('Failed to load feed:', err);
        showLoading(false);
        showEmpty(true);
        showToast('⚠️', 'Failed to load feed — run scrapers first');
    }
}


// ═══════════════════════════════════════════════════════════
// Persistence (localStorage)
// ═══════════════════════════════════════════════════════════

function loadSavedIds() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) {
            const parsed = JSON.parse(raw);
            state.savedIds = new Set(parsed.map(s => s.articleId));
        }
    } catch (e) {
        console.warn('Failed to load saved articles:', e);
    }
}

function saveToPersistence(articleId, source) {
    const savedList = getSavedList();
    if (!savedList.find(s => s.articleId === articleId)) {
        savedList.push({
            articleId,
            savedAt: new Date().toISOString(),
            source,
        });
        localStorage.setItem(STORAGE_KEY, JSON.stringify(savedList));
    }
}

function removeFromPersistence(articleId) {
    const savedList = getSavedList().filter(s => s.articleId !== articleId);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(savedList));
}

function getSavedList() {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    } catch {
        return [];
    }
}


// ═══════════════════════════════════════════════════════════
// Filtering & Searching
// ═══════════════════════════════════════════════════════════

function getFilteredArticles() {
    let articles = [...state.articles];

    // Source filter
    if (state.activeSource === 'saved') {
        articles = articles.filter(a => state.savedIds.has(a.id));
    } else if (state.activeSource !== 'all') {
        articles = articles.filter(a => a.source === state.activeSource);
    }

    // Search filter
    if (state.searchQuery) {
        const q = state.searchQuery.toLowerCase();
        articles = articles.filter(a =>
            (a.title || '').toLowerCase().includes(q) ||
            (a.subtitle || '').toLowerCase().includes(q) ||
            (a.summary || '').toLowerCase().includes(q) ||
            (a.author || '').toLowerCase().includes(q)
        );
    }

    return articles;
}


// ═══════════════════════════════════════════════════════════
// Rendering
// ═══════════════════════════════════════════════════════════

function renderArticles() {
    const articles = getFilteredArticles();

    if (articles.length === 0) {
        dom.grid.classList.add('hidden');
        showEmpty(true);
        return;
    }

    showEmpty(false);
    dom.grid.classList.remove('hidden');
    dom.grid.innerHTML = articles.map((article, i) => createCardHTML(article, i)).join('');

    // Attach event listeners
    dom.grid.querySelectorAll('.btn-save').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleSave(btn.dataset.id, btn.dataset.source);
        });
    });

    dom.grid.querySelectorAll('.article-card').forEach(card => {
        card.addEventListener('click', (e) => {
            // Don't navigate if clicking action buttons
            if (e.target.closest('.card-actions')) return;
            const url = card.dataset.url;
            if (url) window.open(url, '_blank', 'noopener');
        });
    });
}

function createCardHTML(article, index) {
    const isSaved = state.savedIds.has(article.id);
    const sourceLabel = getSourceLabel(article.source);
    const dateStr = formatDate(article.date);
    const delay = Math.min(index * 0.05, 0.5);

    const imageHTML = article.imageUrl
        ? `<div class="card-image"><img src="${escapeHTML(article.imageUrl)}" alt="" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\\'card-image-placeholder\\'><svg width=\\'40\\' height=\\'40\\' viewBox=\\'0 0 24 24\\' fill=\\'none\\' stroke=\\'currentColor\\' stroke-width=\\'1\\'><path d=\\'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z\\'/><polyline points=\\'14 2 14 8 20 8\\'/></svg></div>'"></div>`
        : `<div class="card-image"><div class="card-image-placeholder"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div></div>`;

    const subtitleHTML = article.subtitle
        ? `<p class="card-subtitle">${escapeHTML(article.subtitle)}</p>`
        : '';

    const summaryHTML = article.summary
        ? `<p class="card-summary">${escapeHTML(article.summary)}</p>`
        : '';

    return `
        <article class="article-card" data-url="${escapeHTML(article.url)}" style="animation-delay: ${delay}s" data-id="${article.id}">
            ${imageHTML}
            <div class="card-body">
                <div class="card-meta">
                    <span class="card-source-badge badge-${article.source}">${sourceLabel}</span>
                    <span class="card-date">${dateStr}</span>
                </div>
                <h2 class="card-title">${escapeHTML(article.title)}</h2>
                ${subtitleHTML}
                ${summaryHTML}
            </div>
            <div class="card-footer">
                <span class="card-author">${escapeHTML(article.author || 'Unknown')}</span>
                <div class="card-actions">
                    <button class="btn-save ${isSaved ? 'saved' : ''}" data-id="${article.id}" data-source="${article.source}" aria-label="${isSaved ? 'Unsave' : 'Save'} article" title="${isSaved ? 'Unsave' : 'Save'}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="${isSaved ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
                        </svg>
                    </button>
                    <a class="btn-open" href="${escapeHTML(article.url)}" target="_blank" rel="noopener" aria-label="Open article" title="Open in new tab" onclick="event.stopPropagation()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                            <polyline points="15 3 21 3 21 9"/>
                            <line x1="10" y1="14" x2="21" y2="3"/>
                        </svg>
                    </a>
                </div>
            </div>
        </article>
    `;
}


// ═══════════════════════════════════════════════════════════
// Actions
// ═══════════════════════════════════════════════════════════

function toggleSave(articleId, source) {
    if (state.savedIds.has(articleId)) {
        state.savedIds.delete(articleId);
        removeFromPersistence(articleId);
        showToast('🔖', 'Article removed from saved');
    } else {
        state.savedIds.add(articleId);
        saveToPersistence(articleId, source);
        showToast('⭐', 'Article saved!');
    }

    updateStats();
    updateCounts();
    renderArticles();
}

function setActiveSource(source) {
    state.activeSource = source;

    // Update tab styles
    dom.filterTabs.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.source === source);
    });

    renderArticles();
}


// ═══════════════════════════════════════════════════════════
// UI Helpers
// ═══════════════════════════════════════════════════════════

function showLoading(show) {
    dom.loading.classList.toggle('hidden', !show);
    if (show) {
        dom.grid.classList.add('hidden');
        dom.empty.classList.add('hidden');
    }
}

function showEmpty(show) {
    dom.empty.classList.toggle('hidden', !show);
}

function updateStats() {
    dom.statTotal.textContent = state.articles.length;
    dom.statSaved.textContent = state.savedIds.size;

    if (state.feedMeta?.generatedAt) {
        dom.statUpdated.textContent = formatRelativeTime(state.feedMeta.generatedAt);
    }
}

function updateCounts() {
    const all = state.articles.length;
    const bens = state.articles.filter(a => a.source === 'bens_bites').length;
    const rundown = state.articles.filter(a => a.source === 'the_rundown').length;
    const saved = state.articles.filter(a => state.savedIds.has(a.id)).length;

    dom.countAll.textContent = all;
    dom.countBens.textContent = bens;
    dom.countRundown.textContent = rundown;
    dom.countSaved.textContent = saved;
}


// ═══════════════════════════════════════════════════════════
// Toast System
// ═══════════════════════════════════════════════════════════

function showToast(icon, message, duration = 2500) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<span class="toast-icon">${icon}</span><span>${escapeHTML(message)}</span>`;
    dom.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('toast-exit');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}


// ═══════════════════════════════════════════════════════════
// Formatting Helpers
// ═══════════════════════════════════════════════════════════

function getSourceLabel(source) {
    const labels = {
        bens_bites: "Ben's Bites",
        the_rundown: 'The Rundown',
        reddit: 'Reddit',
    };
    return labels[source] || source;
}

function formatDate(dateStr) {
    if (!dateStr) return 'Unknown date';
    try {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return 'Unknown date';

        const now = new Date();
        const diffMs = now - date;
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        if (diffHours < 1) return 'Just now';
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;

        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
        });
    } catch {
        return 'Unknown date';
    }
}

function formatRelativeTime(isoStr) {
    try {
        const date = new Date(isoStr);
        const now = new Date();
        const diffMin = Math.floor((now - date) / (1000 * 60));

        if (diffMin < 1) return 'Just now';
        if (diffMin < 60) return `${diffMin}m ago`;
        const diffH = Math.floor(diffMin / 60);
        if (diffH < 24) return `${diffH}h ago`;
        return `${Math.floor(diffH / 24)}d ago`;
    } catch {
        return '—';
    }
}

function escapeHTML(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}


// ═══════════════════════════════════════════════════════════
// Event Listeners
// ═══════════════════════════════════════════════════════════

// Search
let searchTimeout;
dom.searchInput.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        state.searchQuery = dom.searchInput.value.trim();
        renderArticles();
    }, 250);
});

// Filter tabs
dom.filterTabs.addEventListener('click', (e) => {
    const tab = e.target.closest('.tab');
    if (tab) {
        setActiveSource(tab.dataset.source);
    }
});

// Refresh button
dom.btnRefresh.addEventListener('click', () => {
    dom.btnRefresh.classList.add('spinning');
    loadFeed().finally(() => {
        setTimeout(() => dom.btnRefresh.classList.remove('spinning'), 600);
    });
});

// Keyboard shortcut: Escape to clear search
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && dom.searchInput === document.activeElement) {
        dom.searchInput.value = '';
        state.searchQuery = '';
        renderArticles();
        dom.searchInput.blur();
    }
    // Cmd/Ctrl + K to focus search
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        dom.searchInput.focus();
    }
});


// ═══════════════════════════════════════════════════════════
// Init
// ═══════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    loadFeed();
});
