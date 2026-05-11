const API_BASE = 'http://localhost:8000';

const SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
];

const SIGN_POS = {
    "Pisces":      [1, 1],
    "Aries":       [1, 2],
    "Taurus":      [1, 3],
    "Gemini":      [1, 4],
    "Cancer":      [2, 4],
    "Leo":         [3, 4],
    "Virgo":       [4, 4],
    "Libra":       [4, 3],
    "Scorpio":     [4, 2],
    "Sagittarius": [4, 1],
    "Capricorn":   [3, 1],
    "Aquarius":    [2, 1],
};

const PLANET_ABBR = {
    Sun: "Su", Moon: "Mo", Mars: "Ma", Mercury: "Me",
    Jupiter: "Ju", Venus: "Ve", Saturn: "Sa", Rahu: "Ra", Ketu: "Ke",
};
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

const PRESET_PLACES = [
    { name: "Gachibowli, Hyderabad", lat: 17.4399, lon: 78.3489 },
    { name: "Hyderabad (city center)", lat: 17.3850, lon: 78.4867 },
    { name: "Bangalore",             lat: 12.9716, lon: 77.5946 },
    { name: "Mumbai",                lat: 19.0760, lon: 72.8777 },
    { name: "Delhi",                 lat: 28.6139, lon: 77.2090 },
    { name: "Chennai",               lat: 13.0827, lon: 80.2707 },
    { name: "Kolkata",               lat: 22.5726, lon: 88.3639 },
    { name: "Pune",                  lat: 18.5204, lon: 73.8567 },
];

// DOM refs
const root      = document.getElementById('today-root');
const loading   = document.getElementById('loading');
const lagnaEl   = document.getElementById('lagna-strip');
const pulseEl   = document.getElementById('pulse-card');
const chartEl   = document.getElementById('chart-sa');
const weatherEl = document.getElementById('weather-list');
const dashaEl   = document.getElementById('dasha-card');
const karakasEl = document.getElementById('karakas-card');
const metaEl    = document.getElementById('chart-meta');

const dateInp   = document.getElementById('ctrl-date');
const timeInp   = document.getElementById('ctrl-time');
const placeSel  = document.getElementById('ctrl-place');
const customBox = document.getElementById('ctrl-custom');
const latInp    = document.getElementById('ctrl-lat');
const lonInp    = document.getElementById('ctrl-lon');
const nowBtn    = document.getElementById('ctrl-now');
const geoBtn    = document.getElementById('ctrl-geo');

let fetchToken = 0;  // debounce/race guard

// ---------- Init ----------
(async function init() {
    populatePlaceDropdown();
    setNow(false);
    placeSel.value = PRESET_PLACES[0].name;
    bindControls();
    await refresh();
})();

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

function setNow(triggerRefresh = true) {
    const now = new Date();
    const pad = n => String(n).padStart(2, '0');
    dateInp.value = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}`;
    timeInp.value = `${pad(now.getHours())}:${pad(now.getMinutes())}`;
    if (triggerRefresh) refresh();
}

function bindControls() {
    [dateInp, timeInp, latInp, lonInp].forEach(el => el.addEventListener('change', refresh));
    placeSel.addEventListener('change', () => {
        if (placeSel.value === '__custom__') {
            customBox.classList.remove('hidden');
            const last = PRESET_PLACES[0];
            latInp.value = last.lat; lonInp.value = last.lon;
        } else {
            customBox.classList.add('hidden');
        }
        refresh();
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
            refresh();
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
    // Treat inputs as LOCAL time, convert to ISO with the local timezone offset.
    if (!dateInp.value || !timeInp.value) return null;
    const local = new Date(`${dateInp.value}T${timeInp.value}:00`);
    return local.toISOString();
}

// ---------- Fetch + render ----------
async function refresh() {
    const myToken = ++fetchToken;
    loading.classList.remove('hidden');
    root.classList.add('hidden');

    try {
        const loc = getSelectedLocation();
        const when = getSelectedDatetime();
        const params = new URLSearchParams({
            lat: loc.lat, lon: loc.lon, place: loc.place, pulse: 'true',
        });
        if (when) params.set('when', when);

        const res = await fetch(`${API_BASE}/today?${params.toString()}`);
        if (myToken !== fetchToken) return;  // a newer request superseded us
        if (!res.ok) throw new Error('API error');
        const chart = await res.json();

        renderAll(chart);
        loading.classList.add('hidden');
        root.classList.remove('hidden');
    } catch (e) {
        if (myToken !== fetchToken) return;
        loading.innerHTML = `<p style="color:#f87171">Could not load. Is the API running?</p>`;
        console.error(e);
    }
}

function renderAll(chart) {
    renderLagna(chart);
    renderPulse(chart);
    renderChart(chart);
    renderWeather(chart);
    renderDasha(chart);
    renderKarakas(chart);
    renderMeta(chart);
}

// ---------- Renderers ----------
function renderLagna(c) {
    const L = c.lagna;
    const sym = STATE_LABEL[L.lord_state].symbol;
    lagnaEl.innerHTML = `
        <div class="lagna-label">The Moment</div>
        <div class="lagna-main">
            Lagna rising in <strong>${L.sign}</strong> (${L.sign_sanskrit}) at ${L.degree.toFixed(1)}° ·
            <em>${L.nakshatra}</em> pada ${L.pada}.
            <br>
            Lagna lord <strong>${L.lord}</strong> is in <strong>${L.lord_sign}</strong>
            <span class="badge">${sym} ${STATE_LABEL[L.lord_state].tag}</span>,
            sitting in the <strong>${ordinal(L.lord_house)}</strong> house.
        </div>
    `;
}

function renderPulse(c) {
    if (!c.pulse) { pulseEl.classList.add('hidden'); return; }
    const src = c.pulse.source === 'gemini' ? 'AI' : 'Template';
    pulseEl.innerHTML = `
        <div class="pulse-tag">Cosmic Pulse <span class="pulse-source">${src}</span></div>
        ${escapeHtml(c.pulse.summary)}
    `;
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
            return `<span class="cell-planet ${p.state}" title="${p.name} · ${p.state}${p.retrograde?' · retrograde':''}${p.combust?' · combust':''}">${PLANET_ABBR[p.name]}${sup}</span>`;
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

function renderWeather(c) {
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
    const d = c.dasha;
    if (!d) { dashaEl.innerHTML = ''; return; }
    const rows = d.timeline.slice(0, 6).map(t => `
        <tr class="${t.current ? 'dasha-current' : ''}">
            <td>${t.lord}</td>
            <td>${t.starts}</td>
            <td>${t.ends}</td>
            <td>${t.years} yr${t.current ? ` (${t.remaining_years} left)` : ''}</td>
        </tr>
    `).join('');
    dashaEl.innerHTML = `
        <h2 class="section-heading-sm">Vimshottari Dasha</h2>
        <p class="dasha-hint">From Moon's nakshatra — ${d.moon_nakshatra}.</p>
        <div class="dasha-current-banner">
            Now running: <strong>${d.current_mahadasha}</strong>
            <span class="muted">· ${d.remaining_years} years remaining</span>
        </div>
        <table class="dasha-table">
            <thead><tr><th>Lord</th><th>Starts</th><th>Ends</th><th>Duration</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

function renderKarakas(c) {
    const k = c.chara_karakas || [];
    const blurbs = {
        Atma: "Soul, life-direction",
        Amatya: "Career, mentor",
        Bhratri: "Siblings, courage",
        Matri: "Mother, comfort",
        Putra: "Children, creativity",
        Gnati: "Relatives, obstacles",
        Dara: "Spouse, partnership",
    };
    karakasEl.innerHTML = `
        <h2 class="section-heading-sm">Chara Karakas <span class="muted">(Jaimini)</span></h2>
        <p class="dasha-hint">Ranked by degree — highest is the soul (Atmakaraka).</p>
        <div class="karakas-list">
            ${k.map(x => `
                <div class="karaka-row">
                    <span class="karaka-name">${x.karaka}</span>
                    <span class="karaka-planet">${x.planet}</span>
                    <span class="karaka-blurb">${blurbs[x.karaka] || ''}</span>
                    <span class="karaka-deg">${x.degree.toFixed(2)}°</span>
                </div>
            `).join('')}
        </div>
    `;
}

function renderMeta(c) {
    const when = new Date(c.datetime_utc);
    metaEl.innerHTML = `
        <span>📍 ${escapeHtml(c.location.place)}</span>
        <span>·</span>
        <span>🕒 ${when.toLocaleString()}</span>
        <span>·</span>
        <span>${escapeHtml(c.ayanamsa)}</span>
        <span>·</span>
        <span>${escapeHtml(c.house_system)} houses</span>
    `;
}

// ---------- Utilities ----------
function ordinal(n) {
    const s = ["th","st","nd","rd"], v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
}
function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
}
