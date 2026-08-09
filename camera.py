import cv2
 
def scan_camera(max_indices=5):
    cameras = []
 
    for index in range(max_indices):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            cameras.append(index)
            cap.release()
    return cameras
 
def open_camera(index):
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        raise ValueError(f"Não foi possível abrir a câmera de índice {index}")
    return cap 
 
def capture_frame(cap):
    ret, frame = cap.read()
    if not ret:
        raise ValueError("Não foi possível capturar o frame da câmera")
    return frame
 
 
def close_camera(cap):  
    cap.release()
 
if __name__ == "__main__":
    print("Procurando câmeras...")
    disponiveis = scan_camera()
    print(f"Câmeras encontradas: {disponiveis}")
 
    if not disponiveis:
        print("Nenhuma câmera encontrada.")
    else:
        indice_teste = disponiveis[0]
        print(f"Abrindo câmera {indice_teste} para teste (aperte 'q' para sair)...")
 
        cap = open_camera(indice_teste)
        while True:
            try:
                frame = capture_frame(cap)
            except ValueError as e:
                print(f"Erro ao capturar frame: {e}")
                break
 
            cv2.imshow("Teste de camera", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
 
        close_camera(cap)
        cv2.destroyAllWindows()