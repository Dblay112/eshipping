/* ── CMC Navbar — Dropdowns, Hamburger, Scroll, SD Search ─── */
(function () {
    'use strict';

    const DELAY = 200;

    function makeHoverDropdown(wrapId, btnId, menuId) {
        const wrap = document.getElementById(wrapId);
        const btn  = document.getElementById(btnId);
        const menu = document.getElementById(menuId);
        if (!wrap || !btn || !menu) return;
        let timer = null;

        const open  = () => { clearTimeout(timer); menu.classList.add('open'); btn.setAttribute('aria-expanded', 'true'); };
        const close = () => { timer = setTimeout(() => { menu.classList.remove('open'); btn.setAttribute('aria-expanded', 'false'); }, DELAY); };
        const force = () => { clearTimeout(timer); menu.classList.remove('open'); btn.setAttribute('aria-expanded', 'false'); };
        const toggle= () => menu.classList.contains('open') ? force() : open();

        wrap.addEventListener('mouseenter', () => { if (window.innerWidth >= 992) open(); });
        wrap.addEventListener('mouseleave', () => { if (window.innerWidth >= 992) close(); });
        menu.addEventListener('mouseenter', () => { if (window.innerWidth >= 992) clearTimeout(timer); });
        menu.addEventListener('mouseleave', () => { if (window.innerWidth >= 992) close(); });
        btn.addEventListener('click', e => { e.stopPropagation(); toggle(); });
        document.addEventListener('click', e => { if (!wrap.contains(e.target)) force(); });
    }

    makeHoverDropdown('opsDropdownWrap',   'opsDropdownBtn',   'opsDropdownMenu');
    makeHoverDropdown('tallyDropdownWrap', 'tallyDropdownBtn', 'tallyDropdownMenu');
    makeHoverDropdown('schedDropdownWrap', 'schedDropdownBtn', 'schedDropdownMenu');
    makeHoverDropdown('ebookDropdownWrap', 'ebookDropdownBtn', 'ebookDropdownMenu');
    makeHoverDropdown('declDropdownWrap',  'declDropdownBtn',  'declDropdownMenu');
    makeHoverDropdown('evacDropdownWrap',  'evacDropdownBtn',  'evacDropdownMenu');
    makeHoverDropdown('userDropdownWrap',  'userDropdownBtn',  'userDropdownMenu');

    /* ── Hamburger ─────────────────────────────────────────── */
    const hamburger  = document.getElementById('cmcHamburger');
    const mobileMenu = document.getElementById('cmcMobileMenu');
    const nav        = document.getElementById('cmcNav');
    if (hamburger) {
        hamburger.addEventListener('click', () => {
            const isOpen = mobileMenu.classList.toggle('open');
            hamburger.classList.toggle('open', isOpen);
            hamburger.setAttribute('aria-expanded', String(isOpen));
            nav.classList.toggle('mobile-open', isOpen);
        });
    }

    /* ── Mobile Accordion ──────────────────────────────────── */
    const accordionBtns = document.querySelectorAll('.cmc-mobile-accordion-btn');
    accordionBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const content = document.getElementById(targetId);
            const isOpen = content.classList.contains('open');

            // Close all other accordions
            document.querySelectorAll('.cmc-mobile-accordion-content').forEach(c => {
                if (c !== content) {
                    c.classList.remove('open');
                }
            });
            document.querySelectorAll('.cmc-mobile-accordion-btn').forEach(b => {
                if (b !== this) {
                    b.classList.remove('active');
                }
            });

            // Toggle current accordion
            content.classList.toggle('open', !isOpen);
            this.classList.toggle('active', !isOpen);
        });
    });

    /* ── Scroll shadow ─────────────────────────────────────── */
    window.addEventListener('scroll', () => {
        if (nav) nav.classList.toggle('scrolled', window.scrollY > 10);
    }, { passive: true });

    /* ── SD Live Search ────────────────────────────────────── */
    const searchInput   = document.getElementById('sdSearchInput');
    const searchResults = document.getElementById('sdSearchResults');
    const searchUrl     = (searchInput && searchInput.dataset.url) || '';

    if (searchInput && searchResults) {
        let searchTimer = null;

        searchInput.addEventListener('input', function () {
            const q = this.value.trim();
            clearTimeout(searchTimer);
            if (q.length < 2) {
                searchResults.classList.remove('open');
                searchResults.innerHTML = '';
                return;
            }
            searchTimer = setTimeout(() => fetchResults(q), 240);
        });

        searchInput.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                searchResults.classList.remove('open');
                this.blur();
            }
        });

        document.addEventListener('click', function (e) {
            if (!searchInput.closest('.cmc-search').contains(e.target)) {
                searchResults.classList.remove('open');
            }
        });

        function fetchResults(q) {
            fetch(searchUrl + '?q=' + encodeURIComponent(q), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(r => r.json())
            .then(data => {
                renderResults(data.results || [], q);
            })
            .catch(() => {
                searchResults.innerHTML = '<div class="sd-search-empty">Error fetching results.</div>';
                searchResults.classList.add('open');
            });
        }

        function renderResults(results, q) {
            if (!results.length) {
                searchResults.innerHTML = '<div class="sd-search-empty">No SD records found for <strong>' + escHtml(q) + '</strong></div>';
                searchResults.classList.add('open');
                return;
            }

            let html = '';
            results.forEach(sd => {
                const badge = sd.is_complete
                    ? '<span class="sd-badge sd-badge-done">Complete</span>'
                    : '<span class="sd-badge sd-badge-active">Active</span>';
                html += `
                <a class="sd-result-item" href="${escHtml(sd.url)}">
                    <div class="sd-result-main">
                        <span class="sd-result-number">${escHtml(sd.sd_number)}</span>
                        <span class="sd-result-vessel">${escHtml(sd.vessel)}</span>
                    </div>
                    <div class="sd-result-meta">
                        <span>${escHtml(sd.buyer)}</span>
                        ${badge}
                    </div>
                </a>`;
            });

            const viewAllQ = encodeURIComponent(q);
            html += `<a class="sd-result-viewall" href="/operations/?q=${viewAllQ}">View all results for "${escHtml(q)}"</a>`;
            searchResults.innerHTML = html;
            searchResults.classList.add('open');
        }

        function escHtml(str) {
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;');
        }
    }
})();
