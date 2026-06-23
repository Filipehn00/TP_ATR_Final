#ifndef BUFFER_HPP
#define BUFFER_HPP

#include <mutex>
#include <condition_variable>
#include <queue>
#include "defs.hpp"


class BufferColetor{

    private:
    std::queue<RegistroLidar> fila; // fila com os dados
    std:: mutex mtx;
    std:: condition_variable cv; //sinalização
    
    public:
    void push(const RegistroLidar& dado); // (Reconstrução)Produtor insere os dados

    RegistroLidar pop(); // (Coletor) Consumidor retirar os dados

};

#endif 