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