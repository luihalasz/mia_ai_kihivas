// Shared site chrome: injects the black top menu bar and the footer into every page,
// so the menu is defined in exactly one place. Links resolve from the site root,
// which is derived from this script's own URL (works from /docs/ too).
(function () {
  // embedded (e.g. the configurator iframe on mia.html): no site chrome
  if (window.self !== window.top) { document.documentElement.classList.add('embedded'); return; }
  const ROOT = new URL('..', document.currentScript.src);
  const url = (p) => new URL(p, ROOT).href;

  // ---------- language: one choice for the whole site (shared with the configurator via 'mia_lang') ----------
  const LANGS = ['hu', 'en', 'it'];
  const STORE_KEY = 'mia_lang';
  let lang = 'hu';
  try { const l = localStorage.getItem(STORE_KEY); if (LANGS.includes(l)) lang = l; } catch (e) {}

  const caret ='<svg class="erd-caret" viewBox="0 0 10 10" aria-hidden="true"><path d="M1 3l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>';
  const cart = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 4h2l2.4 11h11l2-8H7" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><circle cx="9.5" cy="19.5" r="1.5"/><circle cx="17" cy="19.5" r="1.5"/></svg>';

  const MENU = [
    { label: 'Products', items: [
      { href: 'mia.html', label: 'Manyika 2 · MIA', note: 'Félig új koncepció · hamarosan' },
      { href: 'manyika.html', label: 'Manyika', note: 'Az első generáció · 2021–2026' },
    ]},
    { label: 'Accessories', items: [
      { href: 'accessories.html', label: 'Tasak és klipsz', note: 'Méretek, anyagok, behelyezés' },
    ]},
    { href: 'contacts.html', label: 'Contacts' },
    { href: 'career.html', label: 'Career' },
  ];

  const here = location.href.split(/[?#]/)[0].replace(/\/$/, '/index.html');
  const isHere = (href) => url(href) === here;
  const cur = (href) => isHere(href) ? ' aria-current="page"' : '';

  const menuHtml = MENU.map((m, i) => {
    if (!m.items) return `<li><a href="${url(m.href)}"${cur(m.href)}>${m.label}</a></li>`;
    const active = m.items.some((it) => isHere(it.href)) ? ' is-current' : '';
    const sub = m.items.map((it) =>
      `<li><a href="${url(it.href)}"${cur(it.href)}>${it.label}<small>${it.note}</small></a></li>`).join('');
    return `<li><button type="button" class="erd-dd${active}" aria-expanded="false" aria-controls="erd-sub-${i}">${m.label}${caret}</button>` +
           `<ul class="erd-sub" id="erd-sub-${i}">${sub}</ul></li>`;
  }).join('');

  const nav = document.createElement('header');
  nav.className = 'erd-nav';
  nav.innerHTML =
    `<div class="erd-nav__in">
      <a class="erd-brand" href="${url('index.html')}" aria-label="Equipment R&amp;D – főoldal">
        <img src="${url('assets/erd-logo.svg')}" alt=""><span><b>EQUIPMENT</b><i>R&amp;D</i></span>
      </a>
      <nav aria-label="Main" style="display:contents"><ul class="erd-menu">${menuHtml}</ul></nav>
      <a class="erd-store" href="${url('store.html')}"${cur('store.html')}>${cart}STORE</a>
      <div class="erd-lang" role="group" aria-label="Language">${LANGS.map((l) =>
        `<button type="button" data-lang="${l}" lang="${l}">${l.toUpperCase()}</button>`).join('')}</div>
      <button class="erd-burger" type="button" aria-label="Menü" aria-expanded="false">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="2"/></svg>
      </button>
    </div>`;
  document.body.prepend(nav);

  const closeAll = () => nav.querySelectorAll('.erd-menu li.open').forEach((o) => {
    o.classList.remove('open'); o.firstElementChild.setAttribute('aria-expanded', 'false');
  });
  // dropdowns: click/tap toggles (hover handled in CSS on desktop)
  nav.querySelectorAll('.erd-dd').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const li = btn.parentElement, open = !li.classList.contains('open');
      closeAll();
      li.classList.toggle('open', open);
      btn.setAttribute('aria-expanded', String(open));
    });
  });
  document.addEventListener('click', closeAll);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { closeAll(); nav.classList.remove('menu-open'); } });

  const burger = nav.querySelector('.erd-burger');
  burger.addEventListener('click', (e) => {
    e.stopPropagation();
    burger.setAttribute('aria-expanded', String(nav.classList.toggle('menu-open')));
  });

  const footerWanted = !document.documentElement.hasAttribute('data-no-footer');
  if (footerWanted) {
    const foot = document.createElement('footer');
    foot.className = 'erd-foot';
    foot.innerHTML =
      `<div class="erd-foot__in">
        <span>© 2026 Polinvent · Equipment R&amp;D · MIA (Manyika 2) koncepció</span>
        <nav aria-label="Footer"><a href="https://github.com/luihalasz/mia_ai_kihivas">GitHub</a><a href="${url('docs/naplo.html')}">Napló</a><a href="${url('configurator.html')}">Konfigurátor</a></nav>
      </div>`;
    document.body.append(foot);
  }

  // ---------- translation ----------
  // Text nodes and a few attributes are looked up in window.ERD_I18N by their original
  // (whitespace-collapsed) text; the original is remembered so switching back always works.
  const DICT = window.ERD_I18N || {};
  const norm = (s) => s.replace(/\s+/g, ' ').trim();
  const pick = (orig) => { const e = DICT[norm(orig)]; return (e && e[lang]) || null; };
  const origText = new WeakMap();
  const ATTRS = ['alt', 'title', 'aria-label', 'placeholder'];
  // pages with their own dictionary (the configurator) only get the site chrome translated
  const scopes = () => document.documentElement.hasAttribute('data-own-i18n')
    ? [nav] : [document.body];

  function translateTree(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: (n) => (n.parentElement && /^(SCRIPT|STYLE)$/.test(n.parentElement.tagName)) || !n.nodeValue.trim()
        ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
    for (let n; (n = walker.nextNode());) {
      if (!origText.has(n)) origText.set(n, n.nodeValue);
      const o = origText.get(n), t = pick(o);
      const lead = o.match(/^\s*/)[0], trail = o.match(/\s*$/)[0];
      n.nodeValue = t ? lead + t + trail : o;
    }
    root.querySelectorAll('[alt],[title],[aria-label],[placeholder]').forEach((el) => {
      ATTRS.forEach((a) => {
        if (!el.hasAttribute(a)) return;
        const key = 'data-i18n-orig-' + a;
        if (!el.hasAttribute(key)) el.setAttribute(key, el.getAttribute(a));
        const o = el.getAttribute(key);
        el.setAttribute(a, pick(o) || o);
      });
    });
  }

  if (!document.documentElement.hasAttribute('data-i18n-title')) document.documentElement.setAttribute('data-i18n-title', document.title);

  // keep embedded/same-page configurators in step (they read the same 'mia_lang' on load)
  function syncConfigurators() {
    const docs = [document];
    document.querySelectorAll('iframe').forEach((f) => { try { if (f.contentDocument) docs.push(f.contentDocument); } catch (e) {} });
    docs.forEach((d) => {
      const sel = d.getElementById('lang');
      if (sel && sel.tagName === 'SELECT' && sel.value !== lang) {
        sel.value = lang;
        sel.dispatchEvent(new Event('change'));
      }
    });
  }

  function setLang(l, save) {
    lang = l;
    if (save) { try { localStorage.setItem(STORE_KEY, l); } catch (e) {} }
    document.documentElement.lang = l;
    scopes().forEach(translateTree);
    if (footerWanted) translateTree(document.querySelector('.erd-foot'));
    const t = document.documentElement.getAttribute('data-i18n-title');
    if (!document.documentElement.hasAttribute('data-own-i18n')) document.title = pick(t) || t;
    nav.querySelectorAll('.erd-lang button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.lang === l)));
    syncConfigurators();
    // links with per-language targets: <a href="x.md" data-href-en="x.en.md" data-href-it="x.it.md">
    document.querySelectorAll('[data-href-en],[data-href-it]').forEach((a) => {
      if (!a.hasAttribute('data-href-hu')) a.setAttribute('data-href-hu', a.getAttribute('href'));
      a.setAttribute('href', a.getAttribute('data-href-' + l) || a.getAttribute('data-href-hu'));
    });
    // pages with their own per-language content (e.g. the work log) listen for this
    document.dispatchEvent(new CustomEvent('erd:lang', { detail: l }));
  }

  nav.querySelectorAll('.erd-lang button').forEach((b) =>
    b.addEventListener('click', (e) => { e.stopPropagation(); setLang(b.dataset.lang, true); }));
  // another tab changed the language
  window.addEventListener('storage', (e) => { if (e.key === STORE_KEY && LANGS.includes(e.newValue)) setLang(e.newValue, false); });
  setLang(lang, false);
})();
