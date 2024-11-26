// search.js

class MovieSearch {
    constructor() {
        // State management
        this.state = {
            currentQuery: '',
            currentPage: 1,
            currentSort: 'relevance',
            filters: {
                genres: [],
                languages: [],
                rating: 0,
                yearFrom: null,
                yearTo: null,
                contentRating: []
            },
            isLoading: false
        };

        // DOM Elements
        this.elements = {
            searchInput: document.getElementById('search-input'),
            searchResults: document.getElementById('results-grid'),
            pagination: document.getElementById('pagination'),
            resultsCount: document.getElementById('results-count'),
            sortSelect: document.getElementById('sort-by'),
            filterForm: document.getElementById('filter-form'),
            genreFilters: document.getElementById('genre-filters'),
            languageFilters: document.getElementById('language-filters'),
            contentRatingFilters: document.getElementById('content-rating-filters'),
            ratingSlider: document.getElementById('rating-filter'),
            ratingValue: document.getElementById('rating-value'),
            yearFrom: document.getElementById('year-from'),
            yearTo: document.getElementById('year-to'),
            movieModal: document.getElementById('movie-modal'),
            modalContent: document.getElementById('modal-content'),
            loadingOverlay: document.getElementById('loading-overlay')
        };

        // Bind methods
        this.initializeSearch = this.initializeSearch.bind(this);
        this.performSearch = this.performSearch.bind(this);
        this.handleFilterChange = this.handleFilterChange.bind(this);
        this.handleSortChange = this.handleSortChange.bind(this);
        this.handlePageChange = this.handlePageChange.bind(this);
        
        // Initialize search
        this.initializeSearch();
    }

    async initializeSearch() {
        try {
            // Initialize filters
            await this.initializeFilters();
            
            // Initialize year dropdowns
            this.initializeYearDropdowns();
            
            // Initialize rating slider
            this.initializeRatingSlider();
            
            // Set up event listeners
            this.setupEventListeners();
            
            // Perform initial search
            const urlParams = new URLSearchParams(window.location.search);
            this.state.currentQuery = urlParams.get('q') || '';
            await this.performSearch();
            
        } catch (error) {
            console.error('Failed to initialize search:', error);
            this.showError('Failed to initialize search');
        }
    }

    async initializeFilters() {
        try {
            // Load genres
            const genresResponse = await fetch('/api/genres');
            const genres = await genresResponse.json();
            this.renderGenreFilters(genres);

            // Load languages
            const languagesResponse = await fetch('/api/movies/search?size=0');
            const languages = await languagesResponse.json();
            const uniqueLanguages = [...new Set(languages.aggregations.languages.buckets.map(b => b.key))];
            this.renderLanguageFilters(uniqueLanguages);

            // Set up content ratings
            const contentRatings = ['G', 'PG', 'PG-13', 'R', 'NC-17'];
            this.renderContentRatingFilters(contentRatings);

        } catch (error) {
            console.error('Failed to initialize filters:', error);
            throw error;
        }
    }

    renderGenreFilters(genres) {
        if (!this.elements.genreFilters) return;
        
        this.elements.genreFilters.innerHTML = genres.map(genre => `
            <label class="flex items-center text-sm">
                <input type="checkbox" 
                       value="${genre}"
                       class="form-checkbox text-red-600 rounded border-gray-600 bg-gray-700"
                       data-filter="genre">
                <span class="ml-2">${genre}</span>
            </label>
        `).join('');
    }

    renderLanguageFilters(languages) {
        if (!this.elements.languageFilters) return;
        
        this.elements.languageFilters.innerHTML = languages.map(language => `
            <label class="flex items-center text-sm">
                <input type="checkbox" 
                       value="${language}"
                       class="form-checkbox text-red-600 rounded border-gray-600 bg-gray-700"
                       data-filter="language">
                <span class="ml-2">${language}</span>
            </label>
        `).join('');
    }

    renderContentRatingFilters(ratings) {
        if (!this.elements.contentRatingFilters) return;
        
        this.elements.contentRatingFilters.innerHTML = ratings.map(rating => `
            <label class="flex items-center text-sm">
                <input type="checkbox" 
                       value="${rating}"
                       class="form-checkbox text-red-600 rounded border-gray-600 bg-gray-700"
                       data-filter="content-rating">
                <span class="ml-2">${rating}</span>
            </label>
        `).join('');
    }

    initializeYearDropdowns() {
        const currentYear = new Date().getFullYear();
        const years = Array.from({length: 50}, (_, i) => currentYear - i);
        const yearOptions = years.map(year => 
            `<option value="${year}">${year}</option>`
        ).join('');
        
        if (this.elements.yearFrom) {
            this.elements.yearFrom.innerHTML += yearOptions;
        }
        if (this.elements.yearTo) {
            this.elements.yearTo.innerHTML += yearOptions;
        }
    }

    initializeRatingSlider() {
        if (!this.elements.ratingSlider || !this.elements.ratingValue) return;

        this.elements.ratingSlider.addEventListener('input', (e) => {
            const value = e.target.value;
            this.elements.ratingValue.textContent = value;
            this.state.filters.rating = parseFloat(value);
        });
    }

    setupEventListeners() {
        // Search input with debounce
        let searchTimeout;
        this.elements.searchInput?.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.state.currentQuery = e.target.value.trim();
                this.state.currentPage = 1;
                this.performSearch();
            }, 500);
        });

        // Sort select
        this.elements.sortSelect?.addEventListener('change', this.handleSortChange);

        // Filter form
        this.elements.filterForm?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleFilterChange();
        });

        // Year dropdowns
        this.elements.yearFrom?.addEventListener('change', this.handleFilterChange);
        this.elements.yearTo?.addEventListener('change', this.handleFilterChange);

        // Filter checkboxes
        document.querySelectorAll('[data-filter]').forEach(checkbox => {
            checkbox.addEventListener('change', this.handleFilterChange);
        });
    }

    async performSearch() {
        try {
            this.showLoading();
            
            const params = this.buildSearchParams();
            const response = await fetch(`/api/movies/search?${params.toString()}`);
            const data = await response.json();
            
            this.updateResults(data);
            this.updatePagination(data.hits.total.value);
            this.updateResultCount(data.hits.total.value);
            
            // Update URL with search parameters
            history.pushState(
                {}, 
                '', 
                `${window.location.pathname}?${params.toString()}`
            );
            
        } catch (error) {
            console.error('Search error:', error);
            this.showError('Failed to perform search');
        } finally {
            this.hideLoading();
        }
    }

    buildSearchParams() {
        const params = new URLSearchParams();
        
        if (this.state.currentQuery) {
            params.append('query', this.state.currentQuery);
        }
        
        params.append('page', this.state.currentPage.toString());
        params.append('sort', this.state.currentSort);
        
        if (this.state.filters.genres.length) {
            params.append('genres', this.state.filters.genres.join(','));
        }
        if (this.state.filters.languages.length) {
            params.append('languages', this.state.filters.languages.join(','));
        }
        if (this.state.filters.rating > 0) {
            params.append('rating', this.state.filters.rating.toString());
        }
        if (this.state.filters.yearFrom) {
            params.append('yearFrom', this.state.filters.yearFrom);
        }
        if (this.state.filters.yearTo) {
            params.append('yearTo', this.state.filters.yearTo);
        }
        if (this.state.filters.contentRating.length) {
            params.append('contentRating', this.state.filters.contentRating.join(','));
        }
        
        return params;
    }

    updateResults(data) {
        if (!this.elements.searchResults) return;

        if (data.hits.hits.length === 0) {
            this.elements.searchResults.innerHTML = this.getNoResultsHTML();
            return;
        }

        this.elements.searchResults.innerHTML = data.hits.hits
            .map(hit => this.getMovieCardHTML(hit._source))
            .join('');
    }

    getNoResultsHTML() {
        return `
            <div class="col-span-full text-center py-12">
                <i class="fas fa-search text-6xl text-gray-600 mb-4"></i>
                <h2 class="text-2xl font-bold mb-2">No results found</h2>
                <p class="text-gray-400">Try adjusting your filters or search terms</p>
            </div>
        `;
    }

    getMovieCardHTML(movie) {
        return `
            <div class="movie-card bg-gray-800 rounded-lg overflow-hidden cursor-pointer shadow-lg"
                 onclick="movieSearch.showMovieDetails('${movie.movie_id}')">
                <div class="relative aspect-[2/3]">
                    <img src="${movie.poster_url}" 
                         alt="${movie.title}"
                         class="w-full h-full object-cover">
                    <div class="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent opacity-0 hover:opacity-100 transition-opacity">
                        <div class="absolute bottom-0 left-0 p-4">
                            <div class="flex items-center space-x-2 text-sm">
                                <span class="text-green-500">${movie.imdb_rating}/10</span>
                                <span class="text-gray-300">${movie.runtime} min</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="p-4">
                    <h3 class="font-bold text-lg mb-2">${movie.title}</h3>
                    <div class="text-sm text-gray-400 mb-2">
                        ${movie.release_date.split('T')[0]} • ${movie.language}
                    </div>
                    <div class="text-sm text-gray-400">
                        ${movie.genres.join(', ')}
                    </div>
                </div>
            </div>
        `;
    }

    updatePagination(total) {
        if (!this.elements.pagination) return;

        const totalPages = Math.ceil(total / 20);
        let paginationHtml = '';
        
        if (totalPages > 1) {
            paginationHtml = this.getPaginationHTML(totalPages);
        }
        
        this.elements.pagination.innerHTML = paginationHtml;
    }

    getPaginationHTML(totalPages) {
        let html = '';
        
        // Previous button
        if (this.state.currentPage > 1) {
            html += `
                <button onclick="movieSearch.handlePageChange(${this.state.currentPage - 1})" 
                        class="px-4 py-2 bg-gray-800 rounded hover:bg-gray-700 text-gray-300">
                    <i class="fas fa-chevron-left mr-2"></i>Previous
                </button>
            `;
        }
        
        // Page numbers
        for (let i = Math.max(1, this.state.currentPage - 2); 
             i <= Math.min(totalPages, this.state.currentPage + 2); i++) {
            html += `
                <button onclick="movieSearch.handlePageChange(${i})" 
                        class="px-4 py-2 rounded ${i === this.state.currentPage ? 
                            'bg-red-600 text-white' : 
                            'bg-gray-800 hover:bg-gray-700 text-gray-300'}">
                    ${i}
                </button>
            `;
        }
        
        // Next button
        if (this.state.currentPage < totalPages) {
            html += `
                <button onclick="movieSearch.handlePageChange(${this.state.currentPage + 1})" 
                        class="px-4 py-2 bg-gray-800 rounded hover:bg-gray-700 text-gray-300">
                    Next<i class="fas fa-chevron-right ml-2"></i>
                </button>
            `;
        }
        
        return html;
    }

    updateResultCount(total) {
        if (!this.elements.resultsCount) return;

        if (this.state.currentQuery) {
            this.elements.resultsCount.textContent = 
                `Found ${total} results for "${this.state.currentQuery}"`;
        } else {
            this.elements.resultsCount.textContent = `${total} movies`;
        }
    }

    handleSortChange(event) {
        this.state.currentSort = event.target.value;
        this.state.currentPage = 1;
        this.performSearch();
    }

    handleFilterChange() {
        this.state.filters.genres = Array.from(
            document.querySelectorAll('[data-filter="genre"]:checked')
        ).map(cb => cb.value);

        this.state.filters.languages = Array.from(
            document.querySelectorAll('[data-filter="language"]:checked')
        ).map(cb => cb.value);

        this.state.filters.contentRating = Array.from(
            document.querySelectorAll('[data-filter="content-rating"]:checked')
        ).map(cb => cb.value);

        this.state.filters.yearFrom = this.elements.yearFrom?.value || null;
        this.state.filters.yearTo = this.elements.yearTo?.value || null;

        this.state.currentPage = 1;
        this.performSearch();
    }

    handlePageChange(page) {
        this.state.currentPage = page;
        this.performSearch();
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }

    async showMovieDetails(movieId) {
        try {
            this.showLoading();
            const response = await fetch(`/api/movies/${movieId}`);
            const movie = await response.json();
            
            if (!this.elements.modalContent) return;
            
            this.elements.modalContent.innerHTML = this.getMovieDetailsHTML(movie);
            this.elements.movieModal?.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
            
        } catch (error) {
            console.error('Error loading movie details:', error);
            this.showError('Failed to load movie details');
        } finally {
            this.hideLoading();
        }
    }

    getMovieDetailsHTML(movie) {
        return `
            <div class="relative h-[400px] bg-cover bg-center" 
                 style="background-image: url('${movie.poster_url}')">
                <div class="absolute inset-0 bg-gradient-to-t from-gray-900 to-transparent"></div>
                <div class="absolute bottom-0 left-0 p-8">
                    <h2 class="text-4xl font-bold mb-4">${movie.title}</h2>
                    <div class="flex items-center space-x-4 mb-4">
                        <span class="text-green-500">${movie.imdb_rating}/10</span>
                        <span>${movie.release_date}</span>
                        <span>${movie.runtime} min</span>
                        <span class="px-2 py-1 bg-gray-800 rounded">${movie.content_rating}</span>
                    </div>
                    <div class="flex space-x-4">
                        <a href="${movie.streaming_url}" target="_blank"
                           class="bg-red-600 text-white px-8 py-3 rounded-lg hover:bg-red-700 flex items-center">
                            <i class="fas fa-play mr-2"></i> Play
                        </a>
                        <a href="${movie.trailer_url}" target="_blank"
                           class="bg-gray-600 text-white px-8 py-3 rounded-lg hover:bg-gray-700 flex items-center">
                            <i class="fas fa-film mr-2"></i> Trailer
                        </a>
                        <button onclick="movieSearch.addToWatchlist('${movie.movie_id}')"
                                class="bg-gray-600 text-white px-8 py-3 rounded-lg hover:bg-gray-700 flex items-center">
                            <i class="fas fa-plus mr-2"></i> Watchlist
                        </button>
                    </div>
                </div>
            </div>
            <div class="p-8">
                <p class="text-lg mb-6">${movie.plot_summary}</p>
                <div class="grid grid-cols-2 gap-8">
                    <div>
                        <h3 class="text-lg font-bold mb-2">Cast</h3>
                        <p>${movie.cast.join(', ')}</p>
                    </div>
                    <div>
                        <h3 class="text-lg font-bold mb-2">Director</h3>
                        <p>${movie.director}</p>
                    </div>
                    <div>
                        <h3 class="text-lg font-bold mb-2">Genres</h3>
                        <p>${movie.genres.join(', ')}</p>
                    </div>
                    <div>
                        <h3 class="text-lg font-bold mb-2">Language</h3>
                        <p>${movie.language}</p>
                    </div>
                </div>
                
                <!-- Additional Movie Details -->
                <div class="mt-8">
                    <h3 class="text-lg font-bold mb-4">Additional Information</h3>
                    <div class="grid grid-cols-2 gap-8">
                        <div>
                            <h4 class="text-sm text-gray-400">Release Date</h4>
                            <p>${new Date(movie.release_date).toLocaleDateString()}</p>
                        </div>
                        <div>
                            <h4 class="text-sm text-gray-400">Runtime</h4>
                            <p>${movie.runtime} minutes</p>
                        </div>
                        <div>
                            <h4 class="text-sm text-gray-400">Production Companies</h4>
                            <p>${movie.production_companies.join(', ')}</p>
                        </div>
                        <div>
                            <h4 class="text-sm text-gray-400">Content Rating</h4>
                            <p>${movie.content_rating}</p>
                        </div>
                    </div>
                </div>

                <!-- Similar Movies Section -->
                <div class="mt-8">
                    <h3 class="text-lg font-bold mb-4">Similar Movies</h3>
                    <div id="similar-movies" class="grid grid-cols-4 gap-4">
                        <!-- Similar movies will be loaded dynamically -->
                    </div>
                </div>
            </div>
        `;
    }

    closeMovieModal() {
        this.elements.movieModal?.classList.add('hidden');
        document.body.style.overflow = 'auto';
    }

    async addToWatchlist(movieId) {
        try {
            const response = await fetch('/api/watchlist/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ movieId })
            });
            
            if (response.ok) {
                this.showSuccess('Added to watchlist');
            } else {
                throw new Error('Failed to add to watchlist');
            }
        } catch (error) {
            console.error('Error adding to watchlist:', error);
            this.showError('Failed to add to watchlist');
        }
    }

    showLoading() {
        this.state.isLoading = true;
        this.elements.loadingOverlay?.classList.remove('hidden');
    }

    hideLoading() {
        this.state.isLoading = false;
        this.elements.loadingOverlay?.classList.add('hidden');
    }

    showError(message) {
        const notification = document.createElement('div');
        notification.className = 
            'fixed bottom-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg';
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    showSuccess(message) {
        const notification = document.createElement('div');
        notification.className = 
            'fixed bottom-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg';
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// Initialize the search module
const movieSearch = new MovieSearch();

// Export for global access
window.movieSearch = movieSearch;