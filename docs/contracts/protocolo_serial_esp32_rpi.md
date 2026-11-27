# Contrato de Interface: Protocolo Serial ESP32 <-> Raspberry Pi 3B
**Versão:** 1.0 (Congelada na Fase 0)  
**Status:** Congelado / Mandatório  
**Autores:** Agent-Coordinator & Agent-QA-Safety-Auditor  

---

## 1. Parâmetros Físicos e Elétricos
* **Barramento:** UART assíncrona full-duplex via porta USB Serial (`/dev/ttyUSB0` ou `/dev/ttyACM0`).
* **Baud Rate:** 115200 bps (tolerância de clock < 1.5%).
* **Configuração:** 8 bits de dados, sem paridade, 1 stop bit (8N1), sem controle de fluxo por hardware.
* **Frequência Nominal:** 30 Hz (período nominal $T = 33.3\text{ ms}$).

---

## 2. Framing e Estrutura dos Pacotes
Todo pacote transmitido por qualquer extremidade segue o formato:
```text
$<TIPO>,<SEQ>,<PARAM_1>,<PARAM_2>,...<PARAM_N>*<CRC16>\r\n
```

### 2.1 Delimitadores e Campos
1. `$` (ASCII 0x24): Início de pacote (Start of Frame).
2. `<TIPO>`: Identificador alfanumérico da mensagem (`CMD`, `ESTOP`, `RESET`, `TELEM`, `ACK_STOP`, `ACK_RESET`).
3. `,` (ASCII 0x2C): Separador de campos de payload.
4. `<SEQ>`: Inteiro sem sinal de 16 bits ($0$ a $65535$). O próximo número após $65535$ é obrigatoriamente $0$.
5. `*` (ASCII 0x2A): Separador de verificação de integridade (End of Payload).
6. `<CRC16>`: 4 caracteres hexadecimais em maiúsculas (`[0-9A-F]`), com zero à esquerda (*zero-padded*).
7. `\r\n` (ASCII 0x0D 0x0A): Terminador de linha (CR LF).

---

## 3. Especificação do Algoritmo CRC16-CCITT

O algoritmo de verificação deve ser idêntico em C++ (ESP32) e Python/C++ (Raspberry Pi 3B).

* **Padrão:** CRC-16/CCITT-FALSE
* **Polinômio Gerador:** `0x1021` ($x^{16} + x^{12} + x^5 + 1$)
* **Valor Inicial (Init):** `0xFFFF`
* **RefIn (Reflexão de Entrada):** `false` (MSB first)
* **RefOut (Reflexão de Saída):** `false` (MSB first)
* **XorOut (XOR Final):** `0x0000`

### 3.1 Cobertura Exata dos Bytes
O cálculo do CRC16 é aplicado **estritamente sobre todos os bytes ASCII situados entre `$` e `*`** (excluindo o `$`, o `*`, o `<CRC16>` e o `\r\n`).

*Exemplo de Verificação:*
* Linha completa transmitida: `$CMD,1042,3.14,-3.14*7D3B\r\n`
* String de entrada do CRC: `"CMD,1042,3.14,-3.14"` (19 bytes)
* CRC calculado: `0x7D3B` $\rightarrow$ string hexadecimal `"7D3B"`.

---

## 4. Catálogo de Mensagens

### 4.1 Raspberry Pi 3B -> ESP32

#### A. `$CMD` — Comando de Velocidade Angular das Rodas (30 Hz)
* **Sintaxe:** `$CMD,<seq>,<left_rad_s>,<right_rad_s>*<CRC16>\r\n`
* **Parâmetros:**
  * `<left_rad_s>`: Velocidade angular da roda esquerda em rad/s (float com 2 casas decimais, positivo para frente).
  * `<right_rad_s>`: Velocidade angular da roda direita em rad/s (float com 2 casas decimais, positivo para frente).
* **Exemplo:** `$CMD,1042,3.14,-3.14*7D3B\r\n`

#### B. `$ESTOP` — Parada de Emergência Imediata (Assíncrona / Evento)
* **Sintaxe:** `$ESTOP,<seq>,<reason_code>*<CRC16>\r\n`
* **Parâmetros:**
  * `<reason_code>`: 1 = Parada remota solicitada / Software E-Stop, 2 = Obstáculo LiDAR / Segurança, 3 = Watchdog / Erro interno.
* **Ação no ESP32:** Zera PWM imediatamente, desliga Enable da ponte H e comuta estado interno para emergência.
* **Exemplo:** `$ESTOP,1043,1*B820\r\n`

#### C. `$RESET` — Solicitação de Rearme após Emergência
* **Sintaxe:** `$RESET,<seq>*<CRC16>\r\n`
* **Condição:** Só é aceito se comandos de velocidade forem exatamente zero e pino de emergência físico estiver em nível seguro.
* **Exemplo:** `$RESET,1044*E21A\r\n`

---

### 4.2 ESP32 -> Raspberry Pi 3B

#### A. `$TELEM` — Telemetria de Sensores e Odometria (30 Hz)
* **Sintaxe:** `$TELEM,<seq>,<ticks_left>,<ticks_right>,<rad_s_left>,<rad_s_right>,<vbat_mv>,<dist_us_cm>,<safety_state>*<CRC16>\r\n`
* **Parâmetros:**
  * `<ticks_left>`: Inteiro de 32 bits assinado (long) com contagem acumulada do encoder esquerdo.
  * `<ticks_right>`: Inteiro de 32 bits assinado (long) com contagem acumulada do encoder direito.
  * `<rad_s_left>`: Velocidade angular calculada da roda esquerda em rad/s (float, 2 casas).
  * `<rad_s_right>`: Velocidade angular calculada da roda direita em rad/s (float, 2 casas).
  * `<vbat_mv>`: Tensão da bateria em milivolts (ex: 12450 = 12.45 V).
  * `<dist_us_cm>`: Distância do sensor ultrassônico em centímetros (inteiro, 999 = sem obstáculo).
  * `<safety_state>`:
    * `0` = OK / NORMAL
    * `1` = HARDWARE_ESTOP_ACTIVE (Botão cogumelo físico pressionado)
    * `2` = WATCHDOG_TIMEOUT (Sem pacote válido em 200 ms)
    * `3` = DRIVER_FAULT (Sobrecarga de corrente ou falha na ponte H)
    * `4` = ESTOP_CLEARED_PENDING_RESET (Emergência física liberada, aguardando comando $RESET)
* **Exemplo:** `$TELEM,5012,1420,-1418,3.12,-3.13,12450,85,0*2F41\r\n`

#### B. `$ACK_STOP` — Confirmação de Motores Imobilizados
* **Sintaxe:** `$ACK_STOP,<seq>,<motors_off>*<CRC16>\r\n`
* **Parâmetros:** `<motors_off>`: 1 se PWM == 0 e transistores desligados, 0 caso contrário.

#### C. `$ACK_RESET` — Confirmação de Rearme de Emergência
* **Sintaxe:** `$ACK_RESET,<seq>,<success>*<CRC16>\r\n`
* **Parâmetros:** `<success>`: 1 se rearmado com sucesso para estado IDLE, 0 se recusado.

---

## 5. Máquina de Estados do Watchdog e Descarte de Falhas

1. **Watchdog de 200 ms no ESP32:**
   * Um temporizador de hardware zera toda vez que um pacote `$CMD` ou `$ESTOP` com CRC16 válido é processado.
   * Se o timer atingir $200\text{ ms}$, os pinos de acionamento PWM são comutados para nível 0 e os pinos de Enable para nível LOW.
2. **Descarte de Mensagens:**
   * Pacote corrompido ou com CRC divergente é descartado silenciosamente na recepção, incrementando o contador de erros.
   * Não são geradas respostas NACK para evitar congestionamento no barramento serial.
3. **Detecção de Queda de Link na Raspberry Pi 3B:**
   * Se a RPi 3B não receber `$TELEM` válido por mais de $200\text{ ms}$, **interrompe a publicação de `/odom` (ou publica covariância infinita $10^6$)** e reporta `serial_connected: false` no tópico `/agv/hardware_status`.
