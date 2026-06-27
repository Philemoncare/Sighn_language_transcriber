/**
 * SnLag Shared UI Library (Neural UI v3.0)
 * Single source of truth for branding and unified components.
 */

const SnLagUI = {
    /**
     * PREMIUM LOGO SYSTEM
     * Consumed by Navbar, Auth, Admin, and Mobile interfaces.
     */
    getLogo(size = 'md', isLight = false) {
        const sizes = {
            xs: 'w-6 h-6',
            sm: 'w-8 h-8',
            md: 'w-12 h-12',
            lg: 'w-16 h-16',
            xl: 'w-24 h-24'
        };
        const iconSizes = {
            xs: 'text-[10px]',
            sm: 'text-xs',
            md: 'text-xl',
            lg: 'text-2xl',
            xl: 'text-4xl'
        };
        const textSizes = {
            xs: 'text-xs',
            sm: 'text-sm',
            md: 'text-xl',
            lg: 'text-2xl',
            xl: 'text-4xl'
        };

        return `
            <div class="flex items-center gap-3 group cursor-pointer select-none">
                <div class="${sizes[size]} bg-primary rounded-[30%] flex items-center justify-center text-white shadow-xl shadow-primary/20 rotate-3 transition-all duration-700 group-hover:rotate-0 group-hover:scale-110 group-hover:shadow-primary/40 relative overflow-hidden">
                    <div class="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent"></div>
                    <i class="fas fa-brain ${iconSizes[size]} relative z-10"></i>
                </div>
                <div class="flex flex-col leading-none">
                    <h1 class="${textSizes[size]} font-900 tracking-tighter ${isLight ? 'text-white' : 'text-neutral-900 dark:text-white'} transition-colors duration-500">
                        SnLag<span class="text-primary font-900 italic">CORE</span>
                    </h1>
                    <p class="text-[7px] font-800 text-neutral-400 dark:text-neutral-500 uppercase tracking-[0.4em] mt-1 transition-colors duration-500">Universal Intel</p>
                </div>
            </div>
        `;
    },

    getNotificationDropdown() {
        return `
            <div id="notif-dropdown" class="absolute top-full right-0 mt-6 w-80 bg-white dark:bg-neutral-900 rounded-[2.5rem] shadow-3xl border border-neutral-100 dark:border-neutral-800 p-8 hidden animate__animated animate__fadeInUp animate__faster z-[200]">
                <div class="flex justify-between items-center mb-8">
                    <div class="flex items-center gap-3">
                        <i class="fas fa-satellite-dish text-primary"></i>
                        <h4 class="text-xs font-900 uppercase tracking-widest text-neutral-800 dark:text-neutral-200">Signals</h4>
                    </div>
                    <span class="bg-primary/10 text-primary text-[8px] font-900 px-2.5 py-1 rounded-full uppercase">2 Node Activities</span>
                </div>
                <div class="space-y-4">
                    <div class="flex gap-4 p-4 rounded-3xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-100 dark:border-neutral-800 transition-all hover:scale-[1.02] cursor-pointer">
                        <div class="w-10 h-10 rounded-2xl bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center text-primary text-sm">
                            <i class="fas fa-microchip"></i>
                        </div>
                        <div class="flex-1 overflow-hidden">
                            <p class="text-[11px] font-800 text-neutral-700 dark:text-neutral-300">Extraction Success</p>
                            <p class="text-[9px] text-neutral-400 truncate">Greetings_V2 node initialized</p>
                        </div>
                    </div>
                    <div class="flex gap-4 p-4 rounded-3xl hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-all hover:scale-[1.02] cursor-pointer border border-transparent hover:border-neutral-100 dark:hover:border-neutral-800">
                        <div class="w-10 h-10 rounded-2xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center text-emerald-500 text-sm">
                            <i class="fas fa-shield-alt"></i>
                        </div>
                        <div class="flex-1 overflow-hidden">
                            <p class="text-[11px] font-800 text-neutral-700 dark:text-neutral-300">Security Sync</p>
                            <p class="text-[9px] text-neutral-400 truncate">Neural Link established from unknown IP</p>
                        </div>
                    </div>
                </div>
                <button class="w-full mt-8 text-[9px] font-900 uppercase text-neutral-400 hover:text-primary transition-colors py-4 border-t border-neutral-100 dark:border-neutral-800">Clear Data Streams</button>
            </div>
        `;
    },

    getUserMenu(username, role) {
        return `
            <div id="user-dropdown" class="absolute top-full right-0 mt-6 w-72 bg-white dark:bg-neutral-900 rounded-[3rem] shadow-3xl border border-neutral-100 dark:border-neutral-800 overflow-hidden hidden animate__animated animate__fadeInUp animate__faster z-[200]">
                <div class="p-10 bg-neutral-50 dark:bg-neutral-800/40 border-b border-neutral-100 dark:border-neutral-800 relative overflow-hidden">
                    <div class="absolute top-0 right-0 w-24 h-24 bg-primary/5 rounded-full -mr-12 -mt-12 blur-2xl"></div>
                    <p class="text-[10px] font-900 text-neutral-400 uppercase tracking-widest mb-1">Identity Context</p>
                    <p class="text-sm font-900 text-neutral-900 dark:text-white truncate">${username}</p>
                    <div class="flex items-center gap-2 mt-3">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_#10b981]"></span>
                        <p class="text-[8px] font-800 text-primary uppercase tracking-widest">${role}</p>
                    </div>
                </div>
                <div class="p-6 space-y-2">
                    <button onclick="switchView('profile')" class="w-full flex items-center gap-4 px-6 py-4 rounded-2xl hover:bg-neutral-50 dark:hover:bg-neutral-800/80 text-neutral-600 dark:text-neutral-400 hover:text-primary transition-all group border border-transparent hover:border-neutral-100 dark:hover:border-neutral-800">
                        <i class="fas fa-id-card text-base opacity-40 group-hover:opacity-100 transition-opacity"></i>
                        <span class="text-[11px] font-800 uppercase tracking-wider">Neural Profile</span>
                    </button>
                    <button class="w-full flex items-center gap-4 px-6 py-4 rounded-2xl hover:bg-neutral-50 dark:hover:bg-neutral-800/80 text-neutral-600 dark:text-neutral-400 hover:text-primary transition-all group border border-transparent hover:border-neutral-100 dark:hover:border-neutral-800">
                        <i class="fas fa-cog text-base opacity-40 group-hover:opacity-100 transition-opacity"></i>
                        <span class="text-[11px] font-800 uppercase tracking-wider">Node Logic</span>
                    </button>
                    <div class="h-px bg-neutral-100 dark:bg-neutral-800 my-4 mx-8"></div>
                    <button onclick="logout()" class="w-full flex items-center gap-4 px-6 py-4 rounded-2xl hover:bg-red-50 dark:hover:bg-red-900/10 text-neutral-600 dark:text-neutral-400 hover:text-red-500 transition-all group border border-transparent hover:border-red-100 dark:hover:border-red-900/30">
                        <i class="fas fa-power-off text-base opacity-40 group-hover:opacity-100 transition-opacity"></i>
                        <span class="text-[11px] font-800 uppercase tracking-wider">Deactivate Link</span>
                    </button>
                </div>
            </div>
        `;
    }
};
