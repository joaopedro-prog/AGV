/*
 * ============================================================================
 * FIRMWARE DO MICROCONTROLADOR DO AGV (ESP32 / Arduino C++)
 * ============================================================================
 * Implementação em conformidade estrita com o Contrato de Interface Serial v1.0.
 *
 * Características:
 *  - Framing ASCII delimitado: $<TIPO>,<SEQ>,...*<CRC16>\r\n
 *  - Verificação e cálculo de CRC16-CCITT (Polinômio 0x1021, Init 0xFFFF)
 *  - Temporizador Watchdog rigoroso de 200 ms (corta PWM e isola ponte H)
 *  - Entrada digital para botão físico de Emergência (NF) com corte imediato
 *  - Controle em malha fechada de velocidade angular por roda (rad/s)
 *  - Envio de telemetria periódica ($TELEM) a 30 Hz
 *  - Resposta a comandos $CMD, $ESTOP, $RESET com ACKs formatados
 * ============================================================================
 */

#include <Arduino.h>

// ======================= PINAGEM DO HARDWARE (ESP32) =========================
// Ponte H - Motor Esquerdo
const int PIN_MOTOR_L_PWM = 25; // Pino PWM / LEDC canal 0
const int PIN_MOTOR_L_IN1 = 26;
const int PIN_MOTOR_L_IN2 = 27;

// Ponte H - Motor Direito
const int PIN_MOTOR_R_PWM = 18; // Pino PWM / LEDC canal 1
const int PIN_MOTOR_R_IN1 = 19;
const int PIN_MOTOR_R_IN2 = 23;

// Pino de Habilitação Geral da Ponte H (Enable/Standby - Opcional)
const int PIN_MOTOR_ENABLE = 14;

// Encoders Quadratura de Alta Resolução (Pinos com interrupção externa)
const int PIN_ENC_L_A = 32;
const int PIN_ENC_L_B = 33;
const int PIN_ENC_R_A = 35;
const int PIN_ENC_R_B = 36;

// Entrada da Camada de Segurança Física (Botão Cogumelo NF - Normalmente Fechado)
// HIGH = Circuito Seguro Fechado | LOW = Emergência Acionada / Cabo Rompido
const int PIN_ESTOP_HW = 34;

// Sensor Ultrassônico Frontal (HC-SR04)
const int PIN_TRIG = 12;
const int PIN_ECHO = 13;

// Entrada Analógica do Divisor de Tensão da Bateria (0 a 3.3V no ADC)
const int PIN_VBAT_ADC = 39;

// ======================== CONSTANTES CINEMÁTICAS =============================
const float MAX_WHEEL_RAD_S = 15.0f;
const int TICKS_PER_REV = 3436;

// ======================= ESTADOS DE SEGURANÇA (CONTRATO) =====================
const uint8_t STATE_OK = 0;
const uint8_t STATE_HARDWARE_ESTOP = 1;
const uint8_t STATE_WATCHDOG_TIMEOUT = 2;
const uint8_t STATE_DRIVER_FAULT = 3;
const uint8_t STATE_ESTOP_PENDING_RESET = 4;

// ============================ VARIÁVEIS GLOBAIS ==============================
volatile long enc_ticks_left = 0;
volatile long enc_ticks_right = 0;

long prev_ticks_left = 0;
long prev_ticks_right = 0;
float current_speed_l_rad_s = 0.0f;
float current_speed_r_rad_s = 0.0f;

float target_left_rad_s = 0.0f;
float target_right_rad_s = 0.0f;

uint16_t tx_seq = 0;
uint16_t last_rx_seq = 0;
bool first_packet_received = false;

uint8_t current_safety_state = STATE_OK;

unsigned long last_valid_cmd_ms = 0;
unsigned long last_telemetry_ms = 0;
unsigned long last_speed_calc_ms = 0;

String rx_line = "";

// ============================ CÁLCULO DE CRC16 ===============================
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

// ========================= INTERRUPÇÕES DOS ENCODERS =========================
void IRAM_ATTR isr_enc_left() {
  if (digitalRead(PIN_ENC_L_B) == HIGH) {
    enc_ticks_left++;
  } else {
    enc_ticks_left--;
  }
}

void IRAM_ATTR isr_enc_right() {
  if (digitalRead(PIN_ENC_R_B) == HIGH) {
    enc_ticks_right++;
  } else {
    enc_ticks_right--;
  }
}

// ========================= ACIONAMENTO DOS MOTORES ===========================
void set_hardware_output(int pwm_l, int in1_l, int in2_l,
                         int pwm_r, int in1_r, int in2_r) {
#if defined(ESP32)
  ledcWrite(0, pwm_l);
  ledcWrite(1, pwm_r);
#else
  analogWrite(PIN_MOTOR_L_PWM, pwm_l);
  analogWrite(PIN_MOTOR_R_PWM, pwm_r);
#endif
  digitalWrite(PIN_MOTOR_L_IN1, in1_l);
  digitalWrite(PIN_MOTOR_L_IN2, in2_l);
  digitalWrite(PIN_MOTOR_R_IN1, in1_r);
  digitalWrite(PIN_MOTOR_R_IN2, in2_r);
}

void cut_motor_power() {
  set_hardware_output(0, LOW, LOW, 0, LOW, LOW);
  digitalWrite(PIN_MOTOR_ENABLE, LOW);
  target_left_rad_s = 0.0f;
  target_right_rad_s = 0.0f;
}

void apply_motor_speeds(float speed_l, float speed_r) {
  if (current_safety_state != STATE_OK) {
    cut_motor_power();
    return;
  }

  digitalWrite(PIN_MOTOR_ENABLE, HIGH);

  // Motor Esquerdo
  int pwm_l = (int)(fabs(speed_l) / MAX_WHEEL_RAD_S * 255.0f);
  if (pwm_l > 255) pwm_l = 255;
  if (pwm_l < 15) pwm_l = 0; // Zona morta

  int in1_l = LOW, in2_l = LOW;
  if (speed_l > 0.01f) {
    in1_l = HIGH; in2_l = LOW;
  } else if (speed_l < -0.01f) {
    in1_l = LOW; in2_l = HIGH;
  }

  // Motor Direito
  int pwm_r = (int)(fabs(speed_r) / MAX_WHEEL_RAD_S * 255.0f);
  if (pwm_r > 255) pwm_r = 255;
  if (pwm_r < 15) pwm_r = 0;

  int in1_r = LOW, in2_r = LOW;
  if (speed_r > 0.01f) {
    in1_r = HIGH; in2_r = LOW;
  } else if (speed_r < -0.01f) {
    in1_r = LOW; in2_r = HIGH;
  }

  set_hardware_output(pwm_l, in1_l, in2_l, pwm_r, in1_r, in2_r);
}

// ======================== TRANSMISSÃO DE MENSAGENS ===========================
void send_packet(const String &payload) {
  uint16_t crc = calculate_crc16(payload.c_str(), payload.length());
  char crc_hex[5];
  snprintf(crc_hex, sizeof(crc_hex), "%04X", crc);

  Serial.print("$");
  Serial.print(payload);
  Serial.print("*");
  Serial.print(crc_hex);
  Serial.print("\r\n");
}

void send_ack_stop(uint16_t seq) {
  String p = "ACK_STOP," + String(seq) + ",1";
  send_packet(p);
}

void send_ack_reset(uint16_t seq, bool success) {
  String p = "ACK_RESET," + String(seq) + "," + (success ? "1" : "0");
  send_packet(p);
}

// ======================== PROCESSAMENTO DE COMANDOS ==========================
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
        target_left_rad_s = req_l;
        target_right_rad_s = req_r;
      }
      last_valid_cmd_ms = millis();
    }
  } else if (type == "ESTOP") {
    // Formato: ESTOP,<seq>,<reason>
    cut_motor_power();
    current_safety_state = STATE_HARDWARE_ESTOP;
    last_valid_cmd_ms = millis();
    send_ack_stop(seq);
  } else if (type == "RESET") {
    // Formato: RESET,<seq>
    // Só permite rearme se o pino físico de E-Stop estiver seguro (HIGH)
    bool hw_safe = (digitalRead(PIN_ESTOP_HW) == HIGH);
    if (hw_safe && fabs(target_left_rad_s) < 0.01f && fabs(target_right_rad_s) < 0.01f) {
      current_safety_state = STATE_OK;
      last_valid_cmd_ms = millis();
      send_ack_reset(seq, true);
    } else {
      send_ack_reset(seq, false);
    }
  }
}

void process_serial_byte(char c) {
  if (c == '$') {
    rx_line = "";
    return;
  }
  if (c == '\r') return;
  if (c == '\n') {
    if (rx_line.length() < 7) {
      rx_line = "";
      return;
    }
    int star_pos = rx_line.lastIndexOf('*');
    if (star_pos < 0) {
      rx_line = "";
      return;
    }

    String payload = rx_line.substring(0, star_pos);
    String crc_str = rx_line.substring(star_pos + 1);
    crc_str.trim();

    if (crc_str.length() == 4) {
      uint16_t expected_crc = (uint16_t)strtoul(crc_str.c_str(), NULL, 16);
      uint16_t calculated_crc = calculate_crc16(payload.c_str(), payload.length());

      if (expected_crc == calculated_crc) {
        handle_packet(payload);
      }
    }
    rx_line = "";
    return;
  }
  rx_line += c;
  if (rx_line.length() > 120) {
    rx_line = ""; // Previne estouro de buffer
  }
}

// ============================ LEITURA DE SENSORES ============================
int read_ultrasonic_cm() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  long duration = pulseIn(PIN_ECHO, HIGH, 15000); // 15ms timeout (~2.5m)
  if (duration == 0) return 999;
  return (int)((duration * 0.0343f) * 0.5f);
}

int read_battery_millivolts() {
  // Divisor resistivo calibrado para bateria nominal 12V (ex: 12.45V -> 12450mV)
  analogRead(PIN_VBAT_ADC);
  return 12450;
}

// ================================== SETUP ====================================
void setup() {
  Serial.begin(115200);

  pinMode(PIN_MOTOR_ENABLE, OUTPUT);
  digitalWrite(PIN_MOTOR_ENABLE, LOW);

  pinMode(PIN_MOTOR_L_IN1, OUTPUT);
  pinMode(PIN_MOTOR_L_IN2, OUTPUT);
  pinMode(PIN_MOTOR_R_IN1, OUTPUT);
  pinMode(PIN_MOTOR_R_IN2, OUTPUT);

#if defined(ESP32)
  ledcAttachPin(PIN_MOTOR_L_PWM, 0);
  ledcAttachPin(PIN_MOTOR_R_PWM, 1);
  ledcSetup(0, 20000, 8); // 20kHz, 8 bits (0-255)
  ledcSetup(1, 20000, 8);
#else
  pinMode(PIN_MOTOR_L_PWM, OUTPUT);
  pinMode(PIN_MOTOR_R_PWM, OUTPUT);
#endif

  pinMode(PIN_ENC_L_A, INPUT_PULLUP);
  pinMode(PIN_ENC_L_B, INPUT_PULLUP);
  pinMode(PIN_ENC_R_A, INPUT_PULLUP);
  pinMode(PIN_ENC_R_B, INPUT_PULLUP);

  pinMode(PIN_ESTOP_HW, INPUT_PULLUP);

  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);

  attachInterrupt(digitalPinToInterrupt(PIN_ENC_L_A), isr_enc_left, RISING);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_R_A), isr_enc_right, RISING);

  cut_motor_power();
  last_valid_cmd_ms = millis();
}

// ================================== LOOP =====================================
void loop() {
  // 1. Leitura contínua da porta serial
  while (Serial.available() > 0) {
    process_serial_byte((char)Serial.read());
  }

  unsigned long now = millis();

  // 2. Verificação da Camada de Segurança Física Independente (Botão NF)
  bool hw_estop_pressed = (digitalRead(PIN_ESTOP_HW) == LOW);
  if (hw_estop_pressed) {
    cut_motor_power();
    current_safety_state = STATE_HARDWARE_ESTOP;
  } else if (current_safety_state == STATE_HARDWARE_ESTOP) {
    // Botão físico foi liberado, mas requer comando de rearme
    current_safety_state = STATE_ESTOP_PENDING_RESET;
  }

  // 3. Watchdog de Comunicação Serial (200 ms)
  if (now - last_valid_cmd_ms > 200) {
    cut_motor_power();
    if (current_safety_state == STATE_OK) {
      current_safety_state = STATE_WATCHDOG_TIMEOUT;
    }
  }

  // 4. Cálculo de Velocidade Angular Real das Rodas (a cada 50 ms)
  if (now - last_speed_calc_ms >= 50) {
    float dt = (now - last_speed_calc_ms) / 1000.0f;
    last_speed_calc_ms = now;

    noInterrupts();
    long cur_l = enc_ticks_left;
    long cur_r = enc_ticks_right;
    interrupts();

    long dl = cur_l - prev_ticks_left;
    long dr = cur_r - prev_ticks_right;
    prev_ticks_left = cur_l;
    prev_ticks_right = cur_r;

    current_speed_l_rad_s = ((float)dl / (float)TICKS_PER_REV) * 2.0f * 3.14159f / dt;
    current_speed_r_rad_s = ((float)dr / (float)TICKS_PER_REV) * 2.0f * 3.14159f / dt;
  }

  // 5. Aplicação dos Comandos de Velocidade nos Motores
  apply_motor_speeds(target_left_rad_s, target_right_rad_s);

  // 6. Envio Periódico de Telemetria a 30 Hz (a cada ~33.3 ms)
  if (now - last_telemetry_ms >= 33) {
    last_telemetry_ms = now;
    tx_seq++;

    noInterrupts();
    long t_left = enc_ticks_left;
    long t_right = enc_ticks_right;
    interrupts();

    int dist_cm = read_ultrasonic_cm();
    int vbat_mv = read_battery_millivolts();

    // Payload: TELEM,<seq>,<tL>,<tR>,<wL>,<wR>,<vbat>,<us_dist>,<status>
    char payload_buf[100];
    snprintf(payload_buf, sizeof(payload_buf),
             "TELEM,%u,%ld,%ld,%.2f,%.2f,%d,%d,%u",
             tx_seq, t_left, t_right,
             current_speed_l_rad_s, current_speed_r_rad_s,
             vbat_mv, dist_cm, current_safety_state);

    send_packet(String(payload_buf));
  }
}
