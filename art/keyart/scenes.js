// Scene painters for keyart.html (loaded after the helpers).

// Draw a figure from a joint skeleton into ctx: limbs are thick round strokes.
function drawFigure(ctx, ox, oy, s, fig, flip = 1) {
  const P = ([x, y]) => [ox + x * s * flip, oy + y * s];
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  if (fig.torso) { ctx.beginPath(); fig.torso.forEach((p, i) => { const [x, y] = P(p); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.closePath(); ctx.fill(); }
  (fig.limbs || []).forEach(([pts, w0, w1]) => {
    for (let i = 1; i < pts.length; i++) {
      const [x0, y0] = P(pts[i - 1]), [x1, y1] = P(pts[i]);
      ctx.lineWidth = lerp(w0, w1, i / (pts.length - 1)) * s; ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
    }
  });
  if (fig.head) { const [x, y] = P(fig.head); ctx.beginPath(); ctx.ellipse(x, y, fig.headR * s * 0.85, fig.headR * s, 0, 0, 7); ctx.fill(); }
}
function maskCanvas(paint) { const c = document.createElement('canvas'); c.width = W; c.height = H; const x = c.getContext('2d'); x.fillStyle = '#fff'; x.strokeStyle = '#fff'; paint(x); return c; }
function blurred(c, px) { const o = document.createElement('canvas'); o.width = W; o.height = H; const x = o.getContext('2d'); x.filter = `blur(${px}px)`; x.drawImage(c, 0, 0); return o; }

// Molten-fire body: cracks of light over deep red, bright rim, flame tongues rising off the top edges.
function fireBody(mask, bbox, opts = {}) {
  const [bx0, by0, bx1, by1] = bbox, bw = bx1 - bx0, bh = by1 - by0;
  const m = mask.getContext('2d').getImageData(bx0, by0, bw, bh).data;
  const soft = blurred(mask, 16).getContext('2d').getImageData(bx0, by0, bw, bh).data;
  const out = g.getImageData(bx0, by0, bw, bh), d = out.data;
  for (let y = 0; y < bh; y++) for (let x = 0; x < bw; x++) {
    const i = (y * bw + x) * 4, a = m[i + 3] / 255; if (a < 0.02) continue;
    const v = soft[i + 3] / 255; // ~1 deep inside, ~0.5 at the edge
    const X = bx0 + x, Y = by0 + y;
    const n = fbm(X * 0.018, Y * 0.018 - 3.1, 5), crack = Math.max(0, 1 - Math.abs(n - 0.5) / 0.045);
    const heat = Math.min(1, Math.max(0, (1 - v) * 1.9 + crack * 0.9 + (fbm(X * 0.006, Y * 0.006) - 0.4) * 0.6));
    const r = lerp(150, 255, Math.min(1, heat * 1.6)), gg = lerp(25, 235, heat * heat), b = lerp(12, 190, Math.pow(heat, 3));
    d[i] = lerp(d[i], r, a); d[i + 1] = lerp(d[i + 1], gg, a); d[i + 2] = lerp(d[i + 2], b, a);
  }
  g.putImageData(out, bx0, by0);
  // flame tongues from upward-facing edge pixels
  g.save(); g.globalCompositeOperation = 'lighter';
  for (let k = 0; k < (opts.tongues || 5000); k++) {
    const x = Math.floor(R(0, bw)), y = Math.floor(R(8, bh));
    const i = (y * bw + x) * 4, iu = ((y - 7) * bw + x) * 4;
    if (m[i + 3] < 128 || m[iu + 3] > 40) continue;
    const X = bx0 + x, Y = by0 + y, hair = opts.hairY && Y < opts.hairY;
    const len = R(10, 34) * (hair ? 2.8 : 1), lean = (fbm(X * 0.01, Y * 0.01) - 0.5) * len * 1.2;
    const gr = g.createLinearGradient(X, Y, X + lean, Y - len);
    gr.addColorStop(0, 'rgba(255,230,150,0.40)'); gr.addColorStop(0.5, 'rgba(255,120,40,0.20)'); gr.addColorStop(1, 'rgba(200,30,20,0)');
    g.fillStyle = gr; const w = R(1.5, 4) * (hair ? 1.6 : 1);
    g.beginPath(); g.moveTo(X - w, Y); g.quadraticCurveTo(X + lean * 0.3 - w, Y - len * 0.6, X + lean, Y - len); g.quadraticCurveTo(X + lean * 0.3 + w, Y - len * 0.6, X + w, Y); g.fill();
  }
  g.restore();
}

// --- VAHAGN ------------------------------------------------------------------
function masis(x0, base, s, col, snow) {
  g.fillStyle = col; g.beginPath(); g.moveTo(x0, base); g.lineTo(x0 + 350 * s, base - 370 * s); g.lineTo(x0 + 410 * s, base - 382 * s); g.lineTo(x0 + 460 * s, base - 365 * s); g.lineTo(x0 + 840 * s, base); g.fill();
  g.beginPath(); g.moveTo(x0 + 720 * s, base); g.lineTo(x0 + 860 * s, base - 180 * s); g.lineTo(x0 + 1010 * s, base); g.fill();
  g.fillStyle = snow; g.beginPath(); g.moveTo(x0 + 310 * s, base - 328 * s); g.lineTo(x0 + 350 * s, base - 370 * s); g.lineTo(x0 + 410 * s, base - 382 * s); g.lineTo(x0 + 460 * s, base - 365 * s); g.lineTo(x0 + 500 * s, base - 325 * s); g.lineTo(x0 + 455 * s, base - 340 * s); g.lineTo(x0 + 420 * s, base - 318 * s); g.lineTo(x0 + 375 * s, base - 338 * s); g.closePath(); g.fill();
  g.beginPath(); g.moveTo(x0 + 835 * s, base - 150 * s); g.lineTo(x0 + 860 * s, base - 180 * s); g.lineTo(x0 + 888 * s, base - 150 * s); g.lineTo(x0 + 860 * s, base - 160 * s); g.closePath(); g.fill();
}
function vishap(path, rim) {
  const pts = path;
  for (let i = 0; i < pts.length; i++) {
    const [x, y, r] = pts[i];
    g.fillStyle = '#0c0312'; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
    if (i % 7 === 0 && i > 10) { // dorsal spikes
      const [x2, y2] = pts[Math.min(pts.length - 1, i + 1)], a = Math.atan2(y2 - y, x2 - x) - Math.PI / 2;
      g.beginPath(); g.moveTo(x + Math.cos(a - 0.4) * r, y + Math.sin(a - 0.4) * r); g.lineTo(x + Math.cos(a) * r * 2.1, y + Math.sin(a) * r * 2.1); g.lineTo(x + Math.cos(a + 0.4) * r, y + Math.sin(a + 0.4) * r); g.fill();
    }
  }
  g.save(); g.globalCompositeOperation = 'lighter';
  pts.forEach(([x, y, r], i) => { if (i % 2) return; g.strokeStyle = rim; g.lineWidth = 1.6; g.beginPath(); g.arc(x, y, r * 0.92, Math.PI * 0.75, Math.PI * 1.25); g.stroke(); });
  g.restore();
}
function vahagn() {
  const HZ = 650;
  g.fillStyle = vgrad([[0, '#05010f'], [0.35, '#1c0630'], [0.62, '#4a0f45'], [0.82, '#9a2c4c'], [0.95, '#e8714a']], 0, HZ); g.fillRect(0, 0, W, HZ);
  stars(900, 430);
  clouds(140, 560, 'rgba(130,40,110,A)', 0.10, 0.003);
  masis(-40, HZ, 0.62, 'rgba(45,10,42,0.9)', 'rgba(255,200,210,0.25)');
  // the vishap, coiled in the sky, lit by the hero
  const pts = []; for (let t = 0; t <= 1; t += 0.0035) { const x = 1880 - 640 * t + 80 * Math.sin(t * 8), y = 150 + 300 * t - 120 * Math.sin(t * Math.PI * 1.6); pts.push([x, y, t < 0.9 ? lerp(8, 38, Math.min(1, t * 1.6)) : lerp(38, 30, (t - 0.9) * 10)]); }
  g.save(); g.globalAlpha = 0.95; vishap(pts, 'rgba(255,110,60,0.5)');
  const [hx, hy] = pts[pts.length - 1];
  g.fillStyle = '#0c0312'; g.beginPath(); g.moveTo(hx + 20, hy - 30); g.lineTo(hx - 70, hy - 26); g.lineTo(hx - 118, hy - 8); g.lineTo(hx - 70, hy + 4); g.lineTo(hx - 110, hy + 30); g.lineTo(hx - 50, hy + 24); g.lineTo(hx + 20, hy + 34); g.fill();
  g.beginPath(); g.moveTo(hx - 10, hy - 28); g.lineTo(hx + 40, hy - 90); g.lineTo(hx + 18, hy - 26); g.fill(); g.beginPath(); g.moveTo(hx + 10, hy - 24); g.lineTo(hx + 70, hy - 70); g.lineTo(hx + 30, hy - 20); g.fill();
  g.globalCompositeOperation = 'lighter'; glowDot(hx - 52, hy - 14, 18, 'rgba(255,70,30,A)', 1); glowDot(hx - 100, hy + 10, 60, 'rgba(255,90,30,A)', 0.35);
  g.restore();
  // purple sea with the hero's reflection
  g.fillStyle = vgrad([[0, '#5a1650'], [0.25, '#35093d'], [1, '#0b0213']], HZ, H); g.fillRect(0, HZ, W, H - HZ);
  for (let i = 0; i < 2600; i++) {
    const y = HZ + Math.pow(rnd(), 1.6) * (H - HZ), x = R(0, W), len = R(10, 60) * (1 + (y - HZ) / 200), near = Math.exp(-Math.pow((x - 960) / 240, 2));
    g.strokeStyle = rnd() < near * 0.9 ? `rgba(255,${R(120, 200) | 0},80,${R(0.2, 0.75)})` : `rgba(200,110,200,${R(0.03, 0.14)})`;
    g.lineWidth = R(1, 2.5); g.beginPath(); g.moveTo(x - len / 2, y); g.lineTo(x + len / 2, y); g.stroke();
  }
  // the crimson reed
  g.save(); g.lineCap = 'round'; g.strokeStyle = '#8a1220'; g.lineWidth = 14; g.shadowColor = '#ff3b2f'; g.shadowBlur = 26;
  g.beginPath(); g.moveTo(990, 900); g.bezierCurveTo(978, 800, 975, 700, 962, 640); g.stroke();
  g.fillStyle = '#9e1826';
  [[982, 830, 1, 120], [978, 760, -1, 100], [975, 705, 1, 80]].forEach(([x, y, dir, l]) => { g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + dir * l * 0.6, y - l * 0.7, x + dir * l, y - l * 0.35); g.quadraticCurveTo(x + dir * l * 0.5, y - l * 0.45, x, y - 14); g.fill(); });
  g.restore();
  for (let i = 0; i < 300; i++) { const t = rnd(); glowDot(962 + Math.sin(t * 11) * 70 * t + R(-40, 40), 640 - t * 560, R(30, 90) * (0.5 + t), 'rgba(170,120,170,A)', 0.045 * (1 - t)); }
  // the fire youth: arms raised, legs dissolving into the reed's flame
  const cx = 962, hip = 476, s = 0.8;
  const fig = {
    torso: [[-72, -172], [72, -172], [54, -120], [36, -44], [38, 0], [-38, 0], [-36, -44], [-54, -120]],
    limbs: [
      [[[-64, -162], [-138, -236], [-176, -332]], 34, 22], [[[64, -162], [138, -236], [176, -332]], 34, 22],
      [[[-20, -6], [-28, 82], [-10, 172]], 44, 12], [[[20, -6], [30, 82], [10, 172]], 44, 12],
      [[[0, -176], [0, -196]], 30, 30],
    ],
    head: [0, -226], headR: 32,
  };
  const mask = maskCanvas(x => { drawFigure(x, cx, hip, s, fig); x.beginPath(); x.ellipse(cx - 180 * s, hip - 348 * s, 15 * s, 19 * s, -0.3, 0, 7); x.ellipse(cx + 180 * s, hip - 348 * s, 15 * s, 19 * s, 0.3, 0, 7); x.fill(); });
  g.save(); g.globalCompositeOperation = 'lighter';
  glowDot(cx, hip - 110, 600, 'rgba(255,80,40,A)', 0.30); glowDot(cx, hip - 120, 280, 'rgba(255,160,70,A)', 0.30);
  g.filter = 'blur(28px)'; g.globalAlpha = 0.85; g.drawImage(mask, 0, 0); g.filter = 'none'; g.globalAlpha = 1;
  g.restore();
  fireBody(mask, [cx - 240, hip - 330, cx + 240, hip + 160], { tongues: 22000, hairY: hip - 190 * s });
  // soft bloom over the hero
  const snap = document.createElement('canvas'); snap.width = W; snap.height = H; snap.getContext('2d').drawImage(cv, 0, 0);
  g.save(); g.globalCompositeOperation = 'screen'; g.globalAlpha = 0.35; g.filter = 'blur(10px)'; g.drawImage(snap, 0, 0); g.filter = 'none'; g.restore();
  g.save(); g.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 900; i++) { const a = R(0, Math.PI * 2), dd = Math.pow(rnd(), 0.6) * 700; const x = cx + Math.cos(a) * dd * 1.3, y = hip - 140 - Math.abs(Math.sin(a)) * dd * 0.6; g.fillStyle = `rgba(255,${R(120, 220) | 0},60,${R(0.2, 0.9)})`; g.fillRect(x, y, R(1, 3), R(1, 3)); }
  const ey = hip - 230 * s;
  [-1, 1].forEach(k => { glowDot(cx + k * 10 * s, ey, 11, 'rgba(255,255,235,A)', 1); glowDot(cx + k * 10 * s, ey, 34, 'rgba(255,220,120,A)', 0.6); });
  glowDot(cx, hip + 172 * s, 90, 'rgba(255,170,80,A)', 0.8);
  g.restore();
  vignette(0.7);
  badge('ԳԼՈՒԽ I · ԿՈՆՑԵՊՏ');
  title('ՎԱՀԱԳՆ', 'ՎԻՇԱՊԱՔԱՂ', '«Երկնէր երկին, երկնէր երկիր, երկնէր և ծովն ծիրանի…»', '#fff1c2', '#ff8a3a', 'rgba(255,110,40,0.9)', 985);
}

// --- HAYK --------------------------------------------------------------------
function hayk() {
  g.fillStyle = vgrad([[0, '#060b1e'], [0.4, '#1d1d3e'], [0.65, '#6b2f3e'], [0.85, '#d9764a'], [1, '#f6c27a']], 0, 720); g.fillRect(0, 0, W, 720);
  stars(500, 300, '230,235,255');
  clouds(180, 560, 'rgba(255,150,110,A)', 0.07, 0.0028);
  masis(930, 720, 1.0, '#3a2440', 'rgba(255,230,230,0.55)');
  ridge(730, 250, 0.0022, '#2a1a33', 3);
  // valley haze
  g.fillStyle = vgrad([[0, 'rgba(255,150,100,0)'], [1, 'rgba(255,150,100,0.18)']], 620, 820); g.fillRect(0, 620, W, 200);
  ridge(830, 190, 0.003, '#1a1022', 9);
  // Bel: giant king on the far ridge, spear and shield
  const bx = 1560, bf = 770;
  g.fillStyle = '#0e0711'; g.strokeStyle = '#0e0711';
  drawFigure(g, bx, bf - 150, 1.25, {
    torso: [[-52, -150], [52, -150], [44, -60], [70, 0], [80, 120], [-80, 120], [-70, 0], [-44, -60]],
    limbs: [[[[-48, -142], [-92, -80], [-110, -10]], 30, 22], [[[48, -142], [100, -90], [118, -150]], 30, 22]],
    head: [0, -182], headR: 26,
  });
  g.lineWidth = 7; g.beginPath(); g.moveTo(bx + 150, bf - 520); g.lineTo(bx + 145, bf + 20); g.stroke();
  g.beginPath(); g.moveTo(bx + 150, bf - 560); g.lineTo(bx + 140, bf - 515); g.lineTo(bx + 160, bf - 515); g.fill();
  g.beginPath(); g.ellipse(bx - 140, bf - 150, 46, 62, 0, 0, 7); g.fill();
  g.fillStyle = '#d8a54a'; g.beginPath(); const ky = bf - 150 - 182 * 1.25 - 26; g.moveTo(bx - 30, ky + 6); g.lineTo(bx - 22, ky - 28); g.lineTo(bx - 8, ky - 6); g.lineTo(bx, ky - 34); g.lineTo(bx + 8, ky - 6); g.lineTo(bx + 22, ky - 28); g.lineTo(bx + 30, ky + 6); g.fill();
  // Bel's army: rows of torches in perspective
  g.save(); g.globalCompositeOperation = 'lighter';
  for (let r = 0; r < 9; r++) { const y0 = 770 + r * 16, k = 0.6 + r * 0.1; for (let x = 980 + r * 25; x < W + 20; x += R(10, 22) / k) { const y = y0 + R(-3, 3) + (x - 1000) * 0.012; glowDot(x, y, 10 * k, 'rgba(255,130,50,A)', 0.22); glowDot(x, y, 2.2 * k, 'rgba(255,230,170,A)', 0.9); } }
  g.restore();
  // foreground rock and Hayk at full draw
  g.fillStyle = '#060308'; g.beginPath(); g.moveTo(0, H); g.lineTo(0, 820); g.quadraticCurveTo(250, 760, 520, 840); g.quadraticCurveTo(620, 900, 700, H); g.fill();
  const hx = 330, hf = 800, sc = 1.75;
  g.fillStyle = '#060308'; g.strokeStyle = '#060308';
  // cape flowing back in the wind
  g.beginPath(); g.moveTo(hx - 8, hf - 218); g.bezierCurveTo(hx - 120, hf - 200, hx - 190, hf - 120, hx - 250, hf - 30); g.lineTo(hx - 210, hf - 50); g.lineTo(hx - 200, hf - 10); g.bezierCurveTo(hx - 120, hf - 80, hx - 40, hf - 130, hx + 10, hf - 160); g.fill();
  const hayk = {
    torso: [[-16, -122], [24, -124], [16, -62], [10, -40], [-14, -40], [-16, -62]],
    limbs: [
      [[[18, -118], [76, -124], [132, -128]], 12, 9],   // bow arm
      [[[-6, -116], [-46, -124], [14, -140]], 12, 9],   // drawing arm
      [[[0, -42], [42, 0], [70, 52]], 16, 10],          // front leg
      [[[-6, -42], [-34, 4], [-62, 52]], 16, 10],       // back leg
      [[[4, -128], [8, -140]], 10, 10],
    ],
    head: [10, -158], headR: 17,
  };
  drawFigure(g, hx, hf - 52 * sc, sc, hayk);
  // helmet crest
  g.beginPath(); g.moveTo(hx + 4 * sc, hf - 52 * sc - 174 * sc); g.quadraticCurveTo(hx - 30 * sc, hf - 52 * sc - 200 * sc, hx - 50 * sc, hf - 52 * sc - 160 * sc); g.lineTo(hx - 5 * sc, hf - 52 * sc - 165 * sc); g.fill();
  // bow + string + arrow
  const hand = [hx + 132 * sc, hf - 52 * sc - 128 * sc], draw = [hx + 14 * sc, hf - 52 * sc - 140 * sc];
  const t1 = [hand[0] - 22, hand[1] - 120], t2 = [hand[0] - 22, hand[1] + 120];
  g.lineWidth = 7; g.beginPath(); g.moveTo(...t1); g.quadraticCurveTo(hand[0] + 60, hand[1], ...t2); g.stroke();
  g.lineWidth = 1.4; g.strokeStyle = 'rgba(255,215,170,0.85)'; g.beginPath(); g.moveTo(...t1); g.lineTo(...draw); g.lineTo(...t2); g.stroke();
  g.lineWidth = 3; g.strokeStyle = '#060308'; g.beginPath(); g.moveTo(...draw); g.lineTo(hand[0] + 34, hand[1] - 4); g.stroke();
  // the arrow's flight: glowing arc toward Bel's chest
  g.save(); g.globalCompositeOperation = 'lighter';
  const sx = hand[0] + 40, sy = hand[1] - 6, ex = bx, ey = bf - 150 - 110 * 1.25, cxp = 1000, cyp = 130;
  for (let i = 0; i < 2200; i++) { const t = rnd(), it = 1 - t; const x = it * it * sx + 2 * it * t * cxp + t * t * ex, y = it * it * sy + 2 * it * t * cyp + t * t * ey; glowDot(x + R(-3, 3), y + R(-3, 3), R(2, 12) * (0.35 + t), 'rgba(255,200,120,A)', 0.06 + 0.12 * t); }
  const t = 0.86, it = 1 - t, ax = it * it * sx + 2 * it * t * cxp + t * t * ex, ay = it * it * sy + 2 * it * t * cyp + t * t * ey;
  glowDot(ax, ay, 110, 'rgba(255,230,170,A)', 0.55); glowDot(ax, ay, 22, 'rgba(255,255,240,A)', 1);
  g.restore();
  vignette(0.65);
  badge('ԳԼՈՒԽ II · ԿՈՆՑԵՊՏ');
  title('ՀԱՅԿ', 'ՆԵՏԻ ԹՌԻՉՔ', 'Եռաթև նետը խոցեց Բելի կուրծքը…', '#fff3d6', '#f0a24a', 'rgba(255,170,80,0.85)', 995);
}

// --- ARALEZ -------------------------------------------------------------------
function aralez() {
  g.fillStyle = vgrad([[0, '#03101a'], [0.5, '#071a26'], [1, '#010306']]); g.fillRect(0, 0, W, H);
  g.save(); g.globalCompositeOperation = 'lighter';
  const sh = g.createLinearGradient(0, 0, 0, H); sh.addColorStop(0, 'rgba(140,225,255,0.20)'); sh.addColorStop(1, 'rgba(140,225,255,0)');
  g.fillStyle = sh; g.beginPath(); g.moveTo(900, 0); g.lineTo(1020, 0); g.lineTo(1300, H); g.lineTo(620, H); g.fill();
  for (let i = 0; i < 500; i++) { const y = R(0, H), x = lerp(960, 960, 0) + R(-1, 1) * (60 + y * 0.32); g.fillStyle = `rgba(200,240,255,${R(0.05, 0.3)})`; g.fillRect(x, y, 1.5, 1.5); }
  g.restore();
  // cave walls with cold rim light
  [[1.0, '#0b1c27', 0], [0.8, '#06111a', 50], [0.55, '#02070b', 110]].forEach(([k, c, off], j) => {
    const L = [], Rr = [];
    for (let y = -10; y <= H + 10; y += 8) { L.push([250 + off * 2 + fbm(y * 0.005, j * 7) * 420 * k - y * 0.1, y]); Rr.push([W - 270 - off * 2 - fbm(y * 0.005, j * 7 + 3) * 420 * k + y * 0.1, y]); }
    [[L, 0], [Rr, W]].forEach(([pts, edge]) => {
      g.fillStyle = c; g.beginPath(); g.moveTo(edge, -10); pts.forEach(([x, y]) => g.lineTo(x, y)); g.lineTo(edge, H + 10); g.fill();
      g.save(); g.strokeStyle = `rgba(120,215,255,${0.10 + 0.08 * (2 - j)})`; g.lineWidth = 2.5; g.shadowColor = '#5fd0ff'; g.shadowBlur = 18;
      g.beginPath(); pts.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.stroke(); g.restore();
    });
  });
  // underground river at the bottom of the abyss
  g.save(); g.globalCompositeOperation = 'lighter';
  glowDot(960, 1060, 560, 'rgba(40,150,210,A)', 0.35);
  for (let i = 0; i < 1100; i++) { const y = R(940, 1080), x = 960 + R(-1, 1) * (y - 900) * 2.4; g.strokeStyle = `rgba(120,225,255,${R(0.05, 0.25)})`; g.beginPath(); g.moveTo(x, y); g.lineTo(x + R(10, 50), y); g.stroke(); }
  // Ara's soul-lights
  for (let i = 0; i < 140; i++) { const x = R(480, 1440), y = R(90, 930), r = Math.pow(rnd(), 4) * 4 + 1.2; glowDot(x, y, r * 6, 'rgba(255,215,140,A)', 0.30); glowDot(x, y, r, 'rgba(255,250,225,A)', 0.95); }
  g.restore();
  // the Aralez: a leaping winged spirit-dog made of light
  const ax = 900, ay = 560;
  const mask = maskCanvas(x => {
    x.save(); x.translate(ax, ay); x.scale(1.05, 1.05);
    const p = new Path2D();
    p.moveTo(-250, 70); p.quadraticCurveTo(-230, 0, -170, -10);           // tail
    p.quadraticCurveTo(-60, -44, 70, -36);                                 // back
    p.quadraticCurveTo(100, -60, 108, -90); p.lineTo(116, -136); p.lineTo(134, -98); // ear
    p.quadraticCurveTo(150, -90, 172, -86); p.lineTo(236, -62); p.quadraticCurveTo(244, -52, 232, -42); // snout
    p.lineTo(176, -34); p.quadraticCurveTo(150, -6, 132, 26);              // jaw, neck
    p.quadraticCurveTo(160, 70, 196, 104); p.lineTo(182, 116); p.quadraticCurveTo(140, 84, 96, 46); // front legs reaching
    p.quadraticCurveTo(0, 62, -90, 42);                                    // belly
    p.quadraticCurveTo(-150, 90, -214, 128); p.lineTo(-222, 114); p.quadraticCurveTo(-170, 70, -136, 22); // hind leg pushing
    p.closePath(); x.fill(p);
    // feathered wings: fans of long feathers
    [[-10, -36, -2.35, 1, 1.0], [30, -40, -1.95, 0.8, 0.75]].forEach(([wx, wy, a0, alpha, sz]) => {
      x.globalAlpha = alpha;
      for (let f = 0; f < 11; f++) {
        const a = a0 + f * 0.085, len = (230 + f * 22) * sz * (f > 7 ? 1 - (f - 7) * 0.12 : 1);
        x.save(); x.translate(wx, wy); x.rotate(a); x.beginPath(); x.ellipse(len * 0.5, 0, len * 0.5, 20 * sz, 0, 0, 7); x.fill(); x.restore();
      }
      x.save(); x.translate(wx, wy); x.rotate(a0 + 0.4); x.beginPath(); x.ellipse(70 * sz, 0, 90 * sz, 46 * sz, 0, 0, 7); x.fill(); x.restore();
    });
    x.restore();
  });
  g.save(); g.globalCompositeOperation = 'lighter';
  glowDot(ax, ay - 80, 600, 'rgba(80,200,255,A)', 0.25);
  g.filter = 'blur(26px)'; g.globalAlpha = 0.55; g.drawImage(mask, 0, 0); g.globalAlpha = 1; g.filter = 'none';
  const tint = document.createElement('canvas'); tint.width = W; tint.height = H; const tx = tint.getContext('2d');
  tx.drawImage(mask, 0, 0); tx.globalCompositeOperation = 'source-in';
  const gr = tx.createLinearGradient(ax - 400, ay - 300, ax + 250, ay + 120); gr.addColorStop(0, 'rgba(60,150,225,0.35)'); gr.addColorStop(1, 'rgba(215,250,255,0.80)');
  tx.fillStyle = gr; tx.fillRect(0, 0, W, H);
  g.drawImage(tint, 0, 0);
  // shimmering inner particles
  const md = mask.getContext('2d').getImageData(0, 0, W, H).data;
  for (let i = 0; i < 30000; i++) { const x = R(ax - 520, ax + 300) | 0, y = R(ay - 420, ay + 160) | 0; if (md[(y * W + x) * 4 + 3] < 60) continue; g.fillStyle = `rgba(230,255,255,${R(0.05, 0.25)})`; g.fillRect(x, y, R(1, 2.5), R(1, 2.5)); }
  for (let i = 0; i < 1200; i++) { const t = rnd(); const x = ax - 262 - t * 760 + R(-30, 30) * t * 3, y = ay + 74 - t * t * 320 + R(-30, 30) * t * 3; glowDot(x, y, R(1.5, 5), 'rgba(150,230,255,A)', 0.55 * (1 - t)); }
  glowDot(ax + 190, ay - 76, 10, 'rgba(255,255,255,A)', 1); glowDot(ax + 190, ay - 76, 36, 'rgba(160,240,255,A)', 0.7);
  g.restore();
  vignette(0.8);
  badge('ԳԼՈՒԽ III · ԿՈՆՑԵՊՏ');
  title('ԱՐԱԼԵԶ', 'ՀՈԳՈՒ ՎԵՐԱԴԱՐՁԸ', 'Իջի՛ր խորքերը և վերադարձրու Արայի հոգին', '#eaffff', '#6fd3ff', 'rgba(90,200,255,0.9)', 995);
}
