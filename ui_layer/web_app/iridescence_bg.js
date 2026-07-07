/**
 * Iridescence Background Engine (Modern Architectural Port)
 * Ported from React Bits to Vanilla JS for Signly Universal Core.
 * This engine handles WebGL shader execution for the premium background effect.
 */

class IridescenceBackground {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.warn(`Iridescence: Container #${containerId} not found.`);
            return;
        }

        this.options = {
            color: options.color || [0.97, 0.45, 0.08], // Signly Orange
            speed: options.speed || 1.0,
            amplitude: options.amplitude || 0.1,
            mouseReact: options.mouseReact !== undefined ? options.mouseReact : true
        };

        this.mousePos = { x: 0.5, y: 0.5 };
        this.program = null;
        this.renderer = null;
        this.gl = null;
        this.mesh = null;
        this.animateId = null;

        this.vertexShader = `
            attribute vec2 uv;
            attribute vec2 position;
            varying vec2 vUv;
            void main() {
                vUv = uv;
                gl_Position = vec4(position, 0, 1);
            }
        `;

        this.fragmentShader = `
            precision highp float;
            uniform float uTime;
            uniform vec3 uColor;
            uniform vec3 uResolution;
            uniform vec2 uMouse;
            uniform float uAmplitude;
            uniform float uSpeed;
            varying vec2 vUv;

            void main() {
                float mr = min(uResolution.x, uResolution.y);
                vec2 uv = (vUv.xy * 2.0 - 1.0) * uResolution.xy / mr;
                uv += (uMouse - vec2(0.5)) * uAmplitude;

                float d = -uTime * 0.5 * uSpeed;
                float a = 0.0;
                for (float i = 0.0; i < 8.0; ++i) {
                    a += cos(i - d - a * uv.x);
                    d += sin(uv.y * i + a);
                }
                d += uTime * 0.5 * uSpeed;
                vec3 col = vec3(cos(uv * vec2(d, a)) * 0.6 + 0.4, cos(a + d) * 0.5 + 0.5);
                col = cos(col * cos(vec3(d, a, 2.5)) * 0.5 + 0.5) * uColor;
                gl_FragColor = vec4(col, 1.0);
            }
        `;

        this.init();
    }

    async init() {
        if (this.gl) return; // Prevent multiple initializations
        console.log("Iridescence: Initializing Neural Backdrop...");

        // Ensure OGL is loaded
        if (typeof ogl === 'undefined') {
            await this.loadOGL();
        }

        try {
            const { Renderer, Program, Mesh, Color, Triangle } = ogl;

            this.renderer = new Renderer({ alpha: true, premultipliedAlpha: false, antialias: true, dpr: window.devicePixelRatio || 1 });
            this.gl = this.renderer.gl;
            this.gl.clearColor(0, 0, 0, 0);

            this.resize = () => {
                if (!this.container || !this.renderer) return;
                const width = this.container.offsetWidth;
                const height = this.container.offsetHeight;
                this.renderer.setSize(width, height);
                if (this.program) {
                    this.program.uniforms.uResolution.value = [
                        this.gl.canvas.width,
                        this.gl.canvas.height,
                        this.gl.canvas.width / this.gl.canvas.height
                    ];
                }
            };

            window.addEventListener('resize', this.resize, false);

            const geometry = new Triangle(this.gl);
            this.program = new Program(this.gl, {
                vertex: this.vertexShader,
                fragment: this.fragmentShader,
                uniforms: {
                    uTime: { value: 0 },
                    uColor: { value: new Color(...this.options.color) },
                    uResolution: {
                        value: [0, 0, 0]
                    },
                    uMouse: { value: new Float32Array([this.mousePos.x, this.mousePos.y]) },
                    uAmplitude: { value: this.options.amplitude },
                    uSpeed: { value: this.options.speed }
                }
            });

            this.mesh = new Mesh(this.gl, { geometry, program: this.program });
            this.container.appendChild(this.gl.canvas);

            // Set initial size
            this.resize();

            if (this.options.mouseReact) {
                window.addEventListener('mousemove', (e) => {
                    if (!this.program) return;
                    const rect = this.container.getBoundingClientRect();
                    const x = (e.clientX - rect.left) / rect.width;
                    const y = 1.0 - (e.clientY - rect.top) / rect.height;
                    this.mousePos = { x, y };
                    this.program.uniforms.uMouse.value[0] = x;
                    this.program.uniforms.uMouse.value[1] = y;
                });
            }

            this.animate();
            console.log("Iridescence: Neural Backdrop Active.");
        } catch (err) {
            console.error("Iridescence: WebGL Initialization Failed", err);
        }
    }

    animate(t = 0) {
        if (!this.renderer || !this.program) return;
        this.animateId = requestAnimationFrame((time) => this.animate(time));
        this.program.uniforms.uTime.value = t * 0.001;
        this.renderer.render({ scene: this.mesh });
    }

    loadOGL() {
        return new Promise((resolve, reject) => {
            if (document.getElementById('ogl-script')) {
                const check = setInterval(() => {
                    if (typeof ogl !== 'undefined') {
                        clearInterval(check);
                        resolve();
                    }
                }, 50);
                return;
            }
            const script = document.createElement('script');
            script.id = 'ogl-script';
            script.src = 'https://cdn.jsdelivr.net/npm/ogl@1.0.11/dist/ogl.umd.js';
            script.onload = () => resolve();
            script.onerror = (e) => reject(e);
            document.head.appendChild(script);
        });
    }

    destroy() {
        if (this.animateId) cancelAnimationFrame(this.animateId);
        window.removeEventListener('resize', this.resize);
        this.gl?.getExtension('WEBGL_lose_context')?.loseContext();
        if (this.gl?.canvas?.parentNode) {
            this.gl.canvas.parentNode.removeChild(this.gl.canvas);
        }
    }
}
