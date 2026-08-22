# Guia de Referência Prático

Este guia fornece uma síntese técnica dos fluxos de trabalho e comandos necessários para o desenvolvimento e operação do ecossistema **articubot_one**.

O foco é a **reprodutibilidade via DevOps**, a integridade do sistema e a consistência entre ambientes de simulação e hardware real.

---

## 1. Gestão de Contêineres e Infraestrutura — Docker

A conteinerização é o alicerce para evitar a **deriva de dependências**. Ao isolar o ROS 2 (Humble/Jazzy) em contêineres, garantimos maior paridade entre o ambiente de desenvolvimento e o hardware de borda, como Jetson e Raspberry Pi.

Isso reduz conflitos de bibliotecas e drivers e torna o ambiente de execução mais previsível, independentemente do sistema operacional do host.

### Comandos de Operação

| Comando / Flag                      | Descrição                                                                          |
| ----------------------------------- | ---------------------------------------------------------------------------------- |
| `docker build -t articubot_image .` | Compila a imagem base seguindo as instruções do `Dockerfile`.                      |
| `docker run -it`                    | Instancia um contêiner interativo com alocação de TTY.                             |
| `--rm`                              | Remove o contêiner automaticamente após o encerramento.                            |
| `--user ross`                       | Define o usuário interno do contêiner para garantir compatibilidade de permissões. |

### Flags não negociáveis — Rede e IPC

No ROS 2, a descoberta de nós via **DDS (Data Distribution Service)** pode ser prejudicada pelo isolamento de rede padrão do Docker.

A flag `--network=host` permite que o contêiner utilize a pilha de rede do host, facilitando a comunicação transparente entre os processos.

Complementarmente, `--ipc=host` habilita o compartilhamento de memória entre processos, sendo especialmente importante para transferência de dados de alta largura de banda, como:

* Point Clouds de LiDAR;
* Streams de câmeras;
* Dados de sensores;
* Outros fluxos de dados entre processos ROS 2.

### Configuração de Ambiente e UID Match

Para evitar problemas de permissão em arquivos montados do host, o **UID/GID do usuário dentro do contêiner deve, idealmente, coincidir com o usuário do host**.

O kernel Linux gerencia permissões utilizando IDs numéricos, e não os nomes dos usuários.

Exemplo:

```bash
docker run -it \
    --network=host \
    --ipc=host \
    --user ross \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v $(pwd):/home/ross/articubot_one \
    articubot_image
```

Com a infraestrutura validada, podemos prosseguir para o versionamento do código-fonte e da descrição física do robô.

---

## 2. Fluxo de Trabalho de Desenvolvimento — Git

O Git deve ser tratado como parte da **Infraestrutura como Código (IaC)**.

O repositório não deve conter apenas scripts, mas também a definição física e visual do robô, incluindo:

* URDF/Xacro;
* Arquivos de configuração;
* Launch files;
* Configurações do RViz;
* Parâmetros de sensores;
* Parâmetros de navegação.

É uma boa prática versionar arquivos `.rviz` para manter uma experiência de desenvolvimento consistente para toda a equipe.

### Operações de Controle de Versão

```bash
# Verificar o estado do workspace
git status

# Adicionar um arquivo específico
git add <arquivo>

# Registrar uma alteração
git commit -m "mensagem"

# Sincronizar com o repositório remoto
git push
```

### Estratégia de Commits Atômicos

Ao realizar ajustes finos, evite misturar alterações de diferentes camadas do sistema.

Por exemplo, não combine:

* alterações de geometria do URDF, como posição do eixo da roda;
* alterações de parâmetros de sensores, como resolução do LiDAR;
* alterações de ganhos PID.

Commits atômicos facilitam:

* identificação de regressões;
* depuração de comportamento dinâmico;
* revisão de código;
* rollback de parâmetros sensíveis;
* rastreamento das alterações responsáveis por instabilidades.

---

## 3. Compilação e Sourcing do Workspace — ROS 2

O processo de compilação utilizando `colcon` organiza as dependências e prepara os artefatos necessários para o runtime.

O **sourcing** das variáveis de ambiente permite que o ROS 2 encontre os pacotes disponíveis no diretório de instalação.

### Build

```bash
colcon build --symlink-install
```

### Atenção ao Uso de Symlinks

A flag `--symlink-install` é especialmente útil durante o desenvolvimento de:

* URDF/Xacro;
* launch files;
* arquivos de configuração;
* scripts Python.

Ela permite que alterações em arquivos de origem sejam refletidas no workspace sem a necessidade de copiar os arquivos para o diretório `install`.

> **Nota:** a criação de novos arquivos ainda exige uma nova execução do `colcon build` para que eles sejam registrados no workspace de instalação.

### Sourcing

O workspace deve ser carregado em cada novo terminal:

```bash
source install/setup.bash
```

Opcionalmente, o comando pode ser adicionado ao `.bashrc` do contêiner.

Após o workspace ser compilado e carregado, o sistema está pronto para execução.

---

## 4. Operação e Visualização do Robô

A ativação do sistema segue uma hierarquia de dependências.

O `robot_state_publisher` (RSP) funciona como a **fonte da verdade cinemática** do robô, utilizando a descrição do robô para publicar as transformações **TF** e a descrição necessária pelos demais componentes.

### Execução do Sistema

#### Estado do Robô — Core

```bash
ros2 launch articubot_one rsp.launch.py
```

#### Simulação — Gazebo

```bash
ros2 launch articubot_one launch_sim.launch.py use_sim_time:=true
```

> `launch_sim.launch.py` normalmente encapsula a inicialização do `rsp.launch.py`.

#### Visualização — RViz2

```bash
rviz2 -d $(ros2 pkg prefix articubot_one)/share/articubot_one/config/drive_bot.rviz
```

### Interface de Controle e Diagnóstico

#### Joint State Publisher GUI

```bash
ros2 run joint_state_publisher_gui joint_state_publisher_gui
```

Útil para validar:

* hierarquia de frames;
* movimentação das juntas;
* limites físicos;
* comportamento cinemático do modelo.

#### Teleoperação

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Permite controlar diretamente uma base diferencial através de mensagens `Twist`, normalmente publicadas no tópico:

```text
/cmd_vel
```

Após validar a cinemática e o controle manual, o robô pode avançar para a camada de inteligência espacial.

---

## 5. Mapeamento e Navegação Autônoma — SLAM & Nav2

O **SLAM (Simultaneous Localization and Mapping)** converte os dados dos sensores, como LiDAR, em um mapa de ocupação probabilístico.

Essa camada permite que o robô:

* perceba o ambiente;
* construa um mapa;
* estime sua posição;
* planeje trajetórias;
* navegue de forma autônoma.

---

### Configuração de SLAM — `slam_toolbox`

Para iniciar o mapeamento em modo assíncrono:

```bash
ros2 launch slam_toolbox online_async.launch.py \
    params_file:=$(ros2 pkg prefix articubot_one)/share/articubot_one/config/mapper_params_online_async.yaml \
    use_sim_time:=true
```

---

### Stack de Navegação — Nav2

Para ativar o sistema de planejamento e recuperação:

```bash
ros2 launch nav2_bringup navigation.launch.py use_sim_time:=true
```

### Sincronização de Clock

Durante a simulação, o parâmetro:

```bash
use_sim_time:=true
```

deve ser utilizado pelos componentes que precisam acompanhar o relógio da simulação.

Isso mantém componentes como:

* Gazebo;
* SLAM;
* Nav2;
* TF;

sincronizados com o mesmo clock simulado.

Sem essa sincronização, podem ocorrer erros relacionados a timestamps e transformações TF.

### Visualização do Mapa no RViz

Ao visualizar o mapa no RViz2, verifique a política de durabilidade do tópico de mapa.

Para tópicos que utilizam retenção de mensagens, a política:

```text
Durability Policy: Transient Local
```

pode ser necessária para que o RViz receba o mapa mesmo quando a mensagem foi publicada antes da inicialização do próprio RViz.

---

## Conclusão

A arquitetura do **articubot_one** deve ser tratada como um sistema integrado, no qual infraestrutura, código, descrição física, simulação e navegação fazem parte do mesmo fluxo de desenvolvimento.

A combinação de:

* **Docker** para isolamento e reprodutibilidade;
* **Git** para controle de versão;
* **colcon** para compilação;
* **ROS 2** para comunicação entre componentes;
* **Gazebo** para simulação;
* **RViz2** para visualização e diagnóstico;
* **SLAM Toolbox** para mapeamento;
* **Nav2** para navegação autônoma;

permite iterar rapidamente sobre o robô mantendo o ambiente de desenvolvimento controlado e reproduzível.

> **Objetivo:** minimizar o tempo gasto corrigindo problemas de infraestrutura e maximizar o tempo dedicado ao desenvolvimento e refinamento dos algoritmos do robô.
