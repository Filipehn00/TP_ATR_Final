#include "controle.hpp"
#include "mqtt_client.hpp"
#include <iostream>
#include <chrono>
#include <thread>
#include <cmath>
#include <iomanip>
#include <algorithm>

namespace {
constexpr double VELOCIDADE_CRUZEIRO_AUTO = 5.0;
constexpr double VELOCIDADE_INSPECAO = 1.0;
constexpr double AJUSTE_ACLIVE_POR_GRAU = 0.25;
constexpr double BOOST_MAXIMO_ACLIVE = 2.5;
constexpr double FATOR_FREIO_EXTRA = 1.8;
constexpr double LIMITE_FREIO_EXTRA = 2.5;
constexpr double LIMITE_INTEGRAL = 6.0;
constexpr double GANHO_COMPENSACAO_GRAVIDADE = 1.15;
constexpr double GANHO_COMPENSACAO_ROLAMENTO = 0.22;
constexpr double SAIDA_MINIMA_AUTO = -8.0;
constexpr double SAIDA_MAXIMA_AUTO = 16.0;
constexpr double SAIDA_MINIMA_MANUAL = -12.0;
constexpr double SAIDA_MAXIMA_MANUAL = 12.0;

double calcular_velocidade_auto(double inclinacao_graus) {
    double inclinacao_positiva = std::max(0.0, inclinacao_graus);
    double boost = std::min(BOOST_MAXIMO_ACLIVE, inclinacao_positiva * AJUSTE_ACLIVE_POR_GRAU);
    return VELOCIDADE_CRUZEIRO_AUTO + boost;
}

double calcular_freio_extra(double velocidade_atual, double velocidade_alvo) {
    if (velocidade_atual <= velocidade_alvo) {
        return 0.0;
    }

    double excesso = velocidade_atual - velocidade_alvo;
    return -std::min(LIMITE_FREIO_EXTRA, excesso * FATOR_FREIO_EXTRA);
}
}

ControleRobo::ControleRobo() : 
    velocidade_atual(0.0), velocidade_setpoint(2.0), posicao_x(0.0), 
    modo_automatico(true), estado_encoder(0), ultima_posicao_encoder(0.0),
    inclinacao_tunel(0.0), ultimo_setpoint_aplicado(2.0), erro_acumulado(0.0), ultimo_erro(0.0) {}

double ControleRobo::calcular_pid(double dt) {
    if (dt <= 0.0) {
        return 0.0;
    }

    double erro = velocidade_setpoint - velocidade_atual;

    if (std::abs(velocidade_setpoint - ultimo_setpoint_aplicado) > 0.01) {
        erro_acumulado = 0.0;
        ultimo_erro = erro;
        ultimo_setpoint_aplicado = velocidade_setpoint;
    }

    // 1. MODO MANUAL: resposta direta aos comandos da IHM
    if (!modo_automatico) {
        erro_acumulado = 0.0;
        ultimo_erro = erro;
        return std::clamp(erro * 5.0, SAIDA_MINIMA_MANUAL, SAIDA_MAXIMA_MANUAL);
    }

    // 2. MODO AUTOMÁTICO: PID com compensação das perdas da simulação
    double erro_integral = std::clamp(erro_acumulado + erro * dt, -LIMITE_INTEGRAL, LIMITE_INTEGRAL);
    double derivativa = (erro - ultimo_erro) / dt;

    double inclinacao_rad = inclinacao_tunel * M_PI / 180.0;
    double compensacao_gravidade = GANHO_COMPENSACAO_GRAVIDADE * 9.81 * std::sin(inclinacao_rad);
    double compensacao_rolamento = GANHO_COMPENSACAO_ROLAMENTO * std::max(0.0, velocidade_setpoint);

    double saida_controle = (Kp * erro) + (Ki * erro_integral) + (Kd * derivativa) + compensacao_gravidade + compensacao_rolamento;

    if (velocidade_setpoint > 0.0 && velocidade_atual < 0.4 && inclinacao_tunel > 0.0) {
        saida_controle += 1.5;
    }

    saida_controle = std::clamp(saida_controle, SAIDA_MINIMA_AUTO, SAIDA_MAXIMA_AUTO);

    erro_acumulado = erro_integral;
    ultimo_erro = erro;
    return saida_controle;
}

double ControleRobo::atualizar_controle() {
    const double dt = 0.1; // 100ms
    double aceleracao = calcular_pid(dt);
    
    velocidade_atual += aceleracao * dt;
    if (velocidade_atual < 0.0) velocidade_atual = 0.0;
    
    posicao_x += velocidade_atual * dt;

    if (posicao_x - ultima_posicao_encoder >= 1.0) {
        estado_encoder = !estado_encoder;
        ultima_posicao_encoder += 1.0;
    }
    return aceleracao;
}
void ControleRobo::set_velocidade(double v) { velocidade_setpoint = v; }
void ControleRobo::set_modo(bool auto_mode) { modo_automatico = auto_mode; }
void ControleRobo::set_inclinacao(double angulo) { inclinacao_tunel = angulo; }
double ControleRobo::get_posicao_x() const { return posicao_x; }
double ControleRobo::get_velocidade() const { return velocidade_atual; }
double ControleRobo::get_velocidade_setpoint() const { return velocidade_setpoint; }
double ControleRobo::get_inclinacao() const { return inclinacao_tunel; }
int ControleRobo::get_estado_encoder() const { return estado_encoder; }
bool ControleRobo::get_modo_automatico() const { return modo_automatico; }

void tarefa_controle(ControleRobo& robo, MQTTClientWrapper& mqtt, std::mutex& mtx_camera, const bool& falha_detectada) {
    while (true) {
        double aceleracao = robo.atualizar_controle();
        
        // Comunicação Atuadora Básica
        mqtt.publicar_aceleracao(aceleracao);
        mqtt.publicar_velocidade_setpoint(robo.get_velocidade_setpoint());

        // =========================================================================
        // SERIALIZAÇÃO JSON DA TELEMETRIA: Abastece o painel Python via Rede
        // =========================================================================
        std::string json_telemetria = "{\"posicao_x\":" + std::to_string(robo.get_posicao_x()) + 
                                      ",\"velocidade_atual\":" + std::to_string(robo.get_velocidade()) + 
                                      ",\"modo_automatico\":" + (robo.get_modo_automatico() ? "true" : "false") + "}";

        MQTTClient_message pubmsg = MQTTClient_message_initializer;
        pubmsg.payload = (void*)json_telemetria.c_str();
        pubmsg.payloadlen = json_telemetria.length();
        pubmsg.qos = 0;
        pubmsg.retained = 0;
        MQTTClient_publishMessage(mqtt.getClientInstance(), "robo/telemetria", &pubmsg, nullptr);

        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
}

void tarefa_comando_navegacao(ControleRobo& robo, std::mutex& mtx_camera, const bool& falha_detectada) {
    while (true) {
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
        
        // Rotina automatizada só atua se o operador não assumiu o controle manual
        if (robo.get_modo_automatico()) {
            std::lock_guard<std::mutex> lock(mtx_camera);
            if (falha_detectada) {
                robo.set_velocidade(VELOCIDADE_INSPECAO);
            } else {
                double alvo_auto = calcular_velocidade_auto(robo.get_inclinacao());
                if (std::abs(robo.get_velocidade_setpoint() - alvo_auto) > 0.01) {
                    robo.set_velocidade(alvo_auto);
                }
            }
        }
    }
}