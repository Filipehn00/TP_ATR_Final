# ✅ Checklist de Verificação - Etapa 2

Use este checklist para verificar se tudo está funcionando corretamente.

## ✅ Pré-requisitos

- [ ] Python 3.7+ instalado (`python3 --version`)
- [ ] pip3 instalado (`pip3 --version`)
- [ ] Docker instalado (`docker --version`)
- [ ] Docker Compose instalado (`docker-compose --version`)

## ✅ Instalação

- [ ] Navegou para `trabalho/tp-atr-2026-embodied-intelligence`
- [ ] Executou `chmod +x setup.sh`
- [ ] Executou `./setup.sh --full` com sucesso
- [ ] Viu mensagem "Setup Completo Finalizado!"

## ✅ Broker MQTT

- [ ] `docker-compose ps` mostra `mqtt_broker_2026` rodando
- [ ] `docker logs mqtt_broker_2026` não mostra erros
- [ ] Porta 1883 acessível: `nc -zv localhost 1883`

## ✅ Dependências Python

- [ ] `pip3 list | grep pygame` mostra pygame instalado
- [ ] `pip3 list | grep paho` mostra paho-mqtt instalado
- [ ] `pip3 list | grep numpy` mostra numpy instalado

## ✅ Arquivos Necessários

- [ ] `simulator.py` existe
- [ ] `mqtt_test_client.py` existe
- [ ] `mqtt_monitor.py` existe
- [ ] `requirements.txt` existe
- [ ] `docker-compose.yml` existe
- [ ] `config.yml` existe

## ✅ Testes Automatizados

```bash
python3 test_simulador.py
```

Verificar:
- [ ] Teste 0: Dependências - ✅
- [ ] Teste 1: Conectividade MQTT - ✅
- [ ] Teste 2: Física - ✅
- [ ] Teste 3: Sensores - ✅
- [ ] Teste 4: Pygame - ✅
- [ ] Teste 5: Arquivos - ✅
- [ ] Teste 6: Configuração - ✅

## ✅ Teste Manual - Simulador

**Terminal 1:**
```bash
python3 simulator.py
```

Verificar:
- [ ] Janela pygame abre (1400x600)
- [ ] Túnel renderizado em cinza
- [ ] Robô verde no centro
- [ ] Painel de informações aparece (top-left)
- [ ] Mensagem "MQTT: 🟢 Conectado" (se broker rodando)
- [ ] Sem erros de Python

**Esperado:**
```
[SIM] Iniciando Simulador de Inspeção de Túneis...
[SIM] Tentando conectar ao MQTT broker em localhost:1883...
[MQTT] Conectado ao broker!
```

## ✅ Teste Manual - Cliente MQTT

**Terminal 2:**
```bash
python3 mqtt_test_client.py
```

Verificar:
- [ ] Script conecta ao broker
- [ ] Menu de comandos aparece
- [ ] Prompt `Comando>` ativo

**Digite:**
```
a 0.5
```

Verificar no Terminal 1:
- [ ] Robô começa a se mover (para direita)
- [ ] Velocidade aumenta (painel mostra v > 0)
- [ ] Altura muda conforme robô passa por falhas

**Digite:**
```
status
```

Verificar:
- [ ] Status do cliente aparece
- [ ] Mostra última leitura LIDAR
- [ ] Mostra último estado encoder

**Digite:**
```
sair
```

## ✅ Teste Manual - Monitor MQTT

**Terminal 3:**
```bash
python3 mqtt_monitor.py
```

Verificar:
- [ ] Monitor conecta ao broker
- [ ] Mostra "Conectado ao broker!"
- [ ] Lista tópicos monitorados

**Enquanto Terminal 1 (simulador) está rodando:**
- [ ] Aparecem mensagens de `📏 LIDAR`
- [ ] Aparecem mensagens de `⏱️ ENCODER` (a cada metro)
- [ ] Mostra valores realistas (altura ~4m)

## ✅ Teste Integrado

**Execute em 3 terminais simultaneamente:**

Terminal 1: `python3 simulator.py`
Terminal 2: `python3 mqtt_test_client.py`
Terminal 3: `python3 mqtt_monitor.py`

**Sequência de teste:**
```
# Terminal 2
a 0.5          # Robô começa a acelerar
sleep 5
a -0.2         # Robô desacelera
sleep 10
a 0            # Robô para
status         # Ver status final
```

**Verificações:**
- [ ] Terminal 1: Robô se move suavemente
- [ ] Terminal 2: Recebe leituras de LIDAR
- [ ] Terminal 2: Mostra mudança de encoder (~a cada 1m)
- [ ] Terminal 3: Mostra dados sendo publicados
- [ ] Sem travamentos
- [ ] Sem mensagens de erro

## ✅ Teste de Performance

```bash
# Durante execução do simulador
top -p $(pgrep -f simulator.py)
```

Verificar:
- [ ] CPU: < 15%
- [ ] MEM: < 100 MB
- [ ] Sem picos excessivos

## ✅ Teste Offline (sem MQTT)

**Terminal 1:**
Parar broker: `docker-compose down`

**Terminal 2:**
```bash
python3 simulator.py
```

Verificar:
- [ ] Simulador inicia normalmente
- [ ] Painel mostra "MQTT: 🔴 Desconectado"
- [ ] Sem mensagens de erro MQTT
- [ ] Simulador roda em modo offline

## ✅ Teste de Setup.sh Completo

```bash
# Remover tudo
docker-compose down -v
pip3 uninstall -y pygame paho-mqtt numpy

# Executar setup novamente
./setup.sh --full
```

Verificar:
- [ ] Setup detecta dependências faltantes
- [ ] Instala tudo automaticamente
- [ ] Broker inicia com sucesso
- [ ] Testes passam

## ✅ Teste Modes Automáticos

**Teste PID:**
```bash
python3 mqtt_test_client.py --modo pid --duracao 30
```

Verificar:
- [ ] Executa 30 segundos
- [ ] Fase 1 (0-15s): acelera (a=0.5)
- [ ] Fase 2 (15-30s): desacelera (a=-0.2)

**Teste Rampa:**
```bash
python3 mqtt_test_client.py --modo rampa --duracao 20
```

Verificar:
- [ ] Aceleração aumenta gradualmente
- [ ] De a=0 até a=1.0 m/s²
- [ ] Duração total: 20s

## ✅ Teste de Documentação

- [ ] [QUICKSTART.md](QUICKSTART.md) - Legível e completo
- [ ] [ETAPA2_SIMULADOR.md](ETAPA2_SIMULADOR.md) - Detalhado
- [ ] [TECHNICAL_NOTES.md](TECHNICAL_NOTES.md) - Bem escrito
- [ ] [README.md](README.md) - Atualizado

## ✅ Teste Makefile

```bash
make help
```

Verificar todos os targets aparecem:
- [ ] `make simulator`
- [ ] `make mqtt-test`
- [ ] `make mqtt-test-pid`
- [ ] `make mqtt-monitor`
- [ ] `make mqtt-broker-start`
- [ ] `make mqtt-broker-stop`
- [ ] `make install-sim`
- [ ] `make setup-simulator`

## ✅ Teste de Configuração

```bash
cat config.yml | head -20
```

Verificar:
- [ ] Arquivo válido YAML
- [ ] Tem seções: mqtt, fisica, sensores, tunel, graficos
- [ ] Sem erros de sintaxe

## ✅ Limpeza Pós-Testes

```bash
# Parar tudo
docker-compose down

# Verificar tudo parou
docker ps | grep mqtt  # Deve estar vazio
pgrep python3 | grep -E "simulator|mqtt" # Deve estar vazio
```

Verificar:
- [ ] Não há processos orphans
- [ ] Containers parados
- [ ] Sem uso excessivo de porta 1883

---

## 📊 Resultado Final

Se todos os testes acima passarem:

✅ **ETAPA 2 VALIDADA E FUNCIONAL!**

Simulador pronto para:
- Desenvolvimento de algoritmos de controle
- Testes de sensores
- Validação de física
- Integração com sistema C++

---

## 🆘 Se algo falhar

1. Consulte [QUICKSTART.md](QUICKSTART.md)
2. Verifique [ETAPA2_SIMULADOR.md](ETAPA2_SIMULADOR.md) - Troubleshooting
3. Rode `python3 test_simulador.py --verbose`
4. Verifique logs: `docker-compose logs -f mosquitto`

---

**Último teste:** [data/hora]  
**Status:** ✅ COMPLETO / ❌ FALHOU
