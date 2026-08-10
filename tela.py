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


if __name__ == "__main__":
    print("Procurando monitores...")
    disponiveis = scan_monitors()
    print(f"Monitores encontrados: {len(disponiveis)}")
    for i, m in enumerate(disponiveis, start=1):
        print(f"  {i}: {m['width']}x{m['height']}")

    if not disponiveis:
        print("Nenhum monitor encontrado.")
    else:
        indice_teste = 1
        print(f"Abrindo monitor {indice_teste} para teste (aperte 'q' para sair)...")

        sct, monitor = open_monitor(indice_teste)
        while True:
            try:
                frame = capture_frame(sct, monitor)
            except ValueError as e:
                print(f"Erro ao capturar frame: {e}")
                break

            preview = cv2.resize(frame, (960, 540))
            cv2.imshow("Teste de tela", preview)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        close_monitor(sct)
        cv2.destroyAllWindows()