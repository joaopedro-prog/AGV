#!/bin/bash
# ==============================================================================
# setup_rpi.sh — Provisionamento do Host Raspberry Pi 3B para o AGV ELETRON
# ==============================================================================
# Uso (na Raspberry Pi 3B com Ubuntu Server 22.04 64-bit ou RPi OS Lite 64-bit):
#   sudo bash scripts/rpi/setup_rpi.sh
# ==============================================================================

set -e

if [ "$EUID" -ne 0 ]; then
  echo "[ERRO] Execute como root: sudo bash scripts/rpi/setup_rpi.sh"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "======================================================================"
echo "  1/5 - Configurando Swap de 2 GB (proteção contra OOM em 1 GB RAM)"
echo "======================================================================"
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "[OK] Swapfile de 2 GB criado e ativado."
else
  swapon /swapfile 2>/dev/null || true
  echo "[OK] /swapfile já existe."
fi

echo "======================================================================"
echo "  2/5 - Habilitando I2C (MPU6050), UART0 (ESP32) e Câmera CSI V4L2"
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
  grep -q "^dtoverlay=disable-bt" "${BOOT_CFG}" || echo "dtoverlay=disable-bt" >> "${BOOT_CFG}"
  grep -q "^start_x=1" "${BOOT_CFG}"          || echo "start_x=1" >> "${BOOT_CFG}"
  echo "[OK] Parâmetros de hardware gravados em ${BOOT_CFG}."
fi

# Carrega módulos i2c-dev e bcm2835-v4l2 (câmera CSI como /dev/video0) no boot
grep -q "^i2c-dev" /etc/modules       || echo "i2c-dev" >> /etc/modules
grep -q "^bcm2835-v4l2" /etc/modules  || echo "bcm2835-v4l2" >> /etc/modules
modprobe i2c-dev 2>/dev/null || true
modprobe bcm2835-v4l2 2>/dev/null || true

echo "======================================================================"
echo "  3/5 - Instalando regras udev (/dev/agv_esp32, /dev/agv_lidar, /dev/agv_cam)"
echo "======================================================================"
cp "${SCRIPT_DIR}/99-agv-devices.rules" /etc/udev/rules.d/99-agv-devices.rules
udevadm control --reload-rules
udevadm trigger
echo "[OK] Regras udev aplicadas."

echo "======================================================================"
echo "  4/5 - Verificando Docker Engine & Docker Compose Plugin"
echo "======================================================================"
if ! command -v docker >/dev/null 2>&1; then
  echo "Instalando Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
fi
if [ -n "${SUDO_USER}" ]; then
  usermod -aG docker,dialout,video,i2c,gpio "${SUDO_USER}" 2>/dev/null || true
fi
echo "[OK] Docker pronto: $(docker --version)"

echo "======================================================================"
echo "  5/5 - Compilando imagem ARM64 enxuta (sem simulação) e subindo AGV"
echo "======================================================================"
cd "${REPO_DIR}"
docker compose -f docker-compose.rpi.yml build
docker compose -f docker-compose.rpi.yml up -d

echo ""
echo "======================================================================"
echo "  SETUP CONCLUÍDO!"
echo "======================================================================"
echo "  - Container ativo com restart automático: agv_eletron_real"
echo "  - Dashboard Web HMI: http://$(hostname -I | awk '{print $1}'):8080"
echo "  - Reinicie a RPi 3B agora se esta foi a 1a vez ativando I2C/UART/CSI:"
echo "      sudo reboot"
echo "======================================================================"
