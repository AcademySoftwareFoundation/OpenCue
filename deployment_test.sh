echo "Launching cuebot server and rqd hosts"

#podman build -f cuebot/Docker-file-spi-mine -t test_integration

#podman build -f rqd/Dockerfile-e2e -t rqd_test_image
#podman create --name=rqd_test_hostlocalhost/rqd_test_image:latest && podman start rqd_test_host




#replace docker stack with a pod containing a cuebot and an rqd
#podman run <quebot> --add-host <rqd>

#sudo docker stack deploy -c stack_test.yml opencue

echo "Setting env variables for pyoutline"
export RQD_TEST_HOST= rqd_test_host
export USE_OPENCUE=1
export CUEBOT_HOSTS=opencuetest01-vm
export SHOW=swtest
export SHOT=home

echo "Launching job in spk environment"
spk env opencue pyoutline --local
 ./test_job_e2e.py
