import mss
import numpy as np
import cv2

def scan_monitors():
    with mss.mss() as sct:
        monitores = sct.monitors[1:]  # ignora o índice 0 ("todos juntos")
    return monitores


def open_monitor(index):
    sct = mss.mss()
    monitores = sct.monitors
    if index < 1 or index >= len(monitores):
        raise ValueError(f"Não foi possível abrir o monitor de índice {index}")
    monitor = monitores[index]
    return sct, monitor


def capture_frame(sct, monitor):
    img = sct.grab(monitor)
    if img is None:
        raise ValueError("Não foi possível capturar o frame da tela")
    frame = np.array(img)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    return frame


def close_monitor(sct):
    sct.close()