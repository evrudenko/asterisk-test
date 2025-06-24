import asyncio
import logging
import random
import socket
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


class CallManager:

    _queue_worker_task: asyncio.Task | None = None
    _current_playback_task: asyncio.Task | None = None
    _response_playback_task_queue: asyncio.Queue | None = None

    def __init__(self, ip: str, port: int):
        """
        Initializes the Manager with the given IP address and port.

        :param ip: The IP address to bind the socket to.
        :param port: The port number to bind the socket to.
        """
        self._ip = ip
        self._port = port

    async def __aenter__(self) -> "CallManager":
        """
        Initializes the context manager by creating a UDP socket and binding it to the specified IP and port.
        This method is called when entering the context manager.

        :return: The instance of the Manager class.
        """
        # Create a UDP socket
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((self._ip, self._port))
        self._sock.setblocking(False)

        # Initialize the playback task queue
        self._response_playback_task_queue = asyncio.Queue()

        # Create a task to process the playback task queue
        self._queue_worker_task = asyncio.create_task(
            self._process_playback_task_queue()
        )

        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> bool:
        """
        Handles cleanup when exiting the context manager.
        Closes the socket and logs any exceptions that occurred.

        :param exc_type: The type of the exception raised, if any.
        :param exc_value: The value of the exception raised, if any.
        :param traceback: The traceback object, if any.
        :return: True to suppress the exception, False to propagate it.
        """
        # Log any exception that occurred
        if exc_type is not None:
            logger.error("An error occurred: %s", exc_value)

        self.cancel_play()

        # Cancel the queue worker task if it's running
        if self._queue_worker_task and not self._queue_worker_task.done():
            self._queue_worker_task.cancel()
            logger.info("Cancelled queue worker task.")

        # Close the socket
        self._sock.close()
        self._sock = None
        logger.info("Socket closed.")

        return True

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

    async def play_next(
        self,
        audio_data: bytes,
        addr: tuple[str, int],
        sample_rate: int = 8000,
        frame_duration_ms: int = 20,
    ) -> None:
        """
        Plays the given audio data to the specified address using RTP when the playback task queue is available.

        :param audio_data: The audio data to play.
        :param addr: The address (IP, port) to send the audio data to.
        :param sample_rate: The sample rate of the audio data, default is 8000 Hz.
        :param frame_duration_ms: The duration of each audio frame in milliseconds, default is 20 ms.
        :raises RuntimeError: If the playback task queue is not initialized.
        """
        if not self._response_playback_task_queue:
            raise RuntimeError("Playback task queue is not initialized.")

        await self._response_playback_task_queue.put(
            self._stream_bytes_to_socket(
                audio_data, addr, sample_rate, frame_duration_ms
            )
        )
        logger.info(
            "Current tasks in playback queue: %s",
            self._response_playback_task_queue.qsize(),
        )

    def is_playing(self) -> bool:
        """
        Checks if there are any playback tasks currently in the queue.

        :return: True if there are playback tasks in the queue, False otherwise.
        """
        if self._current_playback_task and not self._current_playback_task.done():
            return True
        if not self._response_playback_task_queue:
            return False
        return not self._response_playback_task_queue.empty()

    def cancel_play(self) -> None:
        """
        Cancels the current playback task if it is running.
        This method will remove all tasks from the playback queue.
        """
        if not self._response_playback_task_queue:
            return

        # Cancel all tasks in the playback task queue
        self._empty_playback_task_queue()
        logger.info("Cancelled all playback tasks in the queue.")

        # Cancel the current playback task if it is running
        if self._current_playback_task and not self._current_playback_task.done():
            self._current_playback_task.cancel()
            logger.info("Cancelled current playback task.")

    async def _process_playback_task_queue(self) -> None:
        logger.info("Starting playback task queue worker...")
        while True:
            self._current_playback_task = None
            logger.info("Waiting for playback task in the queue...")
            playback_coroutine = await self._response_playback_task_queue.get()

            logger.info("Playback task received, processing...")
            self._current_playback_task = asyncio.create_task(
                self._run_playback_task(playback_coroutine)
            )
            try:
                await self._current_playback_task
            except asyncio.CancelledError:
                logger.info("Playback task was cancelled.")

    async def _run_playback_task(self, playback_task) -> None:
        """
        Runs the given playback task and handles any exceptions that may occur.

        :param playback_task: The playback task to run.
        """
        try:
            await playback_task
        except Exception as e:
            logger.exception(f"Playback task raised an exception: {e}")
        finally:
            self._response_playback_task_queue.task_done()

    def _empty_playback_task_queue(self) -> None:
        """Empties the given asyncio queue by consuming all items without processing them."""
        if not self._response_playback_task_queue:
            return

        while not self._response_playback_task_queue.empty():
            self._response_playback_task_queue.get_nowait()
            self._response_playback_task_queue.task_done()

    async def _stream_bytes_to_socket(
        self,
        audio_data: bytes,
        addr: tuple[str, int],
        sample_rate: int = 8000,
        frame_duration_ms: int = 20,
    ) -> None:
        """
        Streams audio data as RTP packets to the specified address.

        :param audio_data: The audio data to stream.
        :param addr: The address (IP, port) to send the audio data to.
        :param sample_rate: The sample rate of the audio data, default is 8000 Hz.
        :param frame_duration_ms: The duration of each audio frame in milliseconds, default is 20 ms.
        """
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
            # logger.info(
            #     "Sending RTP packet: seq=%d, timestamp=%d, size=%d",
            #     sequence_number,
            #     timestamp,
            #     len(packet),
            # )
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
