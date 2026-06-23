#include "mqtt_client.hpp"
#include <iostream>
#include <cstring>
#include <cstdlib>
#include <cctype>
#include <algorithm>
#include "controle.hpp"

MQTTClientWrapper::MQTTClientWrapper(const std::string& host, int port)
    : broker_uri("tcp://" + host + ":" + std::to_string(port)),
      client_id("robo_inspecao_cpp"),
      client(nullptr),
      conectado(false),
      ultimo_lidar(0.0),
      ultimo_encoder(false) {
    MQTTClient_create(&client, broker_uri.c_str(), client_id.c_str(), MQTTCLIENT_PERSISTENCE_NONE, nullptr);
    MQTTClient_setCallbacks(client, this, on_connection_lost, on_message_arrived, nullptr);
}

MQTTClientWrapper::~MQTTClientWrapper() {
    desconectar();
}

bool MQTTClientWrapper::conectar() {
    MQTTClient_connectOptions conn_opts = MQTTClient_connectOptions_initializer;
    conn_opts.keepAliveInterval = 20;
    conn_opts.cleansession = 1;

    int rc = MQTTClient_connect(client, &conn_opts);
    if (rc != MQTTCLIENT_SUCCESS) {
        std::cerr << "[MQTT-C++] Erro ao conectar: " << rc << std::endl;
        return false;
    }

    conectado.store(true);
    MQTTClient_subscribe(client, "sensor/lidar", 1);
    MQTTClient_subscribe(client, "sensor/encoder", 1);
    MQTTClient_subscribe(client, "robo/comandos", 1); // Linha adicionada para assinar a interface
    MQTTClient_subscribe(client, "robo/parametros", 1);
    MQTTClient_subscribe(client, "actuator/velocidade_setpoint", 1); // linha adicionada para consertar o ajuste da vel na IHM
    return true;
}

void MQTTClientWrapper::desconectar() {
    if (conectado.load()) {
        MQTTClient_disconnect(client, 1000);
        MQTTClient_destroy(&client);
        conectado.store(false);
    }
}

bool MQTTClientWrapper::publicar_aceleracao(double aceleracao) {
    std::string msg = "{\"valor\": " + std::to_string(aceleracao) + "}";

    MQTTClient_message pubmsg = MQTTClient_message_initializer;
    pubmsg.payload = (void*)msg.c_str();
    pubmsg.payloadlen = static_cast<int>(msg.size());
    pubmsg.qos = 1;
    pubmsg.retained = 0;

    MQTTClient_deliveryToken token;
    int rc = MQTTClient_publishMessage(client, "actuator/aceleracao", &pubmsg, &token);
    if (rc != MQTTCLIENT_SUCCESS) {
        std::cerr << "[MQTT-C++] Falha ao publicar aceleracao: " << rc << std::endl;
        return false;
    }
    MQTTClient_waitForCompletion(client, token, 1000);
    return true;
}

bool MQTTClientWrapper::publicar_velocidade_setpoint(double velocidade) {
    std::string msg = "{\"valor\": " + std::to_string(velocidade) + "}";

    MQTTClient_message pubmsg = MQTTClient_message_initializer;
    pubmsg.payload = (void*)msg.c_str();
    pubmsg.payloadlen = static_cast<int>(msg.size());
    pubmsg.qos = 1;
    pubmsg.retained = 0;

    MQTTClient_deliveryToken token;
    int rc = MQTTClient_publishMessage(client, "actuator/velocidade_setpoint", &pubmsg, &token);
    if (rc != MQTTCLIENT_SUCCESS) {
        std::cerr << "[MQTT-C++] Falha ao publicar velocidade_setpoint: " << rc << std::endl;
        return false;
    }
    MQTTClient_waitForCompletion(client, token, 1000);
    return true;
}

double MQTTClientWrapper::get_ultimo_lidar() const {
    std::lock_guard<std::mutex> guard(state_mutex);
    return ultimo_lidar;
}

bool MQTTClientWrapper::get_ultimo_encoder() const {
    std::lock_guard<std::mutex> guard(state_mutex);
    return ultimo_encoder;
}

void MQTTClientWrapper::on_connection_lost(void* context, char* cause) {
    auto self = static_cast<MQTTClientWrapper*>(context);
    std::cerr << "[MQTT-C++] Conexão perdida: " << (cause ? cause : "desconhecida") << std::endl;
    self->conectado.store(false);
}

int MQTTClientWrapper::on_message_arrived(void* context, char* topicName, int topicLen, MQTTClient_message* message) {
    auto self = static_cast<MQTTClientWrapper*>(context);
    std::string topic(topicName, topicLen > 0 ? topicLen : std::strlen(topicName));
    self->handle_message(topic, message);
    MQTTClient_freeMessage(&message);
    MQTTClient_free(topicName);
    return 1;
}

void MQTTClientWrapper::handle_message(const std::string& topic, MQTTClient_message* message) {
    std::string payload(static_cast<char*>(message->payload), message->payloadlen);
    std::lock_guard<std::mutex> lock(state_mutex);
    
    if (topic == "sensor/lidar") {
        double valor_lidar;
        if (parse_double(payload, "distancia_y", valor_lidar) || parse_double(payload, "valor", valor_lidar)) {
            ultimo_lidar = valor_lidar;
        }
    }
    else if (topic == "sensor/encoder") {
        int valor_enc;
        if (parse_int(payload, "estado", valor_enc)) {
            ultimo_encoder = (valor_enc != 0);
        }
    }
    // =========================================================================
    // CAPTURA DE SINAIS DO SUPERVISÓRIO: Interoperabilidade Manual/Auto
    // =========================================================================
    else if (topic == "robo/comandos") {
        extern ControleRobo meu_robo; // Vincula ao objeto instanciado na main
        
        if (payload == "c_automatico") {
            meu_robo.set_modo(true);
            std::cout << "\n[COMANDO] Supervisório ativou Modo AUTOMÁTICO." << std::endl;
        } 
        else if (payload == "c_man") {
            meu_robo.set_modo(false);
            std::cout << "\n[COMANDO] Supervisório ativou Modo MANUAL." << std::endl;
        } 
        else if (payload == "c_para") {
            meu_robo.set_velocidade(0.0);
            std::cout << "\n[COMANDO] Operador ordenou PARADA de emergência." << std::endl;
        }
        // ... bloco do C++ ...
        else if (payload == "c_para") {
            meu_robo.set_velocidade(0.0);
            std::cout << "\n[COMANDO] Operador pausou." << std::endl;
        }
        else if (payload == "c_emergencia") {
            meu_robo.set_modo(false); // Desarma o Automático!
            meu_robo.set_velocidade(0.0);
            std::cout << "\n[EMERGÊNCIA] Operador acionou a EMG > Sistema desarmado<." << std::endl;
        }
        else if (payload == "c_direita") {
            double v_nova = std::min(5.0, meu_robo.get_velocidade_setpoint() + 0.3);
            meu_robo.set_velocidade(v_nova);
            std::cout << "\n[COMANDO] Ajuste manual: velocidade setpoint -> " << v_nova << " m/s" << std::endl;
        }
        else if (payload == "c_esquerda") {
            double v_nova = std::max(0.0, meu_robo.get_velocidade_setpoint() - 0.3);
            meu_robo.set_velocidade(v_nova);
            std::cout << "\n[COMANDO] Ajuste manual: velocidade setpoint -> " << v_nova << " m/s" << std::endl;
        }
    }
    // tópicos tratados fora do bloco de comandos do supervisório
    else if (topic == "actuator/velocidade_setpoint") {
        double novo_setpoint;
        if (parse_double(payload, "valor", novo_setpoint)) {
            extern ControleRobo meu_robo;
            meu_robo.set_velocidade(novo_setpoint);
            std::cout << "\n[COMANDO] Ajuste via IHM (Setpoint Absoluto) -> " << novo_setpoint << " m/s" << std::endl;
        }
        else {
            try {
                double vel_solicitada = std::stod(payload);
                extern ControleRobo meu_robo;
                meu_robo.set_velocidade(vel_solicitada);
            } catch (...) {}
        }
    }
    else if (topic == "robo/parametros") {
        try {
            double novo_limiar = std::stod(payload);
            extern float threshold_falha;
            threshold_falha = static_cast<float>(novo_limiar) / 100.0f; // cm para metros
            std::cout << "\n[PARÂMETRO] Novo limiar online configurado: " << threshold_falha << "m" << std::endl;
        } catch(...) {}
    }
    else if (topic == "sensor/imu") {
        double valor_inclinacao;
        if (parse_double(payload, "inclinacao", valor_inclinacao)) {
            extern ControleRobo meu_robo;
            // Alimenta dinamicamente a malha PID com o ângulo geográfico real da ladeira!
            meu_robo.set_inclinacao(valor_inclinacao);
        }
    }
}

static bool extract_number(const std::string& payload, const std::string& key, std::string& out_text) {
    std::string needle = "\"" + key + "\"";
    auto pos = payload.find(needle);
    if (pos == std::string::npos) return false;
    pos = payload.find(':', pos + needle.size());
    if (pos == std::string::npos) return false;
    pos++;
    while (pos < payload.size() && std::isspace(static_cast<unsigned char>(payload[pos]))) {
        pos++;
    }
    if (pos >= payload.size()) return false;

    auto end = pos;
    if (payload[end] == '+' || payload[end] == '-') {
        end++;
    }
    while (end < payload.size() && (std::isdigit(static_cast<unsigned char>(payload[end])) || payload[end] == '.' || payload[end] == 'e' || payload[end] == 'E' || payload[end] == '+' || payload[end] == '-')) {
        end++;
    }
    if (end == pos) return false;

    out_text = payload.substr(pos, end - pos);
    return true;
}

bool MQTTClientWrapper::parse_double(const std::string& payload, const std::string& key, double& out_value) {
    std::string text;
    if (!extract_number(payload, key, text)) {
        return false;
    }

    try {
        out_value = std::stod(text);
        return true;
    } catch (...) {
        return false;
    }
}

bool MQTTClientWrapper::parse_int(const std::string& payload, const std::string& key, int& out_value) {
    std::string text;
    if (!extract_number(payload, key, text)) {
        return false;
    }

    try {
        out_value = std::stoi(text);
        return true;
    } catch (...) {
        return false;
    }
}
