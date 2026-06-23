#!/usr/bin/env python3
"""
MONITOR MQTT - Visualizador de Dados em Tempo Real
===================================================

Monitora os tópicos MQTT do simulador e exibe as mensagens
com formatação e análise em tempo real.

Uso:
    python3 mqtt_monitor.py [--broker localhost] [--port 1883]
"""

import paho.mqtt.client as mqtt
import json
import sys
from datetime import datetime
from typing import Dict, Any
import threading

class MonitorMQTT:
    """Monitor de tópicos MQTT com análise de dados"""
    
    def __init__(self, broker: str = "localhost", port: int = 1883):
        self.broker = broker
        self.port = port
        self.client = mqtt.Client(client_id="mqtt_monitor_2026")
        
        # Estado
        self.conectado = False
        self.mensagens_recebidas = 0
        self.ultima_altura_lidar = None
        self.ultima_confianca = None
        self.ultimo_estado_encoder = None
        self.tempo_inicio = datetime.now()
        
        # Configurar callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Lock para thread-safety
        self.lock = threading.Lock()
    
    def conectar(self) -> bool:
        """Conecta ao broker MQTT"""
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            return False
    
    def desconectar(self):
        """Desconecta do broker"""
        self.client.loop_stop()
        self.client.disconnect()
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback de conexão"""
        if rc == 0:
            self.conectado = True
            print("✅ Conectado ao broker MQTT!")
            print(f"   Broker: {self.broker}:{self.port}\n")
            
            # Subscrever a todos os tópicos
            client.subscribe("sensor/#", qos=1)
            client.subscribe("actuator/#", qos=1)
            
            print("📡 Monitorando tópicos:")
            print("   - sensor/lidar")
            print("   - sensor/encoder")
            print("   - actuator/aceleracao")
            print("   - actuator/velocidade_setpoint")
            print("\n" + "="*70 + "\n")
        else:
            self.conectado = False
            print(f"❌ Falha na conexão (código {rc})")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback de desconexão"""
        self.conectado = False
        if rc != 0:
            print(f"\n⚠️  Desconexão inesperada (código {rc})")
    
    def _on_message(self, client, userdata, msg):
        """Callback de mensagem recebida"""
        try:
            payload = json.loads(msg.payload.decode())
            
            with self.lock:
                self.mensagens_recebidas += 1
            
            # Processar por tópico
            if msg.topic == "sensor/lidar":
                self._processar_lidar(payload)
            elif msg.topic == "sensor/encoder":
                self._processar_encoder(payload)
            elif msg.topic.startswith("actuator/"):
                self._processar_atuador(msg.topic, payload)
        
        except Exception as e:
            print(f"❌ Erro ao processar: {e}")
    
    def _processar_lidar(self, payload: Dict[str, Any]):
        """Processa e exibe leitura de LIDAR"""
        timestamp = payload.get("timestamp")
        altura = payload.get("distancia_y")
        confianca = payload.get("nivel_confianca", 0.95)
        
        with self.lock:
            self.ultima_altura_lidar = altura
            self.ultima_confianca = confianca
        
        # Barra de visualização
        barra = "█" * int(altura * 5) + "░" * (25 - int(altura * 5))
        
        print(f"📏 LIDAR")
        print(f"   Timestamp: {timestamp} ms")
        print(f"   Altura: {altura:.2f} m  [{barra}]")
        print(f"   Confiança: {confianca*100:.0f}%")
        print()
    
    def _processar_encoder(self, payload: Dict[str, Any]):
        """Processa e exibe estado do encoder"""
        timestamp = payload.get("timestamp")
        estado = payload.get("estado")
        
        with self.lock:
            self.ultimo_estado_encoder = estado
        
        simbolo = "🔵" if estado == 1 else "⚪"
        
        print(f"⏱️  ENCODER")
        print(f"   Timestamp: {timestamp} ms")
        print(f"   Estado: {estado} {simbolo}")
        print()
    
    def _processar_atuador(self, topico: str, payload: Dict[str, Any]):
        """Processa e exibe comandos de atuadores"""
        valor = payload.get("valor", 0.0)
        
        nome_atuador = topico.replace("actuator/", "").replace("_", " ").title()
        
        if "aceleracao" in topico:
            # Mostrar direção e magnitude
            if valor > 0:
                simbolo = "⬆️ "
                direcao = "Acelera"
            elif valor < 0:
                simbolo = "⬇️ "
                direcao = "Freia"
            else:
                simbolo = "⏸️  "
                direcao = "Parado"
            
            barra = "=" * int(abs(valor) * 10)
            
            print(f"🎛️  ATUADOR")
            print(f"   {nome_atuador}")
            print(f"   Valor: {valor:+.2f} m/s² {simbolo}")
            print(f"   [{barra}]")
        else:
            print(f"🎛️  ATUADOR")
            print(f"   {nome_atuador}")
            print(f"   Valor: {valor:.2f}")
        
        print()
    
    def exibir_status(self):
        """Exibe status do monitor"""
        with self.lock:
            tempo_decorrido = (datetime.now() - self.tempo_inicio).total_seconds()
            frequencia = self.mensagens_recebidas / tempo_decorrido if tempo_decorrido > 0 else 0
        
        print("="*70)
        print(f"📊 STATUS DO MONITOR")
        print(f"   Tempo: {tempo_decorrido:.1f}s")
        print(f"   Mensagens recebidas: {self.mensagens_recebidas}")
        print(f"   Frequência: {frequencia:.1f} msg/s")
        print(f"   Conexão: {'✅ Conectado' if self.conectado else '❌ Desconectado'}")
        
        if self.ultima_altura_lidar is not None:
            print(f"\n   Última leitura LIDAR: {self.ultima_altura_lidar:.2f}m ({self.ultima_confianca*100:.0f}%)")
        
        if self.ultimo_estado_encoder is not None:
            print(f"   Último encoder: {self.ultimo_estado_encoder}")
        
        print("="*70)
    
    def executar(self):
        """Loop principal"""
        if not self.conectar():
            return
        
        try:
            import time
            
            # Exibir status a cada 30 segundos
            proxima_exibicao = time.time() + 30
            
            while True:
                time.sleep(1)
                
                agora = time.time()
                if agora >= proxima_exibicao:
                    print("\n")
                    self.exibir_status()
                    print("\n")
                    proxima_exibicao = agora + 30
        
        except KeyboardInterrupt:
            print("\n\n⏹️  Monitor parado pelo usuário")
            self.exibir_status()
        finally:
            self.desconectar()

def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor MQTT em Tempo Real")
    parser.add_argument("--broker", default="localhost", help="Endereço do broker")
    parser.add_argument("--port", type=int, default=1883, help="Porta MQTT")
    
    args = parser.parse_args()
    
    monitor = MonitorMQTT(args.broker, args.port)
    monitor.executar()

if __name__ == "__main__":
    main()
