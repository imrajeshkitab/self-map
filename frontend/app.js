const API_URL = 'http://localhost:8000/search';

const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');
const resultsContainer = document.getElementById('results-container');
const loadingSection = document.getElementById('loading');
const noResultsSection = document.getElementById('no-results');
const pills = document.querySelectorAll('.pill');

// Event Listeners
searchBtn.addEventListener('click', handleSearch);
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSearch();
});

pills.forEach(pill => {
    pill.addEventListener('click', () => {
        searchInput.value = pill.textContent;
        handleSearch();
    });
});

async function handleSearch() {
    const query = searchInput.value.trim();
    if (!query) return;

    // UI State: Loading
    resultsContainer.innerHTML = '';
    noResultsSection.classList.add('hidden');
    loadingSection.classList.remove('hidden');

    try {
        const response = await fetch(`${API_URL}?q=${encodeURIComponent(query)}&top_k=9&min_score=0`);
        if (!response.ok) throw new Error('Network response was not ok');
        
        const data = await response.json();

        // UI State: Loaded
        loadingSection.classList.add('hidden');

        // Trinity mode (default): {trinity: {house, planet, zodiac}, overflow: [...]}
        // Ranked mode: {results: [...]}
        const trinityItems = data.trinity
            ? ['house', 'planet', 'zodiac'].map(k => data.trinity[k]).filter(Boolean)
            : [];
        const overflowItems = data.overflow || data.results || [];

        if (trinityItems.length === 0 && overflowItems.length === 0) {
            noResultsSection.classList.remove('hidden');
        } else {
            renderResults(trinityItems, overflowItems);
        }
    } catch (error) {
        console.error('Error fetching data:', error);
        loadingSection.classList.add('hidden');
        noResultsSection.classList.remove('hidden');
        noResultsSection.querySelector('p').textContent = "A mystical disturbance prevented us from consulting the stars. Is the API running?";
    }
}

function renderResults(trinityItems, overflowItems) {
    resultsContainer.innerHTML = '';

    if (trinityItems.length > 0) {
        const heading = document.createElement('h2');
        heading.className = 'section-heading';
        heading.textContent = 'The Vedic Trinity';
        resultsContainer.appendChild(heading);

        const trinityGrid = document.createElement('div');
        trinityGrid.className = 'results-grid trinity-grid';
        trinityItems.forEach((item, i) => trinityGrid.appendChild(buildCard(item, i, true)));
        resultsContainer.appendChild(trinityGrid);
    }

    if (overflowItems.length > 0) {
        const heading = document.createElement('h2');
        heading.className = 'section-heading';
        heading.textContent = 'Also Related';
        resultsContainer.appendChild(heading);

        const overflowGrid = document.createElement('div');
        overflowGrid.className = 'results-grid';
        overflowItems.forEach((item, i) => overflowGrid.appendChild(buildCard(item, i, false)));
        resultsContainer.appendChild(overflowGrid);
    }
}

function buildCard(item, index, isTrinity) {
    const card = document.createElement('div');
    card.className = isTrinity ? 'card card-trinity' : 'card';
    card.style.animationDelay = `${index * 0.1}s`;
        
        let typeBadge, title, subtitle, specificDetails;

        if (item.type === 'house') {
            typeBadge = `<span class="card-type type-house">🏠 House</span>`;
            title = `House ${item.house_number}`;
            subtitle = `${item.sanskrit_name} / ${item.english_name}`;
            specificDetails = `
                <div class="detail-row">
                    <span class="detail-label">Ruled By:</span>
                    <span class="detail-value">${item.ruling_planet || 'N/A'}</span>
                </div>
            `;
        } else if (item.type === 'planet') {
            typeBadge = `<span class="card-type type-planet">🪐 Planet</span>`;
            title = item.english_name;
            subtitle = item.sanskrit_name;
            specificDetails = `
                <div class="detail-row">
                    <span class="detail-label">Rules Sign:</span>
                    <span class="detail-value">${item.rules_sign || 'N/A'}</span>
                </div>
            `;
        } else if (item.type === 'zodiac') {
            typeBadge = `<span class="card-type type-zodiac">♈ Zodiac</span>`;
            title = item.english_name;
            subtitle = item.sanskrit_name;
            specificDetails = `
                <div class="detail-row">
                    <span class="detail-label">Element:</span>
                    <span class="detail-value">${item.element || 'N/A'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Quality:</span>
                    <span class="detail-value">${item.quality || 'N/A'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Ruled By:</span>
                    <span class="detail-value">${item.ruling_planet || 'N/A'}</span>
                </div>
            `;
        }

        const keywordsHtml = (item.keywords || '')
            .split(',')
            .slice(0, 5) // Show max 5 keywords
            .map(kw => `<span class="keyword">${kw.trim()}</span>`)
            .join('');

        const scorePercent = Math.round(item.score * 100);

        card.innerHTML = `
            <div class="card-header">
                ${typeBadge}
                <div class="card-score">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 20V10M18 20V4M6 20v-6"></path>
                    </svg>
                    ${scorePercent}% Match
                </div>
            </div>
            <h3 class="card-title">${title}</h3>
            <div class="card-subtitle">${subtitle}</div>
            <div class="card-details">
                ${specificDetails}
            </div>
            <div class="card-desc" title="${item.significance}">
                ${item.significance || 'No description available.'}
            </div>
            <div class="card-keywords">
                ${keywordsHtml}
            </div>
        `;
        
    return card;
}
