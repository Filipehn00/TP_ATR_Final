readme_content = """# 🤖 Sistema Embarcado de Inspeção Automatizada de Túneis
## Trabalho Final de Automação em Tempo Real (ATR) — 2026/1
### Engenharia de Controle e Automação — UFMG

---

## 👥 Componentes do Grupo
* **Arthur Lemos** (Matrícula: 2023427414)
* **Filipe Nunes** (Matrícula: 2023038329)
* **Raymundo Marinho** (Matrícula: 2022082880)

* **Professor Orientador:** Leandro Freitas

---

## 📝 Visão Geral do Projeto
Este projeto consiste no desenvolvimento e na implementação de um **Sistema Ciber-Físico Distribuído** voltado para a inspeção estrutural autônoma de teto de túneis em planos 2D. O ecossistema visa mitigar riscos humanos em inspeções civis confinadas, automatizando a varredura por meio de sensores LIDAR virtuais e processamento pesado episódico simulado (Machine Learning/YOLO). 

A arquitetura de software é dividida em três pilares principais que se comunicam de forma assíncrona por rede através do protocolo **MQTT (Broker Mosquitto)**, isolando o núcleo rígido de processamento de controle das rotinas dinâmicas de interface gráfica.

---

## 🏛️ Arquitetura do Sistema e Critérios de Tempo Real

O ecossistema foi projetado distribuindo responsabilidades em processos paralelos com diferentes níveis de severidade temporal:

1. **Núcleo de Processamento de Controle (Core C++):**
   * **Papel:** Atua como o "Cérebro" lógico do robô de inspeção.
   * **Critério de Tempo Real:** *Hard Real-Time* na malha de controle de tração. Roda em uma thread cíclica periódica rígida de **100 ms** (`tarefa_controle`), onde atrasos de amostragem alteram drasticamente os diferenciais dinâmicos ($dt$) do controlador PID, gerando instabilidades físicas acumuladas.
   * **Concorrência Local:** Utiliza as primitivas POSIX nativas do C++17 (`std::thread`) para disparar as rotinas concorrentes: Reconstrução de Superfície, Coletor de Dados, Controle PID e Processamento da Carga da IA.

2. **Planta de Simulação Física (`simulator.py`):**
   * **Papel:** Modela as condições do mundo físico real (Planta). Desenvolvido em **Pygame**, renderiza o túnel procedural contínuo com anomalias (buracos e saliências geométricas) e injeta forças cinemáticas complexas (gravidade, massa do robô e atrito de rolamento).
   * **Critério de Tempo Real:** *Soft Real-Time*. Opera em taxa síncrona visual estável de 30 FPS.

3. **Sala de Controle / Painel Operador (`interface.py`):**
   * **Papel:** Interface Homem-Máquina (IHM) para monitoramento remoto do operador. Desenvolvida em **Pygame** para garantir total compatibilidade de renderização sob subsistemas Linux como o **WSL**, eliminando falhas de drivers gráficos nativos comuns do Tkinter.
   * **Critério de Tempo Real:** *Soft Real-Time*. O atraso ou descarte pontual de pacotes degrada o tempo de resposta do monitor flutuante, mas não compromete a segurança mecânica local do veículo.

---

## ⛓️ Mecanismos de ATR Implementados no Código

* **Exclusão Mútua (Thread-Safety):** Proteção de seções críticas através de travas exclusivas (`std::mutex`) acopladas ao conceito de RAII via `std::lock_guard`. Utilizado para evitar condições de corrida (*Race Conditions*) nas flags globais de detecção de anomalias acessadas simultaneamente pelas malhas de controle e de inspeção visual.
* **Sincronização Orientada a Eventos:** Implementação de `std::condition_variable` combinada com o método `.wait()` na thread de IA (`tarefa_inspecao_ia`). Isso garante economia estrita de CPU: a thread de inferência pesada permanece no estado *Blocked* consumindo 0% de processamento até que a thread de Reconstrução identifique um buraco e dispare um sinal de interrupção em software (`.notify_all()`), acordando a IA.
* **Desacoplamento por IPC em Rede:** Uso de buffers de sockets e tópicos assíncronos MQTT para garantir isolamento contra falhas elétricas ou de transmissão:
  * `sensor/lidar`: Escaneamento contínuo da distância ao teto.
  * `sensor/encoder`: Sinais digitais discretos de deslocamento de odometria.
  * `sensor/imu`: Ângulos de inclinação geográficos das rampas.
  * `actuator/aceleracao`: Comandos de torque calculados pelo PID enviado à planta.
  * `robo/telemetria`: Envio de strings estruturadas em formato JSON para a IHM Sala de Controle.
  * `robo/comandos`: Eventos discretos disparados por cliques de botões pelo operador.

---

## ⚠️ Limitações Técnicas Identificadas e Diagnósticos

Durante as fases finais de integração sistêmica com a simulação de dinâmica real, os seguintes comportamentos inadequados foram diagnosticados:

1. **Efeito de Recuo Mecânico Reverso (PID Over-Braking):** * *Sintoma:* Ao entrar em uma região de buraco ou saliência, o robô apresenta uma aceleração negativa severa e, em vez de estabilizar na velocidade reduzida de inspeção (1.0 m/s), ele sofre um empurrão para trás de forma instável.
   * *Diagnóstico:* O degrau abrupto imposto no setpoint do PID (de 5.0 m/s para 1.0 m/s) gera um erro instantâneo massivo. Multiplicado pelo ganho proporcional ($K_p$), a saída atinge a saturação mínima. Pela ausência de uma trava cinemática contínua integrada na simulação física para desacelerar até zerar, essa força inverte o sentido da velocidade do robô, provocando marcha ré indesejada. Há necessidade de acoplar rampas suaves de desaceleração e controle de *Anti-Windup*.
2. **Perda de Comandos Assíncronos na IHM (Saturação de I/O):**
   * *Sintoma:* Em modo de operação manual, alguns botões críticos (como a Parada de Emergência) exibem falhas intermitentes de acionamento ou são completamente ignorados pelo robô.
   * *Diagnóstico:* O loop C++ opera em alta velocidade computacional síncrona. Quando ocorrem altas taxas de processamento local, os callbacks assíncronos gerenciados pelas interrupções de I/O da biblioteca de rede acumulam-se na fila de buffers de sockets do Kernel do SO antes de conseguir espaço no escalonador para processamento na RAM, ocasionando o descarte lógico ou atraso de ordens críticas da IHM.

---

## 🛠️ Como Compilar e Executar (Automação IaC)

Para garantir total portabilidade do ecossistema em qualquer computador com sistema operacional Linux zerado (incluindo o subsistema **WSL**), implementou-se um conceito de **Idempotência** no `Makefile`. 

Com apenas um comando, o script checa as dependências do Kernel, instala via `apt` os pacotes de compilação C++, monta uma área Python virtualizada (`.venv`) isolada e roda todos os background processos sem risco de gerar processos zumbis ao fechar.

### Passo Único:
Abra o terminal do Ubuntu/WSL na pasta raiz do projeto e execute:
