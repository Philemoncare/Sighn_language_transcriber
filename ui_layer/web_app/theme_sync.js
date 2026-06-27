/**
 * SnLag Unified Theme & Branding Synchronization
 * Proprietary Neural Core v2.0
 */

const SnLagTheme = {
    tokens: {
        light: {
            '--primary': '#f97316',
            '--primary-glow': 'rgba(249, 115, 22, 0.4)',
            '--secondary': '#fbbf24',
            '--bg': '#fafafa',
            '--surface': '#ffffff',
            '--text-main': '#171717',
            '--text-muted': '#737373',
            '--border': 'rgba(0, 0, 0, 0.05)',
            '--glass': 'rgba(255, 255, 255, 0.7)'
        },
        dark: {
            '--primary': '#f97316',
            '--primary-glow': 'rgba(249, 115, 22, 0.3)',
            '--secondary': '#fbbf24',
            '--bg': '#0a0a0a',
            '--surface': '#171717',
            '--text-main': '#f5f5f5',
            '--text-muted': '#a3a3a3',
            '--border': 'rgba(255, 255, 255, 0.05)',
            '--glass': 'rgba(23, 23, 23, 0.7)'
        }
    },

    apply(mode = 'light') {
        const root = document.documentElement;
        const set = this.tokens[mode] || this.tokens.light;

        Object.entries(set).forEach(([key, val]) => {
            root.style.setProperty(key, val);
        });

        document.body.classList.toggle('dark-mode', mode === 'dark');
        localStorage.setItem('snlag_theme', mode);

        // Sync with Tailwind if needed (programmatic)
        if (mode === 'dark') {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    },

    init() {
        const saved = localStorage.getItem('snlag_theme') || 'light';
        this.apply(saved);
    }
};

const SnLagBranding = {
    getLogoHtml(size = 'md') {
        const sizes = { sm: 'w-8 h-8', md: 'w-12 h-12', lg: 'w-20 h-20' };
        const iconSizes = { sm: 'text-xs', md: 'text-xl', lg: 'text-4xl' };

        return `
            <div class="${sizes[size]} bg-primary rounded-xl flex items-center justify-center text-white shadow-lg shadow-primary/30 rotate-3 transition-transform hover:rotate-0">
                <i class="fas fa-brain ${iconSizes[size]}"></i>
            </div>
        `;
    }
};

SnLagTheme.init();
