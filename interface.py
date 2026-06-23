import json
import sys

import paho.mqtt.client as mqtt
import pygame

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
# janela
W = 560
H = 680
FPS = 30

C_BG        = (14, 17, 22)       # fundo principal
C_PANEL     = (22, 27, 34)       # paineis
C_BORDER    = (30, 144, 255)     # azul primario
C_GREEN     = (0, 220, 100)      # dados / ok
C_ORANGE    = (255, 150, 40)     # manual / aviso
C_RED       = (210, 30, 55)      # emergencia
C_WHITE     = (240, 245, 250)
C_GRAY      = (90, 100, 115)
C_MUTED     = (160, 175, 195)
C_BTN_OFF   = (30, 36, 44)      # botao inativo


class IHMSalaControle:
    def __init__(self):
        pygame.init()
        pygame.font.init()

        self.tela = pygame.display.set_mode((W, H))
        pygame.display.set_caption("IHM REMOTA - SALA DE CONTROLE DE INSPECAO")

        # Estado
        self.posicao_x       = 0.0
        self.velocidade_real = 0.0
        self.aceleracao_real = 0.0
        self.tempo_sim       = 0.0
        self.distancia_lidar = 4.0
        self.confianca_lidar = 0.0
        self.encoder_estado  = 0
        self.modo_auto       = True
        self.e_automatico    = 1
        self.e_inspecao      = 0
        self.j_sp_velocidade = 2.0
        self.fonte_telemetria = "SEM DADOS"
        self.status_texto    = "Aguardando telemetria MQTT..."

        self.texto_setpoint  = "2.0"
        self.editando_setpoint = False

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.conectado = False
        self.conectar_mqtt()

        MG = 16   
        GU = 8    
        IW = W - 2 * MG 

        y = MG

        # --- PAINEL DE TELEMETRIA  ---
        self.panel_tele = pygame.Rect(MG, y, IW, 170)
        y += 170 + GU

        #  LINHA DE STATUS
        self.y_status = y
        y += 28 + GU

        #  LINHA DE MODO
        BTN_W2 = (IW - GU) // 2
        self.btn_auto = pygame.Rect(MG,          y, BTN_W2, 44)
        self.btn_man  = pygame.Rect(MG + BTN_W2 + GU, y, BTN_W2, 44)
        y += 44 + GU

        #  LINHA DE SETPOINT 
        SP_W  = IW - 62 - 62 - 2 * GU  
        self.box_setpoint  = pygame.Rect(MG, y, SP_W, 50)
        self.btn_sp_mais   = pygame.Rect(MG + SP_W + GU,  y, 62,  50)
        self.btn_sp_menos  = pygame.Rect(MG + SP_W + GU + 62 + GU, y, 62, 50)
        y += 50 + GU

        #  LINHA DIRECIONAL (3 botoes iguais) 
        BTN_W3 = (IW - 2 * GU) // 3
        self.btn_left  = pygame.Rect(MG,                    y, BTN_W3, 48)
        self.btn_stop  = pygame.Rect(MG + BTN_W3 + GU,     y, BTN_W3, 48)
        self.btn_right = pygame.Rect(MG + 2*(BTN_W3 + GU), y, BTN_W3, 48)
        y += 48 + GU

        #  PARADA DE EMERGENCIA 
        self.btn_emerg = pygame.Rect(MG, y, IW, 60)
        y += 60 + GU

        # 3 caixas de estado + LiDAR 
        BOX_W = (IW - 2 * GU) // 3
        self.box_inf_1 = pygame.Rect(MG,                   y, BOX_W, 50)
        self.box_inf_2 = pygame.Rect(MG + BOX_W + GU,     y, BOX_W, 50)
        self.box_inf_3 = pygame.Rect(MG + 2*(BOX_W + GU), y, BOX_W, 50)
        y += 50 + GU

        self.y_lidar = y   

        self.rodando = True

    def conectar_mqtt(self):
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
        except Exception as exc:
            self.status_texto = f"Falha MQTT: {exc}"

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.conectado = True
            self.status_texto = "Conectado ao broker MQTT"
            for t in ("sim/telemetria", "robo/telemetria", "sensor/lidar",
                      "sensor/encoder", "actuator/velocidade_setpoint"):
                self.client.subscribe(t)

    def on_message(self, client, userdata, msg):
        try:
            dados = json.loads(msg.payload.decode(errors="ignore"))
        except Exception:
            dados = None
        if msg.topic in ("sim/telemetria", "robo/telemetria") and isinstance(dados, dict):
            self.posicao_x       = float(dados.get("posicao_x",       self.posicao_x))
            self.velocidade_real = float(dados.get("velocidade_atual", self.velocidade_real))
            self.aceleracao_real = float(dados.get("aceleracao_atual", self.aceleracao_real))
            self.tempo_sim       = float(dados.get("tempo",self.tempo_sim))
            # alterado botão emg não ficar alternando modos
            if "modo_automatico" in dados and msg.topic == "robo/telemetria":
                self.modo_auto    = bool(dados["modo_automatico"])
                self.e_automatico = 1 if self.modo_auto else 0
                
            self.fonte_telemetria = "SIMULADOR" if msg.topic == "sim/telemetria" else "C++"
            self.atualizar_estado_inspecao()

        elif msg.topic == "sensor/lidar" and isinstance(dados, dict):
            self.distancia_lidar = float(dados.get("distancia_y",    self.distancia_lidar))
            self.confianca_lidar = float(dados.get("nivel_confianca", 0.0))
            self.atualizar_estado_inspecao()

        elif msg.topic == "sensor/encoder" and isinstance(dados, dict):
            self.encoder_estado = int(dados.get("estado", self.encoder_estado))

        elif msg.topic == "actuator/velocidade_setpoint" and isinstance(dados, dict):
            self.j_sp_velocidade = float(dados.get("valor", self.j_sp_velocidade)) ## corrigi o problema do setpoint
            if not self.editando_setpoint:
                self.texto_setpoint = self._fmt(self.j_sp_velocidade)
            self.j_sp_velocidade = float(dados.get("valor", self.j_sp_velocidade))
            self.texto_setpoint  = self._fmt(self.j_sp_velocidade)
    def _fmt(self, v):
        return str(int(round(v))) if abs(v - round(v)) < 1e-6 else f"{v:.1f}"

    def publicar_comando(self, cmd):
        if self.conectado:
            self.client.publish("robo/comandos", cmd)
        self.status_texto = f"Cmd: {cmd}"

    def publicar_setpoint(self, valor):
        try:
            valor = float(valor)
        except ValueError:
            self.status_texto = "Setpoint invalido"
            return
        self.j_sp_velocidade = valor
        self.texto_setpoint  = self._fmt(valor)
        if self.conectado:
            self.client.publish("actuator/velocidade_setpoint", json.dumps({"valor": valor}))
        self.status_texto = f"Setpoint: {self.texto_setpoint} m/s"

    def atualizar_estado_inspecao(self):
        self.e_inspecao = 1 if abs(self.distancia_lidar - 4.0) >= 0.30 else 0
        if self.e_inspecao:
            self.status_texto = "Falha de superficie — inspecao ativa"
        elif self.conectado:
            self.status_texto = "Sistema operacional"
    def tratar_cliques(self, pos):
        if self.btn_auto.collidepoint(pos):
            self.publicar_comando("c_automatico")
        elif self.btn_man.collidepoint(pos):
            self.publicar_comando("c_man")
        elif self.box_setpoint.collidepoint(pos):
            self.editando_setpoint = True
        elif self.btn_sp_mais.collidepoint(pos):
            self.editando_setpoint = False
            self.publicar_setpoint(self.j_sp_velocidade + 1.0)
        elif self.btn_sp_menos.collidepoint(pos):
            self.editando_setpoint = False
            self.publicar_setpoint(max(0.0, self.j_sp_velocidade - 1.0))
        elif self.btn_left.collidepoint(pos):
            self.publicar_comando("c_esquerda")
        elif self.btn_stop.collidepoint(pos):
            self.publicar_comando("c_para")
        elif self.btn_right.collidepoint(pos):
            self.publicar_comando("c_direita")
        elif self.btn_emerg.collidepoint(pos):
            self.publicar_comando("c_emergencia")

    def tratar_teclas(self, event):
        if self.editando_setpoint:
            if event.key == pygame.K_RETURN:
                self.editando_setpoint = False
                self.publicar_setpoint(self.texto_setpoint)
            elif event.key == pygame.K_BACKSPACE:
                self.texto_setpoint = self.texto_setpoint[:-1]
            elif event.unicode in "0123456789.,-":
                self.texto_setpoint += event.unicode
            return
        if event.key == pygame.K_a:
            self.publicar_comando("c_automatico")
        elif event.key == pygame.K_m:
            self.publicar_comando("c_man")
        elif event.key in (pygame.K_LEFT,  pygame.K_j): self.publicar_comando("c_esquerda")
        elif event.key in (pygame.K_RIGHT, pygame.K_l): self.publicar_comando("c_direita")
        elif event.key in (pygame.K_SPACE, pygame.K_s): self.publicar_comando("c_para")

    def _painel(self, rect, border_color, radius=8):
        pygame.draw.rect(self.tela, C_PANEL, rect, border_radius=radius)
        pygame.draw.rect(self.tela, border_color, rect, 2, border_radius=radius)

    def _label(self, surf, text, color, x, y):
        surf.blit(text, (x, y))

    def _btn(self, rect, bg, label, font, radius=6):
        pygame.draw.rect(self.tela, bg, rect, border_radius=radius)
        txt = font.render(label, True, C_WHITE)
        self.tela.blit(txt, txt.get_rect(center=rect.center))

    def _box_estado(self, rect, border_color, titulo, valor, f_lbl, f_val):
        self._painel(rect, border_color)
        lbl = f_lbl.render(titulo, True, border_color)
        val = f_val.render(valor, True, C_WHITE)
        self.tela.blit(lbl, (rect.x + 8, rect.y + 6))
        self.tela.blit(val, (rect.x + 8, rect.y + 24))

    def executar(self):
        clock = pygame.time.Clock()

        f_mono_lg = pygame.font.SysFont("Courier New", 19, bold=True)
        f_mono_sm = pygame.font.SysFont("Courier New", 13, bold=True)
        f_sans_md = pygame.font.SysFont("Arial", 13, bold=True)
        f_sans_sm = pygame.font.SysFont("Arial", 11, bold=True)
        f_btn_lg  = pygame.font.SysFont("Arial", 14, bold=True)
        f_emerg   = pygame.font.SysFont("Arial", 18, bold=True)
        f_tit     = pygame.font.SysFont("Arial", 11, bold=True)

        while self.rodando:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.rodando = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.tratar_cliques(event.pos)
                    self.editando_setpoint = self.box_setpoint.collidepoint(event.pos)
                elif event.type == pygame.KEYDOWN:
                    self.tratar_teclas(event)

            self.tela.fill(C_BG)

            # ── PAINEL TELEMETRIA
            self._painel(self.panel_tele, C_BORDER, radius=10)
            px, py = self.panel_tele.x + 12, self.panel_tele.y + 10

            hdr = f_sans_sm.render("MONITOR DE TELEMETRIA CRITICA (MQTT)", True, C_BORDER)
            self.tela.blit(hdr, (px, py)); py += 20

            # divisor fino
            pygame.draw.line(self.tela, C_BORDER,
                             (self.panel_tele.x + 8, py),
                             (self.panel_tele.right - 8, py), 1)
            py += 6

            dados_linhas = [
                (f"POSICAO  : {self.posicao_x:.2f} m",       C_GREEN),
                (f"VELOCID. : {self.velocidade_real:.2f} m/s", C_GREEN),
                (f"ACELERAC.: {self.aceleracao_real:.2f} m/s²", C_GREEN),
            ]
            for txt, cor in dados_linhas:
                self.tela.blit(f_mono_lg.render(txt, True, cor), (px, py))
                py += 28

            py += 4
            rodape = f"TEMPO: {self.tempo_sim:6.1f}s   FONTE: {self.fonte_telemetria}"
            self.tela.blit(f_mono_sm.render(rodape, True, C_MUTED), (px, py))

            # ── STATUS ────────────────────────────────────────────────────
            modo_txt = "AUTO (C++ PID)" if self.e_automatico else "MANUAL REMOTO"
            modo_cor = C_BORDER if self.e_automatico else C_ORANGE
            insp_txt = "INSPECAO: ATIVA" if self.e_inspecao else "INSPECAO: NORMAL"
            insp_cor = (255, 80, 80) if self.e_inspecao else C_GREEN

            sy = self.y_status
            self.tela.blit(f_sans_md.render(f"MODO: {modo_txt}", True, modo_cor), (16, sy))
            itxt = f_sans_md.render(insp_txt, True, insp_cor)
            self.tela.blit(itxt, (W - 16 - itxt.get_width(), sy))

            # status bar sutil
            stxt = f_sans_sm.render(self.status_texto, True, C_MUTED)
            self.tela.blit(stxt, (16, sy + 14))

            # ── BOTOES DE MODO ────────────────────────────────────────────
            auto_bg = C_BORDER if self.e_automatico else C_BTN_OFF
            man_bg  = C_ORANGE if not self.e_automatico else C_BTN_OFF
            self._btn(self.btn_auto, auto_bg, "◆  MODO AUTOMATICO", f_btn_lg)
            self._btn(self.btn_man,  man_bg,  "✎  ASSUMIR MANUAL",  f_btn_lg)

            # ── SETPOINT ──────────────────────────────────────────────────
            sp_border = C_GREEN if self.editando_setpoint else (60, 100, 150)
            self._painel(self.box_setpoint, sp_border)
            lbl_sp = f_tit.render("j_sp_velocidade  (m/s)", True, C_MUTED)
            val_sp = f_mono_lg.render(self.texto_setpoint + ("_" if self.editando_setpoint else ""), True, C_WHITE)
            self.tela.blit(lbl_sp, (self.box_setpoint.x + 8, self.box_setpoint.y + 5))
            self.tela.blit(val_sp, (self.box_setpoint.x + 8, self.box_setpoint.y + 22))

            self._btn(self.btn_sp_mais,   (34, 139, 34),   "+1",         f_btn_lg)
            self._btn(self.btn_sp_menos,  (130, 60, 10),   "−1",         f_btn_lg)

            # ── DIRECIONAL ────────────────────────────────────────────────
            dir_bg = (55, 100, 160) if not self.e_automatico else C_BTN_OFF
            self._btn(self.btn_left,  dir_bg,            "◀  ESQUERDA", f_btn_lg)
            self._btn(self.btn_stop,  (65, 72, 82),      "■  PARAR",    f_btn_lg)
            self._btn(self.btn_right, dir_bg,            "DIREITA  ▶",  f_btn_lg)

            # ── EMERGENCIA ────────────────────────────────────────────────
            pygame.draw.rect(self.tela, C_RED, self.btn_emerg, border_radius=8)
            etxt = f_emerg.render("⚠  PARADA DE EMERGENCIA", True, C_WHITE)
            self.tela.blit(etxt, etxt.get_rect(center=self.btn_emerg.center))

            # ── CAIXAS DE ESTADO ──────────────────────────────────────────
            b1_cor = C_BORDER if self.e_automatico else C_ORANGE
            b2_cor = (255, 80, 80) if self.e_inspecao else C_GREEN
            self._box_estado(self.box_inf_1, b1_cor,  "e_automatico", str(self.e_automatico), f_tit, f_btn_lg)
            self._box_estado(self.box_inf_2, b2_cor,  "e_inspecao",   str(self.e_inspecao),   f_tit, f_btn_lg)
            self._box_estado(self.box_inf_3, C_GREEN, "encoder",      str(self.encoder_estado), f_tit, f_btn_lg)

            # ── LIDAR RODAPE ──────────────────────────────────────────────
            lidar_txt = f"LiDAR: {self.distancia_lidar:.2f} m  |  confiança: {self.confianca_lidar:.2f}"
            self.tela.blit(f_sans_sm.render(lidar_txt, True, C_MUTED), (16, self.y_lidar))

            pygame.display.flip()
            clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    app = IHMSalaControle()
    app.executar()