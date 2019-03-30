.PHONY: dock \
	dock-whl \
	dock-test \
	local-whl \
	test-install \
	scp-tnet \
	unit-test

scp-tnet:
	scp dist/tnetserver-1.0-py3-none-any.whl tgard@192.168.1.171:/home/tgard

local-whl:
	python3 setup.py sdist bdist_wheel
	sudo pip3 install --upgrade dist/tnetserver-1.0-py3-none-any.whl

local-test:
	pytest $$(pwd)/test/unit/test_api.py --env $$(pwd)/test/unit/testenv.json

dock:
	sudo docker build --file=./docker/Dockerfile --tag=tnet-test .

dock-whl:
	sudo docker run -v $$(pwd)/tnetserver:/build/tnetserver/ \
	 	-v $$(pwd)/setup.py:/build/setup.py \
		-v $$(pwd)/scripts:/build/scripts/ \
		-ti tnet-test /build/scripts/install.sh

dock-test:
	sudo docker run -v $$(pwd)/test:/build/test/ \
	 	-v $$(pwd)/scripts:/build/scripts/ \
	 	-ti tnet-test /build/scripts/unit-tests.sh
