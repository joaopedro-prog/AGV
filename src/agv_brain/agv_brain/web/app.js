/**
 * AGV Mission Control Web Dashboard
 * Real-time ROS 2 telemetry, camera feed, and robot teleoperation.
 */

// DOM Elements
const connPill = document.getElementById('connection-pill');
const connText = document.getElementById('conn-text');
const robotStateEl = document.getElementById('robot-state');
const robotStateBadge = document.getElementById('robot-state-badge');

const videoStream = document.getElementById('video-stream');
const btnStreamDebug = document.getElementById('btn-stream-debug');
const btnStreamRaw = document.getElementById('btn-stream-raw');
const videoFpsEl = document.getElementById('video-fps');

const gaugeNeedle = document.getElementById('gauge-needle');
const directionTag = document.getElementById('direction-tag');
const errNormEl = document.getElementById('err-norm');
const errPxEl = document.getElementById('err-px');
const lineVisibleBadge = document.getElementById('line-visible-badge');

const btnStart = document.getElementById('btn-start');
const btnStop = document.getElementById('btn-stop');
const btnEmergency = document.getElementById('btn-emergency');

const valLinear = document.getElementById('val-linear');
const valAngular = document.getElementById('val-angular');
const valUltra = document.getElementById('val-ultra');
const ultraBar = document.getElementById('ultra-bar');
const valBattery = document.getElementById('val-battery');
const odomX = document.getElementById('odom-x');
const odomY = document.getElementById('odom-y');
const odomYaw = document.getElementById('odom-yaw');

const dpadUp = document.getElementById('dpad-up');
const dpadDown = document.getElementById('dpad-down');
const dpadLeft = document.getElementById('dpad-left');
const dpadRight = document.getElementById('dpad-right');
const dpadStop = document.getElementById('dpad-stop');
const speedSlider = document.getElementById('speed-slider');
const speedLabel = document.getElementById('speed-label');

const logContainer = document.getElementById('log-container');
const btnClearLog = document.getElementById('btn-clear-log');

// State Variables
let currentStream = 'debug';
let isConnected = false;
let failCount = 0;
let teleopTimer = null;
let currentLinear = 0.0;
let currentAngular = 0.0;
let manualSpeed = parseFloat(speedSlider.value) || 0.25;

// Audio Beep (Web Audio API) for tactile feedback
function playBeep(freq = 600, duration = 0.08) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.05, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + duration);
  } catch (e) {
    // Audio might be blocked by browser policy until interaction
  }
}

// Log Feed Helper
function addLog(msg, type = 'info') {
  const now = new Date();
  const timeStr = now.toTimeString().split(' ')[0];
  const entry = document.createElement('div');
  entry.className = `log-entry log-${type}`;
  entry.innerHTML = `<span class="log-time">${timeStr}</span><span class="log-msg">${msg}</span>`;
  logContainer.appendChild(entry);
  logContainer.scrollTop = logContainer.scrollHeight;

  // Limit entries
  while (logContainer.children.length > 50) {
    logContainer.removeChild(logContainer.firstChild);
  }
}

btnClearLog.addEventListener('click', () => {
  logContainer.innerHTML = '';
});

// Stream Switcher
function setStream(streamType) {
  currentStream = streamType;
  if (streamType === 'debug') {
    videoStream.src = '/api/stream/debug?' + Date.now();
    btnStreamDebug.classList.add('active');
    btnStreamRaw.classList.remove('active');
    addLog('Visualização alterada para HUD de Detecção OpenCV.', 'info');
  } else {
    videoStream.src = '/api/stream/raw?' + Date.now();
    btnStreamRaw.classList.add('active');
    btnStreamDebug.classList.remove('active');
    addLog('Visualização alterada para Câmera Bruta (Raw).', 'info');
  }
}

btnStreamDebug.addEventListener('click', () => setStream('debug'));
btnStreamRaw.addEventListener('click', () => setStream('raw'));

// Send API Command
async function sendCommand(action) {
  playBeep(action === 'START' ? 880 : 440);
  addLog(`Enviando comando [${action}] para o AGV...`, 'cmd');
  try {
    const res = await fetch('/api/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });
    const data = await res.json();
    if (data.status === 'ok') {
      addLog(`Comando [${action}] processado com sucesso!`, 'info');
    } else {
      addLog(`Resposta: ${data.message || 'Comando enviado'}`, 'warn');
    }
  } catch (err) {
    addLog(`Falha ao enviar comando [${action}]: ${err.message}`, 'err');
  }
}

btnStart.addEventListener('click', () => sendCommand('START'));
btnStop.addEventListener('click', () => sendCommand('STOP'));

// Emergency Stop
btnEmergency.addEventListener('click', async () => {
  playBeep(220, 0.3);
  addLog('!!! PARADA DE EMERGÊNCIA ACIONADA PELO USUÁRIO !!!', 'err');
  try {
    await fetch('/api/emergency', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stop: true })
    });
    // Stop all teleoperation immediately
    stopTeleop();
  } catch (err) {
    addLog(`Falha ao acionar emergência: ${err.message}`, 'err');
  }
});

// Telemetry Polling Loop
let lastState = '';
let fpsCounter = 0;
let lastFpsTime = Date.now();

async function pollTelemetry() {
  try {
    const res = await fetch('/api/telemetry');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // Mark online
    if (!isConnected) {
      isConnected = true;
      connPill.className = 'status-pill online';
      connText.textContent = 'ROS 2 ONLINE';
      addLog('Comunicação ROS 2 restabelecida.', 'info');
    }
    failCount = 0;

    // 1. Robot State
    const state = data.state || 'IDLE';
    robotStateEl.textContent = state;
    robotStateBadge.className = 'state-badge';
    if (state === 'FOLLOWING') {
      robotStateBadge.classList.add('state-following');
    } else if (state.includes('LOST') || state.includes('OBSTACLE')) {
      robotStateBadge.classList.add('state-lost');
    }

    if (state !== lastState) {
      addLog(`Estado do AGV: [${state}]`, state === 'FOLLOWING' ? 'info' : 'warn');
      lastState = state;
    }

    // 2. Line Deviation & Guidance Gauge
    const lineFound = !!data.line_found;
    const errNorm = typeof data.line_error === 'number' ? data.line_error : 0.0;
    const errPx = typeof data.line_error_px === 'number' ? data.line_error_px : 0;

    errNormEl.textContent = (errNorm >= 0 ? '+' : '') + errNorm.toFixed(2);
    errPxEl.textContent = `${Math.round(errPx)} px`;

    if (lineFound) {
      lineVisibleBadge.textContent = 'SIM';
      lineVisibleBadge.className = 'badge-mini sim';
      // Needle position: errNorm in [-1.0, 1.0] maps to [5%, 95%]
      const pct = 50 + (errNorm * 45);
      gaugeNeedle.style.left = `${Math.max(5, Math.min(95, pct))}%`;

      if (errNorm > 0.08) {
        directionTag.textContent = 'DESVIO DIREITA ➡';
        directionTag.style.color = 'var(--accent-yellow)';
      } else if (errNorm < -0.08) {
        directionTag.textContent = '⬅ DESVIO ESQUERDA';
        directionTag.style.color = 'var(--accent-yellow)';
      } else {
        directionTag.textContent = 'CENTRALIZADO ✔';
        directionTag.style.color = 'var(--accent-green-bright)';
      }
    } else {
      lineVisibleBadge.textContent = 'NÃO';
      lineVisibleBadge.className = 'badge-mini';
      gaugeNeedle.style.left = '50%';
      directionTag.textContent = 'BUSCANDO PISTA...';
      directionTag.style.color = 'var(--text-muted)';
    }

    // 3. Velocities
    valLinear.textContent = (data.linear_velocity || 0.0).toFixed(2);
    valAngular.textContent = (data.angular_velocity || 0.0).toFixed(2);

    // 4. Ultrasonic Sensor
    if (typeof data.ultrasonic_distance === 'number' && data.ultrasonic_distance > 0) {
      const dist = data.ultrasonic_distance;
      valUltra.textContent = dist.toFixed(2);
      // Progress bar (scale 0m to 2.0m)
      const barPct = Math.min(100, Math.max(0, (dist / 2.0) * 100));
      ultraBar.style.width = `${barPct}%`;
      ultraBar.className = 'progress-fill';
      if (dist < 0.25) {
        ultraBar.classList.add('danger');
      } else if (dist < 0.50) {
        ultraBar.classList.add('warn');
      }
    } else {
      valUltra.textContent = '--';
      ultraBar.style.width = '100%';
      ultraBar.className = 'progress-fill';
    }

    // 5. Battery
    if (typeof data.battery_voltage === 'number' && data.battery_voltage > 0) {
      valBattery.textContent = data.battery_voltage.toFixed(1);
    }

    // 6. Odometry
    odomX.textContent = `${(data.odom_x || 0.0).toFixed(3)} m`;
    odomY.textContent = `${(data.odom_y || 0.0).toFixed(3)} m`;
    const yawDeg = ((data.odom_yaw || 0.0) * 180.0 / Math.PI).toFixed(1);
    odomYaw.innerHTML = `${yawDeg}&deg;`;

    // 7. FPS Counter calculation
    fpsCounter++;
    const now = Date.now();
    if (now - lastFpsTime >= 1000) {
      videoFpsEl.textContent = `FPS: ${fpsCounter}`;
      fpsCounter = 0;
      lastFpsTime = now;
    }

  } catch (err) {
    failCount++;
    if (failCount > 3 && isConnected) {
      isConnected = false;
      connPill.className = 'status-pill offline';
      connText.textContent = 'ROS 2 OFFLINE';
      addLog('Perda de conexão com o servidor ROS 2.', 'err');
    }
  } finally {
    setTimeout(pollTelemetry, 100); // 10 Hz refresh
  }
}

// Teleoperation Logic (Priority 100 on /cmd_vel_joy)
speedSlider.addEventListener('input', (e) => {
  manualSpeed = parseFloat(e.target.value);
  speedLabel.textContent = `${manualSpeed.toFixed(2)} m/s`;
});

function sendTeleop(lin, ang) {
  fetch('/api/teleop', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ linear: lin, angular: ang })
  }).catch(() => {});
}

function startTeleop(lin, ang) {
  currentLinear = lin;
  currentAngular = ang;
  sendTeleop(currentLinear, currentAngular);

  if (teleopTimer) clearInterval(teleopTimer);
  teleopTimer = setInterval(() => {
    sendTeleop(currentLinear, currentAngular);
  }, 80); // Send at ~12 Hz while holding
}

function stopTeleop() {
  currentLinear = 0.0;
  currentAngular = 0.0;
  if (teleopTimer) {
    clearInterval(teleopTimer);
    teleopTimer = null;
  }
  sendTeleop(0.0, 0.0);
  document.querySelectorAll('.dpad-btn').forEach(b => b.classList.remove('pressed'));
}

// Bind D-Pad Buttons (Touch and Mouse)
function bindDpad(btn, lin, ang) {
  const onStart = (e) => {
    e.preventDefault();
    btn.classList.add('pressed');
    startTeleop(lin * manualSpeed, ang * (manualSpeed * 3.5));
  };
  const onEnd = (e) => {
    e.preventDefault();
    btn.classList.remove('pressed');
    stopTeleop();
  };

  btn.addEventListener('mousedown', onStart);
  btn.addEventListener('mouseup', onEnd);
  btn.addEventListener('mouseleave', onEnd);
  btn.addEventListener('touchstart', onStart, { passive: false });
  btn.addEventListener('touchend', onEnd, { passive: false });
}

bindDpad(dpadUp, 1.0, 0.0);
bindDpad(dpadDown, -0.8, 0.0);
bindDpad(dpadLeft, 0.0, 1.0);
bindDpad(dpadRight, 0.0, -1.0);

dpadStop.addEventListener('click', () => {
  stopTeleop();
  addLog('Teleoperação parada (velocidade zero).', 'info');
});

// Keyboard Teleop Controls (W, A, S, D and Arrow Keys)
const activeKeys = new Set();

window.addEventListener('keydown', (e) => {
  // Ignore inside inputs
  if (e.target.tagName === 'INPUT') return;

  const key = e.key.toLowerCase();
  if (['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright', ' '].includes(key)) {
    e.preventDefault();
    if (!activeKeys.has(key)) {
      activeKeys.add(key);
      updateKeyboardTeleop();
    }
  }
});

window.addEventListener('keyup', (e) => {
  const key = e.key.toLowerCase();
  if (activeKeys.has(key)) {
    activeKeys.delete(key);
    updateKeyboardTeleop();
  }
});

function updateKeyboardTeleop() {
  if (activeKeys.has(' ')) {
    dpadStop.classList.add('pressed');
    stopTeleop();
    return;
  }

  let lin = 0.0;
  let ang = 0.0;

  if (activeKeys.has('w') || activeKeys.has('arrowup')) {
    lin += 1.0;
    dpadUp.classList.add('pressed');
  } else {
    dpadUp.classList.remove('pressed');
  }

  if (activeKeys.has('s') || activeKeys.has('arrowdown')) {
    lin -= 0.8;
    dpadDown.classList.add('pressed');
  } else {
    dpadDown.classList.remove('pressed');
  }

  if (activeKeys.has('a') || activeKeys.has('arrowleft')) {
    ang += 1.0;
    dpadLeft.classList.add('pressed');
  } else {
    dpadLeft.classList.remove('pressed');
  }

  if (activeKeys.has('d') || activeKeys.has('arrowright')) {
    ang -= 1.0;
    dpadRight.classList.add('pressed');
  } else {
    dpadRight.classList.remove('pressed');
  }

  if (lin === 0.0 && ang === 0.0) {
    stopTeleop();
  } else {
    startTeleop(lin * manualSpeed, ang * (manualSpeed * 3.5));
  }
}

// Start Telemetry Polling on page load
window.addEventListener('DOMContentLoaded', () => {
  addLog('Iniciando conexão com AGV Mission Control...', 'info');
  pollTelemetry();
});
