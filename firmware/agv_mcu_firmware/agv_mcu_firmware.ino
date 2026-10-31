/*
 * ============================================================================
 * FIRMWARE DO MICROCONTROLADOR DO AGV (Arduino / ESP32 / STM32 / RP2040)
 * ============================================================================
 * Comunica via USB Serial (115200 bps) com o nó 'serial_bridge' na Raspberry Pi.
 *
 * Protocolo Recebido da Raspberry Pi:
 *   CMD,<vel_esq_rad_s>,<vel_dir_rad_s>\n
 *
 * Protocolo Enviado para a Raspberry Pi (30 Hz):
 *   ENC,<pulsos_acumulados_esq>,<pulsos_acumulados_dir>\n
 *   SENS,<distancia_obstaculo_metros>,<tensao_bateria_volts>\n
 * ============================================================================
 */

#include <Arduino.h>

// ======================== [ALTERAR] PINOS DO HARDWARE ========================
// Ponte H - Motor Esquerdo
const int PIN_MOTOR_L_PWM = 5;
const int PIN_MOTOR_L_IN1 = 6;
const int PIN_MOTOR_L_IN2 = 7;

// Ponte H - Motor Direito
const int PIN_MOTOR_R_PWM = 10;
const int PIN_MOTOR_R_IN1 = 8;
const int PIN_MOTOR_R_IN2 = 9;

// Encoders Quadratura (Use pinos com suporte a Interrupt!)
const int PIN_ENC_L_A = 2;
const int PIN_ENC_L_B = 4;
const int PIN_ENC_R_A = 3;
const int PIN_ENC_R_B = 11;

// Sensor Ultrassônico Frontal (HC-SR04) - Opcional
const int PIN_TRIG = 12;
const int PIN_ECHO = 13;

// Constante máxima de velocidade da roda (rad/s) equivalente a PWM 255
const float MAX_WHEEL_RAD_S = 15.0f;

// ============================ VARIÁVEIS GLOBAIS ==============================
volatile long enc_ticks_left = 0;
volatile long enc_ticks_right = 0;

float target_left_rad_s = 0.0f;
float target_right_rad_s = 0.0f;
unsigned long last_cmd_ms = 0;
unsigned long last_telemetry_ms = 0;
String rx_buffer = "";

// ========================= INTERRUPÇÕES DOS ENCODERS =========================
void isr_enc_left() {
  if (digitalRead(PIN_ENC_L_B) == HIGH) {
    enc_ticks_left++;
  } else {
    enc_ticks_left--;
  }
}

void isr_enc_right() {
  if (digitalRead(PIN_ENC_R_B) == HIGH) {
    enc_ticks_right++;
  } else {
    enc_ticks_right--;
  }
}

// ========================= ACIONAMENTO DOS MOTORES ===========================
void set_motor(int pin_pwm, int pin_in1, int pin_in2, float speed_rad_s) {
  int pwm = (int)(fabs(speed_rad_s) / MAX_WHEEL_RAD_S * 255.0f);
  if (pwm > 255) pwm = 255;
  if (pwm < 15) pwm = 0; // Zona morta do motor

  if (speed_rad_s > 0.01f) {
    digitalWrite(pin_in1, HIGH);
    digitalWrite(pin_in2, LOW);
    analogWrite(pin_pwm, pwm);
  } else if (speed_rad_s < -0.01f) {
    digitalWrite(pin_in1, LOW);
    digitalWrite(pin_in2, HIGH);
    analogWrite(pin_pwm, pwm);
  } else {
    digitalWrite(pin_in1, LOW);
    digitalWrite(pin_in2, LOW);
    analogWrite(pin_pwm, 0);
  }
}

float read_ultrasonic_meters() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  long duration = pulseIn(PIN_ECHO, HIGH, 15000); // Timeout 15ms (~2.5m)
  if (duration == 0) return 9.99f; // Sem obstáculo próximo
  return (duration * 0.000343f) * 0.5f;
}

void parse_command(const String &line) {
  // Esperado: CMD,<vel_esq>,<vel_dir>
  if (line.startsWith("CMD,")) {
    int first_comma = line.indexOf(',');
    int second_comma = line.indexOf(',', first_comma + 1);
    if (second_comma > first_comma) {
      target_left_rad_s = line.substring(first_comma + 1, second_comma).toFloat();
      target_right_rad_s = line.substring(second_comma + 1).toFloat();
      last_cmd_ms = millis();
    }
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(PIN_MOTOR_L_PWM, OUTPUT);
  pinMode(PIN_MOTOR_L_IN1, OUTPUT);
  pinMode(PIN_MOTOR_L_IN2, OUTPUT);
  pinMode(PIN_MOTOR_R_PWM, OUTPUT);
  pinMode(PIN_MOTOR_R_IN1, OUTPUT);
  pinMode(PIN_MOTOR_R_IN2, OUTPUT);

  pinMode(PIN_ENC_L_A, INPUT_PULLUP);
  pinMode(PIN_ENC_L_B, INPUT_PULLUP);
  pinMode(PIN_ENC_R_A, INPUT_PULLUP);
  pinMode(PIN_ENC_R_B, INPUT_PULLUP);

  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);

  attachInterrupt(digitalPinToInterrupt(PIN_ENC_L_A), isr_enc_left, RISING);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_R_A), isr_enc_right, RISING);
}

void loop() {
  // 1. Lê comandos enviados pela Raspberry Pi
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n') {
      rx_buffer.trim();
      if (rx_buffer.length() > 0) {
        parse_command(rx_buffer);
      }
      rx_buffer = "";
    } else {
      rx_buffer += c;
    }
  }

  // 2. Watchdog de segurança (para motores se ficar >500ms sem comando da Raspberry)
  if (millis() - last_cmd_ms > 500) {
    target_left_rad_s = 0.0f;
    target_right_rad_s = 0.0f;
  }

  // 3. Aplica velocidades nos motores
  set_motor(PIN_MOTOR_L_PWM, PIN_MOTOR_L_IN1, PIN_MOTOR_L_IN2, target_left_rad_s);
  set_motor(PIN_MOTOR_R_PWM, PIN_MOTOR_R_IN1, PIN_MOTOR_R_IN2, target_right_rad_s);

  // 4. Envia telemetria de encoders e sensores a 30 Hz (a cada ~33ms)
  if (millis() - last_telemetry_ms >= 33) {
    last_telemetry_ms = millis();

    noInterrupts();
    long t_left = enc_ticks_left;
    long t_right = enc_ticks_right;
    interrupts();

    // Linha 1: Pulsos de encoder acumulados
    Serial.print("ENC,");
    Serial.print(t_left);
    Serial.print(",");
    Serial.println(t_right);

    // Linha 2: Sensores conectados no MCU (distância obstáculo em m, tensão bateria em V)
    float dist_m = read_ultrasonic_meters();
    float battery_v = 12.0f; // Ou leitura de divisor de tensão em A0
    Serial.print("SENS,");
    Serial.print(dist_m, 2);
    Serial.print(",");
    Serial.println(battery_v, 2);
  }
}
