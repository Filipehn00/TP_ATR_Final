#include <iostream>
#include <fstream>
#include "coletor.hpp"


void iniciar_coletor(BufferColetor& buffer){

    std::cout << "[COLETOR] Iniciando gravação em .logs/dados_inspecao.txt" << std:: endl;

    std::ofstream log_file("./logs/dados_inspecao.txt", std::ios::app);
    if(!log_file.is_open()){
        std:: cerr << "[ERRO] Não possível abrir o arquivo de log!" << std:: endl;
        return;
    }

    while (true)
    {
        RegistroLidar dado = buffer.pop(); // puxa dado da fila
        log_file << dado.timestamp << "," 
                 << dado.posicao_x << "," 
                 << dado.distancia_y << "," 
                 << dado.nivel_confianca << "\n";
        // gravação do LOG

        log_file.flush(); //salva no disco
    }
    
}   