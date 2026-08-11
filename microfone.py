import sounddevice as sd
import numpy as np
 
 
TAXA_AMOSTRAGEM = 44100  # Hz, padrão de qualidade de CD
CANAIS = 1               # 1 = mono, 2 = estéreo
TAMANHO_BLOCO = 1024     # quantas amostras por captura
 
 
def scan_microfones():
    dispositivos = sd.query_devices()
    microfones = []
    for i, d in enumerate(dispositivos):
        if d['max_input_channels'] > 0:
            microfones.append((i, d['name']))
    return microfones
 
 
def open_microfone(index):
    dispositivos = sd.query_devices()
    if index < 0 or index >= len(dispositivos):
        raise ValueError(f"Não foi possível abrir o microfone de índice {index}")
    if dispositivos[index]['max_input_channels'] == 0:
        raise ValueError(f"O dispositivo de índice {index} não é um microfone (não tem entrada de áudio)")
 
    stream = sd.InputStream(
        device=index,
        channels=CANAIS,
        samplerate=TAXA_AMOSTRAGEM,
        blocksize=TAMANHO_BLOCO,
    )
    stream.start()
    return stream
 
 
def capture_frame(stream):
    dados, overflow = stream.read(TAMANHO_BLOCO)
    if overflow:
        print("Aviso: bloco de áudio perdido (overflow)")
    return dados
 
 
def close_microfone(stream):
    stream.stop()
    stream.close()
 
 
if __name__ == "__main__":
    print("Procurando microfones...")
    disponiveis = scan_microfones()
    print("Microfones encontrados:")
    for i, nome in disponiveis:
        print(f"  {i}: {nome}")
 
    if not disponiveis:
        print("Nenhum microfone encontrado.")
    else:
        indice_teste = disponiveis[0][0]
        print(f"Abrindo microfone {indice_teste} para teste (Ctrl+C para sair)...")
        print("Fale algo e observe o nível de volume abaixo:")
 
        stream = open_microfone(indice_teste)
        try:
            while True:
                bloco = capture_frame(stream)
                volume = np.abs(bloco).mean()
                barra = "#" * int(volume * 500)
                print(f"\rVolume: {barra:<50}", end="")
        except KeyboardInterrupt:
            print("\nEncerrando teste.")
        finally:
            close_microfone(stream)