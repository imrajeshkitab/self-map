const API_BASE = 'http://localhost:8000';

const tabs = document.querySelectorAll('.tab');
const container = document.getElementById('browse-container');
const loading = document.getElementById('loading');

const cache = {};

const TAB_META = {
    houses:  { label: 'Houses (Bhavas)',   count: 12 },
    planets: { label: 'Planets (Grahas)',  count: 9  },
    zodiac:  { label: 'Zodiac Signs (Rashis)', count: 12 },
};

const statusCount = document.getElementById('status-count');
const statusLabel = document.getElementById('status-label');

tabs.forEach(t => t.addEventListener('click', () => switchTab(t.dataset.tab)));

async function switchTab(name) {
    tabs.forEach(t => {
        const isActive = t.dataset.tab === name;
        t.classList.toggle('active', isActive);
        t.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });

    const meta = TAB_META[name];
    if (meta) {
        statusCount.textContent = meta.count;
        statusLabel.textContent = meta.label;
    }
    container.innerHTML = '';
    loading.classList.remove('hidden');

    try {
        if (!cache[name]) {
            const res = await fetch(`${API_BASE}/${name}`);
            const data = await res.json();
            cache[name] = data.items;
        }
        loading.classList.add('hidden');
        render(name, cache[name]);
    } catch (e) {
        loading.classList.add('hidden');
        container.innerHTML = `<p style="text-align:center;color:#94a3b8">Could not load. Is the API running?</p>`;
    }
}

function render(type, items) {
    items.forEach((item, i) => container.appendChild(buildCard(type, item, i)));
}

function buildCard(type, item, index) {
    const card = document.createElement('div');
    card.className = 'card';
    card.style.animationDelay = `${index * 0.05}s`;

    let badge, title, subtitle, details;

    if (type === 'houses') {
        badge = `<span class="card-type type-house">🏠 House ${item.house_number}</span>`;
        title = item.sanskrit_name;
        subtitle = item.english_name;
        details = `
            <div class="detail-row"><span class="detail-label">Ruling Planet:</span><span class="detail-value">${item.ruling_planet || '—'}</span></div>
            <div class="detail-row"><span class="detail-label">Ruling Sign:</span><span class="detail-value">${item.ruling_sign || '—'}</span></div>
        `;
    } else if (type === 'planets') {
        badge = `<span class="card-type type-planet">🪐 Planet</span>`;
        title = `${item.english_name} ${item.symbol || ''}`;
        subtitle = item.sanskrit_name;
        details = `
            <div class="detail-row"><span class="detail-label">Rules:</span><span class="detail-value">${item.rules_sign || '—'}</span></div>
            <div class="detail-row"><span class="detail-label">Exalted In:</span><span class="detail-value">${item.exalted_in || '—'}</span></div>
            <div class="detail-row"><span class="detail-label">Debilitated In:</span><span class="detail-value">${item.debilitated_in || '—'}</span></div>
        `;
    } else {
        badge = `<span class="card-type type-zodiac">♈ Sign ${item.sign_number}</span>`;
        title = item.english_name;
        subtitle = item.sanskrit_name;
        details = `
            <div class="detail-row"><span class="detail-label">Ruled By:</span><span class="detail-value">${item.ruling_planet || '—'}</span></div>
            <div class="detail-row"><span class="detail-label">Element:</span><span class="detail-value">${item.element || '—'}</span></div>
            <div class="detail-row"><span class="detail-label">Quality:</span><span class="detail-value">${item.quality || '—'}</span></div>
        `;
    }

    const keywordsHtml = (item.keywords || '')
        .split(',')
        .map(kw => `<span class="keyword">${kw.trim()}</span>`)
        .join('');

    card.innerHTML = `
        <div class="card-header">${badge}</div>
        <h3 class="card-title">${title}</h3>
        <div class="card-subtitle">${subtitle}</div>
        <div class="card-details">${details}</div>
        <div class="card-desc">${item.significance || ''}</div>
        <div class="card-keywords">${keywordsHtml}</div>
    `;
    return card;
}

// Initial load
switchTab('houses');
