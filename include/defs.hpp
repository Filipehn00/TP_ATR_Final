#ifndef DEFS_HPP
#define DEFS_HPP


#include  <chrono>


struct RegistroLidar{

    long long timestamp; // registro do tempo
    double posicao_x; // posição eixo X
    int distancia_y; // medição da altura no eixo y
    double nivel_confianca; // confiança da medição
};

#endif 

