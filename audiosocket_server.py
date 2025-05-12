import socket
import threading
import time
# from pydub import AudioSegment

HOST = '0.0.0.0'  # слушать на всех интерфейсах
PORT = 8080

def handle_client(conn, addr):
    print(f"[+] New connection from {addr}")

    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            # Здесь вы можете обрабатывать аудио-данные, например, сохранять или отправлять дальше
            print(f"Received {len(data)} bytes")
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        conn.close()
        print(f"[-] Connection from {addr} closed")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[+] AudioSocket server listening on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


# def send_audio_data(data):
#     # Загрузите и конвертируйте WAV в raw PCM
#     sound = AudioSegment.from_wav("message.wav")
#     raw_data = sound.set_frame_rate(8000).set_channels(1).set_sample_width(2).raw_data

#     # Отправка через сокет
#     with socket.create_connection(("localhost", 12345)) as s:  # или аудиосокет-порт
#         s.sendall(raw_data)


if __name__ == '__main__':
    start_server()
