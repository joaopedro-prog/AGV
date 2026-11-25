#!/bin/bash
# ==============================================================================
# rpi_remote_setup_offline.sh — Instalação 100% Offline na Raspberry Pi (CM4/3B/4B)
# ==============================================================================
# Executado automaticamente por scripts/rpi/setup_offline_rpi.ps1 via SSH.
# Instala Docker Engine a partir de pacotes .deb locais, carrega a imagem ARM64
# agv-eletron-rpi:latest (sem simulacao), aplica configuracoes de hardware e sobe
# o container agv_eletron_real com restart automatico no boot.
# ==============================================================================

set -e

if [ "$EUID" -ne 0 ]; then
  echo "[ERRO] Execute com sudo: sudo bash $0"
  exit 1
fi

RPI_USER="${SUDO_USER:-agv}"
RPI_HOME="$(eval echo "~${RPI_USER}")"
REPO_DIR="${RPI_HOME}/AGV"
BUNDLE_DIR="${RPI_HOME}/agv_offline_bundle"

echo "======================================================================"
echo "  1/5 - Verificando Memoria RAM e Swap"
echo "======================================================================"
TOTAL_MEM_MB=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
if [ "${TOTAL_MEM_MB}" -lt 2048 ]; then
  if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    grep -q "^/swapfile " /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "[OK] Swapfile de 2 GB criado (RAM=${TOTAL_MEM_MB} MB)."
  else
    swapon /swapfile 2>/dev/null || true
    echo "[OK] /swapfile ja existe."
  fi
else
  echo "[OK] RAM abundante (${TOTAL_MEM_MB} MB) — pulando swapfile para economizar eMMC."
fi

echo "======================================================================"
echo "  2/5 - Habilitando I2C (MPU6050), UART0 (ESP32) e Modulos de Camera"
echo "======================================================================"
BOOT_CFG=""
if [ -f /boot/firmware/config.txt ]; then
  BOOT_CFG="/boot/firmware/config.txt"
elif [ -f /boot/config.txt ]; then
  BOOT_CFG="/boot/config.txt"
fi

if [ -n "${BOOT_CFG}" ]; then
  grep -q "^dtparam=i2c_arm=on" "${BOOT_CFG}" || echo "dtparam=i2c_arm=on" >> "${BOOT_CFG}"
  grep -q "^enable_uart=1" "${BOOT_CFG}"      || echo "enable_uart=1" >> "${BOOT_CFG}"
  echo "[OK] Parametros verificados em ${BOOT_CFG}."
fi

grep -q "^i2c-dev" /etc/modules      || echo "i2c-dev" >> /etc/modules
grep -q "^bcm2835-v4l2" /etc/modules || echo "bcm2835-v4l2" >> /etc/modules
modprobe i2c-dev 2>/dev/null || true
modprobe bcm2835-v4l2 2>/dev/null || true

echo "======================================================================"
echo "  3/5 - Instalando regras udev (/dev/agv_esp32, /dev/agv_cam)"
echo "======================================================================"
if [ -f "${REPO_DIR}/scripts/rpi/99-agv-devices.rules" ]; then
  cp "${REPO_DIR}/scripts/rpi/99-agv-devices.rules" /etc/udev/rules.d/99-agv-devices.rules
  udevadm control --reload-rules || true
  udevadm trigger || true
  echo "[OK] Regras udev aplicadas."
fi

echo "======================================================================"
echo "  4/5 - Instalando Docker Engine 100% OFFLINE (.deb ARM64)"
echo "======================================================================"
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  if [ -d "${BUNDLE_DIR}/docker_debs" ] && ls "${BUNDLE_DIR}/docker_debs"/*.deb >/dev/null 2>&1; then
    dpkg -i "${BUNDLE_DIR}/docker_debs"/*.deb
    echo "[OK] Pacotes .deb do Docker instalados."
  else
    echo "[ERRO] Pasta ${BUNDLE_DIR}/docker_debs vazia ou ausente!"
    exit 1
  fi
else
  echo "[OK] Docker e Docker Compose ja estao instalados."
fi

systemctl enable docker >/dev/null 2>&1 || true
systemctl start docker
for grp in docker dialout video i2c gpio; do
  if getent group "${grp}" >/dev/null 2>&1; then
    usermod -aG "${grp}" "${RPI_USER}" 2>/dev/null || true
  fi
done
echo "[OK] Docker ativo: $(docker --version)"
echo "[OK] Compose ativo: $(docker compose version)"

echo "======================================================================"
echo "  5/5 - Carregando imagem ARM64 (sem simulacao) e subindo AGV"
echo "======================================================================"
if [ -f "${BUNDLE_DIR}/agv-eletron-rpi.tar.gz" ]; then
  echo "Carregando ${BUNDLE_DIR}/agv-eletron-rpi.tar.gz (aguarde ~30-60s)..."
  docker load -i "${BUNDLE_DIR}/agv-eletron-rpi.tar.gz"
  rm -f "${BUNDLE_DIR}/agv-eletron-rpi.tar.gz"
elif [ -f "${BUNDLE_DIR}/agv-eletron-rpi.tar" ]; then
  docker load -i "${BUNDLE_DIR}/agv-eletron-rpi.tar"
  rm -f "${BUNDLE_DIR}/agv-eletron-rpi.tar"
else
  echo "[ERRO] Arquivo de imagem Docker nao encontrado em ${BUNDLE_DIR}!"
  exit 1
fi

chmod +x "${REPO_DIR}/scripts/rpi/entrypoint_rpi.sh" "${REPO_DIR}/scripts/rpi/agv_beacon.py" "${REPO_DIR}/scripts/teleop_joy_receiver.py" 2>/dev/null || true
mkdir -p "${REPO_DIR}/src/agv_description/worlds" "${REPO_DIR}/src/agv_description/meshes"
chown -R "${RPI_USER}:${RPI_USER}" "${REPO_DIR}"

cd "${REPO_DIR}"
docker compose -f docker-compose.rpi.yml down >/dev/null 2>&1 || true
docker compose -f docker-compose.rpi.yml up -d --no-build

echo ""
echo "======================================================================"
echo "  INSTALACAO OFFLINE CONCLUIDA!"
echo "======================================================================"
echo "  - Container ativo: agv_eletron_real (restart: unless-stopped)"
echo "  - Dashboard Web  : http://$(hostname -I | awk '{print $1}'):8080"
echo "======================================================================"
