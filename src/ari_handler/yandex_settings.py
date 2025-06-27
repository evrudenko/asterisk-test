from pydantic import Field
from pydantic_settings import BaseSettings


class YandexSettings(BaseSettings):
    service_account_id: str = Field(..., validation_alias="YANDEX_SERVICE_ACCOUNT_ID")
    sa_key_id: str = Field(..., validation_alias="YANDEX_SA_KEY_ID")
    private_key: str = Field(..., validation_alias="YANDEX_PRIVATE_KEY")
    folder_id: str = Field(..., validation_alias="YANDEX_FOLDER_ID")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
