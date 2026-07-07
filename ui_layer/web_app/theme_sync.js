/**
 * Signly Global Theme Architecture v11.0
 * Handles persistence and synchronization of Light/Dark modes.
 */

function toggleTheme() {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('snlag_theme', isDark ? 'dark' : 'light');

    // Announce to other tabs
    window.dispatchEvent(new Event('theme-changed'));

    console.log(`Theme Switched: ${isDark ? 'Dark' : 'Light'} Mode`);
}

function initTheme() {
    const savedTheme = localStorage.getItem('snlag_theme');

    // Respect user preference or system default
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
}

// Global hook for external components
window.addEventListener('theme-changed', () => {
    // Optional: Re-render components if they don't use CSS variables
});

// Run initialization immediately to prevent flash of unstyled theme
initTheme();
