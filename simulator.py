#!/usr/bin/env python3
"""
SIMULADOR DE INSPEÇÃO DE TÚNEIS - ETAPA 2
=========================================
1. Física de Newton
2. Sensores: LIDAR (com ruído) e Encoder
3. Renderização 2D — túnel com falhas no TETO, chão plano, gráfico LIDAR
4. MQTT para integração C++
"""

import pygame
import numpy as np
import paho.mqtt.client as mqtt
import json
import threading
import math
from dataclasses import dataclass
from typing import List, Optional
from collections import deque

# ============================================================================
# CONFIGURAÇÕES GLOBAIS
# ============================================================================
MQTT_BROKER   = "localhost"
MQTT_PORT     = 1883
MQTT_TIMEOUT  = 60

DT            = 0.1
MAX_VELOCITY  = 5.0

WINDOW_WIDTH  = 1400
WINDOW_HEIGHT = 750  
FPS           = 30

TUNNEL_HEIGHT_NOM = 4.0   # metros — altura nominal do teto (chão→teto liso)
TUNNEL_WIDTH      = 600   # metros
PPM               = 60    # pixels por metro — escala principal
MAX_TILT_DEG      = 12.0  # limite máximo para os aclives/declives do perfil

# Altura do interior visível do túnel na tela (pixels)
FLOOR_Y  = 480   # y do chão (pixels, de cima)
CEIL_NOM = FLOOR_Y - int(TUNNEL_HEIGHT_NOM * PPM)   # teto nominal ≈ 240 px de cima

# ============================================================================
# PALETA
# ============================================================================
C_BG          = ( 10,  10,  15)   # fundo fora do túnel
C_ROCK_A      = (100,  70,  40)   # rocha clara
C_ROCK_B      = ( 70,  45,  22)   # rocha média
C_ROCK_C      = ( 45,  28,  10)   # rocha escura / sombra
C_DIRT_A      = (110,  80,  45)   # terra clara (base/chão)
C_DIRT_B      = ( 75,  52,  25)   # terra escura
C_AIR         = ( 18,  12,   6)   # interior do túnel (ar)
C_LIGHT_HALO  = (255, 220, 140)   # halo das lâmpadas
C_FLOOR_STRIP = ( 90,  65,  35)   # linhas do piso
C_ROBO_BODY   = ( 55, 110, 170)
C_ROBO_CAB    = ( 80, 160, 220)
C_ROBO_WHEEL  = ( 30,  30,  30)
C_ROBO_DETAIL = (190, 215, 255)
C_LIDAR       = ( 60, 255,  80)
C_ALERT_R     = (220,  45,  45)
C_ALERT_O     = (220, 130,  30)
C_ALERT_G     = ( 50, 190,  70)
C_HUD_ACC     = ( 70, 195, 115)
C_HUD_BG      = ( 12,  12,  22)
C_HUD_TXT     = (195, 195, 195)
C_BTN_N       = (160,  35,  35)
C_BTN_H       = (215,  70,  70)

# ============================================================================
# DADOS
# ============================================================================
@dataclass
class Falha:
    posicao_x:    float   # metros
    profundidade: float   # metros   > 0 → teto desce (saliência)   < 0 → teto sobe (buraco)
    largura:      float   # metros

    def delta_teto(self, x: float) -> float:
        """Variação em metros que a falha aplica ao teto na posição x."""
        if abs(x - self.posicao_x) <= self.largura / 2:
            t = abs(x - self.posicao_x) / (self.largura / 2)
            return self.profundidade * math.exp(-t * t * 2.5)
        return 0.0


@dataclass
class PerfilPiso:
    x: float
    altura: float

# ============================================================================
# FÍSICA
# ============================================================================
class FisicaRobo:
    def __init__(self):
        self.posicao_x          = 0.0
        self.velocidade         = 0.0
        self.aceleracao_comando = 0.0
        self._ultima_enc        = 0.0
        self.estado_encoder     = False

    def atualizar(self, dt, inclinacao_graus=0.0):
        componente_gravidade = 9.81 * math.sin(math.radians(inclinacao_graus))
        amortecimento = 0.15 * self.velocidade
        aceleracao_total = self.aceleracao_comando - componente_gravidade - amortecimento

        self.velocidade += aceleracao_total * dt
        self.velocidade = max(-MAX_VELOCITY, min(self.velocidade, MAX_VELOCITY))
        self.posicao_x += self.velocidade * dt

        if self.posicao_x < 0.0:
            self.posicao_x = 0.0
            if self.velocidade < 0.0:
                self.velocidade = 0.0
        elif self.posicao_x > TUNNEL_WIDTH:
            self.posicao_x = TUNNEL_WIDTH
            if self.velocidade > 0.0:
                self.velocidade = 0.0

    def gerar_evento_encoder(self) -> bool:
        if self.posicao_x - self._ultima_enc >= 1.0:
            self.estado_encoder = not self.estado_encoder
            self._ultima_enc   += 1.0
            return True
        return False

# ============================================================================
# SENSORES
# ============================================================================
class SensorSimulado:
    def __init__(self, sigma=0.05):
        self.sigma = sigma

    def medir_lidar(self, altura_real: float) -> float:
        return max(0.3, round(altura_real + np.random.normal(0, self.sigma), 2))

# ============================================================================
# TÚNEL
# ============================================================================
class Tunel:
    def __init__(self, h_nom=TUNNEL_HEIGHT_NOM):
        self.h_nom  = h_nom
        self.falhas: List[Falha] = []
        self.perfil_piso: List[PerfilPiso] = [PerfilPiso(0.0, 0.0), PerfilPiso(TUNNEL_WIDTH, 0.0)]

    def adicionar_falha(self, f: Falha):
        self.falhas.append(f)

    def definir_perfil_piso(self, pontos: List[PerfilPiso]):
        self.perfil_piso = sorted(pontos, key=lambda p: p.x)

    def altura_chao(self, x: float) -> float:
        if not self.perfil_piso:
            return 0.0
        if x <= self.perfil_piso[0].x:
            return self.perfil_piso[0].altura
        if x >= self.perfil_piso[-1].x:
            return self.perfil_piso[-1].altura

        for p0, p1 in zip(self.perfil_piso, self.perfil_piso[1:]):
            if p0.x <= x <= p1.x:
                if p1.x == p0.x:
                    return p1.altura
                t = (x - p0.x) / (p1.x - p0.x)
                return p0.altura + (p1.altura - p0.altura) * t
        return self.perfil_piso[-1].altura

    def inclinacao_chao(self, x: float) -> float:
        if len(self.perfil_piso) < 2:
            return 0.0

        if x <= self.perfil_piso[0].x:
            p0, p1 = self.perfil_piso[0], self.perfil_piso[1]
        elif x >= self.perfil_piso[-1].x:
            p0, p1 = self.perfil_piso[-2], self.perfil_piso[-1]
        else:
            p0, p1 = self.perfil_piso[0], self.perfil_piso[1]
            for a, b in zip(self.perfil_piso, self.perfil_piso[1:]):
                if a.x <= x <= b.x:
                    p0, p1 = a, b
                    break

        if p1.x == p0.x:
            return 0.0

        angulo = math.degrees(math.atan2(p1.altura - p0.altura, p1.x - p0.x))
        return max(-MAX_TILT_DEG, min(angulo, MAX_TILT_DEG))

    def altura_teto(self, x: float) -> float:
        h = self.h_nom
        for f in self.falhas:
            h -= f.delta_teto(x)
        return max(0.4, h)

    def falha_em(self, x: float) -> Optional[Falha]:
        for f in self.falhas:
            if abs(x - f.posicao_x) <= f.largura / 2:
                return f
        return None

    def gerar_padrao(self):
        self.adicionar_falha(Falha(posicao_x= 60.0, profundidade=-0.9, largura=4.0))
        self.adicionar_falha(Falha(posicao_x=150.0, profundidade= 0.7, largura=3.5))
        self.adicionar_falha(Falha(posicao_x=280.0, profundidade=-1.3, largura=5.0))
        self.adicionar_falha(Falha(posicao_x=420.0, profundidade= 1.0, largura=4.0))
        self.definir_perfil_piso([
            PerfilPiso(0.0, 0.0),
            PerfilPiso(25.0, 0.0),
            PerfilPiso(45.0, 1.35),
            PerfilPiso(70.0, 1.35),
            PerfilPiso(90.0, 0.15),
            PerfilPiso(115.0, 0.15),
            PerfilPiso(135.0, 1.85),
            PerfilPiso(160.0, 1.85),
            PerfilPiso(180.0, 0.35),
            PerfilPiso(205.0, 0.35),
            PerfilPiso(230.0, 1.55),
            PerfilPiso(255.0, 1.55),
            PerfilPiso(285.0, 0.20),
            PerfilPiso(315.0, 0.20),
            PerfilPiso(340.0, 1.40),
            PerfilPiso(365.0, 1.40),
            PerfilPiso(390.0, 0.0),
            PerfilPiso(430.0, 0.0),
            PerfilPiso(TUNNEL_WIDTH, 0.0),
        ])
# ============================================================================
# MQTT
# ============================================================================
class ClienteMQTT:
    def __init__(self, broker, port):
        self.broker = broker; self.port = port
        self.client = mqtt.Client(client_id="sim_tunel_2026")
        self.conectado = False
        self.aceleracao_comando  = 0.0
        self.velocidade_setpoint = 2.0
        self.modo_automatico = True
        self.inclinacao = 0.0
        self._lock = threading.Lock()
        self.client.on_connect    = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message    = self._on_message

    def conectar(self) -> bool:
        try:
            self.client.connect(self.broker, self.port, MQTT_TIMEOUT)
            self.client.loop_start(); return True
        except Exception as e:
            print(f"[MQTT] {e}"); return False

    def desconectar(self):
        self.client.loop_stop(); self.client.disconnect()

    def pub_lidar(self, v, ts):
        self.client.publish("sensor/lidar",
            json.dumps({"timestamp":ts,"distancia_y":round(v,2),"nivel_confianca":0.95}), qos=1)

    def pub_encoder(self, estado, ts):
        self.client.publish("sensor/encoder",
            json.dumps({"timestamp":ts,"estado":int(estado)}), qos=1)

    def pub_imu(self, inclinacao, ts):
        self.client.publish("sensor/imu",
            json.dumps({"timestamp": ts, "inclinacao": round(inclinacao, 2)}), qos=1)

    def pub_telemetria(self, fisika, ts_ms, inclinacao, altura_chao):
        payload = {
            "timestamp": ts_ms,
            "tempo": round(ts_ms / 1000.0, 2),
            "posicao_x": round(fisika.posicao_x, 3),
            "velocidade_atual": round(fisika.velocidade, 3),
            "aceleracao_atual": round(fisika.aceleracao_comando, 3),
            "modo_automatico": self.modo_automatico,
            "inclinacao_tunel": round(inclinacao, 3),
            "altura_chao": round(altura_chao, 3),
            "fonte": "simulator"
        }
        self.client.publish("sim/telemetria", json.dumps(payload), qos=0)

    def get_acel(self):
        with self._lock: return self.aceleracao_comando

    def _on_connect(self, c, u, f, rc):
        self.conectado = rc == 0
        if rc == 0:
            c.subscribe("actuator/#", qos=1)
            c.subscribe("actuator/velocidade_setpoint", qos=1)
            c.subscribe("sensor/imu", qos=1)
            self.client.subscribe("robo/comandos",qos=1)

    def _on_disconnect(self, c, u, rc): self.conectado = False

    def _on_message(self, c, u, msg):
        try:
            payload_text = msg.payload.decode()
            p = json.loads(payload_text)
            with self._lock:
                if msg.topic == "actuator/aceleracao":
                    self.aceleracao_comando = float(p.get("valor", 0.0))
                elif msg.topic == "actuator/velocidade_setpoint":
                    self.velocidade_setpoint = float(p.get("valor", 2.0))
                elif msg.topic == "sensor/imu":
                    self.inclinacao = float(p.get("inclinacao", 0.0))
        except:
            if msg.topic != "robo/comandos":
                return

            cmd = msg.payload.decode().strip().lower()
            with self._lock:
                if cmd == "c_automatico":
                    self.modo_automatico = True
                elif cmd == "c_man":
                    self.modo_automatico = False
                elif cmd == "c_para":
                    self.aceleracao_comando = 0.0
                elif cmd == "c_direita" and not self.modo_automatico:
                    self.aceleracao_comando = 1.6
                elif cmd == "c_esquerda" and not self.modo_automatico:
                    self.aceleracao_comando = -1.6

# ============================================================================
# HELPERS
# ============================================================================
def rrect(surf, color, rect, r=8, bw=0, bc=None):
    pygame.draw.rect(surf, color, rect, border_radius=r)
    if bw and bc:
        pygame.draw.rect(surf, bc, rect, bw, border_radius=r)

def arrow(surf, color, x1, y1, x2, y2, head=7, w=2):
    pygame.draw.line(surf, color, (x1,y1), (x2,y2), w)
    a = math.atan2(y2-y1, x2-x1)
    for da in (math.pi*3/4, -math.pi*3/4):
        pygame.draw.line(surf, color, (x2,y2),
            (int(x2+head*math.cos(a+da)), int(y2+head*math.sin(a+da))), w)

# ============================================================================
# RENDERIZADOR
# ============================================================================
class RenderizadorPygame:
    def __init__(self):
        pygame.init()
        self.tela    = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Simulador de Inspeção de Túneis — Etapa 2")
        self.relogio = pygame.time.Clock()
        self.f_tiny  = pygame.font.SysFont("Arial", 15)
        self.f_sm    = pygame.font.SysFont("Arial", 17, bold=True)
        self.f_md    = pygame.font.SysFont("Arial", 22, bold=True)
        self.f_big   = pygame.font.SysFont("Arial", 28, bold=True)
        self._tick   = 0

        self._rock_surf = self._build_rock_tex(WINDOW_WIDTH, WINDOW_HEIGHT)

    def _build_rock_tex(self, W, H):
        rng = np.random.default_rng(17)
        arr = np.zeros((H, W, 3), dtype=np.uint8)
        arr[:, :, 0] = 70; arr[:, :, 1] = 46; arr[:, :, 2] = 20
        noise = rng.integers(-18, 18, (H, W), dtype=np.int16)
        arr[:, :, 0] = np.clip(arr[:, :, 0].astype(np.int16) + noise, 30, 130)
        arr[:, :, 1] = np.clip(arr[:, :, 1].astype(np.int16) + noise // 2, 20, 90)
        arr[:, :, 2] = np.clip(arr[:, :, 2].astype(np.int16) + noise // 4, 5, 50)
        surf = pygame.surfarray.make_surface(arr.swapaxes(0, 1))
        return surf

    def _camera(self, fisika):
        target = WINDOW_WIDTH // 3
        cam = int(fisika.posicao_x * PPM - target)
        return max(0, min(cam, TUNNEL_WIDTH * PPM - WINDOW_WIDTH))

    def _floor_y_px(self, x_m, tunel):
        return int(FLOOR_Y - tunel.altura_chao(x_m) * PPM)

    def _teto_px(self, x_m, tunel):
        h = tunel.altura_teto(x_m)
        return self._floor_y_px(x_m, tunel) - int(h * PPM)

    def _draw_tunel(self, tunel, cam):
        W, H = WINDOW_WIDTH, WINDOW_HEIGHT
        tela = self.tela
        tela.fill(C_BG)

        step = 3
        pts_teto = []
        pts_chao = []
        for sx in range(-step, W + step, step):
            xm = (sx + cam) / PPM
            fy = self._floor_y_px(xm, tunel)
            ty = self._teto_px(xm, tunel)
            pts_teto.append((sx, ty))
            pts_chao.append((sx, fy))

        poly_ar = pts_teto + list(reversed(pts_chao))
        pygame.draw.polygon(tela, C_AIR, poly_ar)

        rock_poly = pts_teto + [(W + step, 0), (-step, 0)]
        pygame.draw.polygon(tela, C_ROCK_B, rock_poly)

        for vy in range(0, CEIL_NOM - 20, 20):
            pygame.draw.line(tela, C_ROCK_C, (0, vy), (W, vy), 1)

        rng = np.random.default_rng(5)
        for sx in range(0, W, 28):
            xm = (sx + cam) / PPM
            ty = self._teto_px(xm, tunel)
            sh = int(rng.integers(4, 16))
            sc = rng.integers(3)
            col = [C_ROCK_C, C_ROCK_B, C_ROCK_A][sc]
            pts = [(sx, ty), (sx + 14, ty + sh // 2),
                   (sx + 7,  ty + sh), (sx - 7, ty + sh // 2)]
            pygame.draw.polygon(tela, col, pts)

        pygame.draw.lines(tela, C_ROCK_C, False, pts_teto, 5)

        shadow_s = pygame.Surface((W, 12), pygame.SRCALPHA)
        shadow_s.fill((0, 0, 0, 60))
        tela.blit(shadow_s, (0, pts_teto[len(pts_teto)//2][1]))

        chao_poly = pts_chao + [(W + step, H), (-step, H)]
        pygame.draw.polygon(tela, C_DIRT_A, chao_poly)
        for vy in range(FLOOR_Y + 12, H, 16):
            pygame.draw.line(tela, C_DIRT_B, (0, vy), (W, vy), 1)

        pygame.draw.lines(tela, C_DIRT_B, False, pts_chao, 3)

        for xm in range(0, TUNNEL_WIDTH + 1, 5):
            sx = int(xm * PPM - cam)
            if -4 < sx < W + 4:
                fy = self._floor_y_px(xm, tunel)
                pygame.draw.line(tela, C_FLOOR_STRIP, (sx, fy), (sx, fy + 8), 2)
                if xm % 20 == 0:
                    t = self.f_tiny.render(f"{xm}m", True, (120, 90, 50))
                    tela.blit(t, (sx - t.get_width()//2, fy + 10))


        for falha in tunel.falhas:
            fx  = int(falha.posicao_x * PPM - cam)
            if -150 < fx < W + 150:
                lar = int(falha.largura * PPM)
                ty  = self._teto_px(falha.posicao_x, tunel)
                if falha.profundidade < 0:
                    s = pygame.Surface((lar, 30), pygame.SRCALPHA)
                    s.fill((0, 0, 0, 70))
                    tela.blit(s, (fx - lar//2, ty - 10))
                else:
                    s = pygame.Surface((lar, 20), pygame.SRCALPHA)
                    s.fill((*C_ROCK_A, 80))
                    tela.blit(s, (fx - lar//2, ty))
                    pygame.draw.ellipse(tela, (0, 0, 0, 60),
                        (fx - lar//4, ty + 10, lar//2, 10))

    def _draw_robo(self, fisika, tunel, cam):
        xp  = int(fisika.posicao_x * PPM - cam)
        floor_y = self._floor_y_px(fisika.posicao_x, tunel)
        WB, HB = 64, 30
        WR = 11
        body_y  = floor_y - WR * 2 - HB + 8

        sh = pygame.Surface((WB + 24, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 90), sh.get_rect())
        self.tela.blit(sh, (xp - WB//2 - 12, floor_y - 5))

        rrect(self.tela, C_ROBO_BODY, (xp-WB//2, body_y, WB, HB), r=7, bw=2, bc=C_ROBO_DETAIL)

        pygame.draw.line(self.tela, (255, 200, 30),
                         (xp - WB//2 + 6, body_y + HB - 7),
                         (xp + WB//2 - 6, body_y + HB - 7), 3)

        cw, ch = 30, 20
        cx2 = xp - cw//2
        cy2 = body_y - ch + 6
        rrect(self.tela, C_ROBO_CAB, (cx2, cy2, cw, ch), r=6, bw=2, bc=C_ROBO_DETAIL)
        pygame.draw.rect(self.tela, (*C_ROBO_DETAIL, 140),
                         (cx2+4, cy2+3, cw-8, ch-8), border_radius=3)

        angle_off = math.radians((self._tick * 6) % 360)
        for wx_off in (-WB//2 + 13, WB//2 - 13):
            wx = xp + wx_off
            wy = floor_y - WR
            pygame.draw.circle(self.tela, C_ROBO_WHEEL, (wx, wy), WR)
            pygame.draw.circle(self.tela, C_ROBO_DETAIL, (wx, wy), WR, 2)
            for da in range(0, 4):
                a = angle_off + da * math.pi / 2
                ex = int(wx + (WR-3) * math.cos(a))
                ey = int(wy + (WR-3) * math.sin(a))
                pygame.draw.line(self.tela, C_ROBO_DETAIL, (wx, wy), (ex, ey), 1)

        ax, ay0 = xp, cy2
        ay1 = cy2 - 18
        pygame.draw.line(self.tela, C_ROBO_DETAIL, (ax, ay0), (ax, ay1), 2)
        pygame.draw.circle(self.tela, C_LIDAR, (ax, ay1), 5)

        teto_y = self._teto_px(fisika.posicao_x, tunel)
        pygame.draw.line(self.tela, (*C_LIDAR, 120), (ax, ay1), (ax, teto_y), 1)
        for sy in range(teto_y, ay1, 7):
            pygame.draw.circle(self.tela, C_LIDAR, (ax, sy), 1)

        if fisika.velocidade > 0.1:
            for ox in (WB//2 + 5, WB//2 + 17):
                ay_ = body_y + HB//2
                arrow(self.tela, C_HUD_ACC, xp+ox, ay_, xp+ox+10, ay_, head=5, w=2)

    def _draw_hud(self, fisika, tempo, fps, mqtt_ok, lidar_v):
        W = WINDOW_WIDTH
        px, py, pw = W - 270, 56, 255
        linhas = [
            ("POSIÇÃO",    f"{fisika.posicao_x:.2f} m"),
            ("VELOCIDADE", f"{fisika.velocidade:.2f} m/s"),
            ("ACELERAÇÃO", f"{fisika.aceleracao_comando:.2f} m/s²"),
            ("LIDAR",      f"{lidar_v:.2f} m"),
            ("ENCODER",    str(int(fisika.estado_encoder))),
            ("TEMPO",      f"{tempo:.1f} s"),
            ("FPS",        f"{fps:.1f}"),
            ("MQTT",       "● CONECTADO" if mqtt_ok else "○ OFFLINE"),
        ]
        ph = len(linhas) * 26 + 18
        s = pygame.Surface((pw, ph), pygame.SRCALPHA)
        s.fill((*C_HUD_BG, 215))
        self.tela.blit(s, (px, py))
        pygame.draw.rect(self.tela, C_HUD_ACC, (px, py, pw, ph), 1, border_radius=4)
        t = self.f_sm.render("● HUD — INSPEÇÃO", True, C_HUD_ACC)
        self.tela.blit(t, (px + 6, py - 22))
        for i, (lbl, val) in enumerate(linhas):
            y = py + 9 + i * 26
            self.tela.blit(self.f_tiny.render(lbl, True, (130, 130, 150)), (px+8, y))
            vc = (C_ALERT_R if (lbl=="MQTT" and not mqtt_ok)
                  else C_HUD_ACC if (lbl=="MQTT" and mqtt_ok)
                  else C_HUD_TXT)
            self.tela.blit(self.f_sm.render(val, True, vc), (px+130, y))

    def _draw_banda(self, tunel, fisika, msg_falha):
        W = WINDOW_WIDTH
        bh = 44
        s = pygame.Surface((W, bh), pygame.SRCALPHA)
        s.fill((8, 8, 16, 215))
        self.tela.blit(s, (0, 0))
        pygame.draw.line(self.tela, C_HUD_ACC, (0, bh), (W, bh), 1)

        titulo = self.f_big.render("SIMULADOR DE INSPEÇÃO DE TÚNEIS", True, (210, 210, 240))
        self.tela.blit(titulo, (W//2 - titulo.get_width()//2, 8))

        falha = tunel.falha_em(fisika.posicao_x)
        if falha:
            if falha.profundidade < 0:
                txt, cor = "⚠  BURACO NO TETO DETECTADO!", C_ALERT_R
            else:
                txt, cor = "⚠  SALIÊNCIA NO TETO DETECTADA!", C_ALERT_O
        else:
            txt, cor = "✔  TRECHO REGULAR", C_ALERT_G

        at = self.f_sm.render(txt, True, cor)
        self.tela.blit(at, (20, 13))

    def _draw_grafico_lidar(self, historico):
        gx, gy = 80, WINDOW_HEIGHT - 160
        gw, gh = WINDOW_WIDTH - 160, 120

        pygame.draw.rect(self.tela, (15, 15, 20), (gx, gy, gw, gh))

        arrow(self.tela, (200, 200, 200), gx, gy + gh, gx + gw, gy + gh, head=8, w=2)
        arrow(self.tela, (200, 200, 200), gx, gy + gh, gx, gy, head=8, w=2)

        lbl_x = self.f_sm.render("X: TEMPO DE AMOSTRAGEM", True, (200, 200, 200))
        lbl_y = pygame.transform.rotate(self.f_sm.render("Y: DISTÂNCIA DO TETO ", True, (200, 200, 200)), 90)
        titulo = self.f_md.render("GRÁFICO DE DADOS LIDAR PROCESSADOS", True, (255, 255, 255))

        self.tela.blit(titulo, (gx + gw//2 - titulo.get_width()//2, gy - 25))
        self.tela.blit(lbl_x, (gx + gw//2 - lbl_x.get_width()//2, gy + gh + 10))
        self.tela.blit(lbl_y, (gx - 35, gy + gh//2 - lbl_y.get_height()//2))

        if len(historico) < 2:
            return

        janela_s = 40.0
        x_max = historico[-1][0]
        x_min = max(0.0, x_max - janela_s)
        y_min = 0.0
        y_max = 6.0 

        pontos_linha = []
        for tempo_amostra, lidar_y in historico:
            if tempo_amostra < x_min:
                continue

            if x_max <= x_min:
                continue

            px = gx + ((tempo_amostra - x_min) / janela_s) * gw
            py = gy + gh - ((lidar_y - y_min) / (y_max - y_min)) * gh 
            pontos_linha.append((int(px), int(py)))

        if len(pontos_linha) > 1:
            pygame.draw.lines(self.tela, (50, 200, 50), False, pontos_linha, 3)

    def _draw_btn(self):
        r = pygame.Rect(WINDOW_WIDTH - 108, WINDOW_HEIGHT - 48, 90, 34)
        cor = C_BTN_H if r.collidepoint(pygame.mouse.get_pos()) else C_BTN_N
        rrect(self.tela, cor, r, r=8, bw=2, bc=(255,255,255))
        t = self.f_sm.render("SAIR", True, (255,255,255))
        self.tela.blit(t, t.get_rect(center=r.center))

    def renderizar(self, fisika, tunel, sensores, tempo, fps,
                   mqtt_ok, msg_falha, lidar_v, historico_lidar):
        self._tick += 1
        cam = self._camera(fisika)

        self._draw_tunel(tunel, cam)
        self._draw_robo(fisika, tunel, cam)
        self._draw_banda(tunel, fisika, msg_falha)
        self._draw_hud(fisika, tempo, fps, mqtt_ok, lidar_v)
        
        self._draw_grafico_lidar(historico_lidar)
        self._draw_btn()

        if msg_falha and "FIM" not in msg_falha:
            ms = self.f_big.render(msg_falha, True, C_ALERT_R)
            mx = WINDOW_WIDTH//2 - ms.get_width()//2
            bg = pygame.Surface((ms.get_width()+24, ms.get_height()+12), pygame.SRCALPHA)
            bg.fill((0,0,0,170))
            self.tela.blit(bg, (mx-12, WINDOW_HEIGHT//2 - 30))
            self.tela.blit(ms,  (mx,    WINDOW_HEIGHT//2 - 26))

        if msg_falha and "FIM" in msg_falha:
            ms = self.f_big.render(msg_falha, True, C_HUD_ACC)
            mx = WINDOW_WIDTH//2 - ms.get_width()//2
            bg = pygame.Surface((ms.get_width()+24, ms.get_height()+12), pygame.SRCALPHA)
            bg.fill((0,0,0,180))
            self.tela.blit(bg, (mx-12, 52))
            self.tela.blit(ms,  (mx,    56))

        pygame.display.flip()
        self.relogio.tick(FPS)

# ============================================================================
# SIMULADOR PRINCIPAL
# ============================================================================
class SimuladorTunel:
    def __init__(self):
        self.fisika  = FisicaRobo()
        self.tunel   = Tunel()
        self.tunel.gerar_padrao()
        self.sensores = SensorSimulado()
        self.mqtt     = ClienteMQTT(MQTT_BROKER, MQTT_PORT)
        self.render   = RenderizadorPygame()
        self.t_sim    = 0.0
        self.t_pub    = 0.0
        self.lidar_v  = TUNNEL_HEIGHT_NOM
        self.msg      = ""
        self.t_msg    = 0.0
        self.rodando  = True
        
        self.historico_lidar = deque(maxlen=500)

    def processar_eventos(self):
        for ev in pygame.event.get():
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                r = pygame.Rect(WINDOW_WIDTH - 108, WINDOW_HEIGHT - 48, 90, 34)
                if r.collidepoint(ev.pos):
                    self.rodando = False

    def atualizar(self):
        self.inclinacao = self.tunel.inclinacao_chao(self.fisika.posicao_x)
        self.fisika.aceleracao_comando = self.mqtt.get_acel()
        self.fisika.atualizar(DT, self.inclinacao)

        self.inclinacao = self.tunel.inclinacao_chao(self.fisika.posicao_x)

        if self.fisika.gerar_evento_encoder():
            self.mqtt.pub_encoder(self.fisika.estado_encoder, int(self.t_sim*1000))

        h_real = self.tunel.altura_teto(self.fisika.posicao_x)
        self.lidar_v = self.sensores.medir_lidar(h_real)
        
        self.historico_lidar.append((self.t_sim, self.lidar_v))

        falha = self.tunel.falha_em(self.fisika.posicao_x)
        if falha:
            self.msg   = ("BURACO NO TETO! Reduza a velocidade!"
                          if falha.profundidade < 0
                          else "SALIÊNCIA NO TETO! Atenção!")
            self.t_msg = 2.0
        elif self.t_msg > 0:
            self.t_msg -= DT
            if self.t_msg <= 0: self.msg = ""

        if self.t_sim - self.t_pub >= 0.1:
            ts_ms = int(self.t_sim*1000)
            self.mqtt.pub_lidar(self.lidar_v, int(self.t_sim*1000))
            self.mqtt.pub_imu(self.inclinacao, ts_ms)
            self.mqtt.pub_telemetria(
                self.fisika,
                ts_ms,
                self.inclinacao,
                self.tunel.altura_chao(self.fisika.posicao_x),
            )
            self.t_pub = self.t_sim

        self.t_sim += DT

    def executar(self):
        print("[SIM] Iniciando...")
        if not self.mqtt.conectar():
            print("[AVISO] Sem MQTT — modo offline")
        try:
            while self.rodando:
                self.processar_eventos()
                self.atualizar()
                fps = self.render.relogio.get_fps()
                self.render.renderizar(
                    self.fisika, self.tunel, self.sensores,
                    self.t_sim, fps, self.mqtt.conectado,
                    self.msg, self.lidar_v, self.historico_lidar)
        except KeyboardInterrupt:
            print("\n[SIM] Interrompido pelo terminal")
        finally:
            self.mqtt.desconectar()
            pygame.quit()
            print("[SIM] Finalizado")

if __name__ == "__main__":
    SimuladorTunel().executar()