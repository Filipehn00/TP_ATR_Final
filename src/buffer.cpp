#include "buffer.hpp"

//PRODUTOR inserindo dados na fila
void BufferColetor:: push(const RegistroLidar& dado){

    std::lock_guard<std::mutex> lock(mtx);
    fila.push(dado);
    cv.notify_one(); // notifcação que chegou um dado

}
// CONSUMIDOR retirar dados da fila
RegistroLidar BufferColetor::pop(){
    std::unique_lock<std:: mutex> lock(mtx);
    cv.wait(lock, [this](){ return !fila.empty();});

    // acordou, remove o dado da fila
    RegistroLidar dado = fila.front();
    fila.pop();

    return dado;
}