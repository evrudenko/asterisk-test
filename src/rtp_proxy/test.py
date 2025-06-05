import asyncio
import socket

RTP_PORT = 10000
SIP_PORT = 5060
IP_ADDRESS = "0.0.0.0"  # Подставь внешний IP, если вызываешь извне


# RTP listener coroutine
async def handle_rtp():
    print(f"[RTP] Listening on {IP_ADDRESS}:{RTP_PORT}")
    rtp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rtp_sock.bind((IP_ADDRESS, RTP_PORT))
    rtp_sock.setblocking(False)

    loop = asyncio.get_event_loop()
    while True:
        try:
            data, addr = await loop.sock_recvfrom(rtp_sock, 2048)
            print(f"[RTP] {len(data)} bytes from {addr}")
        except Exception as e:
            print(f"[RTP] Error: {e}")


# Very basic SIP server
async def handle_sip():
    print(f"[SIP] Listening on {IP_ADDRESS}:{SIP_PORT}")
    sip_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sip_sock.bind((IP_ADDRESS, SIP_PORT))
    sip_sock.setblocking(False)

    loop = asyncio.get_event_loop()
    while True:
        data, addr = await loop.sock_recvfrom(sip_sock, 2048)
        text = data.decode(errors="ignore")
        print(f"[SIP] Received from {addr}:\n{text}")

        if "INVITE" in text:
            # Extract Call-ID, From-tag, etc.
            call_id = next(
                (
                    line
                    for line in text.splitlines()
                    if line.lower().startswith("call-id:")
                ),
                None,
            )
            from_tag = next(
                (
                    line
                    for line in text.splitlines()
                    if line.lower().startswith("from:")
                ),
                None,
            )
            to = next(
                (line for line in text.splitlines() if line.lower().startswith("to:")),
                None,
            )
            via = next(
                (line for line in text.splitlines() if line.lower().startswith("via:")),
                None,
            )
            cseq = next(
                (
                    line
                    for line in text.splitlines()
                    if line.lower().startswith("cseq:")
                ),
                None,
            )

            sdp = f"""v=0
o=rtpproxy 12345 12345 IN IP4 {IP_ADDRESS}
s=RTP Proxy
c=IN IP4 {IP_ADDRESS}
t=0 0
m=audio {RTP_PORT} RTP/AVP 0
a=rtpmap:0 PCMU/8000
"""

            response = f"""SIP/2.0 200 OK
{via}
{to};tag=123456
{from_tag}
{call_id}
{cseq}
Content-Type: application/sdp
Content-Length: {len(sdp)}

{sdp}"""

            await loop.sock_sendto(sip_sock, response.encode(), addr)
            print(f"[SIP] Sent 200 OK to {addr}")


# Main asyncio entrypoint
async def main():
    await asyncio.gather(
        handle_rtp(),
        handle_sip(),
    )


if __name__ == "__main__":
    asyncio.run(main())
