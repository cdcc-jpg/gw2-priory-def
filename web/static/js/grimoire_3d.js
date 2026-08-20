/**
 * PROJECT PRIORY — NEXT-GEN WEBGL 3D INTERACTIVE GRIMOIRE CONTROLLER
 * Full Three.js PBR rendering, 3D desk props, flat curved parchment geometry,
 * vertex-deformed 3D page flip physics, dynamic 2K CanvasTextures,
 * UnrealBloomPass post-processing, and interactive raycasting.
 * Clean, emoji-free archival typesetting.
 */

(function() {
  'use strict';

  // ── State Management ────────────────────────────────────────────────────────
  let currentSpreadIndex = 0;
  let savedRecipes = [];
  let accountTelemetry = null;
  let isFlipping = false;
  let audioEnabled = localStorage.getItem("priory_audio_3d") === "true";
  let activeCameraMode = "reading";

  // ── Three.js Global Objects ──────────────────────────────────────────────────
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

  // ── Initialize App ──────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
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

  // ── 2. Three.js Scene & Renderer ────────────────────────────────────────────
  function initThreeScene() {
    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x080604, 0.045);

    camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(0, 5.2, 4.2);

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
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

    window.addEventListener("resize", onWindowResize);
  }

  // ── 3. Post-Processing (UnrealBloom) ─────────────────────────────────────────
  function initPostProcessing() {
    const renderScene = new THREE.RenderPass(scene, camera);
    const bloomPass = new THREE.UnrealBloomPass(
      new THREE.Vector2(window.innerWidth, window.innerHeight),
      0.65,
      0.45,
      0.82
    );

    composer = new THREE.EffectComposer(renderer);
    composer.addPass(renderScene);
    composer.addPass(bloomPass);
  }

  // ── 4. Lighting & Candlelight ───────────────────────────────────────────────
  function initLighting() {
    const ambientLight = new THREE.AmbientLight(0x281c20, 0.8);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffdfa0, 0.9);
    dirLight.position.set(2, 8, 4);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 2048;
    dirLight.shadow.mapSize.height = 2048;
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 20;
    dirLight.shadow.bias = -0.0001;
    scene.add(dirLight);

    candleLightLeft = new THREE.PointLight(0xffaa44, 1.8, 8, 1.2);
    candleLightLeft.position.set(-4.2, 1.6, -0.6);
    candleLightLeft.castShadow = true;
    candleLightLeft.shadow.mapSize.width = 1024;
    candleLightLeft.shadow.mapSize.height = 1024;
    candleLightLeft.shadow.bias = -0.0002;
    scene.add(candleLightLeft);

    candleLightRight = new THREE.PointLight(0xff9933, 1.6, 8, 1.2);
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
      color: 0x140d08,
      roughness: 0.45,
      metalness: 0.15,
    });
    const deskMesh = new THREE.Mesh(deskGeo, deskMat);
    deskMesh.position.y = -0.4;
    deskMesh.receiveShadow = true;
    scene.add(deskMesh);

    const wallGeo = new THREE.PlaneGeometry(30, 16);
    const wallMat = new THREE.MeshStandardMaterial({ color: 0x0a0706, roughness: 0.9 });
    const wallMesh = new THREE.Mesh(wallGeo, wallMat);
    wallMesh.position.set(0, 4, -7);
    scene.add(wallMesh);

    createCandleStick(-4.2, 0, -0.6);
    createCandleStick(4.2, 0, -0.6);
    createScryingOrb(3.8, 0, 1.8);
    createInkpotQuill(-3.6, 0, 1.6);
    createScroll(-3.8, 0, -2.0, 0.4);
    createScroll(3.4, 0, -2.2, -0.3);
    createAstrolabe();
    createFloatingParticles();
  }

  function createCandleStick(x, y, z) {
    const group = new THREE.Group();
    group.position.set(x, y, z);

    const baseGeo = new THREE.CylinderGeometry(0.55, 0.65, 0.12, 24);
    const brassMat = new THREE.MeshStandardMaterial({ color: 0xc8963e, metalness: 0.85, roughness: 0.25 });
    const baseMesh = new THREE.Mesh(baseGeo, brassMat);
    baseMesh.castShadow = true;
    group.add(baseMesh);

    const stemGeo = new THREE.CylinderGeometry(0.1, 0.16, 0.8, 16);
    const stemMesh = new THREE.Mesh(stemGeo, brassMat);
    stemMesh.position.y = 0.45;
    stemMesh.castShadow = true;
    group.add(stemMesh);

    const waxGeo = new THREE.CylinderGeometry(0.22, 0.22, 1.0, 20);
    const waxMat = new THREE.MeshStandardMaterial({ color: 0xf5eedb, roughness: 0.6 });
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
    const standMat = new THREE.MeshStandardMaterial({ color: 0x24160a, roughness: 0.7 });
    const standMesh = new THREE.Mesh(standGeo, standMat);
    standMesh.position.y = 0.17;
    standMesh.castShadow = true;
    group.add(standMesh);

    const coreGeo = new THREE.SphereGeometry(0.35, 24, 24);
    const coreMat = new THREE.MeshBasicMaterial({ color: 0x9d5bd2 });
    scryingOrbCore = new THREE.Mesh(coreGeo, coreMat);
    scryingOrbCore.position.y = 0.75;
    group.add(scryingOrbCore);

    const glassGeo = new THREE.SphereGeometry(0.55, 32, 32);
    const glassMat = new THREE.MeshPhysicalMaterial({
      color: 0xecd0ff,
      transmission: 0.9,
      roughness: 0.05,
      ior: 1.5,
      transparent: true,
      opacity: 0.95,
    });
    const glassMesh = new THREE.Mesh(glassGeo, glassMat);
    glassMesh.position.y = 0.75;
    group.add(glassMesh);

    const orbLight = new THREE.PointLight(0x9d5bd2, 1.2, 3.5);
    orbLight.position.y = 0.75;
    group.add(orbLight);

    scene.add(group);
  }

  function createInkpotQuill(x, y, z) {
    const group = new THREE.Group();
    group.position.set(x, y, z);

    const potGeo = new THREE.CylinderGeometry(0.28, 0.38, 0.45, 8);
    const potMat = new THREE.MeshStandardMaterial({ color: 0x110c14, roughness: 0.2, metalness: 0.6 });
    const potMesh = new THREE.Mesh(potGeo, potMat);
    potMesh.position.y = 0.22;
    potMesh.castShadow = true;
    group.add(potMesh);

    const quillGeo = new THREE.ConeGeometry(0.04, 1.4, 6);
    const quillMat = new THREE.MeshStandardMaterial({ color: 0xe8dfc8, roughness: 0.8 });
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
    const scrollMat = new THREE.MeshStandardMaterial({ color: 0xd9cbb0, roughness: 0.8 });
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
      color: 0xc8963e,
      metalness: 0.9,
      roughness: 0.2,
      emissive: 0x5a3810,
      emissiveIntensity: 0.3,
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

  function createFloatingParticles() {
    const N = 120;
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(N * 3);
    const colors = new Float32Array(N * 3);

    for (let i = 0; i < N; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 12;
      positions[i * 3 + 1] = Math.random() * 4 + 0.2;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 8;

      const isPurple = Math.random() < 0.35;
      if (isPurple) {
        colors[i * 3] = 0.62; colors[i * 3 + 1] = 0.36; colors[i * 3 + 2] = 0.82;
      } else {
        colors[i * 3] = 0.85; colors[i * 3 + 1] = 0.65; colors[i * 3 + 2] = 0.25;
      }
    }

    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const mat = new THREE.PointsMaterial({
      size: 0.06,
      vertexColors: true,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending,
    });

    const particles = new THREE.Points(geo, mat);
    scene.add(particles);
  }

  // ── 6. The 3D Grimoire Tome Rig (Flat Open Pages) ───────────────────────────
  function initGrimoireTome() {
    bookGroup = new THREE.Group();
    bookGroup.position.set(0, 0.05, 0);

    const bookDepth = 5.0;
    const pageWidth = 3.35;
    const pageDepth = 4.6;

    // Leather Covers (lying flat on desk)
    const coverMat = new THREE.MeshStandardMaterial({ color: 0x1c1109, roughness: 0.6, metalness: 0.2 });

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

    // Spine Binding
    const spineGeo = new THREE.CylinderGeometry(0.25, 0.25, bookDepth, 16, 1, false, -Math.PI / 2, Math.PI);
    const spineMesh = new THREE.Mesh(spineGeo, coverMat);
    spineMesh.rotation.x = Math.PI / 2;
    spineMesh.position.set(0, 0.04, 0);
    bookGroup.add(spineMesh);

    // Page Stacks (Visible paper volume thickness)
    const stackMat = new THREE.MeshStandardMaterial({ color: 0xd9cea8, roughness: 0.85 });
    const stackLeft = new THREE.Mesh(new THREE.BoxGeometry(3.4, 0.16, pageDepth), stackMat);
    stackLeft.position.set(-1.75, 0.14, 0);
    stackLeft.castShadow = true;
    bookGroup.add(stackLeft);

    const stackRight = new THREE.Mesh(new THREE.BoxGeometry(3.4, 0.16, pageDepth), stackMat);
    stackRight.position.set(1.75, 0.14, 0);
    stackRight.castShadow = true;
    bookGroup.add(stackRight);

    // ── FLAT OPEN PAGES (Positioned horizontally on the stacks) ──
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

    // ── 3D FLIPPING LEAF OVERLAY (Horizontal Pivot Rig) ──
    flipGeo = new THREE.PlaneGeometry(pageWidth, pageDepth, 32, 16);
    flipGeo.translate(pageWidth / 2, 0, 0);
    flipGeo.rotateX(-Math.PI / 2); // pre-rotate geometry to lie flat in X-Z plane

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

  /**
   * Generates a flat horizontal PlaneGeometry lying in the X-Z plane with subtle spine arching.
   */
  function createFlatPageGeometry(width, depth, segments, side) {
    const geo = new THREE.PlaneGeometry(width, depth, segments, segments);
    geo.rotateX(-Math.PI / 2); // lies flat in X-Z plane, normal facing +Y
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

  // ── 7. Dynamic 2K CanvasTexture Renderers (Zero Emojis) ──────────────────────
  function renderAllTextures() {
    renderLeftPageCanvas();
    renderRightPageCanvas();
    textureLeft.needsUpdate = true;
    textureRight.needsUpdate = true;

    if (astrolabeGroup) {
      astrolabeGroup.visible = currentSpreadIndex === 0;
    }
  }

  function renderLeftPageCanvas() {
    const ctx = ctxLeft;
    const W = 2048, H = 2048;

    const bgGrad = ctx.createLinearGradient(0, 0, W, H);
    bgGrad.addColorStop(0, '#f9f2e4');
    bgGrad.addColorStop(0.5, '#eee0c7');
    bgGrad.addColorStop(1, '#dfcea8');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, W, H);

    const spineShadow = ctx.createLinearGradient(W - 120, 0, W, 0);
    spineShadow.addColorStop(0, 'rgba(0,0,0,0)');
    spineShadow.addColorStop(1, 'rgba(40,25,10,0.3)');
    ctx.fillStyle = spineShadow;
    ctx.fillRect(W - 120, 0, 120, H);

    ctx.strokeStyle = '#c8963e';
    ctx.lineWidth = 12;
    ctx.strokeRect(60, 60, W - 120, H - 120);

    ctx.strokeStyle = '#70338a';
    ctx.lineWidth = 4;
    ctx.strokeRect(80, 80, W - 160, H - 160);

    if (currentSpreadIndex === 0) {
      // ── SPREAD 0: CHAPTER I INSCRIPTION ──
      ctx.fillStyle = '#7b6348';
      ctx.font = '36px JetBrains Mono';
      ctx.textAlign = 'center';
      ctx.fillText('FU TH A R K G W H N I J P EI Z S T B E M', W / 2, 160);

      ctx.fillStyle = '#24160a';
      ctx.font = 'bold 84px Cinzel';
      ctx.fillText('CHAPTER I: INSCRIPTION', W / 2, 270);

      ctx.fillStyle = '#70338a';
      ctx.font = '64px Caveat';
      ctx.fillText('~ The Scholar’s Live Ledger ~', W / 2, 350);

      drawAccountEssenceBox(ctx, 140, 420, W - 280, 620);

      ctx.fillStyle = '#24160a';
      ctx.font = 'bold 52px Cinzel';
      ctx.textAlign = 'left';
      ctx.fillText('Fast Inscription Commands', 140, 1140);

      const quicks = [
        '• "Which 2 legendaries can I quickly craft?"',
        '• "How do I craft Twilight?"',
        '• "How do I craft Sunrise?"',
        '• "How do I craft Eternity?"',
        '• "What materials do I need for Aurene\'s Bite?"',
      ];
      ctx.font = '44px Caveat';
      ctx.fillStyle = '#4d3620';
      quicks.forEach((q, idx) => {
        ctx.fillText(q, 160, 1220 + idx * 80);
      });

      ctx.font = 'italic 40px IM Fell English';
      ctx.fillStyle = '#7b6348';
      ctx.textAlign = 'center';
      ctx.fillText('"Truth resides in the knowledge of the archives."', W / 2, 1850);
      ctx.font = 'bold 36px Cinzel';
      ctx.fillStyle = '#c8963e';
      ctx.fillText('— DURMAND PRIORY ARCHIVIST —', W / 2, 1920);

    } else {
      // ── SPREAD N: LEGENDARY ITINERARY ──
      const guide = savedRecipes[currentSpreadIndex - 1];
      const name = (guide.target_quantity > 1 ? `${guide.target_quantity}x ` : '') + (guide.goal_name || 'Legendary Item');
      const chatCode = guide.chat_code || '[&AgErZgAA]';

      ctx.fillStyle = '#1c1424';
      ctx.fillRect(120, 120, W - 240, 360);
      ctx.strokeStyle = '#9d5bd2';
      ctx.lineWidth = 6;
      ctx.strokeRect(120, 120, W - 240, 360);

      ctx.fillStyle = '#9d5bd2';
      ctx.font = 'bold 76px Cinzel';
      ctx.textAlign = 'left';
      ctx.fillText(name, 160, 240);

      ctx.font = '36px JetBrains Mono';
      ctx.fillStyle = '#ffd478';
      ctx.fillText(`Chat Code: ${chatCode}`, 160, 310);

      ctx.font = 'bold 44px Cinzel';
      ctx.fillStyle = '#ffffff';
      ctx.fillText(`Account Readiness: ${guide.readiness_percentage}%`, 160, 410);

      ctx.font = 'italic 42px IM Fell English';
      ctx.fillStyle = '#4d3620';
      wrapText(ctx, `"${guide.executive_summary || 'An artifact of tremendous power and prestige.'}"`, 140, 560, W - 280, 60);

      ctx.fillStyle = '#24160a';
      ctx.font = 'bold 54px Cinzel';
      ctx.fillText('5-Phase Master Crafting Roadmap', 140, 880);

      const phases = guide.master_roadmap_phases || [];
      ctx.font = '40px IM Fell English';
      ctx.fillStyle = '#332014';
      let yOffset = 960;
      phases.forEach((phase, idx) => {
        yOffset = wrapText(ctx, `${idx + 1}. ${phase}`, 160, yOffset, W - 320, 54) + 20;
      });

      if (guide.strategic_recommendations && guide.strategic_recommendations.length > 0) {
        ctx.fillStyle = '#24160a';
        ctx.font = 'bold 50px Cinzel';
        ctx.fillText('Currency & Mystic Conversions', 140, 1500);
        ctx.font = '38px IM Fell English';
        ctx.fillStyle = '#4d3620';
        let recY = 1580;
        guide.strategic_recommendations.slice(0, 3).forEach((rec) => {
          recY = wrapText(ctx, `• ${rec}`, 160, recY, W - 320, 50) + 15;
        });
      }
    }
  }

  function renderRightPageCanvas() {
    const ctx = ctxRight;
    const W = 2048, H = 2048;

    const bgGrad = ctx.createLinearGradient(0, 0, W, H);
    bgGrad.addColorStop(0, '#dfcea8');
    bgGrad.addColorStop(0.5, '#eee0c7');
    bgGrad.addColorStop(1, '#f9f2e4');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, W, H);

    const spineShadow = ctx.createLinearGradient(0, 0, 120, 0);
    spineShadow.addColorStop(0, 'rgba(40,25,10,0.3)');
    spineShadow.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = spineShadow;
    ctx.fillRect(0, 0, 120, H);

    ctx.strokeStyle = '#c8963e';
    ctx.lineWidth = 12;
    ctx.strokeRect(60, 60, W - 120, H - 120);

    ctx.strokeStyle = '#70338a';
    ctx.lineWidth = 4;
    ctx.strokeRect(80, 80, W - 160, H - 160);

    if (currentSpreadIndex === 0) {
      // ── SPREAD 0: THE SCRYING MATRIX ──
      ctx.fillStyle = '#7b6348';
      ctx.font = '36px JetBrains Mono';
      ctx.textAlign = 'center';
      ctx.fillText('P EI Z S T B E M L NG O D F U TH A R K G W', W / 2, 160);

      ctx.fillStyle = '#24160a';
      ctx.font = 'bold 84px Cinzel';
      ctx.fillText('THE SCRYING MATRIX', W / 2, 270);

      ctx.fillStyle = '#70338a';
      ctx.font = '64px Caveat';
      ctx.fillText('~ Alchemical Geometry ~', W / 2, 350);

      drawVitruvianCircle(ctx, W / 2, 900, 480);

      ctx.fillStyle = '#4d3620';
      ctx.font = 'italic 44px IM Fell English';
      wrapText(ctx, '"The Mystic Forge recognizes neither gold nor glory alone, but the harmonious combination of the four alchemical gifts."', W / 2 - 600, 1540, 1200, 64);

      ctx.font = 'bold 38px Cinzel';
      ctx.fillStyle = '#c8963e';
      ctx.fillText('READY TO FORGE TRUTH', W / 2, 1850);

    } else {
      // ── SPREAD N: CHECKLIST & 4-SOCKET MYSTIC FORGE ──
      const guide = savedRecipes[currentSpreadIndex - 1];

      ctx.fillStyle = '#24160a';
      ctx.font = 'bold 64px Cinzel';
      ctx.textAlign = 'center';
      ctx.fillText('ACTIONABLE ITINERARY', W / 2, 180);

      ctx.fillStyle = '#70338a';
      ctx.font = '54px Caveat';
      ctx.fillText('~ Master Crafter’s Checklist & Delta ~', W / 2, 250);

      draw4SocketDisplay(ctx, 140, 310, W - 280, guide.missing_materials_summary || {});

      ctx.textAlign = 'left';
      ctx.fillStyle = '#24160a';
      ctx.font = 'bold 50px Cinzel';
      ctx.fillText('Session Action Items', 140, 860);

      const checklist = guide.session_checklist || [];
      let ckY = 940;
      checklist.slice(0, 5).forEach((item) => {
        ctx.fillStyle = '#24160a';
        ctx.font = 'bold 40px Cinzel';
        ctx.fillText(`[${item.step_number}] ${item.title} (~${item.estimated_time_minutes}m)`, 160, ckY);
        ckY += 52;
        ctx.fillStyle = '#4d3620';
        ctx.font = '38px IM Fell English';
        ckY = wrapText(ctx, item.description, 180, ckY, W - 360, 48) + 30;
      });

      if (guide.motivational_tip) {
        ctx.fillStyle = '#7a2b1f';
        ctx.font = '52px Caveat';
        wrapText(ctx, `Note: ${guide.motivational_tip}`, 160, 1750, W - 320, 60);
      }
    }
  }

  function drawAccountEssenceBox(ctx, x, y, w, h) {
    ctx.fillStyle = 'rgba(0,0,0,0.04)';
    ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = '#cbb68d';
    ctx.lineWidth = 4;
    ctx.strokeRect(x, y, w, h);

    ctx.fillStyle = '#24160a';
    ctx.font = 'bold 50px Cinzel';
    ctx.textAlign = 'left';
    ctx.fillText('LIVE ACCOUNT ESSENCE', x + 40, y + 80);

    const armory = accountTelemetry?.account_armory_count ?? '—';
    const mats = accountTelemetry?.account_materials_count ?? '—';
    const gold = accountTelemetry?.wallet?.liquid_gold != null
      ? `${accountTelemetry.wallet.liquid_gold.toLocaleString(undefined, { maximumFractionDigits: 0 })} g`
      : '—';
    const shards = accountTelemetry?.wallet?.spirit_shards?.toLocaleString() ?? '—';
    const aa = accountTelemetry?.wallet?.astral_acclaim?.toLocaleString() ?? '—';
    const vm = accountTelemetry?.wallet?.volatile_magic?.toLocaleString() ?? '—';

    const stats = [
      ['Armory Legendaries:', String(armory)],
      ['Tracked Materials:', String(mats)],
      ['Liquid Gold:', String(gold)],
      ['Spirit Shards:', String(shards)],
      ['Astral Acclaim:', String(aa)],
      ['Volatile Magic:', String(vm)],
    ];

    stats.forEach(([lbl, val], idx) => {
      const rowX = idx < 3 ? x + 50 : x + w / 2 + 30;
      const rowY = y + 170 + (idx % 3) * 130;

      ctx.fillStyle = '#7b6348';
      ctx.font = '40px IM Fell English';
      ctx.fillText(lbl, rowX, rowY);

      ctx.fillStyle = '#24160a';
      ctx.font = 'bold 44px JetBrains Mono';
      ctx.fillText(val, rowX, rowY + 54);
    });
  }

  function drawVitruvianCircle(ctx, cx, cy, r) {
    ctx.save();
    ctx.strokeStyle = '#c8963e';
    ctx.lineWidth = 6;

    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();

    ctx.strokeStyle = '#70338a';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.82, 0, Math.PI * 2);
    ctx.stroke();

    ctx.strokeStyle = '#c8963e';
    ctx.lineWidth = 4;
    drawPolygon(ctx, cx, cy, r * 0.82, 3, -Math.PI / 2);
    drawPolygon(ctx, cx, cy, r * 0.82, 3, Math.PI / 2);

    ctx.strokeStyle = '#70338a';
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.45, 0, Math.PI * 2);
    ctx.stroke();

    ctx.fillStyle = '#9d5bd2';
    ctx.font = '100px Cinzel';
    ctx.textAlign = 'center';
    ctx.fillText('◈', cx, cy + 35);

    ctx.restore();
  }

  function draw4SocketDisplay(ctx, x, y, w, mats) {
    const entries = Object.entries(mats).slice(0, 4);
    const boxW = (w - 60) / 2;
    const boxH = 220;

    for (let i = 0; i < 4; i++) {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const bx = x + col * (boxW + 60);
      const by = y + row * (boxH + 20);

      ctx.fillStyle = 'rgba(0,0,0,0.03)';
      ctx.fillRect(bx, by, boxW, boxH);
      ctx.strokeStyle = '#c8963e';
      ctx.lineWidth = 3;
      ctx.strokeRect(bx, by, boxW, boxH);

      const entry = entries[i];
      if (entry) {
        ctx.fillStyle = '#9d5bd2';
        ctx.font = 'bold 40px Cinzel';
        ctx.textAlign = 'left';
        ctx.fillText(entry[0], bx + 30, by + 70);

        ctx.fillStyle = '#a03020';
        ctx.font = 'bold 38px JetBrains Mono';
        ctx.fillText(`${entry[1].toLocaleString()} needed`, bx + 30, by + 140);
      } else {
        ctx.fillStyle = '#7b6348';
        ctx.font = 'italic 36px IM Fell English';
        ctx.fillText('Mystic Component', bx + 30, by + 100);
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
    const words = text.split(' ');
    let line = '';
    for (let n = 0; n < words.length; n++) {
      const testLine = line + words[n] + ' ';
      const metrics = ctx.measureText(testLine);
      if (metrics.width > maxWidth && n > 0) {
        ctx.fillText(line, x, y);
        line = words[n] + ' ';
        y += lineHeight;
      } else {
        line = testLine;
      }
    }
    ctx.fillText(line, x, y);
    return y;
  }

  // ── 8. 3D Page Flip Engine (Horizontal Rotation & Vertex Curl) ───────────────
  function turnPage3D(direction) {
    if (isFlipping) return;

    const totalSpreads = 1 + savedRecipes.length;
    const targetIndex = currentSpreadIndex + direction;
    if (targetIndex < 0 || targetIndex >= totalSpreads) return;

    isFlipping = true;
    playSound('sfx-page-turn');

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

        // Vertex curling deformation in Y (normal to horizontal page)
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
    btnPrev.addEventListener("click", () => turnPage3D(-1));
    btnNext.addEventListener("click", () => turnPage3D(1));

    tabInscribe.addEventListener("click", () => {
      if (currentSpreadIndex !== 0) turnPage3D(-currentSpreadIndex);
    });

    document.addEventListener("keydown", (e) => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      if (e.key === "ArrowLeft") turnPage3D(-1);
      if (e.key === "ArrowRight") turnPage3D(1);
    });

    formInscribe.addEventListener("submit", (e) => {
      e.preventDefault();
      const q = inputQuery.value.trim();
      if (q) executeQuery(q);
    });

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
    if (e.target.closest(".hud-layer")) return;

    mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;

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
        accountEssenceBadge.textContent = `${armory} Legendaries • ${gold}g`;
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
        playSound('sfx-forge-chime');
        showCopyNotification(`Forged ${data.guide.goal_name}`);

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
    btnPrev.disabled = currentSpreadIndex === 0;
    btnNext.disabled = currentSpreadIndex >= totalSpreads - 1;

    if (currentSpreadIndex === 0) {
      pageIndicator.textContent = `Chapter I • Inscription • Spread 1 of ${totalSpreads}`;
      tabInscribe.classList.add("active");
    } else {
      const rec = savedRecipes[currentSpreadIndex - 1];
      pageIndicator.textContent = `Chapter II • ${rec.goal_name} • Spread ${currentSpreadIndex + 1} of ${totalSpreads}`;
      tabInscribe.classList.remove("active");
    }

    savedTabsContainer.innerHTML = "";
    savedRecipes.forEach((r, idx) => {
      const tab = document.createElement("button");
      tab.className = `tome-tab-3d ${currentSpreadIndex === idx + 1 ? 'active' : ''}`;
      tab.textContent = r.goal_name;
      tab.addEventListener("click", () => {
        const diff = (idx + 1) - currentSpreadIndex;
        if (diff !== 0) turnPage3D(diff);
      });
      savedTabsContainer.appendChild(tab);
    });
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
        localStorage.setItem("priory_audio_3d", audioEnabled);
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

  // ── 12. Main Animation Loop ─────────────────────────────────────────────────
  function animate() {
    requestAnimationFrame(animate);

    const time = performance.now() * 0.001;

    if (candleLightLeft) {
      candleLightLeft.intensity = 1.8 + Math.sin(time * 12) * 0.15 + Math.cos(time * 23) * 0.1;
    }
    if (candleLightRight) {
      candleLightRight.intensity = 1.6 + Math.cos(time * 14) * 0.14 + Math.sin(time * 19) * 0.08;
    }

    if (scryingOrbCore) {
      const s = 1.0 + Math.sin(time * 2.5) * 0.08;
      scryingOrbCore.scale.set(s, s, s);
    }

    if (astrolabeGroup && astrolabeGroup.visible) {
      astrolabeGroup.rotation.y = time * 0.4;
      astrolabeGroup.children[0].rotation.x = time * 0.3;
      astrolabeGroup.children[1].rotation.y = -time * 0.5;
      astrolabeGroup.children[2].rotation.z = time * 0.6;
      astrolabeGroup.position.y = 0.8 + Math.sin(time * 1.5) * 0.06;
    }

    controls.update();
    composer.render();
  }

  function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
    composer.setSize(window.innerWidth, window.innerHeight);
  }

})();
