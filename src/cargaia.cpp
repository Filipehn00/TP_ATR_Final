#include <iostream>
#include <cmath>
#include <mutex>               // Necessário para std::mutex e std::unique_lock
#include <condition_variable>  // Necessário para std::condition_variable

void tarefa_inspecao_ia(std::condition_variable& cv_camera, bool& falha_detectada, std::mutex& mtx_camera) {
    while (true) {
        std::unique_lock<std::mutex> lock(mtx_camera);
        
        // Aguarda até que falha_detectada seja true
        cv_camera.wait(lock, [&]{ return falha_detectada; }); 

        std::cout << "[IA] Iniciando inspeção detalhada da estrutura..." << std::endl;
        
        // Simulação de processamento pesado (CPU Bound)
        // Realiza cálculos de ponto flutuante para ocupar o processador
        double carga = 0.0;
        for (int i = 0; i < 10000000; ++i) {
            carga += std::sin(i) * std::cos(i) + std::sqrt(std::abs(carga));
        }

        std::cout << "[IA] Inspeção concluída. Resultado: Objeto detectado." << std::endl;
        
        falha_detectada = false; // Reseta o estado para a próxima detecção
        lock.unlock(); // Libera o mutex
    }
}