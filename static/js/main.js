
// Global state management
const state = {
    currentUser: null,
    isLoading: false,
    searchQuery: '',
    filters: {
        genres: [],
        year: null,
        rating: null,
        language: null
    },
    currentPage: 1
};

// DOM Elements
const elements = {
    navBar: document.querySelector('.nav-wrapper'),
    searchInput: document.querySelector('#search-input'),
    searchResults: document.querySelector('#search-results'),
    genreSliders: document.querySelectorAll('.genre-slider'),
    movieModal: document.querySelector('#movie-modal'),
    loadingOverlay: document.querySelector('#loading-overlay'),
    loginModal: document.querySelector('#login-modal')
};

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    initializeNavigation();
    initializeSearch();
    initializeSliders();
    initializeModals();
    handleAuthentication();
});

// Navigation functionality
function initializeNavigation() {
    // Navbar scroll effect
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            elements.navBar?.classList.add('scrolled');
        } else {
            elements.navBar?.classList.remove('scrolled');
        }
    });

    // Mobile menu toggle
    const mobileMenuButton = document.querySelector('#mobile-menu-button');
    const mobileMenu = document.querySelector('#mobile-menu');

    mobileMenuButton?.addEventListener('click', () => {
        mobileMenu?.classList.toggle('hidden');
    });
}

// Search functionality
function initializeSearch() {
    let searchTimeout;

    elements.searchInput?.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        state.searchQuery = e.target.value.trim();

        if (state.searchQuery.length > 2) {
            searchTimeout = setTimeout(() => {
                performSearch();
            }, 500);
        } else {
            elements.searchResults.innerHTML = '';
            elements.searchResults?.classList.add('hidden');
        }
    });
}

async function performSearch() {
    try {
        showLoading();
        const response = await fetch(`/api/movies/search?query=${encodeURIComponent(state.searchQuery)}`);
        const data = await response.json();
        displaySearchResults(data.hits.hits);
    } catch (error) {
        console.error('Search error:', error);
        showError('Failed to perform search');
    } finally {
        hideLoading();
    }
}

function displaySearchResults(results) {
    if (!elements.searchResults) return;

    if (results.length === 0) {
        elements.searchResults.innerHTML = `
            <div class="p-4 text-center text-gray-400">
                No results found for "${state.searchQuery}"
            </div>
        `;
        elements.searchResults.classList.remove('hidden');
        return;
    }

    elements.searchResults.innerHTML = results.map(movie => `
        <a href="/movie/${movie._source.movie_id}" 
           class="block p-4 hover:bg-gray-800 transition-colors">
            <div class="flex items-center space-x-4">
                <img src="${movie._source.poster_url}" 
                     alt="${movie._source.title}"
                     class="w-16 h-24 object-cover rounded">
                <div>
                    <h3 class="font-medium mb-1">${movie._source.title}</h3>
                    <div class="text-sm text-gray-400">
                        ${movie._source.release_date.split('T')[0]} • 
                        ${movie._source.genres.join(', ')}
                    </div>
                </div>
            </div>
        </a>
    `).join('');

    elements.searchResults.classList.remove('hidden');
}

// Slider functionality
function initializeSliders() {
    elements.genreSliders.forEach(slider => {
        const slideWidth = 250; // Width of movie card + margin
        const slidesVisible = Math.floor(slider.offsetWidth / slideWidth);
        
        const prevButton = slider.parentElement.querySelector('.slider-prev');
        const nextButton = slider.parentElement.querySelector('.slider-next');

        prevButton?.addEventListener('click', () => {
            slider.scrollBy({
                left: -slideWidth * slidesVisible,
                behavior: 'smooth'
            });
        });

        nextButton?.addEventListener('click', () => {
            slider.scrollBy({
                left: slideWidth * slidesVisible,
                behavior: 'smooth'
            });
        });

        // Hide/show buttons based on scroll position
        slider.addEventListener('scroll', () => {
            if (prevButton && nextButton) {
                prevButton.style.display = slider.scrollLeft > 0 ? 'flex' : 'none';
                nextButton.style.display = 
                    slider.scrollLeft < (slider.scrollWidth - slider.offsetWidth - 10) ? 'flex' : 'none';
            }
        });
    });
}

// Modal functionality
function initializeModals() {
    // Close modals when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal-backdrop')) {
            closeAllModals();
        }
    });

    // Close modals with escape key
    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });
}

function showMovieModal(movieId) {
    if (!elements.movieModal) return;

    elements.movieModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    loadMovieDetails(movieId);
}

async function loadMovieDetails(movieId) {
    try {
        showLoading();
        const response = await fetch(`/api/movies/${movieId}`);
        const movie = await response.json();
        
        const modalContent = elements.movieModal.querySelector('.modal-content');
        if (!modalContent) return;

        modalContent.innerHTML = createMovieDetailHTML(movie);

        // Load similar movies
        loadSimilarMovies(movieId);
        
    } catch (error) {
        console.error('Error loading movie details:', error);
        showError('Failed to load movie details');
    } finally {
        hideLoading();
    }
}

function createMovieDetailHTML(movie) {
    return `
        <div class="relative">
            <div class="h-96 bg-cover bg-center" 
                 style="background-image: url('${movie.poster_url}')">
                <div class="absolute inset-0 bg-gradient-to-t from-gray-900 to-transparent"></div>
            </div>
            <div class="absolute bottom-0 left-0 p-8 text-shadow">
                <h2 class="text-4xl font-bold mb-4">${movie.title}</h2>
                <div class="flex items-center space-x-4 mb-4">
                    <span class="text-green-500">${movie.imdb_rating}/10</span>
                    <span>${movie.release_date}</span>
                    <span>${movie.runtime} min</span>
                    <span class="px-2 py-1 bg-gray-800 rounded">${movie.content_rating}</span>
                </div>
                <div class="flex space-x-4">
                    <button onclick="playMovie('${movie.streaming_url}')" 
                            class="bg-red-600 text-white px-8 py-3 rounded-lg hover:bg-red-700">
                        <i class="fas fa-play mr-2"></i> Play
                    </button>
                    <button onclick="watchTrailer('${movie.trailer_url}')"
                            class="bg-gray-600 text-white px-8 py-3 rounded-lg hover:bg-gray-700">
                        <i class="fas fa-film mr-2"></i> Trailer
                    </button>
                </div>
            </div>
        </div>
        <!-- Add more movie details sections here -->
    `;
}

// Utility functions
function showLoading() {
    state.isLoading = true;
    elements.loadingOverlay?.classList.remove('hidden');
}

function hideLoading() {
    state.isLoading = false;
    elements.loadingOverlay?.classList.add('hidden');
}

function showError(message) {
    // Implement error notification
    console.error(message);
}

function closeAllModals() {
    elements.movieModal?.classList.add('hidden');
    elements.loginModal?.classList.add('hidden');
    document.body.style.overflow = 'auto';
}

// Authentication handling
function handleAuthentication() {
    const loginForm = document.querySelector('#login-form');
    loginForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        // Implement login logic
    });
}

// Player functionality
function playMovie(url) {
    window.open(url, '_blank');
}

function watchTrailer(url) {
    window.open(url, '_blank');
}

// Export functions for use in other modules
export {
    showMovieModal,
    playMovie,
    watchTrailer,
    performSearch,
    showLoading,
    hideLoading
};

// Initialize tooltips, popovers, etc.
document.addEventListener('DOMContentLoaded', () => {
    // Initialize any third-party libraries here
});

// Add event listener for dynamic content
document.addEventListener('click', (e) => {
    // Handle dynamic content clicks
    if (e.target.matches('.movie-card')) {
        const movieId = e.target.dataset.movieId;
        if (movieId) {
            showMovieModal(movieId);
        }
    }
});

// Handle infinite scroll for movie listings
let isLoadingMore = false;
window.addEventListener('scroll', () => {
    const scrollPosition = window.innerHeight + window.scrollY;
    const pageHeight = document.documentElement.scrollHeight;

    if (scrollPosition >= pageHeight - 1000 && !isLoadingMore) {
        isLoadingMore = true;
        loadMoreMovies();
    }
});

async function loadMoreMovies() {
    try {
        state.currentPage++;
        // Implement loading more movies
        const response = await fetch(`/api/movies/search?page=${state.currentPage}`);
        const data = await response.json();
        appendMovies(data.hits.hits);
    } catch (error) {
        console.error('Error loading more movies:', error);
    } finally {
        isLoadingMore = false;
    }
}

function appendMovies(movies) {
    const container = document.querySelector('#movies-container');
    if (!container) return;

    const movieHTML = movies.map(movie => `
        <div class="movie-card" data-movie-id="${movie._source.movie_id}">
            <!-- Movie card content -->
        </div>
    `).join('');

    container.insertAdjacentHTML('beforeend', movieHTML);
}
