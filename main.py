import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from collections import deque

import cv2
import numpy as np
from PIL import Image, ImageTk

import camera
import tela
import microfone
import som_pc


class TelaSelecao(tk.Tk):
    """
    Janela inicial: deixa o usuário escolher tela, câmera, microfone
    e som do PC através de dropdowns, antes de iniciar a captura.
    """

    def __init__(self):
        super().__init__()
        self.title("Configurar fontes")
        self.geometry("420x300")
        self.resizable(False, False)

        self.escolha = None

        self.monitores = tela.scan_monitors()
        self.cameras = camera.scan_camera()
        self.microfones = microfone.scan_microfones()
        self.dispositivos_loopback = som_pc.scan_dispositivos_loopback()

        self._montar_interface()

    def _montar_interface(self):
        padding = {"padx": 20, "pady": 10}

        tk.Label(self, text="Tela").grid(row=0, column=0, sticky="w", **padding)
        opcoes_tela = [
            f"Monitor {i} ({m['width']}x{m['height']})"
            for i, m in enumerate(self.monitores, start=1)
        ]
        self.combo_tela = ttk.Combobox(self, values=opcoes_tela, state="readonly", width=28)
        self.combo_tela.grid(row=0, column=1, **padding)
        if opcoes_tela:
            self.combo_tela.current(0)

        tk.Label(self, text="Câmera").grid(row=1, column=0, sticky="w", **padding)
        opcoes_camera = [f"Câmera {i}" for i in self.cameras]
        self.combo_camera = ttk.Combobox(self, values=opcoes_camera, state="readonly", width=28)
        self.combo_camera.grid(row=1, column=1, **padding)
        if opcoes_camera:
            self.combo_camera.current(0)

        tk.Label(self, text="Microfone").grid(row=2, column=0, sticky="w", **padding)
        opcoes_microfone = [f"{nome}" for _, nome in self.microfones]
        self.combo_microfone = ttk.Combobox(self, values=opcoes_microfone, state="readonly", width=28)
        self.combo_microfone.grid(row=2, column=1, **padding)
        if opcoes_microfone:
            self.combo_microfone.current(0)

        tk.Label(self, text="Som do PC").grid(row=3, column=0, sticky="w", **padding)
        opcoes_som_pc = [f"{nome}" for _, nome, _ in self.dispositivos_loopback]
        self.combo_som_pc = ttk.Combobox(self, values=opcoes_som_pc, state="readonly", width=28)
        self.combo_som_pc.grid(row=3, column=1, **padding)
        if opcoes_som_pc:
            self.combo_som_pc.current(0)

        botao = tk.Button(self, text="Iniciar transmissão", command=self._confirmar)
        botao.grid(row=4, column=0, columnspan=2, pady=20)

    def _confirmar(self):
        if not (self.monitores and self.cameras and self.microfones and self.dispositivos_loopback):
            messagebox.showerror(
                "Fonte faltando",
                "Não foi possível encontrar todas as fontes necessárias "
                "(tela, câmera, microfone, som do PC)."
            )
            return

        indice_monitor = self.combo_tela.current() + 1
        indice_camera = self.cameras[self.combo_camera.current()]
        indice_microfone = self.microfones[self.combo_microfone.current()][0]
        indice_som_pc = self.dispositivos_loopback[self.combo_som_pc.current()][0]

        self.escolha = {
            "monitor": indice_monitor,
            "camera": indice_camera,
            "microfone": indice_microfone,
            "som_pc": indice_som_pc,
        }
        self.destroy()


class CapturaAudioContinua:
    """
    Fica capturando áudio em segundo plano (numa thread própria),
    guardando um pequeno histórico dos últimos blocos capturados,
    cada um com seu timestamp.

    Isso permite, na hora de mostrar um frame de vídeo, "casar" ele
    com o bloco de áudio cujo timestamp está mais próximo do timestamp
    do vídeo -- em vez de simplesmente pegar o último bloco disponível,
    que pode estar levemente atrasado ou adiantado.
    """

    TAMANHO_HISTORICO = 50  # quantos blocos recentes guardamos

    def __init__(self, stream, funcao_captura):
        self.stream = stream
        self.funcao_captura = funcao_captura
        self.lock = threading.Lock()
        self.historico = deque(maxlen=self.TAMANHO_HISTORICO)  # cada item: (timestamp, bloco)
        self.rodando = True
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def iniciar(self):
        self.thread.start()

    def _loop(self):
        while self.rodando:
            try:
                bloco = self.funcao_captura(self.stream)
            except ValueError as e:
                print(f"Erro ao capturar áudio: {e}")
                continue

            with self.lock:
                self.historico.append((time.time(), bloco))

    def pegar_ultimo(self):
        with self.lock:
            if not self.historico:
                return None, None
            return self.historico[-1][1], self.historico[-1][0]

    def pegar_mais_proximo(self, timestamp_alvo):
        """
        Procura, no histórico, o bloco de áudio cujo timestamp está
        mais próximo do timestamp informado (geralmente o horário em
        que um frame de vídeo foi capturado).

        Devolve (bloco, timestamp_do_bloco, diferenca_em_segundos).
        """
        with self.lock:
            if not self.historico:
                return None, None, None

            melhor = min(self.historico, key=lambda item: abs(item[0] - timestamp_alvo))
            timestamp_bloco, bloco = melhor
            diferenca = timestamp_bloco - timestamp_alvo
            return bloco, timestamp_bloco, diferenca

    def parar(self):
        self.rodando = False
        self.thread.join(timeout=1)


class JanelaPreview(tk.Tk):
    """
    Janela principal da transmissão: mostra o vídeo ao vivo embutido
    na própria interface, com botões para trocar a fonte de vídeo
    (tela/câmera) e a fonte de áudio (microfone/som do pc), em vez
    de teclas.
    """

    LARGURA_SAIDA = 960
    ALTURA_SAIDA = 540
    INTERVALO_MS = 33  # ~30 frames por segundo

    def __init__(self, escolha):
        super().__init__()
        self.title("Preview - Transmissão")
        self.resizable(False, False)

        # --- Abre todas as fontes escolhidas ---
        self.cap = camera.open_camera(escolha["camera"])
        self.sct, self.monitor = tela.open_monitor(escolha["monitor"])

        self.stream_microfone = microfone.open_microfone(escolha["microfone"])
        self.p_som_pc, self.stream_som_pc, _, _ = som_pc.open_som_pc(escolha["som_pc"])

        self.captura_microfone = CapturaAudioContinua(self.stream_microfone, microfone.capture_frame)
        self.captura_som_pc = CapturaAudioContinua(self.stream_som_pc, som_pc.capture_frame)
        self.captura_microfone.iniciar()
        self.captura_som_pc.iniciar()

        self.fonte_video = "tela"       # ou "camera"
        self.fonte_audio = "microfone"  # ou "som_pc"

        # Indica o motivo do fechamento: True = usuário quer voltar
        # e editar as fontes, False = usuário quer sair de vez
        self.voltar_para_selecao = False

        self._montar_interface()

        self.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        self._atualizar_frame()

    def _montar_interface(self):
        # --- Label onde o vídeo é desenhado ---
        self.label_video = tk.Label(self)
        self.label_video.grid(row=0, column=0, columnspan=4)

        # --- Botões de fonte de vídeo ---
        self.botao_tela = tk.Button(
            self, text="Tela", width=14,
            command=lambda: self._definir_fonte_video("tela")
        )
        self.botao_tela.grid(row=1, column=0, padx=10, pady=10)

        self.botao_camera = tk.Button(
            self, text="Câmera", width=14,
            command=lambda: self._definir_fonte_video("camera")
        )
        self.botao_camera.grid(row=1, column=1, padx=10, pady=10)

        # --- Botões de fonte de áudio ---
        self.botao_microfone = tk.Button(
            self, text="Microfone", width=14,
            command=lambda: self._definir_fonte_audio("microfone")
        )
        self.botao_microfone.grid(row=1, column=2, padx=10, pady=10)

        self.botao_som_pc = tk.Button(
            self, text="Som do PC", width=14,
            command=lambda: self._definir_fonte_audio("som_pc")
        )
        self.botao_som_pc.grid(row=1, column=3, padx=10, pady=10)

        # --- Indicador de status (fonte ativa + volume) ---
        self.label_status = tk.Label(self, text="", font=("Segoe UI", 10))
        self.label_status.grid(row=2, column=0, columnspan=4, pady=(0, 10))

        # --- Botão para voltar e editar as fontes escolhidas ---
        self.botao_editar = tk.Button(
            self, text="⬅ Editar fontes", width=20,
            command=self._voltar_para_selecao
        )
        self.botao_editar.grid(row=3, column=0, columnspan=4, pady=(0, 15))

        self._atualizar_botoes()

    def _definir_fonte_video(self, fonte):
        self.fonte_video = fonte
        self._atualizar_botoes()

    def _definir_fonte_audio(self, fonte):
        self.fonte_audio = fonte
        self._atualizar_botoes()

    def _atualizar_botoes(self):
        # Realça visualmente qual fonte está ativa em cada categoria
        self.botao_tela.config(relief=(tk.SUNKEN if self.fonte_video == "tela" else tk.RAISED))
        self.botao_camera.config(relief=(tk.SUNKEN if self.fonte_video == "camera" else tk.RAISED))
        self.botao_microfone.config(relief=(tk.SUNKEN if self.fonte_audio == "microfone" else tk.RAISED))
        self.botao_som_pc.config(relief=(tk.SUNKEN if self.fonte_audio == "som_pc" else tk.RAISED))

    def _atualizar_frame(self):
        try:
            if self.fonte_video == "tela":
                frame = tela.capture_frame(self.sct, self.monitor)
            else:
                frame = camera.capture_frame(self.cap)
        except ValueError as e:
            print(f"Erro ao capturar frame: {e}")
            self.after(self.INTERVALO_MS, self._atualizar_frame)
            return

        frame = cv2.resize(frame, (self.LARGURA_SAIDA, self.ALTURA_SAIDA))
        timestamp_video = time.time()

        # Converte de BGR (OpenCV) para RGB (Pillow/Tkinter) antes de exibir
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        imagem = Image.fromarray(frame_rgb)
        imagem_tk = ImageTk.PhotoImage(image=imagem)

        # Precisamos guardar a referência, senão o Tkinter "esquece"
        # a imagem e a label fica em branco (efeito colateral conhecido)
        self.label_video.imgtk = imagem_tk
        self.label_video.configure(image=imagem_tk)

        # --- Áudio: busca o bloco cujo timestamp está mais próximo
        # do timestamp do frame de vídeo, em vez do "último disponível" ---
        if self.fonte_audio == "microfone":
            bloco_audio, _, diferenca = self.captura_microfone.pegar_mais_proximo(timestamp_video)
        else:
            bloco_audio, _, diferenca = self.captura_som_pc.pegar_mais_proximo(timestamp_video)

        volume = 0.0
        if bloco_audio is not None:
            volume = float(np.abs(bloco_audio).mean())

        diferenca_ms = f"{diferenca * 1000:+.0f}ms" if diferenca is not None else "--"

        self.label_status.config(
            text=(
                f"Vídeo: {self.fonte_video}   |   Áudio: {self.fonte_audio}   |   "
                f"Volume: {volume:.1f}   |   Sincronia: {diferenca_ms}"
            )
        )

        self.after(self.INTERVALO_MS, self._atualizar_frame)

    def _liberar_recursos(self):
        """Para as threads de áudio e fecha câmera, monitor e streams de áudio."""
        self.captura_microfone.parar()
        self.captura_som_pc.parar()

        camera.close_camera(self.cap)
        tela.close_monitor(self.sct)
        microfone.close_microfone(self.stream_microfone)
        som_pc.close_som_pc(self.p_som_pc, self.stream_som_pc)

    def _voltar_para_selecao(self):
        self.voltar_para_selecao = True
        self._liberar_recursos()
        self.destroy()

    def _ao_fechar(self):
        # Fechado pelo "X" da janela -- sai do programa de vez
        self.voltar_para_selecao = False
        self._liberar_recursos()
        self.destroy()


def main():
    while True:
        tela_selecao = TelaSelecao()
        tela_selecao.mainloop()

        if tela_selecao.escolha is None:
            print("Nenhuma fonte selecionada. Encerrando.")
            return

        janela_preview = JanelaPreview(tela_selecao.escolha)
        janela_preview.mainloop()

        if not janela_preview.voltar_para_selecao:
            # Usuário fechou a janela de vez (não pediu para editar)
            return
        # Caso contrário, o loop reinicia e abre a tela de seleção de novo


if __name__ == "__main__":
    main()