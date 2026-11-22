/*
 * ============================================================================
 * FIRMWARE DO MICROCONTROLADOR DO AGV ELETRON (ESP32 DevKit V1)
 * ============================================================================
 * Alinhado estritamente ao:
 *  - Esquemático KiCad Rev 2.0 (SENAI - Projeto AGV / Folhas 1 a 4)
 *  - Contrato de Interface Serial v1.0 ($TIPO,SEQ,...*CRC16\r\n @ 115200 bps)
 *
 * Características:
 *  1. Acionamento Dual REV Spark MAX via PWM Servo 50 Hz (1000..2000 us,
 *     1500 us = neutro/freio) usando LEDC 16 bits (GPIO 13 Esq / GPIO 14 Dir).
 *  2. Leitura de 2x Encoders KY-040 acoplados em redução 20:1 (800 ticks/volta
 *     da roda com interrupção CHANGE em CLK):
 *       - ENC1 (Esq): CLK = GPIO 34, DT = GPIO 35
 *       - ENC2 (Dir): CLK = GPIO 39 (VN), DT = GPIO 36 (VP)
 *  3. Malha fechada Feedforward + PID por roda com rampa suave e anti-windup.
 *  4. Leitura não-bloqueante via interrupção de 2x HC-SR04 (TRIG compartilhado
 *     em GPIO 27; ECHO1 frontal em GPIO 26; ECHO2 traseiro em GPIO 25).
 *  5. Botão de Emergência físico E_STOP_D33 no GPIO 33 (INPUT_PULLUP).
 *  6. Comunicação UART espelhada em Serial (USB) e Serial2 (GPIO 16/17 -> RPi)
 *     com verificação/geração CRC16-CCITT e Watchdog rigoroso de 200 ms.
 * ============================================================================
 */

#include <Arduino.h>
#include <math.h>

// ======================= PINAGEM OFICIAL KICAD REV 2.0 ======================
// Controladores de Motor REV Spark MAX (Sinal PWM Servo 50 Hz)
const int PIN_SPARK_L_PWM = 13; // D13 -> PWM_LEFT  (Spark MAX Esquerdo)
const int PIN_SPARK_R_PWM = 14; // D14 -> PWM_RIGHT (Spark MAX Direito)

// Canais LEDC do ESP32 (50 Hz, 16-bit -> período 20000 us -> 1500 us = 4915)
const int LEDC_CH_LEFT  = 0;
const int LEDC_CH_RIGHT = 1;
const int SPARK_PWM_FREQ_HZ = 50;
const int SPARK_PWM_RES_BITS = 16;

// Encoders Rotativos KY-040 (GPIO 34, 35, 36, 39 são input-only no ESP32;
// o módulo KY-040 já possui resistores pull-up físicos para 3.3V)
const int PIN_ENC_L_CLK = 34; // D34 -> ENC1_CLK
const int PIN_ENC_L_DT  = 35; // D35 -> ENC1_DT
const int PIN_ENC_R_CLK = 39; // VN  -> ENC2_CLK
const int PIN_ENC_R_DT  = 36; // VP  -> ENC2_DT

// Botão de Emergência Físico (KiCad: BTN_E_STOP ligado entre GND e GPIO 33)
const int PIN_ESTOP_HW = 33;  // D33 com INPUT_PULLUP
// Para contato NA ligado ao GND (padrão KiCad SW_Push): pressionado = LOW.
// Se usar contato NF ligado ao GND (cabo rompido/pressionado = HIGH), troque para HIGH.
const int ESTOP_TRIGGER_LEVEL = LOW;

// Sensores Ultrassônicos 2x HC-SR04 (ECHO com divisor resistivo 1k/2k -> 3.3V)
const int PIN_TRIG_SHARED = 27; // D27 -> TRIG_SHARED
const int PIN_ECHO_FRONT  = 26; // D26 -> ECHO1_3V3 (US1 Frontal)
const int PIN_ECHO_REAR   = 25; // D25 -> ECHO2_3V3 (US2 Traseiro)

// UART2 hardware espelhando Serial USB <-> Raspberry Pi 3B GPIO (Pinos 8 e 10)
const int PIN_UART2_RX = 16; // RX2 (GPIO 16) <- RPi_TX_UART
const int PIN_UART2_TX = 17; // TX2 (GPIO 17) -> RPi_RX_UART

// Pino reserva para leitura futura de divisor de bateria (KiCad: "D12 e D32 livres")
// Não usar GPIO 39 (agora dedicado ao ENC2_CLK).
#define ENABLE_VBAT_ADC false
const int PIN_VBAT_ADC = 32;
const float VBAT_DIVIDER_RATIO = 5.0f; // Ex: divisor 40k/10k para até 16.5V

// ======================== CONSTANTES CINEMÁTICAS E PID ======================
const float MAX_WHEEL_RAD_S = 15.0f;
const int KY040_PPR = 20;      // 20 ciclos por volta no eixo do KY-040
const int GEAR_RATIO = 20;     // Redução mecânica 20:1
// Interrupção CHANGE no pino CLK gera 2 bordas/ciclo -> 40 * 20 = 800 ticks/volta da roda
const int TICKS_PER_REV = KY040_PPR * 2 * GEAR_RATIO; // 800

// Ganhos do controlador Feedforward + PID em velocidade angular (rad/s -> esforço [-1..1])
// Ajuste fino em bancada com rodas suspensas conforme inércia real dos CIM
const float FF_GAIN = 1.0f / MAX_WHEEL_RAD_S;
const float PID_KP  = 0.045f;
const float PID_KI  = 0.080f;
const float PID_KD  = 0.002f;
const float PID_INTEGRAL_LIMIT = 0.35f;
const float OUTPUT_SLEW_PER_SEC = 4.5f; // Limita variação brusca de esforço (evita pico de corrente)

// ======================= ESTADOS DE SEGURANÇA (CONTRATO) ====================
const uint8_t STATE_OK                   = 0;
const uint8_t STATE_HARDWARE_ESTOP       = 1;
const uint8_t STATE_WATCHDOG_TIMEOUT     = 2;
const uint8_t STATE_DRIVER_FAULT         = 3;
const uint8_t STATE_ESTOP_PENDING_RESET  = 4;

// ============================ VARIÁVEIS GLOBAIS =============================
volatile long enc_ticks_left  = 0;
volatile long enc_ticks_right = 0;
volatile int prev_clk_l = HIGH;
volatile int prev_clk_r = HIGH;

// Medição não-bloqueante dos 2 sensores ultrassônicos
volatile unsigned long echo_front_start_us = 0;
volatile unsigned long echo_front_dur_us   = 0;
volatile unsigned long echo_front_rx_ms    = 0;

volatile unsigned long echo_rear_start_us  = 0;
volatile unsigned long echo_rear_dur_us    = 0;
volatile unsigned long echo_rear_rx_ms     = 0;

long prev_ticks_left  = 0;
long prev_ticks_right = 0;
float current_speed_l_rad_s = 0.0f;
float current_speed_r_rad_s = 0.0f;

float target_left_rad_s  = 0.0f;
float target_right_rad_s = 0.0f;

// Estado do PID por roda
float pid_int_l = 0.0f, pid_prev_err_l = 0.0f, out_effort_l = 0.0f;
float pid_int_r = 0.0f, pid_prev_err_r = 0.0f, out_effort_r = 0.0f;

uint16_t tx_seq = 0;
uint16_t last_rx_seq = 0;
bool first_packet_received = false;

uint8_t current_safety_state = STATE_OK;

unsigned long last_valid_cmd_ms = 0;
unsigned long last_control_ms   = 0;
unsigned long last_telemetry_ms = 0;
unsigned long last_us_trig_ms   = 0;

String rx_line_usb   = "";
String rx_line_uart2 = "";

// ============================ CÁLCULO DE CRC16 ==============================
/**
 * Calcula CRC16-CCITT (Polinômio: 0x1021, Init: 0xFFFF, RefIn/RefOut: false, XorOut: 0x0000).
 * Abrange estritamente todos os bytes entre '$' e '*'.
 */
uint16_t calculate_crc16(const char* data, size_t length) {
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < length; i++) {
    crc ^= ((uint16_t)(uint8_t)data[i]) << 8;
    for (int j = 0; j < 8; j++) {
      if (crc & 0x8000) {
        crc = (crc << 1) ^ 0x1021;
      } else {
        crc = crc << 1;
      }
    }
  }
  return crc;
}

// ========================= INTERRUPÇÕES DOS ENCODERS ========================
void IRAM_ATTR isr_enc_left() {
  int clk = digitalRead(PIN_ENC_L_CLK);
  int dt  = digitalRead(PIN_ENC_L_DT);
  if (clk != prev_clk_l) {
    prev_clk_l = clk;
    if (clk == dt) {
      enc_ticks_left++;
    } else {
      enc_ticks_left--;
    }
  }
}

void IRAM_ATTR isr_enc_right() {
  int clk = digitalRead(PIN_ENC_R_CLK);
  int dt  = digitalRead(PIN_ENC_R_DT);
  if (clk != prev_clk_r) {
    prev_clk_r = clk;
    if (clk == dt) {
      enc_ticks_right++;
    } else {
      enc_ticks_right--;
    }
  }
}

// ==================== INTERRUPÇÕES NÃO-BLOQUEANTES HC-SR04 ==================
void IRAM_ATTR isr_echo_front() {
  unsigned long now_us = micros();
  if (digitalRead(PIN_ECHO_FRONT) == HIGH) {
    echo_front_start_us = now_us;
  } else {
    unsigned long dur = now_us - echo_front_start_us;
    if (dur >= 120 && dur <= 25000) {
      echo_front_dur_us = dur;
      echo_front_rx_ms = millis();
    }
  }
}

void IRAM_ATTR isr_echo_rear() {
  unsigned long now_us = micros();
  if (digitalRead(PIN_ECHO_REAR) == HIGH) {
    echo_rear_start_us = now_us;
  } else {
    unsigned long dur = now_us - echo_rear_start_us;
    if (dur >= 120 && dur <= 25000) {
      echo_rear_dur_us = dur;
      echo_rear_rx_ms = millis();
    }
  }
}

// ==================== ACIONAMENTO REV SPARK MAX (PWM 50 Hz) =================
void write_spark_max_us(int ledc_channel, float pulse_us) {
  if (pulse_us < 1000.0f) pulse_us = 1000.0f;
  if (pulse_us > 2000.0f) pulse_us = 2000.0f;
  // Período a 50 Hz = 20000 us; resolução 16 bits = 0..65535 (1500 us -> 4915 ticks)
  uint32_t duty = (uint32_t)lroundf((pulse_us / 20000.0f) * 65535.0f);
#if defined(ESP32)
  ledcWrite(ledc_channel, duty);
#endif
}

void reset_pid_state() {
  pid_int_l = 0.0f;
  pid_prev_err_l = 0.0f;
  out_effort_l = 0.0f;

  pid_int_r = 0.0f;
  pid_prev_err_r = 0.0f;
  out_effort_r = 0.0f;
}

void cut_motor_power() {
  write_spark_max_us(LEDC_CH_LEFT,  1500.0f);
  write_spark_max_us(LEDC_CH_RIGHT, 1500.0f);
  target_left_rad_s  = 0.0f;
  target_right_rad_s = 0.0f;
  reset_pid_state();
}

float compute_wheel_pid_effort(float target_w, float meas_w, float dt,
                               float &integral, float &prev_err, float &out_effort) {
  if (fabsf(target_w) < 0.02f) {
    integral = 0.0f;
    prev_err = 0.0f;
    out_effort = 0.0f;
    return 0.0f;
  }

  float ff = target_w * FF_GAIN;
  float err = target_w - meas_w;

  integral += err * dt;
  if (integral >  PID_INTEGRAL_LIMIT) integral =  PID_INTEGRAL_LIMIT;
  if (integral < -PID_INTEGRAL_LIMIT) integral = -PID_INTEGRAL_LIMIT;

  float deriv = (dt > 0.001f) ? (err - prev_err) / dt : 0.0f;
  prev_err = err;

  float desired = ff + (PID_KP * err) + (PID_KI * integral) + (PID_KD * deriv);
  if (desired >  1.0f) desired =  1.0f;
  if (desired < -1.0f) desired = -1.0f;

  // Rampa suave (slew-rate limiter) para proteger bateria e fusíveis 40A dos CIM
  float max_step = OUTPUT_SLEW_PER_SEC * dt;
  float delta = desired - out_effort;
  if (delta >  max_step) delta =  max_step;
  if (delta < -max_step) delta = -max_step;
  out_effort += delta;

  return out_effort;
}

void apply_motor_speeds(float target_l, float target_r, float dt) {
  if (current_safety_state != STATE_OK) {
    cut_motor_power();
    return;
  }

  float eff_l = compute_wheel_pid_effort(
      target_l, current_speed_l_rad_s, dt, pid_int_l, pid_prev_err_l, out_effort_l);
  float eff_r = compute_wheel_pid_effort(
      target_r, current_speed_r_rad_s, dt, pid_int_r, pid_prev_err_r, out_effort_r);

  // Mapeia esforço normalizado [-1.0 .. +1.0] -> [1000 .. 2000 us] (1500 us = neutro)
  float us_l = 1500.0f + (eff_l * 500.0f);
  float us_r = 1500.0f + (eff_r * 500.0f);

  write_spark_max_us(LEDC_CH_LEFT,  us_l);
  write_spark_max_us(LEDC_CH_RIGHT, us_r);
}

// ======================== TRANSMISSÃO DE MENSAGENS ==========================
void send_packet(const String &payload) {
  uint16_t crc = calculate_crc16(payload.c_str(), payload.length());
  char frame[140];
  snprintf(frame, sizeof(frame), "$%s*%04X\r\n", payload.c_str(), crc);

  // Espelha telemetria e ACKs tanto na USB Serial quanto na UART2 (GPIO 16/17 -> RPi)
  Serial.print(frame);
  Serial2.print(frame);
}

void send_ack_stop(uint16_t seq) {
  send_packet("ACK_STOP," + String(seq) + ",1");
}

void send_ack_reset(uint16_t seq, bool success) {
  send_packet("ACK_RESET," + String(seq) + "," + (success ? "1" : "0"));
}

// ======================== PROCESSAMENTO DE COMANDOS =========================
bool is_hw_estop_triggered() {
  return (digitalRead(PIN_ESTOP_HW) == ESTOP_TRIGGER_LEVEL);
}

void handle_packet(const String &payload) {
  int first_comma = payload.indexOf(',');
  if (first_comma < 0) return;

  String type = payload.substring(0, first_comma);
  int second_comma = payload.indexOf(',', first_comma + 1);
  if (second_comma < 0) second_comma = payload.length();

  uint16_t seq = (uint16_t)payload.substring(first_comma + 1, second_comma).toInt();
  last_rx_seq = seq;
  first_packet_received = true;

  if (type == "CMD") {
    // Formato: CMD,<seq>,<left_rad_s>,<right_rad_s>
    int third_comma = payload.indexOf(',', second_comma + 1);
    if (third_comma > second_comma) {
      float req_l = payload.substring(second_comma + 1, third_comma).toFloat();
      float req_r = payload.substring(third_comma + 1).toFloat();

      if (current_safety_state == STATE_OK) {
        target_left_rad_s  = req_l;
        target_right_rad_s = req_r;
      }
      last_valid_cmd_ms = millis();
    }
  } else if (type == "ESTOP") {
    // Formato: ESTOP,<seq>,<reason>
    cut_motor_power();
    current_safety_state = is_hw_estop_triggered()
        ? STATE_HARDWARE_ESTOP
        : STATE_ESTOP_PENDING_RESET;
    last_valid_cmd_ms = millis();
    send_ack_stop(seq);
  } else if (type == "RESET") {
    // Formato: RESET,<seq>
    // Rearme em 5 passos: só permite se E-Stop físico estiver liberado E alvos zerados
    bool hw_safe = !is_hw_estop_triggered();
    if (hw_safe && fabsf(target_left_rad_s) < 0.01f && fabsf(target_right_rad_s) < 0.01f) {
      reset_pid_state();
      current_safety_state = STATE_OK;
      last_valid_cmd_ms = millis();
      send_ack_reset(seq, true);
    } else {
      send_ack_reset(seq, false);
    }
  }
}

void process_serial_byte(char c, String &rx_buf) {
  if (c == '$') {
    rx_buf = "";
    return;
  }
  if (c == '\r') return;
  if (c == '\n') {
    if (rx_buf.length() < 7) {
      rx_buf = "";
      return;
    }
    int star_pos = rx_buf.lastIndexOf('*');
    if (star_pos < 0) {
      rx_buf = "";
      return;
    }

    String payload = rx_buf.substring(0, star_pos);
    String crc_str = rx_buf.substring(star_pos + 1);
    crc_str.trim();

    if (crc_str.length() == 4) {
      uint16_t expected_crc = (uint16_t)strtoul(crc_str.c_str(), NULL, 16);
      uint16_t calculated_crc = calculate_crc16(payload.c_str(), payload.length());

      if (expected_crc == calculated_crc) {
        handle_packet(payload);
      }
    }
    rx_buf = "";
    return;
  }
  rx_buf += c;
  if (rx_buf.length() > 120) {
    rx_buf = ""; // Previne estouro de buffer
  }
}

// ============================ LEITURA DE SENSORES ===========================
void trigger_ultrasonic_nonblocking() {
  digitalWrite(PIN_TRIG_SHARED, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG_SHARED, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG_SHARED, LOW);
}

int get_min_ultrasonic_cm(unsigned long now_ms) {
  noInterrupts();
  unsigned long dur_f = echo_front_dur_us;
  unsigned long rx_f  = echo_front_rx_ms;
  unsigned long dur_r = echo_rear_dur_us;
  unsigned long rx_r  = echo_rear_rx_ms;
  interrupts();

  int cm_front = 999;
  int cm_rear  = 999;

  if (rx_f > 0 && (now_ms - rx_f) < 300) {
    cm_front = (int)((dur_f * 0.0343f) * 0.5f);
  }
  if (rx_r > 0 && (now_ms - rx_r) < 300) {
    cm_rear = (int)((dur_r * 0.0343f) * 0.5f);
  }
  return (cm_front < cm_rear) ? cm_front : cm_rear;
}

int read_battery_millivolts() {
#if ENABLE_VBAT_ADC
  int raw = analogRead(PIN_VBAT_ADC);
  float v_adc = (raw / 4095.0f) * 3.3f;
  return (int)(v_adc * VBAT_DIVIDER_RATIO * 1000.0f);
#else
  // Sem divisor ADC conectado nesta revisão KiCad (GPIO 32 livre para futura expansão)
  return 12400;
#endif
}

// ================================== SETUP ===================================
void setup() {
  Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, PIN_UART2_RX, PIN_UART2_TX);

#if defined(ESP32)
  ledcSetup(LEDC_CH_LEFT,  SPARK_PWM_FREQ_HZ, SPARK_PWM_RES_BITS);
  ledcSetup(LEDC_CH_RIGHT, SPARK_PWM_FREQ_HZ, SPARK_PWM_RES_BITS);
  ledcAttachPin(PIN_SPARK_L_PWM, LEDC_CH_LEFT);
  ledcAttachPin(PIN_SPARK_R_PWM, LEDC_CH_RIGHT);
#endif

  // Inputs dos Encoders KY-040 (pull-ups físicos no módulo KY-040)
  pinMode(PIN_ENC_L_CLK, INPUT);
  pinMode(PIN_ENC_L_DT,  INPUT);
  pinMode(PIN_ENC_R_CLK, INPUT);
  pinMode(PIN_ENC_R_DT,  INPUT);

  prev_clk_l = digitalRead(PIN_ENC_L_CLK);
  prev_clk_r = digitalRead(PIN_ENC_R_CLK);

  attachInterrupt(digitalPinToInterrupt(PIN_ENC_L_CLK), isr_enc_left,  CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_R_CLK), isr_enc_right, CHANGE);

  // Botão físico de emergência
  pinMode(PIN_ESTOP_HW, INPUT_PULLUP);

  // Sensores ultrassônicos não-bloqueantes
  pinMode(PIN_TRIG_SHARED, OUTPUT);
  digitalWrite(PIN_TRIG_SHARED, LOW);
  pinMode(PIN_ECHO_FRONT, INPUT);
  pinMode(PIN_ECHO_REAR,  INPUT);
  attachInterrupt(digitalPinToInterrupt(PIN_ECHO_FRONT), isr_echo_front, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_ECHO_REAR),  isr_echo_rear,  CHANGE);

  cut_motor_power();
  unsigned long boot_ms = millis();
  last_valid_cmd_ms = boot_ms;
  last_control_ms   = boot_ms;
  last_telemetry_ms = boot_ms;
  last_us_trig_ms   = boot_ms;
}

// ================================== LOOP ====================================
void loop() {
  // 1. Leitura contínua de ambas as portas seriais (USB + UART2 RPi)
  while (Serial.available() > 0) {
    process_serial_byte((char)Serial.read(), rx_line_usb);
  }
  while (Serial2.available() > 0) {
    process_serial_byte((char)Serial2.read(), rx_line_uart2);
  }

  unsigned long now = millis();

  // 2. Verificação da Camada de Segurança Física (BTN_E_STOP em GPIO 33)
  if (is_hw_estop_triggered()) {
    cut_motor_power();
    current_safety_state = STATE_HARDWARE_ESTOP;
  } else if (current_safety_state == STATE_HARDWARE_ESTOP) {
    // Botão físico foi solto: transita para pendente de rearme explícito ($RESET)
    current_safety_state = STATE_ESTOP_PENDING_RESET;
  }

  // 3. Watchdog de Comunicação Serial (200 ms)
  if (now - last_valid_cmd_ms > 200) {
    cut_motor_power();
    if (current_safety_state == STATE_OK) {
      current_safety_state = STATE_WATCHDOG_TIMEOUT;
    }
  }

  // 4. Disparo periódico não-bloqueante dos 2x HC-SR04 a 10 Hz (100 ms)
  if (now - last_us_trig_ms >= 100) {
    last_us_trig_ms = now;
    trigger_ultrasonic_nonblocking();
  }

  // 5. Malha fechada PID + atualização Spark MAX 50 Hz (a cada 20 ms)
  if (now - last_control_ms >= 20) {
    float dt = (now - last_control_ms) / 1000.0f;
    last_control_ms = now;
    if (dt <= 0.0f || dt > 0.2f) dt = 0.02f;

    noInterrupts();
    long cur_l = enc_ticks_left;
    long cur_r = enc_ticks_right;
    interrupts();

    long dl = cur_l - prev_ticks_left;
    long dr = cur_r - prev_ticks_right;
    prev_ticks_left  = cur_l;
    prev_ticks_right = cur_r;

    float inst_l = ((float)dl / (float)TICKS_PER_REV) * 2.0f * 3.1415926f / dt;
    float inst_r = ((float)dr / (float)TICKS_PER_REV) * 2.0f * 3.1415926f / dt;

    // Filtro passa-baixa leve para amortecer quantização do encoder KY-040
    current_speed_l_rad_s = 0.65f * current_speed_l_rad_s + 0.35f * inst_l;
    current_speed_r_rad_s = 0.65f * current_speed_r_rad_s + 0.35f * inst_r;

    apply_motor_speeds(target_left_rad_s, target_right_rad_s, dt);
  }

  // 6. Envio periódico de Telemetria a 30 Hz (a cada 33 ms)
  if (now - last_telemetry_ms >= 33) {
    last_telemetry_ms = now;
    tx_seq++;

    noInterrupts();
    long t_left  = enc_ticks_left;
    long t_right = enc_ticks_right;
    interrupts();

    int dist_cm = get_min_ultrasonic_cm(now);
    int vbat_mv = read_battery_millivolts();

    // Payload: TELEM,<seq>,<tL>,<tR>,<wL>,<wR>,<vbat>,<us_dist>,<status>
    char payload_buf[110];
    snprintf(payload_buf, sizeof(payload_buf),
             "TELEM,%u,%ld,%ld,%.2f,%.2f,%d,%d,%u",
             tx_seq, t_left, t_right,
             current_speed_l_rad_s, current_speed_r_rad_s,
             vbat_mv, dist_cm, current_safety_state);

    send_packet(String(payload_buf));
  }
}
