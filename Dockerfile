FROM debian:bullseye

# Установка зависимостей
RUN apt-get update && apt-get install -y \
    asterisk \
    asterisk-modules \
    curl \
    net-tools \
    vim \
    iputils-ping \
    && apt-get clean

# Копируем конфиги
COPY asterisk/ /etc/asterisk/

# Открываем порты (SIP, RTP, AMI, ARI)
EXPOSE 5060/udp 5060/tcp 5038 8088

CMD ["asterisk", "-f"]
