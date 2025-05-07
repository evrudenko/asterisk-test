import socket
import subprocess
import time
from gtts import gTTS

RTP_IP = "127.0.0.1"
RTP_PORT = 4000

def generate_tts(text, wav_path):
    tts = gTTS(text, lang='ru')
    tts.save(wav_path)

def stream_audio_via_rtp(wav_path):
    # ffmpeg: WAV → raw PCM 16-bit → read by Python
    ffmpeg = subprocess.Popen(
        ['ffmpeg', '-i', wav_path, '-f', 's16le', '-ar', '16000', '-ac', '1', '-'],
        stdout=subprocess.PIPE
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        data = ffmpeg.stdout.read(320)  # 20 ms of audio at 16 kHz, 16-bit
        if not data:
            break
        sock.sendto(data, (RTP_IP, RTP_PORT))
        time.sleep(0.02)  # 20 ms

    sock.close()

if __name__ == "__main__":
    text = "Привет, вы позвонили в автоматическую систему. Скажите что-нибудь."
    wav_path = "tts.wav"
    generate_tts(text, wav_path)
    stream_audio_via_rtp(wav_path)
