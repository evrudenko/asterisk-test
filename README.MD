# Asterisk Test Project

This project is designed to test and demonstrate the functionality of the Asterisk system.

## Components

- **Asterisk Server**: The core component that handles VoIP communication.
- **ARI Handler**: Processes calls to Asterisk via ARI and redirects the RTP voice stream to the RTP Listener.
- **RTP Listener**: Listen to RTP stream, recognize pauses and translate speech into text.

## Prerequisites

- Docker and Docker Compose installed on your system.

## How to Run

1. Clone the repository.

2. Start the services using Docker Compose:
    ```bash
    docker compose up
    ```

3. Set up a connection to local Asterisk through your SIP client, such as Zoiper.

4. Call 100 and view Docker Compose logs to see real-time speech recognition results.
