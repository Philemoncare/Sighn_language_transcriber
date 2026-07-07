/**
 * Signly Design System Components v12.0
 * Modern SaaS-grade UI components with Light/Dark Mode support.
 */

const SnLagUI = {
    /**
     * Sidebar Navigation (Desktop)
     */
    getSidebar(activeId = 'dashboard', userData = {}) {
        return `
            <aside class="sidebar motion-entrance">
                <div class="flex items-center justify-between px-6 py-8 mb-4">
                    ${this.getLogo()}
                </div>

                <nav class="flex-1 px-4 space-y-8 overflow-y-auto">
                    <div class="space-y-1">
                        <p class="px-4 text-[10px] font-bold text-muted uppercase tracking-[0.2em] mb-4">Platform</p>
                        ${this.getSidebarLink('dashboard', 'fa-th-large', 'Workspace', activeId === 'dashboard')}
                        ${this.getSidebarLink('meetings', 'fa-video', 'Live Engine', activeId === 'meetings')}
                        ${this.getSidebarLink('library', 'fa-book-open', 'Gesture Library', activeId === 'library')}
                    </div>

                    <div class="space-y-1">
                        <p class="px-4 text-[10px] font-bold text-muted uppercase tracking-[0.2em] mb-4">Personal</p>
                        ${this.getSidebarLink('history', 'fa-history', 'Activity Log', activeId === 'history')}
                        ${this.getSidebarLink('profile', 'fa-user-circle', 'Identity', activeId === 'profile')}
                        ${this.getSidebarLink('settings', 'fa-sliders-h', 'Preferences', activeId === 'settings')}
                    </div>
                </nav>

                <div class="px-4 py-6 mt-auto border-t border-border space-y-4">
                    <div class="flex items-center justify-between px-4">
                        <span class="text-[10px] font-bold text-muted uppercase tracking-widest">Theme</span>
                        <button onclick="toggleTheme()" class="theme-toggle">
                            <i class="fas fa-moon block dark:hidden"></i>
                            <i class="fas fa-sun hidden dark:block"></i>
                        </button>
                    </div>
                    ${this.getCompactUserCard(userData)}
                </div>
            </aside>
        `;
    },

    getSidebarLink(id, icon, label, isActive) {
        return `
            <button onclick="switchView('${id}')"
                class="nav-link w-full flex items-center gap-4 px-4 py-3 rounded-xl transition-all group
                ${isActive ? 'active text-primary bg-primary-alpha' : 'text-muted hover:text-primary hover:bg-bg'}">
                <i class="fas ${icon} nav-icon"></i>
                <span class="font-bold">${label}</span>
            </button>
        `;
    },

    /**
     * Bottom Navigation (Mobile)
     */
    getBottomNav(activeId = 'dashboard') {
        return `
            <nav class="bottom-nav">
                ${this.getBottomNavLink('dashboard', 'fa-th-large', 'Home', activeId === 'dashboard')}
                ${this.getBottomNavLink('meetings', 'fa-video', 'Live', activeId === 'meetings')}
                ${this.getBottomNavLink('library', 'fa-book-open', 'Library', activeId === 'library')}
                ${this.getBottomNavLink('settings', 'fa-sliders-h', 'Settings', activeId === 'settings')}
            </nav>
        `;
    },

    getBottomNavLink(id, icon, label, isActive) {
        return `
            <button onclick="switchView('${id}')"
                class="nav-link ${isActive ? 'active text-primary' : 'text-muted'}">
                <i class="fas ${icon} nav-icon"></i>
                <span class="text-[10px] font-bold uppercase tracking-widest">${label}</span>
            </button>
        `;
    },

    getLogo() {
        return `
            <div class="flex items-center gap-3 select-none cursor-pointer" onclick="window.location.href='index.html'">
                <div class="flex items-center justify-center w-10 h-10 rounded-xl bg-primary text-white shadow-lg shadow-primary/20">
                    <i class="fas fa-hand-holding-heart"></i>
                </div>
                <span class="text-xl font-black tracking-tighter text-primary">Signly</span>
            </div>
        `;
    },

    getCompactUserCard(user) {
        return `
            <div class="flex items-center gap-4 p-3 rounded-2xl bg-surface-raised border border-border group relative cursor-pointer hover:bg-bg transition-colors" onclick="toggleUserMenu()">
                <div class="relative">
                    <img src="${user.avatar_url || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?q=80&w=100'}"
                         class="w-10 h-10 rounded-xl object-cover transition-all">
                    <div class="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-emerald-500 border-2 border-surface"></div>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-xs font-bold text-primary truncate">${user.name || 'Alex Neural'}</p>
                    <p class="text-[10px] font-bold text-muted uppercase tracking-widest">Premium Node</p>
                </div>
                <i class="fas fa-chevron-up text-muted text-[10px]"></i>

                <div id="user-popup" class="absolute bottom-full left-0 w-full mb-3 bg-surface border border-border rounded-2xl shadow-premium p-2 hidden animate-in fade-in slide-in-from-bottom-2 duration-300">
                    <button onclick="switchView('profile')" class="flex items-center gap-3 w-full px-3 py-2 rounded-xl text-xs font-bold text-muted hover:text-primary hover:bg-bg transition-all">
                        <i class="fas fa-user-circle"></i> Profile
                    </button>
                    <div class="h-px bg-border my-1 mx-2"></div>
                    <button onclick="logout()" class="flex items-center gap-3 w-full px-3 py-2 rounded-xl text-xs font-bold text-rose-500 hover:bg-rose-500/10 transition-all">
                        <i class="fas fa-sign-out-alt"></i> Sign Out
                    </button>
                </div>
            </div>
        `;
    },

    getWelcomeHeader(username = 'Neural Node') {
        const displayName = username ? username.split(' ')[0] : 'Node';
        return `
            <div class="mb-12 space-y-2 motion-entrance">
                <h1 class="text-primary">Hello, ${displayName}</h1>
                <p class="text-muted font-medium">Neural Interface Link stable. How can we communicate today?</p>
            </div>
        `;
    },

    getStatCard(label, value, icon, trend = null) {
        return `
            <div class="ui-card ui-card-hover group motion-entrance">
                <div class="flex items-start justify-between mb-8">
                    <div class="w-12 h-12 rounded-xl bg-bg border border-border flex items-center justify-center text-muted group-hover:text-primary transition-all">
                        <i class="fas ${icon} text-xl"></i>
                    </div>
                    ${trend !== null ? `<span class="px-2 py-1 rounded-lg bg-emerald-500/10 text-emerald-500 text-[10px] font-bold">+${trend}%</span>` : ''}
                </div>
                <div>
                    <p class="text-[10px] font-bold text-muted uppercase tracking-widest mb-2">${label}</p>
                    <h2 class="text-primary text-3xl font-black">${value}</h2>
                </div>
            </div>
        `;
    },

    getModernActivityItem(title, meta, status = 'success') {
        const colors = { success: 'bg-emerald-500', alert: 'bg-rose-500', process: 'bg-primary' };
        return `
            <div class="flex items-center gap-5 p-4 rounded-2xl hover:bg-bg transition-all border border-transparent hover:border-border group cursor-pointer">
                <div class="w-10 h-10 rounded-xl bg-surface border border-border flex items-center justify-center text-muted">
                    <div class="w-2 h-2 rounded-full ${colors[status] || 'bg-muted'}"></div>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-bold text-primary truncate">${title}</p>
                    <p class="text-[10px] font-bold text-muted uppercase tracking-widest">${meta}</p>
                </div>
                <i class="fas fa-chevron-right text-muted text-xs opacity-0 group-hover:opacity-100 transition-all"></i>
            </div>
        `;
    },

    getLibraryGrid(items) {
        return `
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 motion-entrance">
                ${items.map(item => this.getLibraryCard(item)).join('')}
            </div>
        `;
    },

    getLibraryCard(item) {
        return `
            <div class="ui-card ui-card-hover group">
                <div class="media-container aspect-video mb-6">
                    <img src="${item.thumbnail}" class="media-content w-full h-full object-cover transition-all duration-700">
                    <div class="absolute inset-0 bg-gradient-to-t from-surface/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-4">
                        <button class="btn-modern btn-modern-primary w-full py-2 text-xs">Play Sequence</button>
                    </div>
                </div>
                <h4 class="text-primary mb-1">${item.name}</h4>
                <p class="text-[10px] font-bold text-muted uppercase tracking-widest">${item.category}</p>
            </div>
        `;
    },

    getSettingsContainer(categories) {
        return `
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-12 motion-entrance">
                <div class="lg:col-span-4 space-y-4">
                    <h2 class="text-primary">System Preferences</h2>
                    <p class="text-sm text-muted leading-relaxed">Configure your neural interface settings, appearance, and security protocols.</p>
                </div>
                <div class="lg:col-span-8 space-y-8">
                    ${categories.join('')}
                </div>
            </div>
        `;
    },

    getSettingsCategory(title, items) {
        return `
            <div class="ui-card space-y-6">
                <h3 class="text-[10px] font-bold text-muted uppercase tracking-[0.3em]">${title}</h3>
                <div class="space-y-6">
                    ${items.join('')}
                </div>
            </div>
        `;
    },

    getSettingsToggle(label, description, isActive, onToggle) {
        return `
            <div class="flex items-center justify-between group">
                <div class="flex-1 pr-8">
                    <h4 class="text-sm font-bold text-primary group-hover:text-primary transition-colors">${label}</h4>
                    <p class="text-xs text-muted mt-1">${description}</p>
                </div>
                <button onclick="${onToggle}" class="w-12 h-6 rounded-full transition-all relative ${isActive ? 'bg-primary' : 'bg-border'}">
                    <div class="absolute top-1 left-1 w-4 h-4 rounded-full bg-white shadow-sm transition-transform ${isActive ? 'translate-x-6' : ''}"></div>
                </button>
            </div>
        `;
    },

    getErrorState(title, message, onRetry) {
        return `
            <div class="flex flex-col items-center justify-center min-h-[400px] text-center space-y-6 motion-entrance">
                <div class="w-20 h-20 rounded-3xl bg-rose-500/10 flex items-center justify-center text-rose-500 text-3xl">
                    <i class="fas fa-exclamation-triangle"></i>
                </div>
                <div class="space-y-2">
                    <h2 class="text-primary">${title}</h2>
                    <p class="text-muted max-w-sm mx-auto">${message}</p>
                </div>
                <button onclick="${onRetry}" class="btn-modern btn-modern-primary px-8">Retry Protocol</button>
            </div>
        `;
    },

    getEmptyState(title, message, actionLabel, onAction) {
        return `
            <div class="flex flex-col items-center justify-center min-h-[400px] text-center space-y-6 motion-entrance">
                <div class="w-20 h-20 rounded-3xl bg-bg border border-border flex items-center justify-center text-muted text-3xl">
                    <i class="fas fa-folder-open"></i>
                </div>
                <div class="space-y-2">
                    <h2 class="text-primary">${title}</h2>
                    <p class="text-muted max-w-sm mx-auto">${message}</p>
                </div>
                ${actionLabel ? `<button onclick="${onAction}" class="btn-modern btn-modern-primary px-8">${actionLabel}</button>` : ''}
            </div>
        `;
    },

    /**
     * Modern Notification System (Toast)
     */
    showNotification(message, type = 'success', duration = 5000) {
        // Create container if not exists
        let container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.className = 'fixed top-8 right-8 z-[9999] flex flex-col gap-4 pointer-events-none w-full max-w-sm px-8 md:px-0';
            document.body.appendChild(container);
        }

        const id = 'notif-' + Date.now();
        const colors = {
            success: { bg: 'bg-emerald-50', border: 'border-emerald-100', text: 'text-emerald-800', icon: 'fa-check-circle', iconColor: 'text-emerald-500' },
            error: { bg: 'bg-rose-50', border: 'border-rose-100', text: 'text-rose-800', icon: 'fa-exclamation-circle', iconColor: 'text-rose-500' },
            warning: { bg: 'bg-orange-50', border: 'border-orange-100', text: 'text-orange-800', icon: 'fa-info-circle', iconColor: 'text-orange-500' }
        };

        const config = colors[type] || colors.success;

        const notif = document.createElement('div');
        notif.id = id;
        notif.className = `${config.bg} ${config.border} border-2 p-4 rounded-2xl shadow-xl shadow-black/5 flex items-start gap-4 pointer-events-auto transform`;
        notif.innerHTML = `
            <div class="${config.iconColor} mt-0.5">
                <i class="fas ${config.icon} text-lg"></i>
            </div>
            <div class="flex-1">
                <p class="text-[10px] font-black uppercase tracking-[0.2em] opacity-40 mb-0.5">${type} Signal</p>
                <p class="text-xs font-bold ${config.text} leading-relaxed">${message}</p>
            </div>
            <button onclick="this.parentElement.remove()" class="text-muted hover:text-primary transition-colors">
                <i class="fas fa-times text-[10px]"></i>
            </button>
        `;

        container.appendChild(notif);

        // GSAP Animation
        if (window.gsap) {
            gsap.from(notif, {
                x: 100,
                opacity: 0,
                duration: 0.8,
                ease: 'power4.out'
            });

            setTimeout(() => {
                gsap.to(notif, {
                    x: 100,
                    opacity: 0,
                    duration: 0.6,
                    ease: 'power4.in',
                    onComplete: () => notif.remove()
                });
            }, duration);
        } else {
            setTimeout(() => notif.remove(), duration);
        }
    }
};
