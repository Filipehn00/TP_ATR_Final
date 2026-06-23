#ifndef MQTT_CLIENT_HPP
#define MQTT_CLIENT_HPP

#include <string>
#include <mutex>
#include <atomic>
#include <MQTTClient.h>

class MQTTClientWrapper {
public:
    MQTTClientWrapper(const std::string& host, int port);
    ~MQTTClientWrapper();
    MQTTClient getClientInstance() { return client; }
    bool conectar();
    void desconectar();

    bool publicar_aceleracao(double aceleracao);
    bool publicar_velocidade_setpoint(double velocidade);

    double get_ultimo_lidar() const;
    bool get_ultimo_encoder() const;

private:
    std::string broker_uri;
    std::string client_id;
    MQTTClient client;
    std::atomic<bool> conectado;
    mutable std::mutex state_mutex;

    double ultimo_lidar;
    bool ultimo_encoder;

    static void on_connection_lost(void* context, char* cause);
    static int on_message_arrived(void* context, char* topicName, int topicLen, MQTTClient_message* message);
    void handle_message(const std::string& topic, MQTTClient_message* message);

    static bool parse_double(const std::string& payload, const std::string& key, double& out_value);
    static bool parse_int(const std::string& payload, const std::string& key, int& out_value);
};

#endif // MQTT_CLIENT_HPP
