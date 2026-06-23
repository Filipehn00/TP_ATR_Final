#!/bin/bash
#
# Setup Script - Etapa 2 Simulador
# ================================
#
# Automatiza a instalação e configuração do simulador de túneis
#
# Uso:
#   chmod +x setup.sh
#   ./setup.sh [--help | --minimal | --full]
#

set -e  # Sair em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções auxiliares
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ${NC}  $1"
}

print_success() {
    echo -e "${GREEN}✓${NC}  $1"
}

print_error() {
    echo -e "${RED}✗${NC}  $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        return 1
    fi
    return 0
}

VENV_DIR=".venv"
PYTHON="python3"

prepare_python_env() {
    if ! $PYTHON -m pip --version >/dev/null 2>&1; then
        print_warning "pip não está disponível no python3. Verificando ambiente..."
    fi

    print_info "Atualizando pip..."
    if ! $PYTHON -m pip install --upgrade pip >/dev/null 2>&1; then
        print_warning "Ambiente Python gerenciado detectado. Criando virtualenv local em $VENV_DIR"
        if [ ! -d "$VENV_DIR" ]; then
            if ! $PYTHON -m venv --help >/dev/null 2>&1; then
                print_error "O módulo python3-venv não está disponível. Instale com: sudo apt-get install python3-venv"
                exit 1
            fi
            $PYTHON -m venv "$VENV_DIR"
            print_success "Virtualenv criado em $VENV_DIR"
        fi
        PYTHON="$PWD/$VENV_DIR/bin/python3"
        print_info "Usando Python do virtualenv: $PYTHON"
        $PYTHON -m pip install --upgrade pip
    else
        print_success "pip atualizado"
    fi
}

pull_mosquitto_image() {
    print_info "Verificando imagem Mosquitto..."
    if docker image inspect eclipse-mosquitto:latest >/dev/null 2>&1; then
        print_success "Imagem Mosquitto já disponível localmente"
        return 0
    fi

    print_info "Baixando imagem Mosquitto..."
    set +e
    output=$(docker pull eclipse-mosquitto:latest 2>&1)
    status=$?
    set -e

    if [ $status -eq 0 ]; then
        print_success "Imagem Mosquitto baixada com sucesso"
        return 0
    fi

    print_warning "Falha ao baixar a imagem Mosquitto"
    echo "$output" | grep -q -i 'network is unreachable' && {
        print_warning "O erro indica problema de rede/IPv6 ao acessar o Docker Hub"
        echo -e "${YELLOW}Tente usar IPv4 ou desativar IPv6 temporariamente:${NC}"
        echo "  sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1"
        echo "  sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1"
        echo "  sudo sysctl -w net.ipv6.conf.lo.disable_ipv6=1"
        echo "Depois execute novamente: docker pull eclipse-mosquitto:latest"
    }

    echo "$output"
    return 1
}

# Programa principal
main() {
    local modo="${1:---full}"
    
    case "$modo" in
        --help)
            show_help
            exit 0
            ;;
        --minimal)
            setup_minimal
            ;;
        --full)
            setup_full
            ;;
        *)
            print_error "Opção desconhecida: $modo"
            show_help
            exit 1
            ;;
    esac
}

show_help() {
    cat << 'EOF'
Setup Script - Etapa 2 Simulador

Opções:
  --help      Mostrar esta ajuda
  --minimal   Instalação mínima (apenas Python)
  --full      Instalação completa (Python + MQTT com Docker)

Exemplos:
  ./setup.sh --full      # Instalação completa (recomendado)
  ./setup.sh --minimal   # Apenas dependências Python
EOF
}

setup_minimal() {
    print_header "Setup Mínimo - Instalando Python e dependências"
    
    # Verificar Python3
    if ! check_command python3; then
        print_error "Python 3 não encontrado. Instale com:"
        echo "  sudo apt-get install python3 python3-pip"
        exit 1
    fi
    print_success "Python 3 encontrado: $(python3 --version)"
    
    # Atualizar pip e preparar ambiente Python
    prepare_python_env
    
    # Instalar dependências Python
    print_info "Instalando dependências Python..."
    if [ -f "requirements.txt" ]; then
        $PYTHON -m pip install -r requirements.txt
        print_success "Dependências Python instaladas"
    else
        print_error "requirements.txt não encontrado no diretório atual"
        exit 1
    fi
    
    print_header "Setup Mínimo Completo!"
    echo -e "${GREEN}Próximo passo:${NC}"
    echo "  python3 simulator.py"
}

setup_full() {
    print_header "Setup Completo - Instalando tudo"
    
    # 1. Verificar Python3
    if ! check_command python3; then
        print_error "Python 3 não encontrado. Instale com:"
        echo "  sudo apt-get install python3 python3-pip"
        exit 1
    fi
    print_success "Python 3 encontrado: $(python3 --version)"
    
    # 2. Verificar Docker
    if ! check_command docker; then
        print_warning "Docker não encontrado!"
        echo -e "${YELLOW}Para instalar Docker:${NC}"
        echo "  https://docs.docker.com/engine/install/"
        echo ""
        echo "Continuando apenas com Python (sem MQTT broker)..."
        echo ""
        setup_minimal
        return
    fi
    print_success "Docker encontrado: $(docker --version)"
    
    # 3. Verificar Docker Compose
    if ! check_command docker-compose; then
        print_warning "Docker Compose não encontrado!"
        echo -e "${YELLOW}Para instalar:${NC}"
        echo "  sudo apt-get install docker-compose"
        echo ""
        echo "Continuando apenas com Python..."
        setup_minimal
        return
    fi
    print_success "Docker Compose encontrado: $(docker-compose --version)"
    
    # 4. Instalar dependências Python
    prepare_python_env
    
    print_info "Instalando dependências Python..."
    if [ -f "requirements.txt" ]; then
        $PYTHON -m pip install -r requirements.txt
        print_success "Dependências Python instaladas"
    else
        print_error "requirements.txt não encontrado"
        exit 1
    fi
    
    # 5. Verificar Docker Compose file
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml não encontrado"
        exit 1
    fi
    print_success "docker-compose.yml encontrado"
    
    # 6. Verificar se mosquitto.conf existe
    if [ ! -f "mosquitto.conf" ]; then
        print_error "mosquitto.conf não encontrado"
        exit 1
    fi
    print_success "mosquitto.conf encontrado"
    
    # 7. Tentar baixar imagem Mosquitto e iniciar MQTT broker
    if ! pull_mosquitto_image; then
        print_warning "Não foi possível baixar a imagem Mosquitto. O broker pode não iniciar."
        print_info "Se você já tiver a imagem localmente, confirme com: docker image ls | grep eclipse-mosquitto"
    fi

    print_info "Iniciando MQTT broker (Mosquitto)..."
    if docker-compose up -d 2>/dev/null; then
        print_success "MQTT broker iniciado"
        echo ""
        print_info "Aguardando broker ficar pronto (3s)..."
        sleep 3
    else
        print_warning "Falha ao iniciar MQTT com Docker Compose"
        print_info "Verifique: docker ps"
        print_info "Se o pull falhou, corrija a conectividade com Docker Hub e tente novamente"
    fi
    
    # 8. Verificar conectividade MQTT
    print_info "Testando conectividade MQTT..."
    if check_mqtt_connection; then
        print_success "MQTT broker respondendo em localhost:1883"
    else
        print_warning "Não foi possível conectar ao MQTT broker"
        echo -e "${YELLOW}Possíveis causas:${NC}"
        echo "  1. Docker não está rodando"
        echo "  2. Conflito de porta 1883"
        echo "  3. Compose não iniciou corretamente"
        echo ""
        echo -e "${YELLOW}Debug:${NC}"
        echo "  docker-compose logs mosquitto"
        echo "  docker-compose ps"
    fi
    
    print_header "Setup Completo Finalizado!"
    echo -e "${GREEN}Próximos passos:${NC}"
    echo ""
    echo "1. Iniciar simulador (terminal 1):"
    echo "   python3 simulator.py"
    echo ""
    echo "2. Cliente MQTT (terminal 2):"
    echo "   python3 mqtt_test_client.py"
    echo ""
    echo -e "${YELLOW}Ou use os targets do Makefile:${NC}"
    echo "  make simulator"
    echo "  make mqtt-test"
    echo "  make mqtt-broker-status"
}

check_mqtt_connection() {
    # Tenta conectar ao MQTT usando python
    python3 << 'PYTHON_EOF'
import socket
import sys

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('localhost', 1883))
    sock.close()
    sys.exit(0 if result == 0 else 1)
except:
    sys.exit(1)
PYTHON_EOF
    return $?
}

# Executar programa principal
main "$@"
