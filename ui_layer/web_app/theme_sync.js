/**
 * SnLag Unified Theme & Branding Synchronization
 * Proprietary Neural Core v3.0
 */

const SnLagTheme = {
    // DESIGN TOKENS
    tokens: {
        light: {
            '--primary': '#f97316',
            '--primary-glow': 'rgba(249, 115, 22, 0.25)',
            '--secondary': '#fbbf24',
            '--accent': '#8b5cf6',
            '--success': '#10b981',
            '--warning': '#f59e0b',
            '--error': '#ef4444',
            '--bg': '#fafafa',
            '--surface': '#ffffff',
            '--surface-muted': '#f3f4f6',
            '--text-main': '#171717',
            '--text-muted': '#737373',
            '--border': 'rgba(0, 0, 0, 0.05)',
            '--glass': 'rgba(255, 255, 255, 0.7)',
            '--nav-bg': 'rgba(255, 255, 255, 0.8)'
        },
        dark: {
            '--primary': '#f97316',
            '--primary-glow': 'rgba(249, 115, 22, 0.15)',
            '--secondary': '#fbbf24',
            '--accent': '#a78bfa',
            '--success': '#34d399',
            '--warning': '#fbbf24',
            '--error': '#f87171',
            '--bg': '#0a0a0a',
            '--surface': '#171717',
            '--surface-muted': '#262626',
            '--text-main': '#f5f5f5',
            '--text-muted': '#a3a3a3',
            '--border': 'rgba(255, 255, 255, 0.05)',
            '--glass': 'rgba(23, 23, 23, 0.7)',
            '--nav-bg': 'rgba(10, 10, 10, 0.8)'
        }
    },

    apply(mode = 'light') {
        const root = document.documentElement;
        const set = this.tokens[mode] || this.tokens.light;

        Object.entries(set).forEach(([key, val]) => {
            root.style.setProperty(key, val);
        });

        if (mode === 'dark') {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }

        localStorage.setItem('snlag_theme', mode);
        console.log(`Neural Core: Theme synced to ${mode.toUpperCase()}`);
    },

    init() {
        const saved = localStorage.getItem('snlag_theme') || 'light';
        this.apply(saved);

        // Listen for system changes if preferred
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
            if (!localStorage.getItem('snlag_theme')) {
                this.apply(e.matches ? 'dark' : 'light');
            }
        });
    }
};

SnLagTheme.init();
