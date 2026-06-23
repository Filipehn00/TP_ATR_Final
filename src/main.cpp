#include <iostream>
#include <chrono>
#include <thread>   
#include <vector>
#include <mutex>
#include <condition_variable>
#include "controle.hpp"
#include "buffer.hpp"
#include "coletor.hpp"
#include "defs.hpp"
#include "mqtt_client.hpp"

// Declarações (Protótipos) das tarefas
void tarefa_reconstrucao(BufferColetor& buffer, std::condition_variable& cv_camera, bool& falha_detectada, std::mutex& mtx_camera, ControleRobo& robo, MQTTClientWrapper& mqtt);
void tarefa_inspecao_ia(std::condition_variable& cv_camera, bool& falha_detectada, std::mutex& mtx_camera);
void tarefa_controle(ControleRobo& robo, MQTTClientWrapper& mqtt, std::mutex& mtx_camera, const bool& falha_detectada);
void tarefa_comando_navegacao(ControleRobo& robo, std::mutex& mtx_camera, const bool& falha_detectada);

// =========================================================================
// ALTERAÇÃO CRÍTICA: Instanciação global para o 'extern' do MQTT funcionar
// =========================================================================
ControleRobo meu_robo; 

int main() {
    std::cout << "===============================================" << std::endl;
    std::cout << "--- SISTEMA DE INSPEÇÃO DE TÚNEIS INICIADO ---" << std::endl;
    std::cout << "===============================================" << std::endl;

    // 1. Instanciação dos recursos compartilhados
    BufferColetor buffer_comum;  
    MQTTClientWrapper mqtt("localhost", 1883);

    // Variáveis de sincronização para eventos (Setas Vermelhas)
    std::mutex mtx_camera;
    std::condition_variable cv_camera;
    bool falha_detectada = false;

    std::cout << "[MAIN] Conectando ao broker MQTT..." << std::endl;
    if (!mqtt.conectar()) {
        std::cerr << "[MAIN] Falha crítica: não foi possível conectar ao MQTT local." << std::endl;
    }
    
    std::this_thread::sleep_for(std::chrono::seconds(1));

    // Lançamento das linhas de execução do Core C++
    std::thread thread_coletor(iniciar_coletor, std::ref(buffer_comum));
    std::thread thread_nav(tarefa_controle, std::ref(meu_robo), std::ref(mqtt), std::ref(mtx_camera), std::cref(falha_detectada));
    
    std::thread thread_comando(tarefa_comando_navegacao, std::ref(meu_robo), std::ref(mtx_camera), std::cref(falha_detectada));
    thread_comando.detach(); 
    
    std::thread thread_recon(tarefa_reconstrucao, std::ref(buffer_comum), std::ref(cv_camera), std::ref(falha_detectada), std::ref(mtx_camera), std::ref(meu_robo), std::ref(mqtt));
    std::thread thread_ia(tarefa_inspecao_ia, std::ref(cv_camera), std::ref(falha_detectada), std::ref(mtx_camera));

    std::cout << "\n[MAIN] Sistema operando em Regime Permanente de Tempo Real." << std::endl;
    std::cout << "[MAIN] Para encerrar a simulação integrada, pressione Ctrl+C no terminal.\n" << std::endl;

    // Laço infinito para manter as tarefas rodando em background para os testes do professor
    while (true) {
        std::this_thread::sleep_for(std::chrono::seconds(2));
    }

    return 0;
}