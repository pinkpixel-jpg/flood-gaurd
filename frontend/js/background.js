(function () {
  var canvas = document.getElementById('bg3d');
  if (!canvas || typeof THREE === 'undefined') return;

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var isHome = document.body.getAttribute('data-page') === 'home';

  var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));

  var scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x2f3e46, 0.052);

  var camera = new THREE.PerspectiveCamera(58, 1, 0.1, 120);
  camera.position.set(0, 2.4, 10);

  function hash(n) { return (Math.sin(n) * 43758.5453) % 1; }

  var terrainGeo = new THREE.PlaneGeometry(70, 40, 54, 30);
  terrainGeo.rotateX(-Math.PI / 2);
  var tPos = terrainGeo.attributes.position;
  var tBase = [];
  for (var i = 0; i < tPos.count; i++) {
    tBase.push({ x: tPos.getX(i), z: tPos.getZ(i), seed: hash(i * 12.9898) });
  }
  var terrain = new THREE.Mesh(
    terrainGeo,
    new THREE.MeshBasicMaterial({
      color: 0xffd166, wireframe: true, transparent: true,
      opacity: 0.05, fog: true
    })
  );
  terrain.position.set(0, -3.4, -6);
  scene.add(terrain);

  var waterGeo = new THREE.PlaneGeometry(80, 30, 60, 9);
  waterGeo.rotateX(-Math.PI / 2);
  var wPos = waterGeo.attributes.position;
  var wBase = [];
  for (var j = 0; j < wPos.count; j++) {
    wBase.push({ x: wPos.getX(j), z: wPos.getZ(j) });
  }
  var waterMesh = new THREE.Mesh(
    waterGeo,
    new THREE.MeshBasicMaterial({
      color: 0xcad2c5, wireframe: true, transparent: true,
      opacity: 0.035, fog: true
    })
  );
  waterMesh.position.set(0, -2.6, 2);
  scene.add(waterMesh);

  var RAIN_COUNT = isHome ? 420 : 220;
  var rainGeo = new THREE.BufferGeometry();
  var rainPosArr = new Float32Array(RAIN_COUNT * 3);
  var rainSpeed = new Float32Array(RAIN_COUNT);
  var rainDrift = new Float32Array(RAIN_COUNT);
  for (var r = 0; r < RAIN_COUNT; r++) {
    rainPosArr[r * 3] = (Math.random() - 0.5) * 36;
    rainPosArr[r * 3 + 1] = Math.random() * 22;
    rainPosArr[r * 3 + 2] = (Math.random() - 0.5) * 26 - 4;
    rainSpeed[r] = 14 + Math.random() * 16;
    rainDrift[r] = (Math.random() - 0.5) * 1.6;
  }
  rainGeo.setAttribute('position', new THREE.BufferAttribute(rainPosArr, 3));
  var rainMat = new THREE.PointsMaterial({
    color: 0xcad2c5, size: 0.055, sizeAttenuation: true,
    transparent: true, opacity: 0, depthWrite: false
  });
  var rain = new THREE.Points(rainGeo, rainMat);
  scene.add(rain);

  var dustCount = isHome ? 90 : 50;
  var dustGeo = new THREE.BufferGeometry();
  var dustArr = new Float32Array(dustCount * 3);
  for (var d = 0; d < dustCount; d++) {
    dustArr[d * 3] = (Math.random() - 0.5) * 34;
    dustArr[d * 3 + 1] = Math.random() * 14 + 1;
    dustArr[d * 3 + 2] = (Math.random() - 0.5) * 24;
  }
  dustGeo.setAttribute('position', new THREE.BufferAttribute(dustArr, 3));
  var dustMat = new THREE.PointsMaterial({
    color: 0xcad2c5, size: 0.035, transparent: true,
    opacity: 0.28, depthWrite: false
  });
  var dust = new THREE.Points(dustGeo, dustMat);
  scene.add(dust);

  var state = { rain: 0, target: isHome ? 0 : 0.35 };
  window.FGBG = {
    rainState: state,
    setRain: function (v) { state.target = v; }
  };

  var pointer = { x: 0, y: 0 };
  window.addEventListener('pointermove', function (e) {
    pointer.x = (e.clientX / window.innerWidth - 0.5) * 2;
    pointer.y = (e.clientY / window.innerHeight - 0.5) * 2;
  }, { passive: true });

  function resize() {
    renderer.setSize(window.innerWidth, window.innerHeight, false);
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize);
  resize();

  var clock = new THREE.Clock();
  var running = true;
  document.addEventListener('visibilitychange', function () {
    running = !document.hidden;
    if (running) clock.getDelta();
  });

  function frame() {
    requestAnimationFrame(frame);
    if (!running) return;
    var dt = Math.min(clock.getDelta(), 0.05);
    var t = clock.elapsedTime;

    state.rain += (state.target - state.rain) * Math.min(dt * 1.6, 1);
    rainMat.opacity = 0.34 * state.rain;

    for (var k = 0; k < RAIN_COUNT; k++) {
      rainPosArr[k * 3 + 1] -= rainSpeed[k] * dt * Math.max(state.rain, 0.001);
      rainPosArr[k * 3] += rainDrift[k] * dt;
      if (rainPosArr[k * 3 + 1] < -2) {
        rainPosArr[k * 3 + 1] = 20 + Math.random() * 4;
        rainPosArr[k * 3] = (Math.random() - 0.5) * 36;
      }
    }
    rainGeo.attributes.position.needsUpdate = true;

    for (var a = 0; a < tPos.count; a++) {
      var bx = tBase[a].x, bz = tBase[a].z;
      var hh =
        Math.sin(bx * 0.18 + t * 0.42) * Math.cos(bz * 0.16 - t * 0.3) * 0.85 +
        Math.sin((bx + bz) * 0.09 + t * 0.22) * 1.45 +
        Math.sin(bx * 0.42 - bz * 0.31 + tBase[a].seed * 6.28 + t * 0.55) * 0.28;
      tPos.setY(a, hh);
    }
    terrainGeo.attributes.position.needsUpdate = true;

    for (var b = 0; b < wPos.count; b++) {
      var wx = wBase[b].x, wz = wBase[b].z;
      wPos.setY(b, Math.sin(wx * 0.5 + t * 1.15) * 0.09 + Math.cos(wz * 0.7 + t * 0.85) * 0.07);
    }
    waterGeo.attributes.position.needsUpdate = true;

    dust.rotation.y = t * 0.012;

    var camX = pointer.x * 0.7;
    var camY = 2.4 - pointer.y * 0.35;
    camera.position.x += (camX - camera.position.x) * 0.03;
    camera.position.y += (camY - camera.position.y) * 0.03;
    camera.lookAt(0, 0.4, -4);

    renderer.render(scene, camera);
  }

  if (reduced) {
    rainMat.opacity = 0;
    renderer.render(scene, camera);
  } else {
    frame();
  }
})();
