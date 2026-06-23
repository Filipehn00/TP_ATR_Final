# 🤖 Sistema de Inspeção de Integridade Estrutural (tp-atr-2026-embodied-intelligence)

## 📋 Objetivo

Desenvolver um sistema de inspeção de integridade estrutural para mapear o perfil do teto de um túnel, detectando anomalias superficiais (buracos/saliências) que podem indicar riscos estruturais.

---

## 🏗️ Arquitetura do Projeto

```
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 1: Sistema de Controle (C++)                        │
│  - Controle PID (navegação do robô)                        │
│  - Reconstrução 3D (LIDAR + processamento)                │
│  - Inspeção por IA (análise de imagens)                   │
│  - Buffer thread-safe para sensores                       │
└─────────────────────────────────────────────────────────────┘
                           │
                      [MQTT Broker]
                           │
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 2: Simulador Python                                  │
│  - Renderização 2D do túnel (Pygame)                       │
│  - Física realista (Newton)                                │
│  - Sensores simulados (LIDAR + Encoder)                   │
│  - Comunicação MQTT com sistema C++                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Etapas do Projeto

### ✅ Etapa 1: Sistema de Controle e Processamento (COMPLETA)

**Arquivos:**
- `src/controle.cpp` - Controlador PID com compensação de gravidade (IMU)
- `src/recontsupf.cpp` - Processamento LIDAR com filtro média móvel
- `src/cargaia.cpp` - Simulação de carga computacional (IA)
- `src/coletor.cpp` - Coleta e logging de dados em arquivo
- `src/buffer.cpp` - Buffer thread-safe com condition_variable

**Recursos:**
- Threads sincronizadas (pthreads)
- Condition variables para sincronização de eventos
- Detector de anomalias estruturais
- Logging em arquivo (`logs/dados_inspecao.txt`)

---

### ✅ Etapa 2: Simulador e Ambiente Virtual (COMPLETA)

**Componentes:**

#### 1️⃣ Simulador Gráfico (`simulator.py`)
- **Renderização:** Pygame 2D com túnel, robô e falhas
- **Física:** Integração numérica de Newton (Euler)
- **Sensores:** LIDAR com ruído gaussiano + Encoder
- **Comunicação:** Cliente MQTT integrado
- **Status:** Painel de informações em tempo real

#### 2️⃣ Cliente MQTT de Teste (`mqtt_test_client.py`)
- Modo interativo para controlar manualmente
- Modo PID automático (30s acelerando + 30s freando)
- Modo rampa (aceleração gradual)
- Recepção de dados de sensores

#### 3️⃣ Monitor MQTT (`mqtt_monitor.py`)
- Visualização em tempo real dos tópicos
- Análise de frequência de mensagens
- Formatação legível das leituras

#### 4️⃣ Broker MQTT (Docker)
- Mosquitto lightweight
- Configuração pronta em `docker-compose.yml`
- Persistence ativada
- Logging detalhado

**Arquivos de Documentação:**
- `QUICKSTART.md` - Guia de início rápido (2 minutos)
- `ETAPA2_SIMULADOR.md` - Documentação técnica completa
- `TECHNICAL_NOTES.md` - Decisões de design e validação
- `config.yml` - Parâmetros customizáveis

---

## 🚀 Quick Start

### Instalação Rápida (5 minutos)

```bash
# 1. Navegar ao diretório
cd trabalho/tp-atr-2026-embodied-intelligence

# 2. Setup automático (recomendado)
chmod +x setup.sh
./setup.sh --full

# Ou instalação manual:
pip3 install -r requirements.txt
docker-compose up -d
```

### Executar Simulação

**Terminal 1 - Simulador Gráfico:**
```bash
make simulator
# Ou: python3 simulator.py
```

**Terminal 2 - Cliente Interativo:**
```bash
make mqtt-test
# Ou: python3 mqtt_test_client.py
```

**Terminal 3 - Monitor (opcional):**
```bash
python3 mqtt_monitor.py
```

### Comando Exemplos no Cliente

```
a 0.5      # Acelerar
a -0.3     # Desacelerar
a 0        # Parar
status     # Ver status
sair       # Sair
```

---

## 📊 Tópicos MQTT

### Publicados (Simulador → C++)

| Tópico | Frequência | Payload |
|--------|-----------|---------|
| `sensor/lidar` | 10 Hz | `{timestamp, distancia_y, nivel_confianca}` |
| `sensor/encoder` | Mudança | `{timestamp, estado}` |

### Subscritos (C++ → Simulador)

| Tópico | Payload |
|--------|---------|
| `actuator/aceleracao` | `{valor}` (m/s²) |
| `actuator/velocidade_setpoint` | `{valor}` (m/s) |

---

## 🛠️ Targets Disponíveis

```bash
make help              # Ver todos os targets

# Compilação C++
make                   # Compilar sistema
make run               # Compilar e executar
make clean             # Limpar

# Simulador Python
make install-sim       # Instalar dependências
make simulator         # Executar simulador
make mqtt-test         # Cliente interativo
make mqtt-test-pid     # Teste automático
make mqtt-monitor      # Monitorar MQTT

# Docker/MQTT
make mqtt-broker-start # Iniciar Mosquitto
make mqtt-broker-stop  # Parar Mosquitto
make mqtt-broker-status # Ver status

# Setup
make setup-simulator   # Instalação completa
```

---

## 📁 Estrutura de Arquivos

```
tp-atr-2026-embodied-intelligence/
├── 📄 README.md                    (este arquivo)
├── 📄 Makefile                     (targets para compilação e simulador)
├── 📄 QUICKSTART.md               (início rápido)
├── 📄 ETAPA2_SIMULADOR.md         (documentação técnica completa)
├── 📄 TECHNICAL_NOTES.md          (decisões de design)
│
├── 🐍 Python (Etapa 2)
│   ├── simulator.py               (simulador principal)
│   ├── mqtt_test_client.py        (cliente MQTT)
│   ├── mqtt_monitor.py            (monitor em tempo real)
│   ├── requirements.txt           (dependências Python)
│   └── config.yml                 (configuração simulador)
│
├── 🐳 Docker (MQTT)
│   ├── docker-compose.yml         (orquestração)
│   └── mosquitto.conf             (config Mosquitto)
│
├── 📜 Scripts
│   └── setup.sh                   (setup automático)
│
├── 📂 include/ (Headers C++)
│   ├── controle.hpp
│   ├── buffer.hpp
│   ├── coletor.hpp
│   ├── defs.hpp
│   └── visao.hpp
│
├── 📂 src/ (Código-fonte C++)
│   ├── main.cpp                   (orquestração)
│   ├── controle.cpp               (PID + IMU)
│   ├── buffer.cpp                 (fila thread-safe)
│   ├── coletor.cpp                (logging)
│   ├── recontsupf.cpp             (LIDAR + processamento)
│   ├── cargaia.cpp                (simulação IA)
│   └── yolo.cpp                   (placeholder YOLO)
│
├── 📂 bin/
│   └── robo_inspecao              (executável compilado)
│
├── 📂 build/                       (objetos compilados)
│
└── 📂 logs/
    └── dados_inspecao.txt         (arquivo de log)
```

---

## 🔍 Componentes da Etapa 2

### 1. Física (Newton's Laws)

```
v(t+dt) = v(t) + a(t) * dt
x(t+dt) = x(t) + v(t+dt) * dt

Método: Euler Explícito
dt = 0.1s (10 Hz)
Erro: O(dt) = ~1% para dt=0.1s
```

### 2. Sensores

**LIDAR:**
- Altura do teto com ruído Gaussiano
- σ = 0.05m (5cm desvio padrão)
- Quantização: 1cm

**Encoder:**
- Muda de estado (0 ↔ 1) a cada 1 metro
- Publicado somente em mudança

### 3. Túnel

**Altura nominal:** 4.0 m

**Falhas pré-configuradas:**
- 20m: Buraco -0.8m (2m largo)
- 50m: Saliência +0.6m (3m largo)
- 100m: Buraco -1.2m (4m largo)
- 150m: Saliência +0.8m (2.5m largo)

### 4. Visualização

- Renderização 2D em Pygame
- Câmera segue robô (1/3 da tela)
- Painel de informações (tempo, FPS, posição, velocidade, encoder)
- Raio LIDAR visível
- Falhas destacadas em cores

---

## 📋 Dependências

### C++
```
- g++17 ou superior
- pthreads
- OpenCV 4.5+
```

### Python
```
- Python 3.7+
- pygame >= 2.1.0
- paho-mqtt >= 1.6.1
- numpy >= 1.21.0
```

### Docker
```
- Docker 20.10+
- Docker Compose 1.29+
```

---

## 🧪 Testes de Validação

### Teste 1: Aceleração Constante
```bash
# Cliente:
a 0.5
# Esperado: robô acelera linearmente
# Verificar: v ∝ t, x ∝ t²
```

### Teste 2: Freio
```bash
# Cliente:
a -0.3
# Esperado: robô desacelera e para
```

### Teste 3: LIDAR com Ruído
```bash
# Monitor:
# Altura flutua em torno de 4.0m ± 0.05m
```

### Teste 4: Encoder
```bash
# Monitor:
# Estado muda a cada 1m (visível no log)
```

---

## 🐛 Troubleshooting

| Problema | Solução |
|----------|---------|
| "Conexão MQTT recusada" | `docker-compose up -d` |
| "ModuleNotFoundError: pygame" | `pip3 install -r requirements.txt` |
| "Port 1883 already in use" | `docker-compose down` |
| "Simulador travado" | Verifique CPU com `top` |
| "Sem permissão: setup.sh" | `chmod +x setup.sh` |

---

## 📚 Documentação

1. **[QUICKSTART.md](QUICKSTART.md)** ⚡ - Setup em 2 minutos
2. **[ETAPA2_SIMULADOR.md](ETAPA2_SIMULADOR.md)** 📖 - Documentação técnica completa
3. **[TECHNICAL_NOTES.md](TECHNICAL_NOTES.md)** 🔬 - Decisões de design e validação

---

## 🎯 Próximas Etapas (Etapa 3+)

- [ ] Integração C++ com MQTT (libpaho-mqtt)
- [ ] Publicar aceleração do PID no MQTT
- [ ] Subscrever sensor/lidar no C++
- [ ] Testes de ciclo fechado
- [ ] Integração com sistema real de hardware

---

## 📞 Contato e Suporte

**Projeto:** tp-atr-2026-embodied-intelligence  
**Disciplina:** ATR (Atividades Técnicas em Robótica)  
**Data:** Junho 2026  
**Status:** ✅ Etapa 1 e 2 Completas

---

## 📄 Licença

Este projeto é fornecido como-é para fins educacionais.

---

**Última atualização:** Junho 2026 ✨
