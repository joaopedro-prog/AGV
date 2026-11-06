# Especificação da Máquina de Estados de Segurança e Parada
**Versão:** 1.0 (Congelada na Fase 0)  
**Status:** Congelado / Mandatório  
**Autores:** Agent-Coordinator & Agent-QA-Safety-Auditor  

---

## 1. Estados Globais do AGV

A máquina de estados unificada rege tanto a lógica de controle onboard quanto os indicadores visuais do Dashboard Web:

```text
[1] IDLE (Standby Seguro)
[2] EM_MOVIMENTO (Navegação / Teleoperação)
[3] REMOTE_STOP_REQUESTED (Parada Remota Solicitada)
[4] STOP_CONFIRMED (Parada Confirmada)
[5] HARDWARE_ESTOP_ACTIVE (Emergência Física / Watchdog Acionado)
[6] RECOVERY_PENDING (Aguardando Comando de Rearme)
```

---

## 2. Tabela de Transições de Estado

| Estado Atual | Evento de Gatilho | Novo Estado | Ação Executada | Indicador no Dashboard |
| :--- | :--- | :--- | :--- | :--- |
| **IDLE** | Comando START / Serviço `set_following(true)` | **EM_MOVIMENTO** | Inicia controlador PID seguidor de linha em `/cmd_vel_line` | 🟢 Verde estável |
| **EM_MOVIMENTO** | Botão STOP no Dashboard / Tópico `/agv/command: STOP` | **REMOTE_STOP_REQUESTED** | Aplica desaceleração controlada via rampa de software | 🟡 Amarelo pulsante |
| **REMOTE_STOP_REQUESTED**| Encoders das rodas com $\|v\| \le 0.005\text{ m/s}$ por 150 ms e `$ACK_STOP` do ESP32 | **STOP_CONFIRMED** | Corta PWM para 0; robô imobilizado em segurança | 🔵 Azul estável |
| **STOP_CONFIRMED** | Reset pelo operador ou novo comando de operação | **IDLE** | Sistema pronto em standby para nova missão | 🔵 Azul estável |
| **QUALQUER ESTADO** | Botão cogumelo mecânico pressionado / Watchdog de 200 ms expirado / Queda serial | **HARDWARE_ESTOP_ACTIVE** | **Corte físico imediato de alimentação VMOT dos motores** e inibição da ponte H | 🔴 Vermelho piscante com alarme sonoro |
| **HARDWARE_ESTOP_ACTIVE**| Desarme mecânico manual do botão cogumelo | **RECOVERY_PENDING** | Circuito elétrico fecha; ESP32 sinaliza `ESTOP_CLEARED_PENDING_RESET` | 🟠 Laranja estável ("Pronto para Rearme") |
| **RECOVERY_PENDING** | Operador clica em "REARMAR" no Dashboard (`/agv/reset_emergency`) | **IDLE** | Handshake de velocidade zero enviado ao ESP32; saída rearmada com sucesso | 🔵 Azul estável |

---

## 3. Procedimento Mandatório de Rearme em 5 Passos (Recovery)

1. **Passo 1 (Interlock Mecânico):** O operador humano deve ir até o AGV físico, verificar a ausência de pessoas ou obstáculos em contato com a estrutura e desarmar manualmente o botão cogumelo (girando-o ou puxando-o para destravar o mecanismo).
2. **Passo 2 (Verificação Elétrica):** Com o botão liberado, o circuito normalmente fechado (NF) fecha. O ESP32 e o pino GPIO BCM 17 da Raspberry Pi detectam o nível lógico alto. O ESP32 envia no `$TELEM` o status `ESTOP_CLEARED_PENDING_RESET`.
3. **Passo 3 (Comando de Software):** O operador clica explicitamente no botão "REARMAR SISTEMA (RESET)" na interface do Dashboard Web, que chama o serviço `/agv/reset_emergency`.
4. **Passo 4 (Validação de Velocidade Zero e Handshake):** A Raspberry Pi 3B verifica que todos os tópicos de velocidade estão zerados e envia `$RESET,<seq>*CRC` para o ESP32. O ESP32 reativa os drivers dos motores e responde com `$ACK_RESET,1*CRC`.
5. **Passo 5 (Transição para Standby):** O supervisor comuta para o estado `IDLE`.
