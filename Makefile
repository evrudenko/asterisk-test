IMAGE_NAME=asterisk-python
CONTAINER_NAME=asterisk-container

.PHONY: build run stop logs shell clean

# Сборка Docker-образа
build:
	docker build -t $(IMAGE_NAME) .

# Запуск контейнера с пробросом портов
run:
	docker run -d --name $(CONTAINER_NAME) \
		-p 5060:5060/udp \
		-p 5060:5060/tcp \
		-p 5038:5038 \
		-p 8088:8088 \
		-p 10000-10050:10000-10050/udp \
		--rm \
		$(IMAGE_NAME)

# Остановка контейнера
stop:
	docker stop $(CONTAINER_NAME)

# Просмотр логов контейнера
logs:
	docker logs -f $(CONTAINER_NAME)

# Войти внутрь контейнера
shell:
	docker exec -it $(CONTAINER_NAME) bash

# Удалить образ и остановить контейнер
clean: stop
	docker rmi $(IMAGE_NAME) || true
