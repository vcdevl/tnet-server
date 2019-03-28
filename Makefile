.PHONY: dock \
	whl

dock:
	docker build --file=./docker/Dockerfile --tag=tnetwhl .

whl:
	docker run -ti tnetwhl
