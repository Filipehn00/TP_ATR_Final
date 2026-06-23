#ifndef CONTROLE_HPP
#define CONTROLE_HPP

#include <mutex>

class MQTTClientWrapper;

class ControleRobo {
private:
    double velocidade_atual;
    double velocidade_setpoint;
    double posicao_x;
    bool modo_automatico;
    int estado_encoder; 
    double ultima_posicao_encoder;
    double inclinacao_tunel;
    double ultimo_setpoint_aplicado;
    
    const double Kp = 2.8;
    const double Ki = 0.30;
    const double Kd = 0.08;
    double erro_acumulado;
    double ultimo_erro;

    double calcular_pid(double dt);

public:
    ControleRobo();

    double atualizar_controle(); 
    
    // Getters e Setters
    void set_velocidade(double v);
    void set_modo(bool auto_mode);
    void set_inclinacao(double angulo);
    
    double get_posicao_x() const;
    double get_velocidade() const;
    double get_velocidade_setpoint() const;
    double get_inclinacao() const;
    int get_estado_encoder() const;
    bool get_modo_automatico() const;
};

// Mantendo os 4 parâmetros para o main.cpp e as interrupções de hardware funcionarem!
void tarefa_controle(ControleRobo& robo, MQTTClientWrapper& mqtt, std::mutex& mtx_camera, const bool& falha_detectada);
void tarefa_comando_navegacao(ControleRobo& robo, std::mutex& mtx_camera, const bool& falha_detectada);

#endif // CONTROLE_HPP