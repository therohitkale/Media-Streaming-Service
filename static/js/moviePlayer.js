class MoviePlayer {
    constructor() {
        this.state = {
            currentMovie: null,
            isPlaying: false,
            currentTime: 0,
            duration: 0,
            volume: 1,
            isMuted: false,
            isFullscreen: false,
            quality: 'auto',
            playbackSpeed: 1,
            subtitles: 'off'
        };

        this.elements = {
            container: document.getElementById('movie-player-container'),
            video: document.getElementById('video-element'),
            controls: document.getElementById('player-controls'),
            playButton: document.getElementById('play-button'),
            progressBar: document.getElementById('progress-bar'),
            currentTimeDisplay: document.getElementById('current-time'),
            durationDisplay: document.getElementById('duration'),
            volumeControl: document.getElementById('volume-control'),
            muteButton: document.getElementById('mute-button'),
            fullscreenButton: document.getElementById('fullscreen-button'),
            settingsButton: document.getElementById('settings-button'),
            settingsMenu: document.getElementById('settings-menu'),
            qualityOptions: document.getElementById('quality-options'),
            speedOptions: document.getElementById('speed-options'),
            subtitlesButton: document.getElementById('subtitles-button'),
            subtitlesMenu: document.getElementById('subtitles-menu'),
            loader: document.getElementById('player-loader')
        };

        this.bindEvents();
    }

    bindEvents() {
        // Video element events
        this.elements.video?.addEventListener('loadedmetadata', () => this.onVideoLoaded());
        this.elements.video?.addEventListener('timeupdate', () => this.onTimeUpdate());
        this.elements.video?.addEventListener('play', () => this.onPlay());
        this.elements.video?.addEventListener('pause', () => this.onPause());
        this.elements.video?.addEventListener('waiting', () => this.showLoader());
        this.elements.video?.addEventListener('playing', () => this.hideLoader());
        this.elements.video?.addEventListener('ended', () => this.onEnded());

        // Control events
        this.elements.playButton?.addEventListener('click', () => this.togglePlay());
        this.elements.progressBar?.addEventListener('input', (e) => this.seek(e.target.value));
        this.elements.volumeControl?.addEventListener('input', (e) => this.setVolume(e.target.value));
        this.elements.muteButton?.addEventListener('click', () => this.toggleMute());
        this.elements.fullscreenButton?.addEventListener('click', () => this.toggleFullscreen());
        this.elements.settingsButton?.addEventListener('click', () => this.toggleSettings());

        // Keyboard controls
        document.addEventListener('keydown', (e) => this.handleKeyPress(e));

        // Auto-hide controls
        let controlsTimeout;
        this.elements.container?.addEventListener('mousemove', () => {
            this.showControls();
            clearTimeout(controlsTimeout);
            controlsTimeout = setTimeout(() => this.hideControls(), 3000);
        });

        this.elements.container?.addEventListener('mouseleave', () => {
            if (this.state.isPlaying) {
                this.hideControls();
            }
        });
    }

    async loadMovie(movieId) {
        try {
            this.showLoader();
            const response = await fetch(`/api/movies/${movieId}/stream`);
            const movieData = await response.json();
            
            this.state.currentMovie = movieData;
            
            if (this.elements.video) {
                this.elements.video.src = movieData.streamingUrl;
                this.elements.video.poster = movieData.poster_url;

                // Set up qualities if available
                if (movieData.qualities) {
                    this.setupQualityOptions(movieData.qualities);
                }

                // Set up subtitles if available
                if (movieData.subtitles) {
                    this.setupSubtitles(movieData.subtitles);
                }
            }
            
            this.hideLoader();
            return true;
        } catch (error) {
            console.error('Error loading movie:', error);
            this.showError('Failed to load movie');
            return false;
        }
    }

    setupQualityOptions(qualities) {
        if (!this.elements.qualityOptions) return;

        this.elements.qualityOptions.innerHTML = qualities.map(quality => `
            <button class="quality-option ${this.state.quality === quality ? 'active' : ''}"
                    onclick="player.setQuality('${quality}')">
                ${quality}p
            </button>
        `).join('');
    }

    setupSubtitles(subtitles) {
        if (!this.elements.video) return;

        // Remove existing tracks
        while (this.elements.video.firstChild) {
            this.elements.video.removeChild(this.elements.video.firstChild);
        }

        // Add new subtitle tracks
        subtitles.forEach(sub => {
            const track = document.createElement('track');
            track.kind = 'subtitles';
            track.label = sub.label;
            track.srclang = sub.lang;
            track.src = sub.url;
            this.elements.video.appendChild(track);
        });

        // Update subtitles menu
        if (this.elements.subtitlesMenu) {
            this.elements.subtitlesMenu.innerHTML = `
                <button class="subtitle-option ${this.state.subtitles === 'off' ? 'active' : ''}"
                        onclick="player.setSubtitles('off')">
                    Off
                </button>
                ${subtitles.map(sub => `
                    <button class="subtitle-option ${this.state.subtitles === sub.lang ? 'active' : ''}"
                            onclick="player.setSubtitles('${sub.lang}')">
                        ${sub.label}
                    </button>
                `).join('')}
            `;
        }
    }

    togglePlay() {
        if (!this.elements.video) return;
        
        if (this.state.isPlaying) {
            this.elements.video.pause();
        } else {
            this.elements.video.play();
        }
    }

    seek(time) {
        if (!this.elements.video) return;
        
        const newTime = (time * this.elements.video.duration) / 100;
        this.elements.video.currentTime = newTime;
    }

    setVolume(volume) {
        if (!this.elements.video) return;
        
        this.state.volume = volume;
        this.elements.video.volume = volume;
        
        // Update volume icon
        if (this.elements.muteButton) {
            if (volume === 0) {
                this.elements.muteButton.innerHTML = '<i class="fas fa-volume-mute"></i>';
            } else if (volume < 0.5) {
                this.elements.muteButton.innerHTML = '<i class="fas fa-volume-down"></i>';
            } else {
                this.elements.muteButton.innerHTML = '<i class="fas fa-volume-up"></i>';
            }
        }
    }

    toggleMute() {
        if (!this.elements.video) return;
        
        if (this.state.isMuted) {
            this.elements.video.volume = this.state.volume;
            this.state.isMuted = false;
        } else {
            this.elements.video.volume = 0;
            this.state.isMuted = true;
        }
    }

    toggleFullscreen() {
        if (!this.elements.container) return;
        
        if (!document.fullscreenElement) {
            this.elements.container.requestFullscreen();
            this.state.isFullscreen = true;
        } else {
            document.exitFullscreen();
            this.state.isFullscreen = false;
        }
    }

    setQuality(quality) {
        if (!this.state.currentMovie?.qualities) return;
        
        this.state.quality = quality;
        const currentTime = this.elements.video?.currentTime || 0;
        
        // Update video source with new quality
        if (this.elements.video) {
            this.elements.video.src = this.state.currentMovie.qualities.find(q => q.quality === quality).url;
            this.elements.video.currentTime = currentTime;
        }
        
        // Update quality menu
        document.querySelectorAll('.quality-option').forEach(option => {
            option.classList.toggle('active', option.textContent === `${quality}p`);
        });
    }

    setPlaybackSpeed(speed) {
        if (!this.elements.video) return;
        
        this.state.playbackSpeed = speed;
        this.elements.video.playbackRate = speed;
        
        // Update speed menu
        document.querySelectorAll('.speed-option').forEach(option => {
            option.classList.toggle('active', option.textContent === `${speed}x`);
        });
    }

    setSubtitles(lang) {
        if (!this.elements.video) return;
        
        this.state.subtitles = lang;
        
        // Update subtitle tracks
        Array.from(this.elements.video.textTracks).forEach(track => {
            track.mode = track.language === lang ? 'showing' : 'hidden';
        });
        
        // Update subtitles menu
        document.querySelectorAll('.subtitle-option').forEach(option => {
            option.classList.toggle('active', 
                (lang === 'off' && option.textContent === 'Off') || 
                option.getAttribute('data-lang') === lang
            );
        });
    }

    onVideoLoaded() {
        if (!this.elements.video) return;
        
        this.state.duration = this.elements.video.duration;
        if (this.elements.durationDisplay) {
            this.elements.durationDisplay.textContent = this.formatTime(this.state.duration);
        }
    }

    onTimeUpdate() {
        if (!this.elements.video) return;
        
        this.state.currentTime = this.elements.video.currentTime;
        
        // Update progress bar
        if (this.elements.progressBar) {
            const progress = (this.state.currentTime / this.state.duration) * 100;
            this.elements.progressBar.value = progress;
        }
        
        // Update time display
        if (this.elements.currentTimeDisplay) {
            this.elements.currentTimeDisplay.textContent = this.formatTime(this.state.currentTime);
        }
    }

    onPlay() {
        this.state.isPlaying = true;
        if (this.elements.playButton) {
            this.elements.playButton.innerHTML = '<i class="fas fa-pause"></i>';
        }
    }

    onPause() {
        this.state.isPlaying = false;
        if (this.elements.playButton) {
            this.elements.playButton.innerHTML = '<i class="fas fa-play"></i>';
        }
    }

    onEnded() {
        this.state.isPlaying = false;
        if (this.elements.playButton) {
            this.elements.playButton.innerHTML = '<i class="fas fa-redo"></i>';
        }
    }

    handleKeyPress(event) {
        switch(event.key.toLowerCase()) {
            case ' ':
            case 'k':
                event.preventDefault();
                this.togglePlay();
                break;
            case 'f':
                event.preventDefault();
                this.toggleFullscreen();
                break;
            case 'm':
                event.preventDefault();
                this.toggleMute();
                break;
            case 'arrowleft':
                event.preventDefault();
                this.seek(this.state.currentTime - 10);
                break;
            case 'arrowright':
                event.preventDefault();
                this.seek(this.state.currentTime + 10);
                break;
            case 'arrowup':
                event.preventDefault();
                this.setVolume(Math.min(1, this.state.volume + 0.1));
                break;
            case 'arrowdown':
                event.preventDefault();
                this.setVolume(Math.max(0, this.state.volume - 0.1));
                break;
        }
    }

    showControls() {
        this.elements.controls?.classList.remove('opacity-0');
    }

    hideControls() {
        if (this.state.isPlaying) {
            this.elements.controls?.classList.add('opacity-0');
        }
    }

    showLoader() {
        this.elements.loader?.classList.remove('hidden');
    }

    hideLoader() {
        this.elements.loader?.classList.add('hidden');
    }

    formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }

    showError(message) {
        const notification = document.createElement('div');
        notification.className = 
            'fixed bottom-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// Initialize player
const player = new MoviePlayer();

// Export for global access
window.player = player;