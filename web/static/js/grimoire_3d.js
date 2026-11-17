/**
 * PRIORY GRIMOIRE — WEBGL 3D WORKBENCH CONTROLLER
 * Three.js PBR rendering, ResizeObserver 1fr viewport sizing, dynamic Daylight/Nocturne
 * CSS token resolution, vertex-deformed 3D page flip physics, and 2K CanvasTextures.
 * Strictly emoji-free, upright optical sans typography, monospace quarantined to chat codes.
 */

(function() {
  'use strict';

  // ── State Management ────────────────────────────────────────────────────────
  let currentSpreadIndex = 0;
  let savedRecipes = [];
  let accountTelemetry = null;
  let isFlipping = false;
  let audioEnabled = false;
  try {
    audioEnabled = localStorage.getItem("priory_audio_3d") === "true";
  } catch (_) {}
  let activeCameraMode = "reading";

  // ── Three.js Global Objects ─────────────────────────────────────────────────
  let scene, camera, renderer, controls, composer;
  let bookGroup, leftPageMesh, rightPageMesh, flipPivot, flipGeo;
  let textureLeft, textureRight, textureFlipFront, textureFlipBack;
  let canvasLeft, canvasRight, canvasFlipFront, canvasFlipBack;
  let ctxLeft, ctxRight, ctxFlipFront, ctxFlipBack;
  let candleLightLeft, candleLightRight, scryingOrbCore, astrolabeGroup;
  let raycaster, mouse;

  // ── DOM Handles ─────────────────────────────────────────────────────────────
  const container = document.getElementById("webgl-container");
  const btnPrev = document.getElementById("btn-prev-3d");
  const btnNext = document.getElementById("btn-next-3d");
  const pageIndicator = document.getElementById("page-indicator-3d");
  const tabInscribe = document.getElementById("tab-3d-inscribe");
  const savedTabsContainer = document.getElementById("saved-tabs-container");
  const formInscribe = document.getElementById("form-inscribe-3d");
  const inputQuery = document.getElementById("input-query-3d");
  const btnForge = document.getElementById("btn-forge-3d");
  const forgeBtnText = document.getElementById("forge-btn-text");
  const forgeSpinner = document.getElementById("forge-spinner");
  const audioToggle = document.getElementById("audio-toggle-3d");
  const accountEssenceBadge = document.getElementById("account-essence-badge");
  const copyBadge = document.getElementById("copy-badge");
  const btnThemeToggle3d = document.getElementById("btn-theme-toggle-3d");
  const labelTheme3d = document.getElementById("label-theme-3d");

  // ── Dynamic CSS Token Reader ────────────────────────────────────────────────
  function readThemeTokens() {
    const cs = getComputedStyle(document.documentElement);
    const g = (name) => (cs.getPropertyValue(name) || "").trim();
    return {
      bgCanvas: g("--bg-canvas"),
      bgSurface1: g("--bg-surface-1"),
      bgSurface2: g("--bg-surface-2"),
      bgSurface3: g("--bg-surface-3"),
      borderSubtle: g("--border-subtle"),
      borderStrong: g("--border-strong"),
      textPrimary: g("--text-primary"),
      textSecondary: g("--text-secondary"),
      textMuted: g("--text-muted"),
      accentPrimary: g("--accent-primary"),
      accentPrimaryText: g("--accent-primary-text"),
      accentOchre: g("--accent-ochre"),
      statusClear: g("--status-clear"),
      statusWarn: g("--status-warn"),
      statusAvoid: g("--status-avoid"),
      sigilContFg: g("--sigil-cont-fg"),
      sigilContBg: g("--sigil-cont-bg"),
      sigilRoleFg: g("--sigil-role-fg"),
      sigilRoleBg: g("--sigil-role-bg"),
      sigilGdcFg: g("--sigil-gdc-fg"),
      sigilIndFg: g("--sigil-ind-fg"),
      fontSans: g("--font-sans") || "-apple-system, BlinkMacSystemFont, 'Inter', 'SF Pro Text', system-ui, sans-serif",
      fontMono: g("--font-mono") || "'JetBrains Mono', 'SF Mono', ui-monospace, Menlo, monospace",
    };
  }

  let tokens = readThemeTokens();

  function applyTheme3d(mode) {
    const isDark = mode === "dark";
    document.documentElement.classList.toggle("dark", isDark);
    document.documentElement.classList.toggle("light", !isDark);
    if (labelTheme3d) labelTheme3d.textContent = isDark ? "Daylight" : "Nocturne";
    tokens = readThemeTokens();
    if (scene && tokens.bgCanvas) {
      scene.background = new THREE.Color(tokens.bgCanvas);
      scene.fog = new THREE.FogExp2(tokens.bgCanvas, 0.042);
    }
    if (ctxLeft && ctxRight) {
      renderAllTextures();
    }
  }

  // ── Initialize App ──────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    try {
      const savedTheme = localStorage.getItem("priory_grimoire_theme");
      if (savedTheme === "light" || savedTheme === "dark") {
        applyTheme3d(savedTheme);
      } else {
        applyTheme3d(document.documentElement.classList.contains("dark") ? "dark" : "light");
      }
    } catch (_) {
      tokens = readThemeTokens();
    }

    initCanvases();
    initThreeScene();
    initPostProcessing();
    initLighting();
    initDeskAndProps();
    initGrimoireTome();
    initInteraction();
    initAudio();
    loadSavedRecipes();
    fetchAccountStatus();
    renderAllTextures();
    animate();
  });

  // ── 1. Canvases & Textures ──────────────────────────────────────────────────
  function initCanvases() {
    const W = 2048, H = 2048;

    canvasLeft = document.createElement("canvas");
    canvasLeft.width = W; canvasLeft.height = H;
    ctxLeft = canvasLeft.getContext("2d");

    canvasRight = document.createElement("canvas");
    canvasRight.width = W; canvasRight.height = H;
    ctxRight = canvasRight.getContext("2d");

    canvasFlipFront = document.createElement("canvas");
    canvasFlipFront.width = W; canvasFlipFront.height = H;
    ctxFlipFront = canvasFlipFront.getContext("2d");

    canvasFlipBack = document.createElement("canvas");
    canvasFlipBack.width = W; canvasFlipBack.height = H;
    ctxFlipBack = canvasFlipBack.getContext("2d");

    textureLeft = new THREE.CanvasTexture(canvasLeft);
    textureLeft.anisotropy = 8;
    textureRight = new THREE.CanvasTexture(canvasRight);
    textureRight.anisotropy = 8;
    textureFlipFront = new THREE.CanvasTexture(canvasFlipFront);
    textureFlipFront.anisotropy = 8;
    textureFlipBack = new THREE.CanvasTexture(canvasFlipBack);
    textureFlipBack.anisotropy = 8;
  }

  function getViewportSize() {
    const w = container && container.clientWidth > 0 ? container.clientWidth : window.innerWidth;
    const h = container && container.clientHeight > 0 ? container.clientHeight : window.innerHeight;
    return { w, h };
  }

  // ── 2. Three.js Scene & Renderer ────────────────────────────────────────────
  function initThreeScene() {
    const { w, h } = getViewportSize();

    scene = new THREE.Scene();
    if (tokens.bgCanvas) {
      scene.background = new THREE.Color(tokens.bgCanvas);
      scene.fog = new THREE.FogExp2(tokens.bgCanvas, 0.042);
    }

    camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
    camera.position.set(0, 5.2, 4.2);

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.05;
    controls.minDistance = 2.0;
    controls.maxDistance = 10.0;
    controls.target.set(0, 0.25, 0);

    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2();

    if (typeof ResizeObserver !== "undefined" && container) {
      const ro = new ResizeObserver(() => onViewportResize());
      ro.observe(container);
    } else {
      window.addEventListener("resize", onViewportResize);
    }
  }

  // ── 3. Post-Processing (UnrealBloom) ────────────────────────────────────────
  function initPostProcessing() {
    const { w, h } = getViewportSize();
    const renderScene = new THREE.RenderPass(scene, camera);
    const bloomPass = new THREE.UnrealBloomPass(
      new THREE.Vector2(w, h),
      0.35,
      0.4,
      0.88
    );

    composer = new THREE.EffectComposer(renderer);
    composer.addPass(renderScene);
    composer.addPass(bloomPass);
  }

  // ── 4. Lighting & Candlelight ───────────────────────────────────────────────
  function initLighting() {
    const ambientLight = new THREE.AmbientLight(0xd8d2c8, 0.75);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xfff5e4, 0.85);
    dirLight.position.set(2, 8, 4);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 2048;
    dirLight.shadow.mapSize.height = 2048;
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 20;
    dirLight.shadow.bias = -0.0001;
    scene.add(dirLight);

    candleLightLeft = new THREE.PointLight(0xffb866, 1.2, 8, 1.2);
    candleLightLeft.position.set(-4.2, 1.6, -0.6);
    candleLightLeft.castShadow = true;
    candleLightLeft.shadow.mapSize.width = 1024;
    candleLightLeft.shadow.mapSize.height = 1024;
    candleLightLeft.shadow.bias = -0.0002;
    scene.add(candleLightLeft);

    candleLightRight = new THREE.PointLight(0xffad55, 1.1, 8, 1.2);
    candleLightRight.position.set(4.2, 1.6, -0.6);
    candleLightRight.castShadow = true;
    candleLightRight.shadow.mapSize.width = 1024;
    candleLightRight.shadow.mapSize.height = 1024;
    candleLightRight.shadow.bias = -0.0002;
    scene.add(candleLightRight);
  }

  // ── 5. Desk Environment & 3D Props ──────────────────────────────────────────
  function initDeskAndProps() {
    const deskGeo = new THREE.BoxGeometry(22, 0.8, 14);
    const deskMat = new THREE.MeshStandardMaterial({
      color: 0x1a1d26,
      roughness: 0.65,
      metalness: 0.1,
    });
    const deskMesh = new THREE.Mesh(deskGeo, deskMat);
    deskMesh.position.y = -0.4;
    deskMesh.receiveShadow = true;
    scene.add(deskMesh);

    createCandleStick(-4.2, 0, -0.6);
    createCandleStick(4.2, 0, -0.6);
    createScryingOrb(3.8, 0, 1.8);
    createInkpotQuill(-3.6, 0, 1.6);
    createScroll(-3.8, 0, -2.0, 0.4);
    createScroll(3.4, 0, -2.2, -0.3);
    createAstrolabe();
  }

  function createCandleStick(x, y, z) {
    const group = new THREE.Group();
    group.position.set(x, y, z);

    const baseGeo = new THREE.CylinderGeometry(0.55, 0.65, 0.12, 24);
    const brassMat = new THREE.MeshStandardMaterial({ color: 0xb88438, metalness: 0.85, roughness: 0.25 });
    const baseMesh = new THREE.Mesh(baseGeo, brassMat);
    baseMesh.castShadow = true;
    group.add(baseMesh);

    const stemGeo = new THREE.CylinderGeometry(0.1, 0.16, 0.8, 16);
    const stemMesh = new THREE.Mesh(stemGeo, brassMat);
    stemMesh.position.y = 0.45;
    stemMesh.castShadow = true;
    group.add(stemMesh);

    const waxGeo = new THREE.CylinderGeometry(0.22, 0.22, 1.0, 20);
    const waxMat = new THREE.MeshStandardMaterial({ color: 0xf3efe6, roughness: 0.6 });
    const waxMesh = new THREE.Mesh(waxGeo, waxMat);
    waxMesh.position.y = 1.35;
    waxMesh.castShadow = true;
    group.add(waxMesh);

    const flameGeo = new THREE.ConeGeometry(0.08, 0.28, 12);
    const flameMat = new THREE.MeshBasicMaterial({ color: 0xffe070 });
    const flameMesh = new THREE.Mesh(flameGeo, flameMat);
    flameMesh.position.y = 1.95;
    group.add(flameMesh);

    scene.add(group);
  }

  function createScryingOrb(x, y, z) {
    const group = new THREE.Group();
    group.position.set(x, y, z);

    const standGeo = new THREE.CylinderGeometry(0.55, 0.75, 0.35, 8);
    const standMat = new THREE.MeshStandardMaterial({ color: 0x252a38, roughness: 0.7 });
    const standMesh = new THREE.Mesh(standGeo, standMat);
    standMesh.position.y = 0.17;
    standMesh.castShadow = true;
    group.add(standMesh);

    const coreGeo = new THREE.SphereGeometry(0.35, 24, 24);
    const coreMat = new THREE.MeshBasicMaterial({ color: 0x7ea4d4 });
    scryingOrbCore = new THREE.Mesh(coreGeo, coreMat);
    scryingOrbCore.position.y = 0.75;
    group.add(scryingOrbCore);

    const glassGeo = new THREE.SphereGeometry(0.55, 32, 32);
    const glassMat = new THREE.MeshPhysicalMaterial({
      color: 0xdce6f5,
      transmission: 0.9,
      roughness: 0.05,
      ior: 1.5,
      transparent: true,
      opacity: 0.95,
    });
    const glassMesh = new THREE.Mesh(glassGeo, glassMat);
    glassMesh.position.y = 0.75;
    group.add(glassMesh);

    const orbLight = new THREE.PointLight(0x7ea4d4, 1.0, 3.5);
    orbLight.position.y = 0.75;
    group.add(orbLight);

    scene.add(group);
  }

  function createInkpotQuill(x, y, z) {
    const group = new THREE.Group();
    group.position.set(x, y, z);

    const potGeo = new THREE.CylinderGeometry(0.28, 0.38, 0.45, 8);
    const potMat = new THREE.MeshStandardMaterial({ color: 0x1e222e, roughness: 0.25, metalness: 0.6 });
    const potMesh = new THREE.Mesh(potGeo, potMat);
    potMesh.position.y = 0.22;
    potMesh.castShadow = true;
    group.add(potMesh);

    const quillGeo = new THREE.ConeGeometry(0.04, 1.4, 6);
    const quillMat = new THREE.MeshStandardMaterial({ color: 0xe9e4d8, roughness: 0.8 });
    const quillMesh = new THREE.Mesh(quillGeo, quillMat);
    quillMesh.position.set(0.08, 0.75, 0);
    quillMesh.rotation.z = -0.35;
    quillMesh.rotation.x = 0.2;
    quillMesh.castShadow = true;
    group.add(quillMesh);

    scene.add(group);
  }

  function createScroll(x, y, z, rotY) {
    const scrollGeo = new THREE.CylinderGeometry(0.18, 0.18, 1.6, 16);
    const scrollMat = new THREE.MeshStandardMaterial({ color: 0xded8ca, roughness: 0.8 });
    const scrollMesh = new THREE.Mesh(scrollGeo, scrollMat);
    scrollMesh.rotation.z = Math.PI / 2;
    scrollMesh.rotation.y = rotY;
    scrollMesh.position.set(x, 0.18, z);
    scrollMesh.castShadow = true;
    scene.add(scrollMesh);
  }

  function createAstrolabe() {
    astrolabeGroup = new THREE.Group();
    astrolabeGroup.position.set(1.75, 0.8, 0);

    const goldMat = new THREE.MeshStandardMaterial({
      color: 0xb88438,
      metalness: 0.9,
      roughness: 0.22,
      emissive: 0x3b2a12,
      emissiveIntensity: 0.25,
    });

    const ring1 = new THREE.Mesh(new THREE.TorusGeometry(0.9, 0.018, 12, 48), goldMat);
    const ring2 = new THREE.Mesh(new THREE.TorusGeometry(0.7, 0.015, 12, 48), goldMat);
    const ring3 = new THREE.Mesh(new THREE.TorusGeometry(0.5, 0.012, 12, 48), goldMat);

    ring1.rotation.x = Math.PI / 3;
    ring2.rotation.y = Math.PI / 4;
    ring3.rotation.z = Math.PI / 6;

    astrolabeGroup.add(ring1);
    astrolabeGroup.add(ring2);
    astrolabeGroup.add(ring3);

    scene.add(astrolabeGroup);
  }

  // ── 6. The 3D Grimoire Tome Rig ─────────────────────────────────────────────
  function initGrimoireTome() {
    bookGroup = new THREE.Group();
    bookGroup.position.set(0, 0.05, 0);

    const bookDepth = 5.0;
    const pageWidth = 3.35;
    const pageDepth = 4.6;

    const coverMat = new THREE.MeshStandardMaterial({ color: 0x252a38, roughness: 0.6, metalness: 0.2 });

    const coverLeft = new THREE.Mesh(new THREE.BoxGeometry(3.6, 0.08, bookDepth), coverMat);
    coverLeft.position.set(-1.85, 0.04, 0);
    coverLeft.castShadow = true;
    coverLeft.receiveShadow = true;
    bookGroup.add(coverLeft);

    const coverRight = new THREE.Mesh(new THREE.BoxGeometry(3.6, 0.08, bookDepth), coverMat);
    coverRight.position.set(1.85, 0.04, 0);
    coverRight.castShadow = true;
    coverRight.receiveShadow = true;
    bookGroup.add(coverRight);

    const spineGeo = new THREE.CylinderGeometry(0.25, 0.25, bookDepth, 16, 1, false, -Math.PI / 2, Math.PI);
    const spineMesh = new THREE.Mesh(spineGeo, coverMat);
    spineMesh.rotation.x = Math.PI / 2;
    spineMesh.position.set(0, 0.04, 0);
    bookGroup.add(spineMesh);

    const stackMat = new THREE.MeshStandardMaterial({ color: 0xded8ca, roughness: 0.85 });
    const stackLeft = new THREE.Mesh(new THREE.BoxGeometry(3.4, 0.16, pageDepth), stackMat);
    stackLeft.position.set(-1.75, 0.14, 0);
    stackLeft.castShadow = true;
    bookGroup.add(stackLeft);

    const stackRight = new THREE.Mesh(new THREE.BoxGeometry(3.4, 0.16, pageDepth), stackMat);
    stackRight.position.set(1.75, 0.14, 0);
    stackRight.castShadow = true;
    bookGroup.add(stackRight);

    const leftPageGeo = createFlatPageGeometry(pageWidth, pageDepth, 24, "left");
    const leftPageMat = new THREE.MeshStandardMaterial({
      map: textureLeft,
      roughness: 0.85,
      metalness: 0.05,
      side: THREE.FrontSide,
    });
    leftPageMesh = new THREE.Mesh(leftPageGeo, leftPageMat);
    leftPageMesh.position.set(-1.75, 0.225, 0);
    leftPageMesh.receiveShadow = true;
    bookGroup.add(leftPageMesh);

    const rightPageGeo = createFlatPageGeometry(pageWidth, pageDepth, 24, "right");
    const rightPageMat = new THREE.MeshStandardMaterial({
      map: textureRight,
      roughness: 0.85,
      metalness: 0.05,
      side: THREE.FrontSide,
    });
    rightPageMesh = new THREE.Mesh(rightPageGeo, rightPageMat);
    rightPageMesh.position.set(1.75, 0.225, 0);
    rightPageMesh.receiveShadow = true;
    bookGroup.add(rightPageMesh);

    flipGeo = new THREE.PlaneGeometry(pageWidth, pageDepth, 32, 16);
    flipGeo.translate(pageWidth / 2, 0, 0);
    flipGeo.rotateX(-Math.PI / 2);

    const flipMatFront = new THREE.MeshStandardMaterial({ map: textureFlipFront, roughness: 0.85, side: THREE.FrontSide });
    const flipMatBack = new THREE.MeshStandardMaterial({ map: textureFlipBack, roughness: 0.85, side: THREE.BackSide });

    flipPivot = new THREE.Group();
    flipPivot.position.set(0, 0.235, 0);
    flipPivot.visible = false;

    const flipMeshFront = new THREE.Mesh(flipGeo, flipMatFront);
    flipMeshFront.castShadow = true;
    flipPivot.add(flipMeshFront);

    const flipMeshBack = new THREE.Mesh(flipGeo, flipMatBack);
    flipMeshBack.castShadow = true;
    flipPivot.add(flipMeshBack);

    bookGroup.add(flipPivot);
    scene.add(bookGroup);
  }

  function createFlatPageGeometry(width, depth, segments, side) {
    const geo = new THREE.PlaneGeometry(width, depth, segments, segments);
    geo.rotateX(-Math.PI / 2);
    const pos = geo.attributes.position;

    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const u = side === "left" ? (width / 2 - x) / width : (x + width / 2) / width;
      const arch = Math.sin(Math.min(1, Math.max(0, u)) * Math.PI) * 0.015;
      pos.setY(i, arch);
    }
    geo.computeVertexNormals();
    return geo;
  }

  // ── 7. Dynamic 2K CanvasTexture Renderers (Priory Tokens, Zero Emojis/Italics) ──
  function renderAllTextures() {
    tokens = readThemeTokens();
    renderLeftPageCanvas();
    renderRightPageCanvas();
    textureLeft.needsUpdate = true;
    textureRight.needsUpdate = true;

    if (astrolabeGroup) {
      astrolabeGroup.visible = currentSpreadIndex === 0;
    }
  }

  function drawPageChrome(ctx, W, H, isLeft) {
    const t = tokens;
    ctx.fillStyle = t.bgSurface1;
    ctx.fillRect(0, 0, W, H);

    ctx.fillStyle = t.bgSurface2;
    ctx.fillRect(60, 60, W - 120, 90);

    ctx.strokeStyle = t.borderSubtle;
    ctx.lineWidth = 4;
    ctx.strokeRect(60, 60, W - 120, H - 120);

    ctx.beginPath();
    ctx.moveTo(60, 150);
    ctx.lineTo(W - 60, 150);
    ctx.stroke();

    // Subtle spine hairline
    ctx.fillStyle = t.borderSubtle;
    if (isLeft) {
      ctx.fillRect(W - 6, 0, 6, H);
    } else {
      ctx.fillRect(0, 0, 6, H);
    }
  }

  function renderLeftPageCanvas() {
    const ctx = ctxLeft;
    const W = 2048, H = 2048;
    const t = tokens;

    drawPageChrome(ctx, W, H, true);

    if (currentSpreadIndex === 0) {
      ctx.fillStyle = t.textMuted;
      ctx.font = `500 32px ${t.fontSans}`;
      ctx.textAlign = "left";
      ctx.fillText("CHAPTER I · QUERY CONSOLE", 100, 116);

      ctx.fillStyle = t.textPrimary;
      ctx.font = `600 68px ${t.fontSans}`;
      ctx.fillText("Priory Grimoire", 100, 260);

      ctx.fillStyle = t.textSecondary;
      ctx.font = `400 38px ${t.fontSans}`;
      ctx.fillText("Account Essence & Legendary Workbench", 100, 325);

      drawAccountEssenceBox(ctx, 100, 390, W - 200, 660);

      ctx.fillStyle = t.textPrimary;
      ctx.font = `600 44px ${t.fontSans}`;
      ctx.textAlign = "left";
      ctx.fillText("Preset Queries", 100, 1150);

      const quicks = [
        "1. Which 2 legendaries can I quickly craft?",
        "2. How do I craft Twilight?",
        "3. How do I craft Sunrise?",
        "4. How do I craft Eternity?",
        "5. What materials do I need for Aurene's Bite?",
      ];
      ctx.font = `400 38px ${t.fontSans}`;
      ctx.fillStyle = t.textSecondary;
      quicks.forEach((q, idx) => {
        const y = 1230 + idx * 82;
        ctx.fillText(q, 110, y);
        ctx.strokeStyle = t.borderSubtle;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(100, y + 26);
        ctx.lineTo(W - 100, y + 26);
        ctx.stroke();
      });

      ctx.fillStyle = t.textMuted;
      ctx.font = `400 32px ${t.fontSans}`;
      ctx.fillText("Durmand Priory Semantic Knowledge Graph · ISO 21838-2", 100, 1900);
    } else {
      const guide = savedRecipes[currentSpreadIndex - 1];
      if (isComparativeRanking(guide)) {
        drawLeaderboardLeftPage(ctx, guide, W, H);
      } else {
        drawStandardRoadmapLeftPage(ctx, guide, W, H);
      }
    }
  }

  function renderRightPageCanvas() {
    const ctx = ctxRight;
    const W = 2048, H = 2048;
    const t = tokens;

    drawPageChrome(ctx, W, H, false);

    if (currentSpreadIndex === 0) {
      ctx.fillStyle = t.textMuted;
      ctx.font = `500 32px ${t.fontSans}`;
      ctx.textAlign = "left";
      ctx.fillText("SCRYING MATRIX · MYSTIC FORGE", 100, 116);

      ctx.fillStyle = t.textPrimary;
      ctx.font = `600 68px ${t.fontSans}`;
      ctx.fillText("Ontological Synthesis", 100, 260);

      drawVitruvianCircle(ctx, W / 2, 920, 440);

      ctx.fillStyle = t.textSecondary;
      ctx.font = `400 40px ${t.fontSans}`;
      ctx.textAlign = "left";
      wrapText(
        ctx,
        "The Mystic Forge combines four canonical inputs: Precursor, Gift of Mastery, Gift of Fortune, and Item-Specific Gift, audited against live account inventory and Wallace 15% Trading Post tax.",
        140,
        1520,
        W - 280,
        58
      );

      ctx.fillStyle = t.accentPrimary;
      ctx.font = `500 34px ${t.fontSans}`;
      ctx.fillText("READY FOR QUERY EXECUTION", 140, 1860);
    } else {
      const guide = savedRecipes[currentSpreadIndex - 1];
      if (isComparativeRanking(guide)) {
        drawLeaderboardRightPage(ctx, guide, W, H);
      } else {
        drawStandardRoadmapRightPage(ctx, guide, W, H);
      }
    }
  }

  function isComparativeRanking(guide) {
    if (!guide) return false;
    const name = (guide.goal_name || "").toLowerCase();
    if (name.includes("closest:") || name.includes("closest") || name.includes("ranking") || name.includes("rankings") || name.includes("recommendation") || name.includes("leaderboard")) {
      return true;
    }
    if (guide.target_quantity > 1 && (!guide.master_roadmap_phases || guide.master_roadmap_phases.length === 0)) {
      return true;
    }
    if ((!guide.master_roadmap_phases || guide.master_roadmap_phases.length === 0) && (guide.strategic_recommendations && guide.strategic_recommendations.length > 0)) {
      return true;
    }
    if (guide.strategic_recommendations && guide.strategic_recommendations.some(r => r.includes("Leaderboard") || r.includes("Closest Legendaries"))) {
      return true;
    }
    return false;
  }

  function stripEmojis(s) {
    return String(s || "").replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, "").replace(/\s{2,}/g, " ").trim();
  }

  function extractLeaderboardData(guide) {
    const items = [];
    if (!guide) return items;

    const recs = guide.strategic_recommendations || [];
    for (const raw of recs) {
      const line = raw.trim();
      const match = line.match(/\*?#(\d+)\s+([^*(]+?)(?:\s*\(([^)]+)\))?\*?:\s*\*?([\d.]+)%?\s*Ready\*?\s*\|\s*(?:Est\.?\s*Cost:\s*)?~?([\d.,]+)g\s*\|\s*\[([^\]]+)\](.*)/i);
      if (match) {
        items.push({
          rank: parseInt(match[1], 10),
          name: match[2].trim().replace(/\*\*/g, ""),
          subtype: match[3] ? match[3].trim() : "Weapon",
          readiness: parseFloat(match[4]),
          cost: parseFloat(match[5].replace(/,/g, "")),
          archetype: match[6].trim(),
          hasKit: line.includes("Bank Kit") || (match[7] && match[7].includes("Bank Kit")),
          hasGate: line.includes("gate") || (match[7] && match[7].includes("gate"))
        });
        continue;
      }
      const m2 = line.match(/#(\d+)\s+([A-Za-z0-9' -]+?)(?:\s*\(([^)]+)\))?[:\s-]+(\d+(?:\.\d+)?)%/i);
      if (m2) {
        const goldM = line.match(/([\d.,]+)\s*g\b/);
        const archM = line.match(/\[([^\]]+)\]/);
        items.push({
          rank: parseInt(m2[1], 10),
          name: m2[2].trim().replace(/\*\*/g, ""),
          subtype: m2[3] ? m2[3].trim() : "Weapon",
          readiness: parseFloat(m2[4]),
          cost: goldM ? parseFloat(goldM[1].replace(/,/g, "")) : 0,
          archetype: archM ? archM[1] : "Standard Crafting",
          hasKit: line.includes("Bank Kit"),
          hasGate: line.includes("gate")
        });
      }
    }

    if (items.length === 0 && guide.goal_name) {
      const topName = guide.goal_name.replace(/^Closest:\s*/i, "").trim();
      items.push({
        rank: 1,
        name: topName,
        subtype: "Weapon",
        readiness: parseFloat(guide.readiness_percentage) || 0,
        cost: 0,
        archetype: "Precursor & Gifts",
        hasKit: recs.some(r => r.includes("Starter Kit") || r.includes("Bank")),
        hasGate: false
      });
    }

    return items;
  }

  function drawLeaderboardLeftPage(ctx, guide, W, H) {
    const t = tokens;
    ctx.fillStyle = t.textMuted;
    ctx.font = `500 32px ${t.fontSans}`;
    ctx.textAlign = "left";
    ctx.fillText("CHAPTER II · COMPARATIVE LEADERBOARD", 100, 116);

    ctx.fillStyle = t.textPrimary;
    ctx.font = `600 58px ${t.fontSans}`;
    ctx.fillText(stripEmojis(guide.goal_name || "Comparative Ranking"), 100, 240);

    // Executive Summary Bar
    ctx.fillStyle = t.bgSurface2;
    ctx.fillRect(100, 290, W - 200, 160);
    ctx.strokeStyle = t.borderSubtle;
    ctx.lineWidth = 3;
    ctx.strokeRect(100, 290, W - 200, 160);
    ctx.fillStyle = t.accentPrimary;
    ctx.fillRect(100, 290, 8, 160);

    ctx.fillStyle = t.textPrimary;
    ctx.font = `400 34px ${t.fontSans}`;
    const execText = stripEmojis(guide.executive_summary || "Evaluated against live materials, wallet, and precursor readiness.");
    wrapText(ctx, execText, 132, 345, W - 270, 44);

    // Flat 1px hairline-divided leaderboard rows
    const items = extractLeaderboardData(guide);
    const rowX = 100;
    const rowW = W - 200;
    const startY = 500;
    const rowH = 225;

    items.slice(0, 5).forEach((item, idx) => {
      const ry = startY + idx * rowH;
      const isTop = idx === 0;

      ctx.fillStyle = isTop ? t.bgSurface2 : t.bgSurface1;
      ctx.fillRect(rowX, ry, rowW, rowH);
      ctx.strokeStyle = t.borderSubtle;
      ctx.lineWidth = 2;
      ctx.strokeRect(rowX, ry, rowW, rowH);

      if (isTop) {
        ctx.fillStyle = t.accentPrimary;
        ctx.fillRect(rowX, ry, 8, rowH);
      }

      // Rank
      ctx.textAlign = "left";
      ctx.fillStyle = isTop ? t.accentPrimary : t.textMuted;
      ctx.font = `600 46px ${t.fontSans}`;
      ctx.fillText(`#${item.rank}`, rowX + 32, ry + 75);

      // Name & Subtype
      ctx.fillStyle = t.textPrimary;
      ctx.font = `600 44px ${t.fontSans}`;
      ctx.fillText(item.name, rowX + 140, ry + 75);

      ctx.fillStyle = t.textMuted;
      ctx.font = `400 32px ${t.fontSans}`;
      ctx.fillText(item.subtype, rowX + 140, ry + 125);

      const flags = [item.archetype];
      if (item.hasKit) flags.push("Bank Kit Ready");
      if (item.hasGate) flags.push("Time-Gated");
      ctx.fillStyle = t.textSecondary;
      ctx.font = `400 28px ${t.fontSans}`;
      ctx.fillText(flags.join(" · "), rowX + 140, ry + 178);

      // Right-aligned metrics (strictly sans-serif, never monospace on numbers)
      const rightEdge = rowX + rowW - 32;
      ctx.textAlign = "right";
      ctx.fillStyle = t.textPrimary;
      ctx.font = `600 44px ${t.fontSans}`;
      ctx.fillText(`${item.readiness}%`, rightEdge, ry + 75);

      // Flat progress bar
      const barW = 320;
      const barH = 14;
      const barX = rightEdge - barW;
      const barY = ry + 100;
      ctx.fillStyle = t.bgSurface3;
      ctx.fillRect(barX, barY, barW, barH);
      const fillW = Math.max(4, (Math.min(100, Math.max(0, item.readiness)) / 100) * barW);
      ctx.fillStyle = t.statusClear;
      ctx.fillRect(barX, barY, fillW, barH);

      ctx.fillStyle = t.sigilContFg;
      ctx.font = `500 34px ${t.fontSans}`;
      const costStr = item.cost > 0 ? `Est. ~${item.cost.toLocaleString()}g` : "Est. ~0g";
      ctx.fillText(costStr, rightEdge, ry + 178);
    });

    ctx.textAlign = "left";
    ctx.fillStyle = t.textMuted;
    ctx.font = `400 32px ${t.fontSans}`;
    ctx.fillText("Archivist Sector Leaderboard Audit", 100, 1900);
  }

  function drawLeaderboardRightPage(ctx, guide, W, H) {
    const t = tokens;
    ctx.fillStyle = t.textMuted;
    ctx.font = `500 32px ${t.fontSans}`;
    ctx.textAlign = "left";
    ctx.fillText("STRATEGIC ACCELERATION & CHECKLIST", 100, 116);

    ctx.fillStyle = t.textPrimary;
    ctx.font = `600 58px ${t.fontSans}`;
    ctx.fillText("Priority Action Sequence", 100, 240);

    const x = 100;
    const w = W - 200;

    const starterKitRec = (guide.strategic_recommendations || []).find(r => r.includes("Starter Kit") || r.includes("Bank Starter Kit"));
    const kitText = starterKitRec
      ? stripEmojis(starterKitRec.replace(/\*\*/g, ""))
      : "Bank Starter Kit synergy: check owned starter kits to bypass precursor and weapon gift crafting costs.";

    ctx.fillStyle = t.bgSurface2;
    ctx.fillRect(x, 290, w, 175);
    ctx.strokeStyle = t.borderSubtle;
    ctx.lineWidth = 2;
    ctx.strokeRect(x, 290, w, 175);

    ctx.fillStyle = t.sigilContFg;
    ctx.font = `600 34px ${t.fontSans}`;
    ctx.fillText("Bank Starter Kit Synergy", x + 28, 345);
    ctx.fillStyle = t.textSecondary;
    ctx.font = `400 32px ${t.fontSans}`;
    wrapText(ctx, kitText, x + 28, 395, w - 56, 42);

    const boosterRec = (guide.strategic_recommendations || []).find(r => r.includes("Booster") || r.includes("Speed Analysis") || r.includes("Zhaitaffy"));
    const boosterText = boosterRec
      ? stripEmojis(boosterRec.replace(/\*\*/g, ""))
      : "Stack Experience, Heroic, and Guild Tavern buffs; convert Astral Acclaim to Mystic Clovers in Wizard's Vault.";

    ctx.fillStyle = t.bgSurface2;
    ctx.fillRect(x, 490, w, 175);
    ctx.strokeStyle = t.borderSubtle;
    ctx.strokeRect(x, 490, w, 175);

    ctx.fillStyle = t.accentPrimary;
    ctx.font = `600 34px ${t.fontSans}`;
    ctx.fillText("Speed & Booster Acceleration", x + 28, 545);
    ctx.fillStyle = t.textSecondary;
    ctx.font = `400 32px ${t.fontSans}`;
    wrapText(ctx, boosterText, x + 28, 595, w - 56, 42);

    ctx.fillStyle = t.textPrimary;
    ctx.font = `600 44px ${t.fontSans}`;
    ctx.fillText("Actionable Checklist", x, 750);

    const checklist = guide.session_checklist || [];
    let ckY = 825;
    checklist.slice(0, 5).forEach((item) => {
      ctx.fillStyle = t.textPrimary;
      ctx.font = `600 36px ${t.fontSans}`;
      const header = `[${item.step_number}] ${stripEmojis(item.title)}`;
      ctx.fillText(header, x + 16, ckY);

      ctx.textAlign = "right";
      ctx.fillStyle = t.accentPrimary;
      ctx.font = `500 32px ${t.fontSans}`;
      ctx.fillText(`${item.estimated_time_minutes}m · ${item.game_mode || "Session"}`, x + w - 16, ckY);

      ctx.textAlign = "left";
      if (item.chat_code) {
        ctx.fillStyle = t.sigilGdcFg;
        ctx.font = `400 28px ${t.fontMono}`;
        ctx.fillText(item.chat_code, x + 16, ckY + 40);
        ckY += 40;
      }

      ckY += 44;
      ctx.fillStyle = t.textSecondary;
      ctx.font = `400 32px ${t.fontSans}`;
      ckY = wrapText(ctx, stripEmojis(item.description), x + 16, ckY, w - 40, 42) + 34;
    });

    if (guide.motivational_tip) {
      ctx.fillStyle = t.textMuted;
      ctx.font = `400 32px ${t.fontSans}`;
      wrapText(ctx, `Note: ${stripEmojis(guide.motivational_tip.replace(/\*\*/g, ""))}`, x, 1780, w, 44);
    }
  }

  function drawStandardRoadmapLeftPage(ctx, guide, W, H) {
    const t = tokens;
    const name = (guide.target_quantity > 1 ? `${guide.target_quantity}x ` : "") + stripEmojis(guide.goal_name || "Legendary Item");
    const chatCode = guide.chat_code || "[&AgErZgAA]";

    ctx.fillStyle = t.textMuted;
    ctx.font = `500 32px ${t.fontSans}`;
    ctx.textAlign = "left";
    ctx.fillText("CHAPTER II · CRAFTING ROADMAP", 100, 116);

    ctx.fillStyle = t.bgSurface2;
    ctx.fillRect(100, 185, W - 200, 260);
    ctx.strokeStyle = t.borderSubtle;
    ctx.lineWidth = 3;
    ctx.strokeRect(100, 185, W - 200, 260);

    ctx.fillStyle = t.textPrimary;
    ctx.font = `600 62px ${t.fontSans}`;
    ctx.fillText(name, 136, 270);

    ctx.fillStyle = t.accentPrimary;
    ctx.font = `400 32px ${t.fontMono}`;
    ctx.fillText(chatCode, 136, 330);

    ctx.fillStyle = t.statusClear;
    ctx.font = `600 40px ${t.fontSans}`;
    ctx.fillText(`Account Readiness: ${guide.readiness_percentage}%`, 136, 405);

    ctx.fillStyle = t.textSecondary;
    ctx.font = `400 36px ${t.fontSans}`;
    wrapText(ctx, stripEmojis(guide.executive_summary || "Structured crafting blueprint."), 100, 520, W - 200, 50);

    ctx.fillStyle = t.textPrimary;
    ctx.font = `600 44px ${t.fontSans}`;
    ctx.fillText("Master Crafting Roadmap", 100, 820);

    const phases = guide.master_roadmap_phases || [];
    ctx.font = `400 35px ${t.fontSans}`;
    ctx.fillStyle = t.textSecondary;
    let yOffset = 895;
    phases.forEach((phase, idx) => {
      yOffset = wrapText(ctx, `${idx + 1}. ${stripEmojis(phase)}`, 116, yOffset, W - 232, 48) + 20;
    });

    if (guide.strategic_recommendations && guide.strategic_recommendations.length > 0) {
      ctx.fillStyle = t.textPrimary;
      ctx.font = `600 42px ${t.fontSans}`;
      ctx.fillText("Currency & Mystic Conversions", 100, 1460);
      ctx.font = `400 34px ${t.fontSans}`;
      ctx.fillStyle = t.textSecondary;
      let recY = 1530;
      guide.strategic_recommendations.slice(0, 3).forEach((rec) => {
        recY = wrapText(ctx, `- ${stripEmojis(rec)}`, 116, recY, W - 232, 46) + 14;
      });
    }
  }

  function drawStandardRoadmapRightPage(ctx, guide, W, H) {
    const t = tokens;
    ctx.fillStyle = t.textMuted;
    ctx.font = `500 32px ${t.fontSans}`;
    ctx.textAlign = "left";
    ctx.fillText("ACTIONABLE ITINERARY & MISSING DELTA", 100, 116);

    ctx.fillStyle = t.textPrimary;
    ctx.font = `600 54px ${t.fontSans}`;
    ctx.fillText("Outstanding Components", 100, 235);

    draw4SocketDisplay(ctx, 100, 280, W - 200, guide.missing_materials_summary || {});

    ctx.fillStyle = t.textPrimary;
    ctx.font = `600 44px ${t.fontSans}`;
    ctx.fillText("Session Action Items", 100, 840);

    const checklist = guide.session_checklist || [];
    let ckY = 915;
    checklist.slice(0, 5).forEach((item) => {
      ctx.fillStyle = t.textPrimary;
      ctx.font = `600 36px ${t.fontSans}`;
      ctx.fillText(`[${item.step_number}] ${stripEmojis(item.title)} (${item.estimated_time_minutes}m)`, 116, ckY);
      ckY += 48;
      ctx.fillStyle = t.textSecondary;
      ctx.font = `400 34px ${t.fontSans}`;
      ckY = wrapText(ctx, stripEmojis(item.description), 132, ckY, W - 264, 44) + 28;
    });

    if (guide.motivational_tip) {
      ctx.fillStyle = t.textMuted;
      ctx.font = `400 34px ${t.fontSans}`;
      wrapText(ctx, `Note: ${stripEmojis(guide.motivational_tip)}`, 100, 1780, W - 200, 46);
    }
  }

  function drawAccountEssenceBox(ctx, x, y, w, h) {
    const t = tokens;
    ctx.fillStyle = t.bgSurface2;
    ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = t.borderSubtle;
    ctx.lineWidth = 3;
    ctx.strokeRect(x, y, w, h);

    ctx.fillStyle = t.textPrimary;
    ctx.font = `600 40px ${t.fontSans}`;
    ctx.textAlign = "left";
    ctx.fillText("Live Account Essence", x + 36, y + 72);

    const armory = accountTelemetry?.account_armory_count ?? "—";
    const mats = accountTelemetry?.account_materials_count ?? "—";
    const gold = accountTelemetry?.wallet?.liquid_gold != null
      ? `${accountTelemetry.wallet.liquid_gold.toLocaleString(undefined, { maximumFractionDigits: 0 })}g`
      : "—";
    const shards = accountTelemetry?.wallet?.spirit_shards?.toLocaleString() ?? "—";
    const aa = accountTelemetry?.wallet?.astral_acclaim?.toLocaleString() ?? "—";
    const vm = accountTelemetry?.wallet?.volatile_magic?.toLocaleString() ?? "—";

    const stats = [
      ["Armory Legendaries", String(armory)],
      ["Tracked Materials", String(mats)],
      ["Liquid Gold", String(gold)],
      ["Spirit Shards", String(shards)],
      ["Astral Acclaim", String(aa)],
      ["Volatile Magic", String(vm)],
    ];

    const colW = (w - 72) / 2;
    stats.forEach(([lbl, val], idx) => {
      const col = idx < 3 ? 0 : 1;
      const row = idx % 3;
      const rx = x + 36 + col * colW;
      const ry = y + 165 + row * 150;

      ctx.textAlign = "left";
      ctx.fillStyle = t.textMuted;
      ctx.font = `400 32px ${t.fontSans}`;
      ctx.fillText(lbl, rx, ry);

      ctx.fillStyle = t.textPrimary;
      ctx.font = `600 44px ${t.fontSans}`;
      ctx.fillText(val, rx, ry + 56);
    });
  }

  function drawVitruvianCircle(ctx, cx, cy, r) {
    const t = tokens;
    ctx.save();
    ctx.strokeStyle = t.borderStrong;
    ctx.lineWidth = 4;

    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();

    ctx.strokeStyle = t.accentPrimary;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.82, 0, Math.PI * 2);
    ctx.stroke();

    ctx.strokeStyle = t.accentOchre;
    ctx.lineWidth = 3;
    drawPolygon(ctx, cx, cy, r * 0.82, 3, -Math.PI / 2);
    drawPolygon(ctx, cx, cy, r * 0.82, 3, Math.PI / 2);

    ctx.strokeStyle = t.sigilGdcFg;
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.45, 0, Math.PI * 2);
    ctx.stroke();

    // Draw central diamond BFO GDC sigil geometrically
    ctx.strokeStyle = t.sigilGdcFg;
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.moveTo(cx, cy - 55);
    ctx.lineTo(cx + 55, cy);
    ctx.lineTo(cx, cy + 55);
    ctx.lineTo(cx - 55, cy);
    ctx.closePath();
    ctx.stroke();

    ctx.fillStyle = t.sigilGdcFg;
    ctx.beginPath();
    ctx.arc(cx, cy, 14, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  function draw4SocketDisplay(ctx, x, y, w, mats) {
    const t = tokens;
    const entries = Object.entries(mats).slice(0, 4);
    const boxW = (w - 40) / 2;
    const boxH = 220;

    for (let i = 0; i < 4; i++) {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const bx = x + col * (boxW + 40);
      const by = y + row * (boxH + 24);

      ctx.fillStyle = t.bgSurface2;
      ctx.fillRect(bx, by, boxW, boxH);
      ctx.strokeStyle = t.borderSubtle;
      ctx.lineWidth = 2;
      ctx.strokeRect(bx, by, boxW, boxH);

      const entry = entries[i];
      if (entry) {
        ctx.fillStyle = t.textPrimary;
        ctx.font = `600 36px ${t.fontSans}`;
        ctx.textAlign = "left";
        ctx.fillText(entry[0], bx + 28, by + 76);

        ctx.fillStyle = t.statusAvoid;
        ctx.font = `500 34px ${t.fontSans}`;
        ctx.fillText(`${entry[1].toLocaleString()} needed`, bx + 28, by + 146);
      } else {
        ctx.fillStyle = t.textMuted;
        ctx.font = `400 32px ${t.fontSans}`;
        ctx.fillText("Mystic Component", bx + 28, by + 110);
      }
    }
  }

  function drawPolygon(ctx, cx, cy, r, sides, startAngle) {
    ctx.beginPath();
    for (let i = 0; i < sides; i++) {
      const a = startAngle + (i * Math.PI * 2) / sides;
      const x = cx + Math.cos(a) * r;
      const y = cy + Math.sin(a) * r;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.stroke();
  }

  function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
    if (!text) return y;
    const paragraphs = String(text).split("\n");
    let currentY = y;
    for (let p = 0; p < paragraphs.length; p++) {
      const words = paragraphs[p].split(" ");
      let line = "";
      for (let n = 0; n < words.length; n++) {
        const testLine = line + words[n] + " ";
        const metrics = ctx.measureText(testLine);
        if (metrics.width > maxWidth && n > 0) {
          ctx.fillText(line, x, currentY);
          line = words[n] + " ";
          currentY += lineHeight;
        } else {
          line = testLine;
        }
      }
      ctx.fillText(line, x, currentY);
      if (p < paragraphs.length - 1) {
        currentY += lineHeight;
      }
    }
    return currentY;
  }

  // ── 8. 3D Page Flip Engine ──────────────────────────────────────────────────
  function turnPage3D(direction) {
    if (isFlipping) return;

    const totalSpreads = 1 + savedRecipes.length;
    const targetIndex = currentSpreadIndex + direction;
    if (targetIndex < 0 || targetIndex >= totalSpreads) return;

    isFlipping = true;
    playSound("sfx-page-turn");

    if (direction > 0) {
      ctxFlipFront.drawImage(canvasRight, 0, 0);
      textureFlipFront.needsUpdate = true;

      const oldSpread = currentSpreadIndex;
      currentSpreadIndex = targetIndex;
      renderLeftPageCanvas();
      ctxFlipBack.drawImage(canvasLeft, 0, 0);
      textureFlipBack.needsUpdate = true;
      currentSpreadIndex = oldSpread;
    } else {
      ctxFlipFront.drawImage(canvasLeft, 0, 0);
      textureFlipFront.needsUpdate = true;

      const oldSpread = currentSpreadIndex;
      currentSpreadIndex = targetIndex;
      renderRightPageCanvas();
      ctxFlipBack.drawImage(canvasRight, 0, 0);
      textureFlipBack.needsUpdate = true;
      currentSpreadIndex = oldSpread;
    }

    flipPivot.visible = true;
    const startRot = direction > 0 ? 0 : Math.PI;
    const endRot = direction > 0 ? Math.PI : 0;
    flipPivot.rotation.z = startRot;

    const animObj = { progress: 0 };

    gsap.to(animObj, {
      progress: 1,
      duration: 0.85,
      ease: "power2.inOut",
      onUpdate: () => {
        const curRot = THREE.MathUtils.lerp(startRot, endRot, animObj.progress);
        flipPivot.rotation.z = curRot;

        const pos = flipGeo.attributes.position;
        const bendFactor = Math.sin(animObj.progress * Math.PI) * 0.35;

        for (let i = 0; i < pos.count; i++) {
          const x = pos.getX(i);
          const u = Math.min(1, Math.max(0, x / 3.35));
          const yLift = Math.sin(u * Math.PI) * bendFactor;
          pos.setY(i, yLift);
        }
        flipGeo.computeVertexNormals();
        pos.needsUpdate = true;
      },
      onComplete: () => {
        currentSpreadIndex = targetIndex;
        renderAllTextures();
        updateHUD();
        flipPivot.visible = false;
        isFlipping = false;
      }
    });
  }

  // ── 9. Interaction & HUD Events ─────────────────────────────────────────────
  function initInteraction() {
    if (btnPrev) btnPrev.addEventListener("click", () => turnPage3D(-1));
    if (btnNext) btnNext.addEventListener("click", () => turnPage3D(1));

    if (tabInscribe) {
      tabInscribe.addEventListener("click", () => {
        if (currentSpreadIndex !== 0) turnPage3D(-currentSpreadIndex);
      });
    }

    if (btnThemeToggle3d) {
      btnThemeToggle3d.addEventListener("click", () => {
        const next = document.documentElement.classList.contains("dark") ? "light" : "dark";
        applyTheme3d(next);
        try { localStorage.setItem("priory_grimoire_theme", next); } catch (_) {}
      });
    }

    document.addEventListener("keydown", (e) => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      if (e.key === "ArrowLeft") turnPage3D(-1);
      if (e.key === "ArrowRight") turnPage3D(1);
    });

    if (formInscribe) {
      formInscribe.addEventListener("submit", (e) => {
        e.preventDefault();
        const q = inputQuery.value.trim();
        if (q) executeQuery(q);
      });
    }

    document.querySelectorAll(".spell-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const q = chip.getAttribute("data-q");
        inputQuery.value = q;
        executeQuery(q);
      });
    });

    document.querySelectorAll(".cam-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".cam-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        setCameraMode(btn.getAttribute("data-mode"));
      });
    });

    window.addEventListener("click", onSceneClick);
  }

  function onSceneClick(e) {
    if (!renderer || e.target !== renderer.domElement) return;

    const rect = renderer.domElement.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;

    mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects([leftPageMesh, rightPageMesh]);

    if (intersects.length > 0) {
      const hit = intersects[0];
      if (hit.object === rightPageMesh) {
        turnPage3D(1);
      } else if (hit.object === leftPageMesh) {
        turnPage3D(-1);
      }
    }
  }

  function setCameraMode(mode) {
    activeCameraMode = mode;
    let targetPos, targetLook;

    switch (mode) {
      case "inspect":
        targetPos = { x: -0.6, y: 3.4, z: 2.4 };
        targetLook = { x: -0.6, y: 0.25, z: 0 };
        break;
      case "astrolabe":
        targetPos = { x: 1.6, y: 3.6, z: 2.2 };
        targetLook = { x: 1.6, y: 0.4, z: 0 };
        break;
      case "orbit":
        targetPos = { x: 3.2, y: 4.8, z: 5.2 };
        targetLook = { x: 0, y: 0.25, z: 0 };
        break;
      case "reading":
      default:
        targetPos = { x: 0, y: 5.2, z: 4.2 };
        targetLook = { x: 0, y: 0.25, z: 0 };
        break;
    }

    gsap.to(camera.position, {
      x: targetPos.x, y: targetPos.y, z: targetPos.z,
      duration: 1.2,
      ease: "power2.out"
    });

    gsap.to(controls.target, {
      x: targetLook.x, y: targetLook.y, z: targetLook.z,
      duration: 1.2,
      ease: "power2.out"
    });
  }

  // ── 10. API Data & Query Pipeline ───────────────────────────────────────────
  async function fetchAccountStatus() {
    try {
      const res = await fetch("/api/status");
      accountTelemetry = await res.json();
      if (accountEssenceBadge) {
        const armory = accountTelemetry.account_armory_count ?? 0;
        const gold = accountTelemetry.wallet?.liquid_gold != null
          ? Math.round(accountTelemetry.wallet.liquid_gold)
          : 0;
        accountEssenceBadge.textContent = `${armory} Legendaries · ${gold}g`;
      }
      renderAllTextures();
    } catch (err) {
      console.warn("Failed to fetch status:", err);
    }
  }

  async function executeQuery(query) {
    if (btnForge) {
      btnForge.disabled = true;
      forgeBtnText.classList.add("hidden");
      forgeSpinner.classList.remove("hidden");
    }

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await res.json();

      if (data.success && data.guide) {
        playSound("sfx-forge-chime");
        showCopyNotification(`Loaded ${data.guide.goal_name}`);

        const existingIdx = savedRecipes.findIndex(r => r.goal_name === data.guide.goal_name);
        if (existingIdx !== -1) {
          savedRecipes[existingIdx] = data.guide;
          currentSpreadIndex = existingIdx + 1;
        } else {
          savedRecipes.push(data.guide);
          saveRecipesToStorage();
          currentSpreadIndex = savedRecipes.length;
        }

        renderAllTextures();
        updateHUD();
      } else {
        alert(data.error || "The Priory could not resolve this goal.");
      }
    } catch (err) {
      alert("Connection error: " + err.message);
    } finally {
      if (btnForge) {
        btnForge.disabled = false;
        forgeBtnText.classList.remove("hidden");
        forgeSpinner.classList.add("hidden");
      }
    }
  }

  function updateHUD() {
    const totalSpreads = 1 + savedRecipes.length;
    if (btnPrev) btnPrev.disabled = currentSpreadIndex === 0;
    if (btnNext) btnNext.disabled = currentSpreadIndex >= totalSpreads - 1;

    if (pageIndicator) {
      if (currentSpreadIndex === 0) {
        pageIndicator.textContent = `Chapter I · Inscription · Spread 1 of ${totalSpreads}`;
        if (tabInscribe) tabInscribe.classList.add("active");
      } else {
        const rec = savedRecipes[currentSpreadIndex - 1];
        pageIndicator.textContent = `Chapter II · ${rec.goal_name} · Spread ${currentSpreadIndex + 1} of ${totalSpreads}`;
        if (tabInscribe) tabInscribe.classList.remove("active");
      }
    }

    if (savedTabsContainer) {
      savedTabsContainer.innerHTML = "";
      savedRecipes.forEach((r, idx) => {
        const tab = document.createElement("button");
        tab.className = `tome-tab-3d ${currentSpreadIndex === idx + 1 ? "active" : ""}`;
        tab.type = "button";
        tab.textContent = r.goal_name;
        tab.addEventListener("click", () => {
          const diff = (idx + 1) - currentSpreadIndex;
          if (diff !== 0) turnPage3D(diff);
        });
        savedTabsContainer.appendChild(tab);
      });
    }
  }

  function loadSavedRecipes() {
    try {
      const raw = localStorage.getItem("priory_grimoire_recipes");
      if (raw) savedRecipes = JSON.parse(raw);
    } catch (e) {
      savedRecipes = [];
    }
    updateHUD();
  }

  function saveRecipesToStorage() {
    try {
      localStorage.setItem("priory_grimoire_recipes", JSON.stringify(savedRecipes));
    } catch (e) {}
    updateHUD();
  }

  // ── 11. Audio & Notifications ───────────────────────────────────────────────
  function initAudio() {
    if (audioToggle) {
      audioToggle.textContent = audioEnabled ? "Sound On" : "Sound Off";
      if (audioEnabled) audioToggle.classList.add("active");

      audioToggle.addEventListener("click", () => {
        audioEnabled = !audioEnabled;
        try { localStorage.setItem("priory_audio_3d", audioEnabled); } catch (_) {}
        audioToggle.textContent = audioEnabled ? "Sound On" : "Sound Off";
        audioToggle.classList.toggle("active", audioEnabled);
      });
    }
  }

  function playSound(id) {
    if (!audioEnabled) return;
    const el = document.getElementById(id);
    if (el) {
      el.currentTime = 0;
      el.play().catch(() => {});
    }
  }

  function showCopyNotification(msg) {
    if (!copyBadge) return;
    copyBadge.textContent = msg;
    copyBadge.classList.remove("hidden");
    setTimeout(() => {
      copyBadge.classList.add("hidden");
    }, 2000);
  }

  // ── 12. Main Animation Loop & ResizeObserver ────────────────────────────────
  function animate() {
    requestAnimationFrame(animate);

    const time = performance.now() * 0.001;

    if (candleLightLeft) {
      candleLightLeft.intensity = 1.2 + Math.sin(time * 12) * 0.1 + Math.cos(time * 23) * 0.06;
    }
    if (candleLightRight) {
      candleLightRight.intensity = 1.1 + Math.cos(time * 14) * 0.1 + Math.sin(time * 19) * 0.05;
    }

    if (scryingOrbCore) {
      const s = 1.0 + Math.sin(time * 2.5) * 0.06;
      scryingOrbCore.scale.set(s, s, s);
    }

    if (astrolabeGroup && astrolabeGroup.visible) {
      astrolabeGroup.rotation.y = time * 0.4;
      astrolabeGroup.children[0].rotation.x = time * 0.3;
      astrolabeGroup.children[1].rotation.y = -time * 0.5;
      astrolabeGroup.children[2].rotation.z = time * 0.6;
      astrolabeGroup.position.y = 0.8 + Math.sin(time * 1.5) * 0.05;
    }

    controls.update();
    composer.render();
  }

  function onViewportResize() {
    if (!camera || !renderer || !composer) return;
    const { w, h } = getViewportSize();
    if (w <= 0 || h <= 0) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
    composer.setSize(w, h);
  }
})();
