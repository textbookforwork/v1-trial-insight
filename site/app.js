(() => {
  'use strict';

  const PERSPECTIVE_LABEL = { student: '學生視角', teacher: '老師視角' };

  // ----- DOM refs -----
  const els = {
    search: document.getElementById('search'),
    searchClear: document.getElementById('search-clear'),
    categoryChips: document.getElementById('category-chips'),
    perspectiveChips: document.querySelector('[data-group="perspective"]'),
    emptyState: document.getElementById('empty-state'),
    results: document.getElementById('results'),
    summary: document.getElementById('results-summary'),
    list: document.getElementById('card-list'),
    overview: document.getElementById('category-overview'),
    overviewSummary: document.getElementById('overview-summary'),
    overviewList: document.getElementById('overview-list'),
    insights: document.getElementById('insights'),
    panel: document.getElementById('panel'),
    panelBody: document.getElementById('panel-body'),
    panelBack: document.getElementById('panel-back'),
    panelClose: document.getElementById('panel-close'),
    panelScrim: document.getElementById('panel-scrim'),
    metaCounts: document.getElementById('meta-counts'),
    metaDate: document.getElementById('meta-date'),
  };

  // ----- State -----
  const state = {
    data: null,
    cardsById: new Map(),
    fuse: null,
    query: '',
    perspective: 'all',
    category: null,    // "<perspective>:<code>" or null
    panelStack: [],
  };

  // ----- DOM helpers -----
  function h(tag, props, ...children) {
    const el = document.createElement(tag);
    if (props) {
      for (const k of Object.keys(props)) {
        const v = props[k];
        if (v == null || v === false) continue;
        if (k === 'class') el.className = v;
        else if (k === 'dataset') Object.assign(el.dataset, v);
        else if (k === 'onClick') el.addEventListener('click', v);
        else if (k === 'hidden' && v) el.hidden = true;
        else el.setAttribute(k, v === true ? '' : v);
      }
    }
    appendChildren(el, children);
    return el;
  }

  function appendChildren(parent, children) {
    for (const ch of children) {
      if (ch == null || ch === false) continue;
      if (Array.isArray(ch)) appendChildren(parent, ch);
      else if (typeof ch === 'string' || typeof ch === 'number') {
        parent.appendChild(document.createTextNode(String(ch)));
      } else {
        parent.appendChild(ch);
      }
    }
  }

  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  // ----- Init -----
  init();

  async function init() {
    try {
      const res = await fetch('data.json', { cache: 'no-cache' });
      state.data = await res.json();
    } catch (err) {
      clear(els.list);
      els.list.appendChild(h('div', { class: 'no-results' }, '無法載入資料：', String(err)));
      showResults();
      return;
    }

    state.data.cards.forEach((c) => state.cardsById.set(c.id, c));

    state.fuse = new Fuse(state.data.cards, {
      includeMatches: true,
      includeScore: true,
      threshold: 0.35,
      ignoreLocation: true,
      minMatchCharLength: 2,
      keys: [
        { name: 'title', weight: 3 },
        { name: 'code', weight: 2.5 },
        { name: 'problem', weight: 1 },
        { name: 'observation', weight: 0.8 },
        { name: 'categoryName', weight: 0.6 },
      ],
    });

    renderMeta();
    renderCategoryChips();
    bindEvents();
    syncFromHash();
  }

  // ----- Header meta -----
  function renderMeta() {
    const { counts, generatedAt } = state.data;
    els.metaCounts.textContent = `${counts.total} 項需求（學生 ${counts.student} ／ 老師 ${counts.teacher}）`;
    els.metaDate.textContent = `更新 ${generatedAt}`;
  }

  // ----- Category chips -----
  function renderCategoryChips() {
    clear(els.categoryChips);
    const persp = state.perspective;
    if (persp === 'all' || persp === 'insights') {
      els.categoryChips.hidden = true;
      return;
    }
    els.categoryChips.hidden = false;

    const cats = state.data.categories[persp].map((c) => ({ perspective: persp, ...c }));
    for (const c of cats) {
      const id = `${c.perspective}:${c.code}`;
      const active = state.category === id;
      const btn = h(
        'button',
        {
          class: 'chip' + (active ? ' is-active' : ''),
          dataset: { category: id },
          type: 'button',
        }
      );
      btn.appendChild(document.createTextNode(c.code));
      btn.appendChild(h('span', { class: 'chip-count' }, String(c.count)));
      els.categoryChips.appendChild(btn);
    }
  }

  // ----- Events -----
  function bindEvents() {
    let searchTimer;
    els.search.addEventListener('input', (e) => {
      clearTimeout(searchTimer);
      const v = e.target.value;
      els.searchClear.hidden = !v;
      searchTimer = setTimeout(() => {
        state.query = v.trim();
        render();
      }, 80);
    });

    els.searchClear.addEventListener('click', () => {
      els.search.value = '';
      els.searchClear.hidden = true;
      state.query = '';
      render();
      els.search.focus();
    });

    els.perspectiveChips.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-perspective]');
      if (!btn) return;
      const v = btn.dataset.perspective;
      if (v === state.perspective) {
        // Same perspective re-click: clear category to return to overview
        if (state.category) {
          state.category = null;
          renderCategoryChips();
          render();
        }
        return;
      }
      state.perspective = v;
      if (state.category && v !== 'all') {
        const [p] = state.category.split(':');
        if (p !== v) state.category = null;
      }
      for (const b of els.perspectiveChips.querySelectorAll('.chip')) {
        b.classList.toggle('is-active', b.dataset.perspective === v);
      }
      renderCategoryChips();
      render();
    });

    els.categoryChips.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-category]');
      if (!btn) return;
      const id = btn.dataset.category;
      state.category = state.category === id ? null : id;
      for (const b of els.categoryChips.querySelectorAll('.chip')) {
        b.classList.toggle('is-active', b.dataset.category === state.category);
      }
      render();
    });

    els.list.addEventListener('click', (e) => {
      const card = e.target.closest('[data-card-id]');
      if (!card) return;
      openCard(card.dataset.cardId, { resetStack: true });
    });

    els.insights.addEventListener('click', (e) => {
      const tag = e.target.closest('.ref-tag');
      if (!tag) return;
      e.preventDefault();
      const id = `${tag.dataset.perspective}-${tag.dataset.code}`;
      if (state.cardsById.has(id)) {
        openCard(id, { resetStack: true });
      }
    });

    for (const hint of document.querySelectorAll('.hint')) {
      hint.addEventListener('click', () => {
        els.search.value = hint.dataset.q;
        els.searchClear.hidden = false;
        state.query = hint.dataset.q;
        render();
        els.search.focus();
      });
    }

    els.panelBack.addEventListener('click', () => {
      if (state.panelStack.length > 1) {
        state.panelStack.pop();
        const prev = state.panelStack[state.panelStack.length - 1];
        renderPanel(prev);
      }
    });

    els.panelClose.addEventListener('click', closePanel);
    els.panelScrim.addEventListener('click', closePanel);

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !els.panel.hidden) closePanel();
      if (e.key === '/' && document.activeElement !== els.search) {
        e.preventDefault();
        els.search.focus();
      }
    });

    window.addEventListener('hashchange', syncFromHash);
  }

  // ----- Main render -----
  function render() {
    const hasQuery = !!state.query;
    const hasPerspective = state.perspective !== 'all';
    const hasCategory = !!state.category;

    if (state.perspective === 'insights') {
      if (hasQuery) {
        // 搜尋時自動跳回「全部」視角，否則搜尋輸入會看似沒有效果
        state.perspective = 'all';
        for (const b of els.perspectiveChips.querySelectorAll('.chip')) {
          b.classList.toggle('is-active', b.dataset.perspective === 'all');
        }
        renderCategoryChips();
      } else {
        showInsights();
        return;
      }
    }

    if (!hasQuery && !hasPerspective && !hasCategory) {
      showEmpty();
      return;
    }

    if (!hasQuery && hasPerspective && !hasCategory) {
      showCategoryOverview();
      return;
    }

    let cards = state.data.cards;

    if (state.perspective !== 'all') {
      cards = cards.filter((c) => c.perspective === state.perspective);
    }
    if (state.category) {
      const [catPersp, catCode] = state.category.split(':');
      cards = cards.filter((c) => c.perspective === catPersp && c.category === catCode);
    }

    if (hasQuery) {
      // 代碼型 query：精確比對，避開 Fuse 對短代碼把 J 跟 .8 拆開命中的雜訊
      //   "J.8" / "j8" / "j.8"  → 該卡片
      //   "J"   / "j."          → 整個 J 大項
      const upper = state.query.toUpperCase();
      const codeMatch = upper.match(/^([A-Z])\.?(\d+)$/);
      const categoryMatch = upper.match(/^([A-Z])\.?$/);
      if (codeMatch) {
        const code = `${codeMatch[1]}.${codeMatch[2]}`;
        cards = cards.filter((c) => c.code === code);
      } else if (categoryMatch) {
        const cat = categoryMatch[1];
        cards = cards.filter((c) => c.category === cat);
      } else {
        const ids = new Set(cards.map((c) => c.id));
        const fuseResults = state.fuse.search(state.query).filter((r) => ids.has(r.item.id));
        cards = fuseResults.map((r) => r.item);
      }
    }

    renderList(cards);
    showResults();
    renderSummary(cards.length);
  }

  function renderSummary(count) {
    const parts = [];
    parts.push(`${count} 項`);
    if (state.query) parts.push(`符合「${state.query}」`);
    if (state.perspective !== 'all') parts.push(PERSPECTIVE_LABEL[state.perspective]);
    if (state.category) {
      const [p, code] = state.category.split(':');
      const cat = state.data.categories[p].find((c) => c.code === code);
      const name = cat ? cat.name : '';
      parts.push(`${p === 'student' ? '生' : '師'}·${code}${name ? ' ' + name : ''}`);
    }
    els.summary.textContent = parts.join(' · ');
  }

  function renderList(cards) {
    clear(els.list);
    if (!cards.length) {
      els.list.appendChild(h('div', { class: 'no-results' }, '沒有找到符合條件的需求'));
      return;
    }
    const frag = document.createDocumentFragment();
    for (const c of cards) frag.appendChild(buildCard(c));
    els.list.appendChild(frag);
  }

  function buildCard(c) {
    return h(
      'button',
      {
        type: 'button',
        class: 'card',
        dataset: { cardId: c.id },
      },
      h('div', { class: 'card-head' },
        h('span', { class: `badge badge-${c.perspective}` }, PERSPECTIVE_LABEL[c.perspective]),
        h('span', { class: 'card-code' }, c.code)
      ),
      buildHighlighted('div', 'card-title', c.title)
    );
  }

  function buildHighlighted(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;
    appendHighlighted(node, text, state.query);
    return node;
  }

  function appendHighlighted(parent, text, query) {
    if (!text) return;
    const tokens = (query || '').split(/\s+/).filter((t) => t.length >= 2);
    if (!tokens.length) {
      parent.appendChild(document.createTextNode(text));
      return;
    }
    const escaped = tokens.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    const re = new RegExp(`(${escaped.join('|')})`, 'gi');
    let lastIdx = 0;
    for (const m of text.matchAll(re)) {
      if (m.index > lastIdx) {
        parent.appendChild(document.createTextNode(text.slice(lastIdx, m.index)));
      }
      const mark = document.createElement('mark');
      mark.textContent = m[0];
      parent.appendChild(mark);
      lastIdx = m.index + m[0].length;
    }
    if (lastIdx < text.length) {
      parent.appendChild(document.createTextNode(text.slice(lastIdx)));
    }
  }

  function showEmpty() {
    els.results.hidden = true;
    els.overview.hidden = true;
    els.insights.hidden = true;
    els.emptyState.hidden = false;
    syncHashFromState();
  }

  function showResults() {
    els.emptyState.hidden = true;
    els.overview.hidden = true;
    els.insights.hidden = true;
    els.results.hidden = false;
    syncHashFromState();
  }

  function showCategoryOverview() {
    els.emptyState.hidden = true;
    els.results.hidden = true;
    els.insights.hidden = true;
    els.overview.hidden = false;
    renderCategoryOverview();
    syncHashFromState();
  }

  function showInsights() {
    if (!els.panel.hidden) closePanel();
    els.emptyState.hidden = true;
    els.results.hidden = true;
    els.overview.hidden = true;
    els.insights.hidden = false;
    if (!els.insights.dataset.rendered) {
      els.insights.innerHTML = state.data.insightsHtml || '<p class="no-results">尚未產生跨視角洞察內容</p>';
      els.insights.dataset.rendered = '1';
    }
    window.scrollTo({ top: 0 });
    syncHashFromState();
  }

  function renderCategoryOverview() {
    const persp = state.perspective;
    const cats = state.data.categories[persp];
    const total = cats.reduce((sum, c) => sum + c.count, 0);
    els.overviewSummary.textContent = `${PERSPECTIVE_LABEL[persp]} · ${cats.length} 個主題 · ${total} 項需求`;

    clear(els.overviewList);
    els.overviewList.style.gridTemplateRows = `repeat(${Math.ceil(cats.length / 2)}, auto)`;
    const frag = document.createDocumentFragment();
    for (const c of cats) {
      const id = `${persp}:${c.code}`;
      frag.appendChild(
        h(
          'button',
          {
            type: 'button',
            class: 'overview-item',
            dataset: { category: id },
            onClick: () => {
              state.category = id;
              renderCategoryChips();
              render();
              window.scrollTo({ top: 0 });
            },
          },
          h('span', { class: 'overview-code' }, c.code),
          h('span', { class: 'overview-name' }, c.name),
          h('span', { class: 'overview-count' }, `${c.count} 項`)
        )
      );
    }
    els.overviewList.appendChild(frag);
  }

  // ----- Panel -----
  function openCard(id, { resetStack = false } = {}) {
    if (resetStack) state.panelStack = [];
    if (state.panelStack[state.panelStack.length - 1] !== id) {
      state.panelStack.push(id);
    }
    renderPanel(id);
  }

  function renderPanel(id) {
    const c = state.cardsById.get(id);
    if (!c) return;

    for (const el of els.list.querySelectorAll('.card.is-open')) el.classList.remove('is-open');
    const listEl = els.list.querySelector(`[data-card-id="${id}"]`);
    if (listEl) listEl.classList.add('is-open');

    const regular = c.relations.filter((r) => !r.conflict);
    const conflict = c.relations.filter((r) => r.conflict);

    clear(els.panelBody);
    const sections = [];

    sections.push(
      h('div', { class: 'panel-meta' },
        h('span', { class: `badge badge-${c.perspective}` }, PERSPECTIVE_LABEL[c.perspective]),
        h('span', { class: 'card-code' }, c.code),
        h('span', { class: 'card-cat' }, c.categoryName)
      )
    );
    sections.push(h('h2', { class: 'panel-title' }, c.title));

    sections.push(
      h('section', { class: 'panel-section' },
        h('p', { class: 'panel-label' }, '問題'),
        h('div', { class: 'panel-problem' }, c.problem)
      )
    );

    if (c.observation) {
      sections.push(
        h('section', { class: 'panel-section' },
          h('div', { class: 'panel-observation' },
            h('span', { class: 'obs-label' }, '觀察'),
            c.observation
          )
        )
      );
    }

    if (c.relations.length) {
      const relSection = h('section', { class: 'panel-section panel-section--relations' },
        h('p', { class: 'panel-label' }, '跨視角關聯')
      );
      if (regular.length) relSection.appendChild(buildRelationGroup(regular, false));
      if (conflict.length) relSection.appendChild(buildRelationGroup(conflict, true));
      sections.push(relSection);
    }

    appendChildren(els.panelBody, sections);

    els.panelBack.hidden = state.panelStack.length <= 1;
    els.panel.hidden = false;
    els.panel.setAttribute('aria-hidden', 'false');
    els.panelScrim.hidden = false;
    els.panelBody.scrollTop = 0;
    syncHashFromState();
  }

  function buildRelationGroup(rels, isConflict) {
    const label = isConflict ? '視角衝突／對立' : '相關';
    const ul = h('ul', { class: 'relation-list' });
    for (const r of rels) {
      const targetId = `${r.perspective}-${r.code}`;
      const exists = state.cardsById.has(targetId);
      const codeEl = h('span', { class: 'rel-code' }, r.code);
      let link;
      if (exists) {
        link = h(
          'button',
          {
            type: 'button',
            class: 'relation-link',
            dataset: { relId: targetId, perspective: r.perspective },
            onClick: () => openCard(targetId),
          },
          codeEl, h('span', null, r.title || '')
        );
      } else {
        link = h(
          'span',
          {
            class: 'relation-link',
            dataset: { perspective: r.perspective },
            style: 'cursor:default;opacity:0.6;',
          },
          codeEl, h('span', null, `${r.title || ''}（找不到對應卡片）`)
        );
      }
      ul.appendChild(h('li', null, link));
    }
    return h(
      'div',
      { class: 'relation-group' },
      h('div', { class: 'relation-group-label' + (isConflict ? ' is-conflict' : '') }, label),
      ul
    );
  }

  function closePanel() {
    els.panel.hidden = true;
    els.panel.setAttribute('aria-hidden', 'true');
    els.panelScrim.hidden = true;
    state.panelStack = [];
    for (const el of els.list.querySelectorAll('.card.is-open')) el.classList.remove('is-open');
    syncHashFromState();
  }

  // ----- URL hash sync -----
  function syncHashFromState() {
    const params = new URLSearchParams();
    if (state.query) params.set('q', state.query);
    if (state.perspective !== 'all') params.set('p', state.perspective);
    if (state.category) params.set('c', state.category);
    const open = state.panelStack[state.panelStack.length - 1];
    if (open) params.set('open', open);
    const hash = '#/' + (params.toString() ? '?' + params.toString() : '');
    if (location.hash !== hash) {
      history.replaceState(null, '', hash);
    }
  }

  function syncFromHash() {
    const raw = location.hash.replace(/^#\/?/, '');
    const qs = raw.startsWith('?') ? raw.slice(1) : raw;
    const params = new URLSearchParams(qs);
    state.query = params.get('q') || '';
    state.perspective = params.get('p') || 'all';
    state.category = params.get('c') || null;

    els.search.value = state.query;
    els.searchClear.hidden = !state.query;
    for (const b of els.perspectiveChips.querySelectorAll('.chip')) {
      b.classList.toggle('is-active', b.dataset.perspective === state.perspective);
    }
    renderCategoryChips();
    render();

    const open = params.get('open');
    if (open && state.cardsById.has(open)) {
      openCard(open, { resetStack: true });
    } else if (!els.panel.hidden) {
      closePanel();
    }
  }

  // ----- Utilities -----
  function truncate(s, n) {
    if (!s) return '';
    return s.length > n ? s.slice(0, n) + '…' : s;
  }
})();
