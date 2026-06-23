#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <chrono>

// Cabeçalhos do seu projeto
#include "buffer.hpp" 
#include "defs.hpp"
#include "controle.hpp" // Adicionado para conhecer o robô
#include "mqtt_client.hpp"

// =========================================================================
// FUNÇÃO SIMULADA (LIDAR)
// =========================================================================
float obter_leitura_lidar_simulado() {
    static int cont = 0;
    cont++;
    if (cont == 30) {
        cont = 0;
        return 5.5f; // Falha simulada a cada 3 segundos
    }
    return 4.0f; // Altura padrão
}
// =========================================================================

// Variáveis globais para os parâmetros configuráveis
float threshold_falha = 0.5; // Variação severa em metros
bool sinal_reduzir_velocidade = false; 

// ASSINATURA ATUALIZADA COM ControleRobo& robo
void tarefa_reconstrucao(BufferColetor& buffer, std::condition_variable& cv_camera, bool& falha_detectada, std::mutex& mtx_camera, ControleRobo& robo, MQTTClientWrapper& mqtt) {
    std::vector<float> janela_media;
    const int N = 5; // Ordem do filtro
    float altura_referencia = 4.0; // Altura padrão do túnel

    while (true) {
        // Ciclo da tarefa especificado na arquitetura (100 ms)
        std::this_thread::sleep_for(std::chrono::milliseconds(100));

        float leitura_suja = static_cast<float>(mqtt.get_ultimo_lidar());
        if (leitura_suja <= 0.0f) {
            leitura_suja = obter_leitura_lidar_simulado();
        }
        
        // Pega a posição diretamente do PID!
        float pos_x = robo.get_posicao_x();

        // Implementação da Média Móvel
        janela_media.push_back(leitura_suja);
        if (janela_media.size() > N) {
            janela_media.erase(janela_media.begin());
        }
        
        float altura_filtrada = std::accumulate(janela_media.begin(), janela_media.end(), 0.0f) / static_cast<float>(janela_media.size());

        // Detecção de Falha (Buraco ou Saliência)
if (std::abs(altura_filtrada - altura_referencia) > threshold_falha) {
            
            // Só dispara se a falha ainda não estiver sendo tratada (Evita spam de mensagens)
            if (!falha_detectada) {
                std::cout << "[RECONSTRUÇÃO] Buraco detectado em X: " << pos_x << "m. Freando para 1.0 m/s!" << std::endl;
                
                robo.set_velocidade(1.0); // Força a velocidade de inspeção segura
                
                {
                    std::lock_guard<std::mutex> lock(mtx_camera);
                    falha_detectada = true;
                }
                cv_camera.notify_all(); // Seta vermelha: Acorda a IA!
            }
        }

        // Cria o registro e envia para o buffer do Coletor
        RegistroLidar registro;
        registro.timestamp = static_cast<long>(time(0));
        registro.posicao_x = pos_x;
        registro.distancia_y = altura_filtrada;
        registro.nivel_confianca = 0.95f;

        buffer.push(registro);
    }
}