# ============================================================================
# ORQUESTRADOR DE INSTALAÇÃO E EXECUÇÃO AUTOMÁTICA - ATR 2026
# ============================================================================

# Compilador e Flags C++
CXX = g++
CXXFLAGS = -Wall -std=c++17 -pthread -I./include -I/usr/include/paho $(shell pkg-config --cflags opencv4 2>/dev/null || echo "")
LDFLAGS = $(shell pkg-config --libs opencv4 2>/dev/null || echo "-lopencv_core -lopencv_dnn") -L/usr/lib -lpaho-mqtt3c

# Diretórios
SRC_DIR = src
OBJ_DIR = build
BIN_DIR = bin
TARGET = $(BIN_DIR)/robo_inspecao

# Python Environment local
VENV_DIR = .venv
PYTHON = $(VENV_DIR)/bin/python3

# Fontes e Objetos
SOURCES = $(wildcard $(SRC_DIR)/*.cpp)
OBJECTS = $(patsubst $(SRC_DIR)/%.cpp,$(OBJ_DIR)/%.o,$(SOURCES))

# ----------------------------------------------------------------------------
# 1. Regra Padrão (Garante que tudo seja instalado antes de compilar)
# ----------------------------------------------------------------------------
all: setup-env dir $(TARGET)

# Cria pastas físicas de organização do projeto
dir:
	@mkdir -p $(OBJ_DIR)
	@mkdir -p $(BIN_DIR)
	@mkdir -p logs

# ----------------------------------------------------------------------------
# 2. SISTEMA INTELIGENTE DE DEPLOY AUTOMÁTICO (Para Computadores Novos)
# ----------------------------------------------------------------------------
setup-env:
	@echo "🔍 Verificando integridade e dependências do sistema Linux..."
	@if [ ! -f /usr/include/MQTTClient.h ] || [ ! -d /usr/include/opencv4 ] || [ ! -f /usr/include/python3.*/Python.h ]; then \
		echo "⚠️  Dependências nativas ausentes! Instalando pacotes do Ubuntu (solicitando sudo)..."; \
		sudo apt update && sudo apt install -y g++ libpaho-mqtt-dev mosquitto mosquitto-clients \
		libopencv-dev python3-dev python3-tk python3-pip python3-venv libsdl2-dev pkg-config; \
		sudo systemctl enable mosquitto && sudo systemctl start mosquitto; \
	else \
		echo "✓ Pacotes APT do sistema operacional já estão ok."; \
	fi
	@if [ ! -d $(VENV_DIR) ]; then \
		echo "📦 Criando ambiente isolado Python (.venv)..."; \
		python3 -m venv $(VENV_DIR); \
		$(PYTHON) -m pip install --upgrade pip; \
		echo "🐍 Instalando bibliotecas gráficas e de redes (Pygame, CustomTkinter, Paho)..."; \
		$(PYTHON) -m pip install pygame customtkinter paho-mqtt numpy; \
	else \
		echo "✓ Ambiente Python (.venv) já está configurado."; \
	fi
	@echo "🎯 Sistema pronto para compilação e execução!"

# ----------------------------------------------------------------------------
# 3. Compilação do Binário Core
# ----------------------------------------------------------------------------
$(TARGET): $(OBJECTS)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -rf $(OBJ_DIR) $(BIN_DIR) logs

# ----------------------------------------------------------------------------
# 4. COMANDO ÚNICO SUPREMO DE APRESENTAÇÃO
# ----------------------------------------------------------------------------
# Compila o C++, levanta o Pygame interativo e abre o Supervisório IHM remodelado
# Executa o simulador gráfico, o supervisório remoto na raiz e o cérebro C++ nativamente
# Executa o simulador do robô, a IHM remota e o cérebro C++ em duas janelas isoladas no WSL
# Executa as duas janelas Pygame isoladas e o cérebro C++ juntos nativamente
run-all: all
	@echo "🚀 INICIALIZANDO ECOSSISTEMA COMPLETO DE DUAS JANELAS..."
	@mkdir -p logs
	@echo "[SO-Background] Lançando Planta Física do Túnel..."
	@$(PYTHON) simulator.py & SIM_PID=$$! ; \
	echo "[SO-Background] Lançando IHM Sala de Controle..." ; \
	$(PYTHON) interface.py & INT_PID=$$! ; \
	echo "[SO-Foreground] Executando Cérebro de Tempo Real em C++..." ; \
	./$(TARGET) ; \
	echo "⏹️  Limpando processos..." ; \
	kill $$SIM_PID $$INT_PID 2>/dev/null || true

.PHONY: all dir clean setup-env run-all