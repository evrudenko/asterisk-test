import requests


class AriClient:
    """ARI Client."""

    def __init__(self, host: str, port: int, username: str = "ariuser", password: str = "ariuser"):
        """
        Args:
            host (str): Hostname of the Asterisk server.
            port (int): Port of the Asterisk ARI interface.
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def channels_external_media(self, channel_id: str, app: str, external_host: str, format: str = "slin16"):
        """
        Create an external media channel.
        Args:
            channel_id (str): The ID of the channel.
            app (str): The application name.
            external_host (str): Hostname/IP:port of external host.
            format (str): Format to encode audio in. Default is 'slin16'.
        """
        url = f"http://{self.host}:{self.port}/ari/channels/externalMedia"
        params = {
            "channelId": channel_id,
            "app": app,
            "external_host": external_host,
            "format": format,
            "encapsulation": "rtp",
            "transport": "udp",
            "connection_type": "client",
            "direction": "both",
        }
        print("URL:", url)
        response = requests.post(url, params=params, auth=(self.username, self.password))
        if response.status_code == 200:
            print("✅ ExternalMedia создан")
        else:
            print(f"⚠️ Ошибка externalMedia: {response.status_code} - {response.text}")
    
    def originate_channel(self, endpoint: str, app: str, format: str = "slin16") -> str | None:
        """
        Originate a channel.
        Args:
            endpoint (str): The endpoint to originate the channel to.
            app (str): The application name.
            format (str): Audio format to use.
        """
        url = f"http://{self.host}:{self.port}/ari/channels"
        data = {
            "endpoint": endpoint,
            "app": app,
            # "formats": format,
        }
        print("URL:", url)
        print("Data:", data)
        response = requests.post(url, json=data, auth=(self.username, self.password))
        if response.status_code == 200:
            print("✅ Channel originated")
            return response.json().get("id")
        else:
            print(f"⚠️ Ошибка originate: {response.status_code} - {response.text}")
            return
