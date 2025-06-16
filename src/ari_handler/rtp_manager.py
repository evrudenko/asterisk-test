import asyncio
import logging
import queue
import random
import socket
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


class RTPManager:
    """
    RTPManager is a class for managing RTP (Real-time Transport Protocol) streams.
    It provides methods to receive audio data from an RTP stream and to send audio data
    to a specified address using RTP.
    """

    _play_task: asyncio.Task | None = None

    def __init__(self, ip: str, port: int):
        """
        Initializes the RTPManager with the given IP address and port.

        :param ip: The IP address to bind the socket to.
        :param port: The port number to bind the socket to.
        """
        self._init_socket(ip, port)

    async def audio_channel(
        self, packet_size: int = 2048
    ) -> AsyncGenerator[tuple[bytes, tuple[str, int]], None]:
        """
        Asynchronous generator for receiving audio data from an RTP stream.

        :param packet_size: The size of the packet to receive, default is 2048 bytes.
        :rtype: AsyncGenerator[tuple[bytes, tuple[str, int]], None]
        :return: An asynchronous generator that yields tuples of audio data and the sender's address.
        """
        if not self._sock:
            raise RuntimeError("Socket is not initialized.")
        if packet_size < 12:
            raise ValueError(
                "Packet size must be at least 12 bytes to accommodate RTP header."
            )
        loop = asyncio.get_running_loop()
        while True:
            data, addr = await loop.sock_recvfrom(self._sock, packet_size)
            if not data:  # TODO if call muted data can be empty
                break
            yield data[12:], addr

    async def play(
        self,
        audio_data: bytes,
        addr: tuple[str, int],
        sample_rate: int = 8000,
        frame_duration_ms: int = 20,
    ) -> None:
        """
        Streams audio data to the specified address using RTP.

        :param audio_data: The audio data to stream.
        :param addr: The address (IP, port) to send the audio data to.
        :param sample_rate: The sample rate of the audio data, default is 8000 Hz.
        :param frame_duration_ms: The duration of each audio frame in milliseconds, default is 20 ms.
        """
        if not self._sock:
            raise RuntimeError("Socket is not initialized.")

        # Cancel any existing play task if it's running
        if self._play_task and not self._play_task.done():
            self._play_task.cancel()
            logger.info("Cancelled existing play task.")

        # Create a new task to stream the audio data
        logger.info(
            f"Starting RTP stream to {addr} with sample rate {sample_rate} Hz and frame duration {frame_duration_ms} ms."
        )
        self._play_task = asyncio.create_task(
            self._stream_bytes(audio_data, addr, sample_rate, frame_duration_ms)
        )

    def is_playing(self) -> bool:
        """
        Checks if the RTP play task is currently running.

        :return: True if the play task is running, False otherwise.
        """
        return self._play_task is not None and not self._play_task.done()

    def cancel_play(self):
        """Cancels the current RTP play task if it is running."""
        if self.is_playing():
            self._play_task.cancel()
            self._play_task = None
            logger.info("Cancelled RTP play task.")
        else:
            logger.info("No RTP play task to cancel.")

    def close(self):
        """Closes the socket."""
        if self._sock:
            self._sock.close()
            self._sock = None
            logger.info("Socket closed.")

    def _init_socket(self, ip: str, port: int):
        """
        Initializes the UDP socket for receiving RTP packets.

        :param ip: The IP address to bind the socket to.
        :param port: The port number to bind the socket to.
        """
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((ip, port))
        self._sock.setblocking(False)

    async def _stream_bytes(
        self,
        audio_data: bytes,
        addr: tuple[str, int],
        sample_rate: int = 8000,
        frame_duration_ms: int = 20,
    ) -> None:
        loop = asyncio.get_running_loop()

        frame_size = int(sample_rate / 1000 * frame_duration_ms)
        rtp_header = self._generate_initial_rtp_header()

        sequence_number = 0
        timestamp = 0
        for i in range(0, len(audio_data), frame_size):
            payload = audio_data[i : i + frame_size]

            # Update RTP header with sequence number and timestamp
            rtp_header[2:4] = sequence_number.to_bytes(2, "big")
            rtp_header[4:8] = timestamp.to_bytes(4, "big")

            packet = rtp_header + payload
            await loop.sock_sendto(self._sock, packet, addr)

            sequence_number += 1
            timestamp += frame_size

            await asyncio.sleep(frame_duration_ms / 1000)

    def _generate_initial_rtp_header(self):
        """
        Generates an initial RTP header with a random SSRC.

        :return: A bytearray representing the RTP header.
        """
        ssrc = random.randint(0, 0xFFFFFFFF)
        return bytearray(
            [
                0x80,  # Version 2, no padding, no extension
                0x00,  # Payload type
                0x00,
                0x00,  # Sequence number
                0x00,
                0x00,
                0x00,
                0x00,  # Timestamp
                (ssrc >> 24) & 0xFF,
                (ssrc >> 16) & 0xFF,
                (ssrc >> 8) & 0xFF,
                ssrc & 0xFF,
            ]
        )
