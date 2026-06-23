# Etapa 2: Ambiente de Simulação - Documentação Técnica

## 📋 Visão Geral

A Etapa 2 implementa um **ambiente de simulação completo** que:
- ✅ Renderiza o túnel em 2D com pygame
- ✅ Simula física realista (Newton)
- ✅ Emula sensores (LIDAR + Encoder) com ruído
- ✅ Comunica via MQTT com o sistema C++
- ✅ Fornece interface gráfica de visualização

## 🏗️ Arquitetura da Simulação

```
┌─────────────────────────────────────────────────────────┐
│                  CLIENTE MQTT (C++)                      │
│              (Controle PID + Threads)                    │
└──────────────────────┬──────────────────────────────────┘
                       │ MQTT Broker
                       │ (Mosquitto)
        ┌──────────────┴───────────────┐
        │ sensor/lidar                 │ actuator/aceleracao
        │ sensor/encoder               │ actuator/velocidade_setpoint
        │                              │
        ▼                              ▼
┌─────────────────────────────────────────────────────────┐
│        SIMULADOR PYTHON (simulator.py)                   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Renderizador Pygame                             │   │
│  │ - Túnel 2D                                      │   │
│  │ - Falhas estruturais                            │   │
│  │ - Posição do robô                               │   │
│  │ - Painel de informações                         │   │
│  └─────────────────────────────────────────────────┘   │
│                       △                                  │
│                       │ Dados de simulação               │
│                       │                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Motor de Física (FisicaRobo)                    │   │
│  │ - Aceleração (comando do C++)                   │   │
│  │ - Velocidade (integração)                       │   │
│  │ - Posição (integração)                          │   │
│  └─────────────────────────────────────────────────┘   │
│                       △                                  │
│                       │ Altura real                      │
│                       │                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Ambiente Túnel (Tunel)                          │   │
│  │ - Geometria base (altura 4m)                    │   │
│  │ - Falhas (buracos/saliências)                   │   │
│  │ - Função altura(x) → altura_real                │   │
│  └─────────────────────────────────────────────────┘   │
│                       △                                  │
│                       │ Leitura + ruído                  │
│                       │                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Sensores Simulados (SensorSimulado)             │   │
│  │ - LIDAR: altura_real → altura_ruidosa          │   │
│  │ - Encoder: detecção de mudança (1m)             │   │
│  └─────────────────────────────────────────────────┘   │
│                       △                                  │
│                       │ Publica via MQTT                 │
│                       │                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Cliente MQTT (ClienteMQTT)                      │   │
│  │ - Publica: sensor/lidar, sensor/encoder         │   │
│  │ - Subscreve: actuator/*                         │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 📦 Dependências

### Python
```bash
pip3 install -r requirements.txt
```

- **pygame**: Renderização gráfica 2D
- **paho-mqtt**: Cliente MQTT
- **numpy**: Operações numéricas (ruído, perfil gaussiano)

### Broker MQTT
```bash
docker-compose up -d  # Inicia Mosquitto
```

## 🚀 Como Usar

### 1. Setup Inicial (primeira vez)

```bash
# Navegar para o diretório do projeto
cd trabalho/tp-atr-2026-embodied-intelligence

# Instalar dependências
make install-sim

# Iniciar broker MQTT
make mqtt-broker-start
```

### 2. Executar o Simulador

**Terminal 1 - Simulador Gráfico:**
```bash
make simulator
```

Você verá:
- Túnel 2D renderizado
- Robô se movendo (quando receber comandos de aceleração)
- LIDAR simulado (linha vertical no robô)
- Painel de status com: tempo, FPS, posição, velocidade, encoder
- Indicador de conexão MQTT

### 3. Enviar Comandos ao Simulador (Modo Teste)

**Terminal 2 - Cliente MQTT Interativo:**
```bash
make mqtt-test
```

Comandos disponíveis:
```
a 0.5      → Acelerar com 0.5 m/s²
a -0.2     → Desacelerar com 0.2 m/s²
a 0        → Parar aceleração
v 3.0      → Definir velocidade setpoint em 3.0 m/s
status     → Ver status atual
sair       → Sair do cliente
```

**Exemplos de Teste:**

```bash
# Teste 1: Aceleração constante
a 0.5        # Acelera
sleep 10
a -0.3       # Desacelera
```

```bash
# Teste 2: Parar gradualmente
a -0.1       # Freio suave
sleep 30
```

### 4. Testes Automáticos

```bash
# Teste PID simulado (fase de aceleração + desaceleração)
make mqtt-test-pid

# Teste de rampa (aceleração gradual)
make mqtt-test-rampa
```

### 5. Monitorar Tópicos MQTT

```bash
# Terminal 3 - Monitor MQTT (requer mosquitto-clients)
make mqtt-monitor

# Saída:
# sensor/lidar {"timestamp": 1000, "distancia_y": 4.05, "nivel_confianca": 0.95}
# sensor/encoder {"timestamp": 1000, "estado": 1}
```

## 🎮 Controles Pygame

| Tecla | Ação |
|-------|------|
| **ESC** | Sair do simulador |
| **Botão fechar** | Sair do simulador |

## 📊 Tópicos MQTT

### Publicados (Simulador → Sistema C++)

#### `sensor/lidar`
```json
{
  "timestamp": 5000,          // ms desde o início
  "distancia_y": 4.05,        // metros (altura do teto)
  "nivel_confianca": 0.95     // 0.0-1.0
}
```
**Frequência:** 10 Hz (a cada 100ms)

#### `sensor/encoder`
```json
{
  "timestamp": 12000,
  "estado": 1                 // 0 ou 1 (alterna a cada metro)
}
```
**Frequência:** Sempre que há mudança de estado (a cada metro)

### Subscritos (Sistema C++ → Simulador)

#### `actuator/aceleracao`
```json
{
  "valor": 0.5                // m/s² (positivo = acelera, negativo = freia)
}
```

#### `actuator/velocidade_setpoint`
```json
{
  "valor": 2.5                // m/s (velocidade desejada)
}
```

## 🔬 Modelos Físicos Implementados

### 1. Física de Newton

```
x(t) = x₀ + v₀*t + ½*a*t²
v(t) = v₀ + a*t

Método: Euler Explícito
Δt = 0.1s (passo de simulação)
```

**Características:**
- Sem atrito (idealizado para túnel horizontal)
- Velocidade máxima limitada (segurança)
- Sem movimento reverso (robô não anda de ré)

### 2. Modelo de Ruído no LIDAR

```
h_medida = h_real + N(μ=0, σ=0.05m)

σ = 0.05m = 5cm (desv. padrão)
Quantização: arredonda para 0.01m
```

### 3. Geometria do Túnel

**Altura nominal:** 4.0 m

**Falhas pré-configuradas:**

| Posição | Tipo | Profundidade | Largura |
|---------|------|--------------|---------|
| 20m | Buraco | -0.8m | 2.0m |
| 50m | Saliência | +0.6m | 3.0m |
| 100m | Buraco | -1.2m | 4.0m |
| 150m | Saliência | +0.8m | 2.5m |

**Perfil de falha:** Gaussiano (suaviza transições)

```
profundidade(x) = prof_max * exp(-(Δx / (width/2))²)
```

### 4. Encoder

Muda de estado (0 ↔ 1) a cada **1 metro** percorrido.

## 📈 Visualização

### Painel de Informações (topo-esquerda)

```
Tempo: 12.5s
FPS: 29.8
Posição: 15.34m
Velocidade: 1.52m/s
Aceleração: 0.50m/s²
Encoder: 1
MQTT: 🟢 Conectado
```

### Renderização do Túnel

- **Linhas cinzas:** Paredes superior/inferior do túnel
- **Pontos vermelhos:** Falhas detectadas (buracos/saliências)
- **Retângulo verde:** Corpo do robô
- **Linha amarela:** Raio LIDAR (sensor virtual)
- **Câmera:** Segue o robô (mantém centralizado)

## 🐛 Troubleshooting

### "Erro de conexão MQTT"
```bash
# Verificar se broker está rodando
docker ps | grep mosquitto

# Se não está, iniciar:
make mqtt-broker-start

# Verificar logs do broker:
docker logs mqtt_broker_2026
```

### "ImportError: No module named 'pygame'"
```bash
pip3 install -r requirements.txt
```

### "Port 1883 already in use"
```bash
# Matar processo anterior:
docker-compose down

# Ou mudar porta no docker-compose.yml e ClienteMQTT
```

### Simulador lento ou travando
- Reduza a qualidade visual (aumente `step` em `_renderizar_tunel`)
- Aumente `DT` (passo de simulação) se o C++ não conseguir acompanhar
- Verifique CPU: `top` ou `htop`

## 🔗 Integração com Sistema C++

### Próxima Etapa: Publicar Aceleração do PID

No seu `controle.cpp`, após calcular a aceleração do PID:

```cpp
#include <paho-mqtt/cpp/client.h>

// Publicar no MQTT
json payload;
payload["valor"] = saida_controle;  // aceleração calculada

mqtt_client.publish("actuator/aceleracao", 
                   payload.dump(), 
                   1, false);
```

### Receber Dados dos Sensores

No seu `recontsupf.cpp` e `coletor.cpp`:

```cpp
// Subscrever a sensor/lidar
mqtt_client.subscribe("sensor/lidar");

// Callback recebe dados:
// {timestamp: X, distancia_y: Y, nivel_confianca: Z}
```

## 📝 Estrutura de Arquivos

```
trabalho/tp-atr-2026-embodied-intelligence/
├── simulator.py              ← Simulador principal
├── mqtt_test_client.py       ← Cliente de teste
├── requirements.txt          ← Dependências Python
├── docker-compose.yml        ← Configuração MQTT
├── mosquitto.conf            ← Config Mosquitto
├── Makefile                  ← Targets para simulador
├── src/
│   ├── main.cpp
│   ├── controle.cpp
│   ├── buffer.cpp
│   ├── coletor.cpp
│   └── recontsupf.cpp        ← PRÓXIMO: Integrar MQTT aqui
└── include/
    ├── controle.hpp
    ├── buffer.hpp
    ├── defs.hpp
    └── visao.hpp
```

## 🎯 Próximos Passos (Integração)

1. **Compilar sistema C++ com suporte a MQTT**
   - Instalar libpaho-mqtt-dev
   - Adicionar ao Makefile: `-I/usr/include/mqtt -lpaho-mqtt3c`

2. **Modificar `recontsupf.cpp`**
   - Conectar ao MQTT ao iniciar thread
   - Subscrever `sensor/lidar`
   - Usar altura medida no filtro

3. **Modificar `controle.cpp`**
   - Publicar `actuator/aceleração` após calcular PID

4. **Modificar `coletor.cpp`**
   - Subscrever `sensor/encoder`
   - Usar estado real do encoder

## 📚 Referências

- [Paho-MQTT Python](https://eclipse.dev/paho/index.php?page=clients/python/index.php)
- [Pygame Docs](https://www.pygame.org/docs/)
- [Mosquitto MQTT Broker](https://mosquitto.org/)
- [Newton's Laws](https://en.wikipedia.org/wiki/Newton%27s_laws_of_motion)

---

**Autor:** Sistema de Inspeção de Túneis 2026  
**Data de Criação:** Junho 2026  
**Status:** ✅ Etapa 2 Completa (Simulador Funcional)
