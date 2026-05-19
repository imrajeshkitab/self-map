const API_BASE = 'http://localhost:8000';

const SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
];
const SIGN_POS = {
    "Pisces":      [1, 1], "Aries":       [1, 2], "Taurus":      [1, 3], "Gemini":      [1, 4],
    "Cancer":      [2, 4], "Leo":         [3, 4], "Virgo":       [4, 4], "Libra":       [4, 3],
    "Scorpio":     [4, 2], "Sagittarius": [4, 1], "Capricorn":   [3, 1], "Aquarius":    [2, 1],
};
const PLANET_ABBR = { Sun:"Su", Moon:"Mo", Mars:"Ma", Mercury:"Me", Jupiter:"Ju", Venus:"Ve", Saturn:"Sa", Rahu:"Ra", Ketu:"Ke" };

const STATE_LABEL = {
    exalted:     { tag: "Exalted",     symbol: "⭐" },
    debilitated: { tag: "Debilitated", symbol: "⚠️" },
    own:         { tag: "Own Sign",    symbol: "🏠" },
    neutral:     { tag: "Neutral",     symbol: "✦"  },
};
const REL_LABEL = {
    friend:  { tag: "Friend's sign",  cls: "rel-friend"  },
    enemy:   { tag: "Enemy's sign",   cls: "rel-enemy"   },
    neutral: { tag: "Neutral sign",   cls: "rel-neutral" },
    own:     { tag: "Own sign",       cls: "rel-own"     },
};
const KARAKA_BLURBS = {
    Atma: "Soul, life-direction",
    Amatya: "Career, mentor",
    Bhratri: "Siblings, courage",
    Matri: "Mother, comfort",
    Putra: "Children, creativity",
    Gnati: "Relatives, obstacles",
    Dara: "Spouse, partnership",
};

const PRESET_PLACES = [
    { name: "Gachibowli, Hyderabad",  lat: 17.4399, lon: 78.3489 },
    { name: "Hyderabad (city center)", lat: 17.3850, lon: 78.4867 },
    { name: "Bangalore",              lat: 12.9716, lon: 77.5946 },
    { name: "Mumbai",                 lat: 19.0760, lon: 72.8777 },
    { name: "Delhi",                  lat: 28.6139, lon: 77.2090 },
    { name: "Chennai",                lat: 13.0827, lon: 80.2707 },
    { name: "Kolkata",                lat: 22.5726, lon: 88.3639 },
    { name: "Pune",                   lat: 18.5204, lon: 73.8567 },
];

// DOM refs
const inputEl     = document.getElementById('ask-input');
const askBtn      = document.getElementById('ask-btn');
const againBtn    = document.getElementById('ask-again-btn');
const loadingEl   = document.getElementById('ask-loading');
const resultEl    = document.getElementById('ask-result');
const verdictEl   = document.getElementById('verdict-banner');
const answerEl    = document.getElementById('answer-card');
const evidenceEl  = document.getElementById('evidence-list');
const chartEl     = document.getElementById('chart-sa');
const metaPanel   = document.getElementById('ask-chart-meta');
const askLocEl    = document.getElementById('ask-loc');
const askTimeEl   = document.getElementById('ask-time');
const pulseEl     = document.getElementById('pulse-card');
const weatherEl   = document.getElementById('weather-list');
const dashaEl     = document.getElementById('dasha-card');
const karakasEl   = document.getElementById('karakas-card');

const dateInp     = document.getElementById('ctrl-date');
const timeInp     = document.getElementById('ctrl-time');
const placeSel    = document.getElementById('ctrl-place');
const customBox   = document.getElementById('ctrl-custom');
const latInp      = document.getElementById('ctrl-lat');
const lonInp      = document.getElementById('ctrl-lon');
const nowBtn      = document.getElementById('ctrl-now');
const geoBtn      = document.getElementById('ctrl-geo');

// ---------- Init ----------
populatePlaceDropdown();
setNow(false);
placeSel.value = PRESET_PLACES[0].name;
bindControls();
updateMetaLine();

askBtn.addEventListener('click', submit);
inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
});
document.querySelectorAll('.ex-pill').forEach(el => {
    el.addEventListener('click', () => {
        inputEl.value = el.textContent;
        submit();
    });
});
againBtn.addEventListener('click', () => {
    resultEl.classList.add('hidden');
    inputEl.value = '';
    inputEl.focus();
    setNow(false);   // reset to "now" so the next question is fresh
    updateMetaLine();
});

// ---------- Controls ----------
function populatePlaceDropdown() {
    PRESET_PLACES.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.name; opt.textContent = p.name;
        placeSel.appendChild(opt);
    });
    const custom = document.createElement('option');
    custom.value = '__custom__';
    custom.textContent = 'Custom lat/lon…';
    placeSel.appendChild(custom);
}

function setNow(triggerUpdate = true) {
    const now = new Date();
    const pad = n => String(n).padStart(2, '0');
    dateInp.value = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}`;
    timeInp.value = `${pad(now.getHours())}:${pad(now.getMinutes())}`;
    if (triggerUpdate) updateMetaLine();
}

function bindControls() {
    [dateInp, timeInp, latInp, lonInp].forEach(el => el.addEventListener('change', updateMetaLine));
    placeSel.addEventListener('change', () => {
        if (placeSel.value === '__custom__') {
            customBox.classList.remove('hidden');
            const last = PRESET_PLACES[0];
            if (!latInp.value) latInp.value = last.lat;
            if (!lonInp.value) lonInp.value = last.lon;
        } else {
            customBox.classList.add('hidden');
        }
        updateMetaLine();
    });
    nowBtn.addEventListener('click', () => setNow(true));
    geoBtn.addEventListener('click', useGeolocation);
}

function useGeolocation() {
    if (!navigator.geolocation) return alert('Geolocation not supported.');
    geoBtn.textContent = '📍 Locating…';
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            placeSel.value = '__custom__';
            customBox.classList.remove('hidden');
            latInp.value = pos.coords.latitude.toFixed(4);
            lonInp.value = pos.coords.longitude.toFixed(4);
            geoBtn.textContent = '📍 My location';
            updateMetaLine();
        },
        () => { geoBtn.textContent = '📍 My location'; alert('Could not get location.'); },
        { timeout: 5000 }
    );
}

function getSelectedLocation() {
    if (placeSel.value === '__custom__') {
        return { lat: parseFloat(latInp.value), lon: parseFloat(lonInp.value), place: 'Custom location' };
    }
    const p = PRESET_PLACES.find(p => p.name === placeSel.value) || PRESET_PLACES[0];
    return { lat: p.lat, lon: p.lon, place: p.name };
}

function getSelectedDatetime() {
    if (!dateInp.value || !timeInp.value) return null;
    const local = new Date(`${dateInp.value}T${timeInp.value}:00`);
    return local.toISOString();
}

function updateMetaLine() {
    const loc = getSelectedLocation();
    askLocEl.textContent = loc.place + (placeSel.value === '__custom__'
        ? ` (${loc.lat}, ${loc.lon})` : '');
    const dt = (dateInp.value && timeInp.value)
        ? new Date(`${dateInp.value}T${timeInp.value}:00`).toLocaleString()
        : 'now';
    askTimeEl.textContent = dt;
}

async function submit() {
    const q = inputEl.value.trim();
    if (!q) return;

    loadingEl.classList.remove('hidden');
    resultEl.classList.add('hidden');

    try {
        const loc = getSelectedLocation();
        const when = getSelectedDatetime();
        const params = new URLSearchParams({
            q, lat: loc.lat, lon: loc.lon, place: loc.place,
        });
        if (when) params.set('when', when);

        const res = await fetch(`${API_BASE}/ask?${params.toString()}`);
        if (!res.ok) throw new Error('API error');
        const data = await res.json();
        render(data);
        loadingEl.classList.add('hidden');
        resultEl.classList.remove('hidden');
        resultEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (e) {
        loadingEl.classList.add('hidden');
        alert('Something went wrong. Is the API running?');
        console.error(e);
    }
}

function render(data) {
    renderVerdict(data);
    renderAnswer(data);
    renderEvidence(data);
    renderChart(data.chart);
    renderMetaPanel(data.chart);
    renderPulse(data.chart);
    renderWeather(data.chart);
    renderDasha(data.chart);
    renderKarakas(data.chart);
}

function renderVerdict(data) {
    const v = data.verdict;
    const cls = 'verdict-' + v.label.replace(/ /g, '-');
    verdictEl.className = 'verdict-banner ' + cls;
    verdictEl.innerHTML = `
        <div class="v-question">
            <span class="muted">You asked about <b>${escapeHtml(data.intent.label)}</b>:</span><br>
            "${escapeHtml(data.question)}"
        </div>
        <div class="v-right">
            <div class="v-label">${capitalize(v.label)}</div>
            <div class="v-meta">Score ${v.score} · ${v.confidence} confidence</div>
        </div>
    `;
}

function renderAnswer(data) {
    const tag = data.answer_source === 'gemini' ? 'AI' : 'Template';
    // The reading is markdown with ## section headers — render via marked.
    // Falls back to a simple paragraph wrap if marked isn't loaded.
    let body;
    if (window.marked) {
        body = window.marked.parse(data.answer || '');
    } else {
        body = escapeHtml(data.answer || '')
            .replace(/\n\n+/g, '</p><p>')
            .replace(/^/, '<p>').replace(/$/, '</p>');
    }
    answerEl.innerHTML = `
        <div class="answer-tag">The Reading <span class="answer-source">${tag}</span></div>
        <div class="answer-body">${body}</div>
    `;
}

function renderEvidence(data) {
    const items = data.evidence.evidence || [];
    evidenceEl.innerHTML = '';
    items.forEach(e => {
        const scoreClass = e.score > 0 ? 'score-pos' : e.score < 0 ? 'score-neg' : 'score-zero';
        const row = document.createElement('div');
        row.className = 'evidence-row';
        row.innerHTML = `
            <div class="ev-top">
                <span class="ev-factor">${escapeHtml(e.factor)}<span class="weight-tag ${e.weight}">${e.weight}</span></span>
                <span class="score-chip ${scoreClass}">${e.score > 0 ? '+' : ''}${e.score}</span>
            </div>
            <div class="ev-subject">${escapeHtml(e.subject)}</div>
            <div class="ev-detail">${escapeHtml(e.detail)}</div>
        `;
        row.addEventListener('click', () => row.classList.toggle('open'));
        evidenceEl.appendChild(row);
    });
}

function renderChart(c) {
    const lagnaSign = c.lagna.sign;
    const bySign = {};
    c.planets.forEach(p => (bySign[p.sign] ||= []).push(p));

    chartEl.innerHTML = '';
    SIGNS.forEach(sign => {
        const [row, col] = SIGN_POS[sign];
        const houseNum = c.houses.find(h => h.sign === sign).number;
        const cell = document.createElement('div');
        cell.className = 'chart-cell' + (sign === lagnaSign ? ' has-lagna' : '');
        cell.style.gridRow = row; cell.style.gridColumn = col;

        const planets = (bySign[sign] || []).map(p => {
            const tags = [];
            if (p.retrograde) tags.push('R');
            if (p.combust)    tags.push('C');
            const sup = tags.length ? `<sup>${tags.join('')}</sup>` : '';
            return `<span class="cell-planet ${p.state}" title="${p.name} · ${p.state}">${PLANET_ABBR[p.name]}${sup}</span>`;
        }).join('');

        cell.innerHTML = `
            <div class="cell-house">H${houseNum}</div>
            <div class="cell-sign">${sign}</div>
            <div class="cell-planets">${planets}</div>
        `;
        chartEl.appendChild(cell);
    });

    const center = document.createElement('div');
    center.className = 'chart-cell center';
    center.style.gridRow = '2 / span 2';
    center.style.gridColumn = '2 / span 2';
    center.textContent = 'PRASHNA';
    chartEl.appendChild(center);
}

function renderMetaPanel(c) {
    const when = new Date(c.datetime_utc);
    metaPanel.innerHTML = `
        <div class="meta-row"><span class="meta-label">Cast at</span><span class="meta-value">${when.toLocaleString()}</span></div>
        <div class="meta-row"><span class="meta-label">Location</span><span class="meta-value">${escapeHtml(c.location.place)}</span></div>
        <div class="meta-row"><span class="meta-label">Lagna</span><span class="meta-value">${c.lagna.sign} ${c.lagna.degree.toFixed(1)}°</span></div>
        <div class="meta-row"><span class="meta-label">Lagna lord</span><span class="meta-value">${c.lagna.lord} (${c.lagna.lord_state})</span></div>
        <div class="meta-row"><span class="meta-label">Mahadasha</span><span class="meta-value">${c.dasha?.current_mahadasha || '—'} · ${c.dasha?.remaining_years ?? '?'} yrs</span></div>
        <div class="meta-row"><span class="meta-label">Ayanamsa</span><span class="meta-value">${c.ayanamsa}</span></div>
        <div class="meta-row"><span class="meta-label">House system</span><span class="meta-value">${c.house_system}</span></div>
    `;
}

function renderPulse(c) {
    if (!c || !c.pulse) { pulseEl.innerHTML = ''; return; }
    const src = c.pulse.source === 'gemini' ? 'AI' : 'Template';
    pulseEl.innerHTML = `
        <div class="pulse-tag">Cosmic Pulse <span class="pulse-source">${src}</span></div>
        ${escapeHtml(c.pulse.summary)}
    `;
}

function renderWeather(c) {
    if (!c) return;
    const order = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"];
    const sorted = order.map(n => c.planets.find(p => p.name === n)).filter(Boolean);

    weatherEl.innerHTML = '';
    sorted.forEach(p => {
        const st  = STATE_LABEL[p.state];
        const rel = REL_LABEL[p.relation] || REL_LABEL.neutral;
        const flagBits = [];
        if (p.retrograde) flagBits.push('<span class="retro-tag">RETRO</span>');
        if (p.combust)    flagBits.push('<span class="retro-tag combust-tag">COMBUST</span>');
        const row = document.createElement('div');
        row.className = 'weather-row';
        row.innerHTML = `
            <div class="w-main">
                <div class="w-top">
                    <span class="w-name">${p.name}</span>
                    ${flagBits.join('')}
                </div>
                <span class="w-loc">in <b>${p.sign}</b> · ${ordinal(p.house)} house · ${p.degree.toFixed(1)}°</span>
                <span class="w-sub">
                    ${p.nakshatra} (pada ${p.pada}) · ${p.avastha} ·
                    <span class="rel-chip ${rel.cls}">${rel.tag}</span>
                </span>
            </div>
            <span class="state-badge state-${p.state}" title="${st.tag}">${st.symbol} ${st.tag}</span>
        `;
        weatherEl.appendChild(row);
    });
}

function renderDasha(c) {
    if (!c || !c.dasha) { dashaEl.innerHTML = ''; return; }
    const d = c.dasha;

    // ---- 3-tier "now running" header (MD / AD / PD) ----
    const md = d.timeline.find(t => t.current);
    const ad = (d.antardasha_timeline || []).find(t => t.current);
    const pd = (d.pratyantar_timeline || []).find(t => t.current);

    const tier = (label, lord, total, remaining, unit) => {
        if (!lord) return '';
        const elapsed = total - remaining;
        const pct = total > 0 ? Math.max(2, Math.min(100, (elapsed / total) * 100)) : 0;
        return `
            <div class="dba-tier">
                <div class="dba-tier-head">
                    <span class="dba-label">${label}</span>
                    <span class="dba-lord">${lord}</span>
                    <span class="dba-remaining">${remaining} ${unit} left</span>
                </div>
                <div class="dba-bar"><div class="dba-bar-fill" style="width:${pct}%"></div></div>
            </div>
        `;
    };

    const mdBlock = md ? tier('MD',
        md.lord,
        md.years,
        d.remaining_years,
        'yrs') : '';
    const adBlock = ad ? tier('AD',
        ad.lord,
        ad.years,
        d.antardasha_remaining_years,
        'yrs') : '';
    const pdBlock = pd ? tier('PD',
        pd.lord,
        pd.years * 365.25,
        d.pratyantar_remaining_days,
        'days') : '';

    // ---- MD timeline table ----
    const mdRows = d.timeline.slice(0, 6).map(t => `
        <tr class="${t.current ? 'dasha-current' : ''}">
            <td>${t.lord}</td>
            <td>${t.starts}</td>
            <td>${t.ends}</td>
            <td>${t.years} yr${t.current ? ` (${t.remaining_years} left)` : ''}</td>
        </tr>
    `).join('');

    // ---- AD timeline (within current MD) ----
    const adRows = (d.antardasha_timeline || []).map(t => `
        <tr class="${t.current ? 'dasha-current' : ''}">
            <td>${t.lord}</td>
            <td>${t.starts}</td>
            <td>${t.ends}</td>
            <td>${(t.years * 12).toFixed(1)} mo${t.current ? ` (${t.remaining_days}d left)` : ''}</td>
        </tr>
    `).join('');

    dashaEl.innerHTML = `
        <h2 class="section-heading-sm">Vimshottari DBA</h2>
        <p class="dasha-hint">From Moon's nakshatra — ${d.moon_nakshatra}.
            Three nested layers of timing: Mahadasha (years) → Antardasha (months) → Pratyantar (days).</p>

        <div class="dba-stack">
            ${mdBlock}
            ${adBlock}
            ${pdBlock}
        </div>

        <details class="dba-details">
            <summary>Mahadasha timeline (next 6)</summary>
            <table class="dasha-table">
                <thead><tr><th>Lord</th><th>Starts</th><th>Ends</th><th>Duration</th></tr></thead>
                <tbody>${mdRows}</tbody>
            </table>
        </details>

        <details class="dba-details">
            <summary>Antardasha timeline (within ${d.current_mahadasha} MD)</summary>
            <table class="dasha-table">
                <thead><tr><th>Lord</th><th>Starts</th><th>Ends</th><th>Duration</th></tr></thead>
                <tbody>${adRows}</tbody>
            </table>
        </details>
    `;
}

function renderKarakas(c) {
    if (!c) return;
    const k = c.chara_karakas || [];
    karakasEl.innerHTML = `
        <h2 class="section-heading-sm">Chara Karakas <span class="muted">(Jaimini)</span></h2>
        <p class="dasha-hint">Ranked by degree — highest is the soul (Atmakaraka).</p>
        <div class="karakas-list">
            ${k.map(x => `
                <div class="karaka-row">
                    <span class="karaka-name">${x.karaka}</span>
                    <span class="karaka-planet">${x.planet}</span>
                    <span class="karaka-blurb">${KARAKA_BLURBS[x.karaka] || ''}</span>
                    <span class="karaka-deg">${x.degree.toFixed(2)}°</span>
                </div>
            `).join('')}
        </div>
    `;
}

function ordinal(n) {
    const s = ["th","st","nd","rd"], v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

function capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
}
