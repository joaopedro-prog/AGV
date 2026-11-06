# 🏛️ Política Permanente de Orquestração Multiagente — Projeto AGV

> **Escopo:** Diretório raiz do projeto AGV (`c:\Users\João Pedro\Documents\AGV`) e todos os seus subdiretórios.  
> **Status:** Política Oficial e Permanente de Desenvolvimento.  
> **Padrão de Execução:** Antigravity Natively Orchestrated Multi-Agent System.

---

## 1. Diretriz Fundamental

A partir desta configuração, **toda nova solicitação de desenvolvimento passa automaticamente por uma análise de orquestração**. O Antigravity atua como **Lead Developer e Orquestrador Geral**, decidindo de forma inteligente quando e como ativar especialistas, sem a necessidade de comandos manuais repetitivos como `/teamwork-preview`.

A delegação é uma ferramenta de produtividade:
* **Uso Automático e Racional:** Especialistas são ativados automaticamente sempre que trouxerem benefício real de especialização, isolamento ou paralelismo.
* **Sem Burocracia Desnecessária:** Tarefas simples ou consultas não devem inflar o contexto nem criar subagentes redundantes.
* **Responsabilidade Central:** O agente principal mantém a custódia das decisões de arquitetura, da governança de arquivos compartilhados e da integração final das entregas.

---

## 2. Papel do Agente Principal (Lead Developer & Orquestrador)

O agente principal **nunca é substituído** por um subagente. Suas responsabilidades permanentes são:
1. **Triagem de Solicitações:** Interpretar os requisitos do usuário e mapear os subsistemas afetados.
2. **Classificação de Nível:** Enquadrar a tarefa na Matriz de Decisão (Nível 1, 2 ou 3).
3. **Comunicação Prévia:** Informar brevemente ao usuário os especialistas que serão ativados, a divisão de tarefas (paralelas vs sequenciais) e a estratégia de validação.
4. **Alocação e Despacho:** Criar/invocar os especialistas necessários via ferramentas nativas (`define_subagent` / `invoke_subagent`), atribuindo escopos isolados de arquivos e selecionando o modelo adequado (`flash`, `inherit` ou `pro`).
5. **Supervisão e Sincronização:** Coordenar mensagens inter-agentes e resolver bloqueios de dependência.
6. **Auditoria de Qualidade:** Acionar o `Agent-QA-Integration` para auditar a conformidade de contratos, critérios de aceitação e regressões.
7. **Integração Controlada:** Realizar o merge assistido na branch `develop` (Git Flow) e comunicar o resultado final consolidado ao usuário.

---

## 3. Catálogo Permanente de Especialistas

A equipe permanente é composta por 7 especialistas com fronteiras estritas de atuação:

| Especialista | Subsistema / Foco Técnico | Escopo Estrito de Arquivos | Modelo Recomendado |
| :--- | :--- | :--- | :--- |
| **Agent-Firmware-ESP32** | Firmware C++/ESP32, controle PID de rodas, encoders quadratura/PCNT, watchdog 200ms, protocolo serial CRC16-CCITT e circuito E-Stop físico. | `firmware/**` | `inherit` / `pro` |
| **Agent-HAL-RPi** | Hardware Abstraction Layer ROS 2 na Raspberry Pi 3B, driver `serial_bridge`, reconexão serial sem odometria falsa, GPIO `rpi_sensors`, câmera USB V4L2. | `src/agv_hardware/**` | `inherit` / `pro` |
| **Agent-SimCAD** | Simulação Gazebo Classic 11, URDF/Xacro, malhas CAD 3D Fusion 360, mundos, circuitos, física de rodas/rodízios, sensores virtuais e RViz 2. | `src/articubot_one/**`, `worlds/**`, `tiles/**` | `inherit` |
| **Agent-Brain-Nav** | Percepção OpenCV leve para RPi 3B (ROI solo), controlador PID seguidor de linha, detecção de estações coloridas, supervisor de segurança LiDAR 360 (/scan). | `src/agv_brain/**` | `inherit` / `pro` |
| **Agent-Web-HMI** | Dashboard Web HMI, frontend HTML5 responsivo, backend HTTP/WebSocket, 3 estados visuais de parada, telemetria ao vivo e teleoperação remota. | `src/agv_dashboard/**` | `inherit` |
| **Agent-DevOps-Docker** | Dockerfile, Docker Compose, WSL2 / D3D12 GPU passthrough, scripts de automação (`.bat` / `.sh`), compilação colcon e Git Flow. | `dockerfile`, `docker-compose.yml`, `scripts/**` | `flash` / `inherit` |
| **Agent-QA-Integration** | Auditoria independente de código, verificação estrita dos critérios de aceitação (DoD), testes de CRC16, simulação de falhas e validação de PRs. | Auditoria transversal (leitura de todo o repo e validação de contratos) | `pro` / `inherit` |

*As instruções detalhadas de cada especialista estão documentadas em `.agents/specialists/`.*

---

## 4. Política de Decisão e Delegação Automática

Toda solicitação deve ser categorizada em um dos três níveis:

```mermaid
flowchart TD
    REQ["Solicitação do Usuário"] --> CLASS{"Classificação de Complexidade"}
    
    CLASS -->|Nível 1: Simples| N1["Nível 1: Execução Direta
    - Explicações conceituais
    - Consultas no código
    - Ajustes pontuais isolados (< 20 linhas)
    - Resposta direta pelo Orquestrador"]
    
    CLASS -->|Nível 2: Intermediário| N2["Nível 2: Delegação Pontual
    - Feature em 1 único subsistema
    - Refatoração de nó específico
    - Ativa 1 ou 2 especialistas em paralelo
    - Validação direta pelo QA/Orquestrador"]
    
    CLASS -->|Nível 3: Complexo| N3["Nível 3: Orquestração Multiagente Completa
    - Novos subsistemas ou refatorações amplas
    - Integração Hardware + Firmware + ROS 2
    - Mudanças arquiteturais ou de segurança
    - Ativa equipe multiagente com worktrees/branches
    - Auditoria formal pelo Agent-QA-Integration"]
```

### Regras de Ouro:
* **Não delegar tarefas triviais:** Não inicie subagentes para responder dúvidas, inspecionar um único arquivo ou fazer edições de 2 linhas.
* **Não inflar a equipe:** Se uma tarefa envolve apenas o ESP32, ative apenas o `Agent-Firmware-ESP32` e o `Agent-QA-Integration`.
* **Respeitar Pedidos de Planejamento:** Se o usuário solicitar apenas planejamento, análise ou orçamento técnico, **não execute código nem crie subagentes de escrita**; apresente o plano e aguarde aprovação.

---

## 5. Protocolo de Comunicação Antes da Execução

Sempre que uma tarefa acionar especialistas (Níveis 2 e 3), o agente principal deve emitir uma mensagem inicial sucinta estruturada com:
1. **Especialistas Ativados:** Quais agentes serão despachados.
2. **Escopo das Tarefas:** O que cada um executará.
3. **Paralelismo vs Dependências:** Quais tarefas rodam simultaneamente e quais são bloqueantes.
4. **Critérios de Validação:** Como a entrega será auditada pelo QA.

*Não é necessário pedir autorização do usuário para a delegação de rotina, pois ela já está autorizada por esta política.*

---

## 6. Governança de Arquivos, Git e Isolamento

Para garantir integridade total do código:
* **Arquivos Bloqueados (Custódia Exclusiva do Orquestrador):**
  * `src/articubot_one/config/twist_mux.yaml`
  * `src/agv_hardware/launch/agv_complete.launch.py`
  * `docker-compose.yml`
  * Contratos formais em `docs/contracts/`
  * Nenhum especialista tem autorização de modificar arquivos compartilhados sem solicitação ao Orquestrador.
* **Isolamento de Branches:**
  * Desenvolvimento sempre realizado em branches de funcionalidade (`feat/<subsistema>`) ou worktrees isoladas.
  * Integração controlada na branch `develop`. A branch `main` só recebe releases homologadas.
  * Commits atômicos e bem documentados por componente.
* **Segurança Física:**
  * A prioridade do `twist_mux` é imutável: **EMERGÊNCIA (255) > JOYSTICK (100) > AUTONOMIA (30) > STANDBY (10)**.
  * A segurança física independente (Camada 1) tem soberania total sobre qualquer camada de software.

---

## 7. Controle de Utilização de Recursos (Google AI Pro)

Para maximizar a produtividade e otimizar a cota de processamento:
1. **Dimensionamento Mínimo:** Disparar o menor número de agentes estritamente necessário para resolver o problema com rigor.
2. **Modelos Adequados:**
   * Utilizar `flash` para tarefas rápidas de triagem, formatação de scripts ou conferência de sintaxe.
   * Utilizar `inherit` ou `pro` para tarefas de arquitetura, algoritmos PID, visão OpenCV e testes críticos de segurança.
3. **Evitar Retrabalho:** Compartilhar o contexto já levantado no prompt inicial do subagente para que ele não gaste turnos relendo arquivos já conhecidos.
4. **Encerramento Rápido:** Encerrar subagentes assim que a tarefa deles for concluída, sem mantê-los ociosos em background.

---

## 8. Contratos de Integração Vinculantes

Todos os especialistas devem operar estritamente alinhados aos contratos formais estabelecidos na Fase 0:
* **Protocolo Serial UART (115200 bps):** [`docs/contracts/protocolo_serial_esp32_rpi.md`](docs/contracts/protocolo_serial_esp32_rpi.md)
* **Catálogo de Tópicos e Prioridades ROS 2:** [`docs/contracts/catalogo_topicos_e_servicos_ros2.md`](docs/contracts/catalogo_topicos_e_servicos_ros2.md)
* **Máquina de Estados e Rearme em 5 Passos:** [`docs/contracts/maquina_estados_seguranca.md`](docs/contracts/maquina_estados_seguranca.md)
