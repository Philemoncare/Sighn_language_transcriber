/**
 * FloatingLines Vanilla JS Component
 * Adapted from React Bits FloatingLines
 * High-performance vivid background engine
 */

const vertexShader = `
precision highp float;
void main() {
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

const fragmentShader = `
precision highp float;

uniform float iTime;
uniform vec3  iResolution;
uniform float animationSpeed;

uniform bool enableTop;
uniform bool enableMiddle;
uniform bool enableBottom;

uniform int topLineCount;
uniform int middleLineCount;
uniform int bottomLineCount;

uniform float topLineDistance;
uniform float middleLineDistance;
uniform float bottomLineDistance;

uniform vec3 topWavePosition;
uniform vec3 middleWavePosition;
uniform vec3 bottomWavePosition;

uniform vec2 iMouse;
uniform bool interactive;
uniform float bendRadius;
uniform float bendStrength;
uniform float bendInfluence;

uniform bool parallax;
uniform float parallaxStrength;
uniform vec2 parallaxOffset;

uniform vec3 lineGradient[8];
uniform int lineGradientCount;

const vec3 BLACK = vec3(0.0);
const vec3 PINK  = vec3(233.0, 71.0, 245.0) / 255.0;
const vec3 BLUE  = vec3(47.0,  75.0, 162.0) / 255.0;

mat2 rotate(float r) {
  return mat2(cos(r), sin(r), -sin(r), cos(r));
}

vec3 background_color(vec2 uv) {
  vec3 col = vec3(0.01, 0.02, 0.05); // Deep base
  float y = sin(uv.x - 0.2) * 0.3 - 0.1;
  float m = uv.y - y;
  col += mix(BLUE, BLACK, smoothstep(0.0, 1.2, abs(m)));
  col += mix(PINK, BLACK, smoothstep(0.0, 1.2, abs(m - 0.8)));
  return col * 0.3;
}

vec3 getLineColor(float t, vec3 baseColor) {
  if (lineGradientCount <= 0) return baseColor;
  vec3 gradientColor;
  float clampedT = clamp(t, 0.0, 0.9999);
  float scaled = clampedT * float(lineGradientCount - 1);
  int idx = int(floor(scaled));
  float f = fract(scaled);

  vec3 c1 = vec3(0.0);
  vec3 c2 = vec3(0.0);

  if (idx == 0) { c1 = lineGradient[0]; c2 = lineGradient[1]; }
  else if (idx == 1) { c1 = lineGradient[1]; c2 = lineGradient[2]; }
  else if (idx == 2) { c1 = lineGradient[2]; c2 = lineGradient[3]; }
  else if (idx == 3) { c1 = lineGradient[3]; c2 = lineGradient[4]; }
  else if (idx == 4) { c1 = lineGradient[4]; c2 = lineGradient[5]; }
  else if (idx == 5) { c1 = lineGradient[5]; c2 = lineGradient[6]; }
  else if (idx == 6) { c1 = lineGradient[6]; c2 = lineGradient[7]; }
  else { c1 = lineGradient[7]; c2 = lineGradient[7]; }

  gradientColor = mix(c1, c2, f);
  return gradientColor;
}

float wave(vec2 uv, float offset, vec2 screenUv, vec2 mouseUv, bool shouldBend) {
  float time = iTime * animationSpeed;
  float x_offset   = offset;
  float x_movement = time * 0.15;
  float amp        = sin(offset + time * 0.3) * 0.3;
  float y          = sin(uv.x + x_offset + x_movement) * amp;

  if (shouldBend) {
    vec2 d = screenUv - mouseUv;
    float influence = exp(-dot(d, d) * bendRadius);
    float bendOffset = (mouseUv.y - screenUv.y) * influence * bendStrength * bendInfluence;
    y += bendOffset;
  }
  float m = uv.y - y;
  // Brighter lines
  return 0.025 / max(abs(m) + 0.005, 1e-3);
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
  vec2 baseUv = (2.0 * fragCoord - iResolution.xy) / iResolution.y;
  baseUv.y *= -1.0;
  if (parallax) baseUv += parallaxOffset;

  vec3 col = background_color(baseUv);

  vec2 mouseUv = vec2(0.0);
  if (interactive) {
    mouseUv = (2.0 * iMouse - iResolution.xy) / iResolution.y;
    mouseUv.y *= -1.0;
  }

  if (enableBottom) {
    for (int i = 0; i < 32; ++i) {
      if (i >= bottomLineCount) break;
      float fi = float(i);
      float t = fi / max(float(bottomLineCount - 1), 1.0);
      vec3 lineCol = getLineColor(t, vec3(1.0));
      float angle = bottomWavePosition.z * log(length(baseUv) + 1.0);
      vec2 ruv = baseUv * rotate(angle);
      col += lineCol * wave(
        ruv + vec2(bottomLineDistance * fi + bottomWavePosition.x, bottomWavePosition.y),
        1.5 + 0.2 * fi,
        baseUv,
        mouseUv,
        interactive
      ) * 0.15;
    }
  }

  if (enableMiddle) {
    for (int i = 0; i < 32; ++i) {
      if (i >= middleLineCount) break;
      float fi = float(i);
      float t = fi / max(float(middleLineCount - 1), 1.0);
      vec3 lineCol = getLineColor(t, vec3(1.0));
      float angle = middleWavePosition.z * log(length(baseUv) + 1.0);
      vec2 ruv = baseUv * rotate(angle);
      col += lineCol * wave(
        ruv + vec2(middleLineDistance * fi + middleWavePosition.x, middleWavePosition.y),
        2.0 + 0.15 * fi,
        baseUv,
        mouseUv,
        interactive
      ) * 0.4;
    }
  }

  if (enableTop) {
    for (int i = 0; i < 32; ++i) {
      if (i >= topLineCount) break;
      float fi = float(i);
      float t = fi / max(float(topLineCount - 1), 1.0);
      vec3 lineCol = getLineColor(t, vec3(1.0));
      float angle = topWavePosition.z * log(length(baseUv) + 1.0);
      vec2 ruv = baseUv * rotate(angle);
      ruv.x *= -1.0;
      col += lineCol * wave(
        ruv + vec2(topLineDistance * fi + topWavePosition.x, topWavePosition.y),
        1.0 + 0.2 * fi,
        baseUv,
        mouseUv,
        interactive
      ) * 0.1;
    }
  }
  fragColor = vec4(col, 1.0);
}

void main() {
  vec4 color = vec4(0.0);
  mainImage(color, gl_FragCoord.xy);
  gl_FragColor = color;
}
`;

class FloatingLines {
  constructor(containerId, props = {}) {
    this.container = document.getElementById(containerId);
    if (!this.container) return;

    this.props = {
      linesGradient: props.linesGradient || ['#f97316', '#ea580c', '#3b82f6'],
      enabledWaves: props.enabledWaves || ['top', 'middle', 'bottom'],
      lineCount: props.lineCount || [10, 15, 20],
      lineDistance: props.lineDistance || [8, 6, 4],
      topWavePosition: props.topWavePosition || { x: 10.0, y: 0.5, rotate: -0.4 },
      middleWavePosition: props.middleWavePosition || { x: 5.0, y: 0.0, rotate: 0.2 },
      bottomWavePosition: props.bottomWavePosition || { x: 2.0, y: -0.7, rotate: 0.4 },
      animationSpeed: props.animationSpeed || 1.2,
      interactive: props.interactive !== undefined ? props.interactive : true,
      bendRadius: props.bendRadius || 12.0,
      bendStrength: props.bendStrength || -6.0,
      mouseDamping: props.mouseDamping || 0.06,
      parallax: props.parallax !== undefined ? props.parallax : true,
      parallaxStrength: props.parallaxStrength || 0.3,
      mixBlendMode: props.mixBlendMode || 'screen'
    };

    this.targetMouse = new THREE.Vector2(-1000, -1000);
    this.currentMouse = new THREE.Vector2(-1000, -1000);
    this.targetInfluence = 0;
    this.currentInfluence = 0;
    this.targetParallax = new THREE.Vector2(0, 0);
    this.currentParallax = new THREE.Vector2(0, 0);

    this.init();
  }

  getLineCount(waveType) {
    if (typeof this.props.lineCount === 'number') return this.props.lineCount;
    const index = ['top', 'middle', 'bottom'].indexOf(waveType);
    return this.props.lineCount[index] ?? 6;
  }

  getLineDistance(waveType) {
    if (typeof this.props.lineDistance === 'number') return this.props.lineDistance;
    const index = ['top', 'middle', 'bottom'].indexOf(waveType);
    return this.props.lineDistance[index] ?? 5;
  }

  hexToVec3(hex) {
    let value = hex.trim().replace('#', '');
    let r = 255, g = 255, b = 255;
    if (value.length === 3) {
      r = parseInt(value[0] + value[0], 16);
      g = parseInt(value[1] + value[1], 16);
      b = parseInt(value[2] + value[2], 16);
    } else if (value.length === 6) {
      r = parseInt(value.slice(0, 2), 16);
      g = parseInt(value.slice(2, 4), 16);
      b = parseInt(value.slice(4, 6), 16);
    }
    return new THREE.Vector3(r / 255, g / 255, b / 255);
  }

  init() {
    this.scene = new THREE.Scene();
    this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    this.camera.position.z = 1;

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.domElement.style.width = '100%';
    this.renderer.domElement.style.height = '100%';
    this.renderer.domElement.style.mixBlendMode = this.props.mixBlendMode;
    this.container.appendChild(this.renderer.domElement);

    const topLineCount = this.props.enabledWaves.includes('top') ? this.getLineCount('top') : 0;
    const middleLineCount = this.props.enabledWaves.includes('middle') ? this.getLineCount('middle') : 0;
    const bottomLineCount = this.props.enabledWaves.includes('bottom') ? this.getLineCount('bottom') : 0;

    const uniforms = {
      iTime: { value: 0 },
      iResolution: { value: new THREE.Vector3(1, 1, 1) },
      animationSpeed: { value: this.props.animationSpeed },
      enableTop: { value: this.props.enabledWaves.includes('top') },
      enableMiddle: { value: this.props.enabledWaves.includes('middle') },
      enableBottom: { value: this.props.enabledWaves.includes('bottom') },
      topLineCount: { value: topLineCount },
      middleLineCount: { value: middleLineCount },
      bottomLineCount: { value: bottomLineCount },
      topLineDistance: { value: this.getLineDistance('top') * 0.01 },
      middleLineDistance: { value: this.getLineDistance('middle') * 0.01 },
      bottomLineDistance: { value: this.getLineDistance('bottom') * 0.01 },
      topWavePosition: { value: new THREE.Vector3(this.props.topWavePosition.x, this.props.topWavePosition.y, this.props.topWavePosition.rotate) },
      middleWavePosition: { value: new THREE.Vector3(this.props.middleWavePosition.x, this.props.middleWavePosition.y, this.props.middleWavePosition.rotate) },
      bottomWavePosition: { value: new THREE.Vector3(this.props.bottomWavePosition.x, this.props.bottomWavePosition.y, this.props.bottomWavePosition.rotate) },
      iMouse: { value: new THREE.Vector2(-1000, -1000) },
      interactive: { value: this.props.interactive },
      bendRadius: { value: this.props.bendRadius },
      bendStrength: { value: this.props.bendStrength },
      bendInfluence: { value: 0 },
      parallax: { value: this.props.parallax },
      parallaxStrength: { value: this.props.parallaxStrength },
      parallaxOffset: { value: new THREE.Vector2(0, 0) },
      lineGradient: { value: Array.from({ length: 8 }, () => new THREE.Vector3(1, 1, 1)) },
      lineGradientCount: { value: 0 }
    };

    if (this.props.linesGradient && this.props.linesGradient.length > 0) {
      const stops = this.props.linesGradient.slice(0, 8);
      uniforms.lineGradientCount.value = stops.length;
      stops.forEach((hex, i) => {
        const color = this.hexToVec3(hex);
        uniforms.lineGradient.value[i].set(color.x, color.y, color.z);
      });
    }

    this.material = new THREE.ShaderMaterial({
      uniforms,
      vertexShader,
      fragmentShader
    });

    const geometry = new THREE.PlaneGeometry(2, 2);
    this.mesh = new THREE.Mesh(geometry, this.material);
    this.scene.add(this.mesh);

    this.clock = new THREE.Clock();
    this.resize();

    window.addEventListener('resize', () => this.resize());
    if (this.props.interactive) {
      this.renderer.domElement.addEventListener('pointermove', e => this.handlePointerMove(e));
      this.renderer.domElement.addEventListener('pointerleave', () => this.handlePointerLeave());
    }

    this.animate();
  }

  resize() {
    if (!this.container || !this.renderer) return;
    const width = this.container.clientWidth || 1;
    const height = this.container.clientHeight || 1;
    this.renderer.setSize(width, height, false);
    this.material.uniforms.iResolution.value.set(this.renderer.domElement.width, this.renderer.domElement.height, 1);
  }

  handlePointerMove(event) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const dpr = this.renderer.getPixelRatio();

    this.targetMouse.set(x * dpr, (rect.height - y) * dpr);
    this.targetInfluence = 1.0;

    if (this.props.parallax) {
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const offsetX = (x - centerX) / rect.width;
      const offsetY = -(y - centerY) / rect.height;
      this.targetParallax.set(offsetX * this.props.parallaxStrength, offsetY * this.props.parallaxStrength);
    }
  }

  handlePointerLeave() {
    this.targetInfluence = 0.0;
  }

  animate() {
    if (!this.renderer) return;
    requestAnimationFrame(() => this.animate());

    this.material.uniforms.iTime.value = this.clock.getElapsedTime();

    if (this.props.interactive) {
      this.currentMouse.lerp(this.targetMouse, this.props.mouseDamping);
      this.material.uniforms.iMouse.value.copy(this.currentMouse);
      this.currentInfluence += (this.targetInfluence - this.currentInfluence) * this.props.mouseDamping;
      this.material.uniforms.bendInfluence.value = this.currentInfluence;
    }

    if (this.props.parallax) {
      this.currentParallax.lerp(this.targetParallax, this.props.mouseDamping);
      this.material.uniforms.parallaxOffset.value.copy(this.currentParallax);
    }

    this.renderer.render(this.scene, this.camera);
  }
}
