/**
 * Signly BubbleMenu Component (Vanilla JS + GSAP)
 * Adapted from React Bits for SnLag Architecture
 */

class BubbleMenu {
    constructor(options = {}) {
        this.logo = options.logo || 'Signly';
        this.items = options.items || [];
        this.cta = options.cta || null; // { label, href }
        this.menuBg = options.menuBg || '#fff';
        this.menuContentColor = options.menuContentColor || '#111';
        this.useFixedPosition = options.useFixedPosition || false;
        this.animationEase = options.animationEase || 'back.out(1.5)';
        this.animationDuration = options.animationDuration || 0.5;
        this.staggerDelay = options.staggerDelay || 0.12;

        this.isMenuOpen = false;
        this.init();
    }

    init() {
        this.render();
        this.bindEvents();
    }

    render() {
        // Create root nav
        this.nav = document.createElement('nav');
        this.nav.className = `bubble-menu ${this.useFixedPosition ? 'fixed' : 'absolute'}`;
        this.nav.setAttribute('aria-label', 'Main navigation');

        // Logo Bubble
        const logoBubble = document.createElement('div');
        logoBubble.className = 'bubble logo-bubble';
        logoBubble.style.background = this.menuBg;
        logoBubble.innerHTML = `<span class="logo-content">${this.logo}</span>`;
        this.nav.appendChild(logoBubble);

        // Optional CTA
        if (this.cta) {
            const ctaBtn = document.createElement('a');
            ctaBtn.href = this.cta.href;
            ctaBtn.className = 'bg-[#f97316] text-white px-6 h-[48px] md:h-[56px] flex items-center justify-center text-[10px] font-900 uppercase tracking-widest hover:brightness-110 transition-all rounded-md pointer-events-auto ml-auto mr-4';
            ctaBtn.innerText = this.cta.label;
            this.nav.appendChild(ctaBtn);
        }

        // Toggle Bubble
        this.toggleBtn = document.createElement('button');
        this.toggleBtn.type = 'button';
        this.toggleBtn.className = 'bubble toggle-bubble menu-btn';
        this.toggleBtn.style.background = this.menuBg;
        this.toggleBtn.innerHTML = `
            <span class="menu-line" style="background: ${this.menuContentColor}"></span>
            <span class="menu-line" style="background: ${this.menuContentColor}"></span>
        `;
        this.nav.appendChild(this.toggleBtn);

        // Overlay
        this.overlay = document.createElement('div');
        this.overlay.className = `bubble-menu-overlay ${this.useFixedPosition ? 'fixed' : 'absolute'}`;

        const itemsContainer = document.createElement('div');
        itemsContainer.className = 'bubble-menu-items';

        const pillList = document.createElement('ul');
        pillList.className = 'pill-list';
        pillList.setAttribute('role', 'menu');

        this.bubbles = [];
        this.labels = [];

        this.items.forEach((item, idx) => {
            const li = document.createElement('li');
            li.className = 'pill-col';
            li.setAttribute('role', 'none');

            const a = document.createElement('a');
            a.href = item.href;
            a.className = 'pill-link';
            a.setAttribute('role', 'menuitem');
            a.style.setProperty('--item-rot', `${item.rotation ?? 0}deg`);
            a.style.setProperty('--pill-bg', this.menuBg);
            a.style.setProperty('--pill-color', this.menuContentColor);
            a.style.setProperty('--hover-bg', item.hoverStyles?.bgColor || '#f3f4f6');
            a.style.setProperty('--hover-color', item.hoverStyles?.textColor || this.menuContentColor);

            const span = document.createElement('span');
            span.className = 'pill-label';
            span.innerText = item.label;

            a.appendChild(span);
            a.onclick = () => this.toggle(); // Close menu on navigation
            li.appendChild(a);
            pillList.appendChild(li);

            this.bubbles.push(a);
            this.labels.push(span);
        });

        itemsContainer.appendChild(pillList);
        this.overlay.appendChild(itemsContainer);

        document.body.appendChild(this.nav);
        document.body.appendChild(this.overlay);
    }

    bindEvents() {
        this.toggleBtn.onclick = () => this.toggle();
        this.overlay.onclick = (e) => {
            if (e.target === this.overlay || e.target.classList.contains('bubble-menu-items')) {
                this.toggle();
            }
        };

        window.addEventListener('resize', () => {
            if (this.isMenuOpen) {
                const isDesktop = window.innerWidth >= 900;
                this.bubbles.forEach((bubble, i) => {
                    const rotation = isDesktop ? (this.items[i].rotation ?? 0) : 0;
                    gsap.set(bubble, { rotation });
                });
            }
        });
    }

    toggle() {
        this.isMenuOpen = !this.isMenuOpen;
        this.toggleBtn.classList.toggle('open', this.isMenuOpen);

        if (this.isMenuOpen) {
            gsap.set(this.overlay, { display: 'flex' });
            gsap.killTweensOf([...this.bubbles, ...this.labels]);
            gsap.set(this.bubbles, { scale: 0, transformOrigin: '50% 50%' });
            gsap.set(this.labels, { y: 24, autoAlpha: 0 });

            this.bubbles.forEach((bubble, i) => {
                const delay = i * this.staggerDelay + gsap.utils.random(-0.05, 0.05);
                const tl = gsap.timeline({ delay });

                tl.to(bubble, {
                    scale: 1,
                    duration: this.animationDuration,
                    ease: this.animationEase
                });
                if (this.labels[i]) {
                    tl.to(this.labels[i], {
                        y: 0,
                        autoAlpha: 1,
                        duration: this.animationDuration,
                        ease: 'power3.out'
                    }, `-=${this.animationDuration * 0.9}`);
                }
            });
            document.body.style.overflow = 'hidden';
        } else {
            gsap.killTweensOf([...this.bubbles, ...this.labels]);
            gsap.to(this.labels, {
                y: 24,
                autoAlpha: 0,
                duration: 0.2,
                ease: 'power3.in'
            });
            gsap.to(this.bubbles, {
                scale: 0,
                duration: 0.2,
                ease: 'power3.in',
                onComplete: () => {
                    gsap.set(this.overlay, { display: 'none' });
                }
            });
            document.body.style.overflow = '';
        }
    }
}
