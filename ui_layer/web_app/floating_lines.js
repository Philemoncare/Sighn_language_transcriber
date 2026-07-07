class LightLinesAnimation {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!containerId) return;

        this.speedMultiplier = options.speedMultiplier || 1;
        this.animations = [];
        this.frameId = null;
        this.isVisible = false;

        this.init();
    }

    init() {
        const lightsDown = [
            { selector: ".light4", from: -1080, to: 1080 },
            { selector: ".light5", from: -1080, to: 1080 },
            { selector: ".light6", from: -1080, to: 1080 },
            { selector: ".light7", from: -1080, to: 1080 },
            { selector: ".light8", from: -1080, to: 1080 },
            { selector: ".light11", from: -1080, to: 1080 },
            { selector: ".light12", from: -1080, to: 1080 },
            { selector: ".light13", from: -1080, to: 1080 },
            { selector: ".light14", from: -1080, to: 1080 },
            { selector: ".light15", from: -1080, to: 1080 },
            { selector: ".light16", from: -1080, to: 1080 },
        ];

        const lightsUp = [
            { selector: ".light1", from: 1080, to: -1080 },
            { selector: ".light2", from: 1080, to: -1080 },
            { selector: ".light3", from: 1080, to: -1080 },
            { selector: ".light9", from: 1080, to: -1080 },
            { selector: ".light10", from: 1080, to: -1080 },
            { selector: ".light17", from: 1080, to: -1080 },
        ];

        const allLights = [...lightsDown, ...lightsUp];
        this.animations = allLights.map((light) => {
            const element = this.container.querySelector(light.selector);
            const duration = (Math.floor(Math.random() * 59) + 2) * 0.5 + 0.5;
            return {
                element,
                from: light.from,
                to: light.to,
                duration: duration / this.speedMultiplier,
                startTime: performance.now() - Math.random() * 5000
            };
        });

        const observer = new IntersectionObserver(([entry]) => {
            this.isVisible = entry.isIntersecting;
        }, { threshold: 0 });

        observer.observe(this.container);
        this.animate = this.animate.bind(this);
        this.frameId = requestAnimationFrame(this.animate);
    }

    animate(time) {
        if (!this.isVisible) {
            this.frameId = requestAnimationFrame(this.animate);
            return;
        }

        this.animations.forEach((ref) => {
            if (!ref.element) return;

            const elapsed = (time - ref.startTime) / 1000;
            const progress = (elapsed % ref.duration) / ref.duration;
            const currentY = ref.from + (ref.to - ref.from) * progress;

            ref.element.style.transform = `translateY(${currentY}px)`;
        });

        this.frameId = requestAnimationFrame(this.animate);
    }

    stop() {
        if (this.frameId) cancelAnimationFrame(this.frameId);
    }
}

// Export for global use
window.LightLinesAnimation = LightLinesAnimation;
