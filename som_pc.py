import pyaudiowpatch as pyaudio
import numpy as np


TAMANHO_BLOCO = 1024


def scan_dispositivos_loopback():
    """
    Procura dispositivos de LOOPBACK -- ou seja, dispositivos que
    representam "o que está sendo reproduzido" (saída), disfarçados
    de entrada para que possamos gravar.

    No Windows, cada dispositivo de saída normal (alto-falante,
    fone, etc) tem uma versão "loopback" correspondente.
    """
    p = pyaudio.PyAudio()
    dispositivos = []

    try:
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info.get("isLoopbackDevice", False):
                dispositivos.append((i, info["name"], info))
    finally:
        p.terminate()

    return dispositivos


def open_som_pc(index):
    p = pyaudio.PyAudio()
    info = p.get_device_info_by_index(index)

    if not info.get("isLoopbackDevice", False):
        p.terminate()
        raise ValueError(f"O dispositivo de índice {index} não é um dispositivo de loopback válido")

    stream = p.open(
        format=pyaudio.paInt16,
        channels=int(info["maxInputChannels"]),
        rate=int(info["defaultSampleRate"]),
        frames_per_buffer=TAMANHO_BLOCO,
        input=True,
        input_device_index=index,
    )

    # Guardamos "p" junto pro poder fechar tudo depois
    return p, stream, int(info["maxInputChannels"]), int(info["defaultSampleRate"])


def capture_frame(stream):
    dados_brutos = stream.read(TAMANHO_BLOCO, exception_on_overflow=False)
    bloco = np.frombuffer(dados_brutos, dtype=np.int16)
    return bloco


def close_som_pc(p, stream):
    stream.stop_stream()
    stream.close()
    p.terminate()