# 🚀 Quick Start - Etapa 2 Simulador

## Instalação Rápida (2 minutos)

### Opção 1: Setup Automático (RECOMENDADO)

```bash
cd trabalho/tp-atr-2026-embodied-intelligence

# Dar permissão de execução
chmod +x setup.sh

# Instalação completa (Python + Docker + MQTT)
./setup.sh --full
```

### Opção 2: Setup Manual

```bash
cd trabalho/tp-atr-2026-embodied-intelligence

# Instalar dependências
pip3 install -r requirements.txt

# Iniciar MQTT broker
docker-compose up -d
```

### Opção 3: Apenas Python (sem MQTT)

```bash
pip3 install -r requirements.txt
python3 simulator.py
```

---

## ▶️ Executar Simulador

**Terminal 1 - Simulador Gráfico:**
```bash
make simulator

# Ou:
python3 simulator.py
```

Você verá uma janela com:
- Túnel 2D renderizado
- Robô se movendo
- Painel de status (tempo, posição, velocidade, etc)

---

## 🎮 Enviar Comandos

**Terminal 2 - Cliente MQTT Interativo:**
```bash
make mqtt-test

# Ou:
python3 mqtt_test_client.py
```

Exemplo de comandos:
```
a 0.5      # Acelerar a 0.5 m/s²
a -0.2     # Desacelerar
a 0        # Parar aceleração
status     # Ver status
sair       # Sair
```

---

## 📊 Testar Automaticamente

```bash
# Teste 1: Simulação PID (30s acelera + 30s desacelera)
make mqtt-test-pid

# Teste 2: Rampa de velocidade gradual
make mqtt-test-rampa

# Teste 3: Monitor de tópicos MQTT
make mqtt-monitor
```

---

## 🔧 Verificar Status

```bash
# MQTT broker rodando?
docker-compose ps

# Logs do broker:
docker-compose logs -f mosquitto
```

---

## ⚙️ Customizar Simulação

Editar `simulator.py`:

```python
# Linha ~80: CONFIGURAÇÕES GLOBAIS

# Mudar altura do túnel:
TUNNEL_HEIGHT = 4.0  # metros

# Mudar velocidade máxima:
MAX_VELOCITY = 5.0   # m/s

# Mudar ruído do LIDAR:
SIGMA_RUIDO = 0.05   # 5cm desvio padrão

# Mudar frequência de simulação:
DT = 0.1             # 100ms
```

---

## 🛑 Parar Tudo

```bash
# Parar broker MQTT
docker-compose down

# Parar container (force):
docker-compose down -v
```

---

## ❓ Problemas?

### Erro: "Conexão recusada" (MQTT)
```bash
# Broker não está rodando:
make mqtt-broker-start

# Ou verificar:
docker ps | grep mosquitto
```

### Erro: "ModuleNotFoundError: pygame"
```bash
pip3 install -r requirements.txt
```

### Porta 1883 ocupada
```bash
# Matar processo:
docker-compose down

# Ou mudar porta no docker-compose.yml
```

---

## 📚 Documentação Completa

Ver [ETAPA2_SIMULADOR.md](ETAPA2_SIMULADOR.md)

---

## 🎯 Próximas Etapas

1. Compilar C++ com suporte a MQTT
2. Integrar `recontsupf.cpp` com sensor/lidar
3. Integrar `controle.cpp` com actuator/aceleracao
4. Testes de ciclo fechado

---

**Tempo médio:** ~30 minutos (primeira vez)  
**Tempo futuro:** ~5 minutos (apenas rodar simulador)
