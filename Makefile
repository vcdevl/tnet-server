.PHONY: dock-build \
	dock-whl \
	local-whl \
	scp-tnet

scp-tnet:
	scp dist/tnetserver-1.0-py3-none-any.whl tgard@192.168.1.171:/home/tgard

local-whl:
	python3 setup.py sdist bdist_wheel

dock:
	docker build --file=./docker/Dockerfile --tag=tnetwhl .

whl:
	docker run -ti tnetwhl
