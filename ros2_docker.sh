#!/usr/bin/env bash

set -e

CONTAINER_NAME=ros_humble_ai
IMAGE_NAME=ros:humble-ros-base-1.0
HOST_WS_DIR="$HOME/cgp_ws"

exists=$(docker ps -a --filter "name=^/${CONTAINER_NAME}$" --format '{{.Names}}' | wc -l)

if [ "$exists" -ne 0 ]; then
    running=$(docker ps --filter "name=^/${CONTAINER_NAME}$" --format '{{.Names}}' | wc -l)
    if [ "$running" -eq 0 ]; then
        echo "Container exists but is stopped. Starting..."
        docker start -ai "${CONTAINER_NAME}"
        exit 0
    else
        echo "Container '${CONTAINER_NAME}' is already running. Attaching..."
        docker exec -it "${CONTAINER_NAME}" bash
        exit 0
    fi
fi

mkdir -p "${HOST_WS_DIR}"

xhost +

docker run -it \
    --name "${CONTAINER_NAME}" \
    --net=host \
    --privileged \
    --env="DISPLAY" \
    --env="QT_X11_NO_MITSHM=1" \
    -e PULSE_SERVER=unix:/run/user/1000/pulse/native \
    -e ALSA_CARD=0 \
    -v /run/user/1000/pulse:/run/user/1000/pulse:ro \
    -v ~/.config/pulse:/root/.config/pulse:ro \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v $HOME/.Xauthority:/root/.Xauthority \
    -e XAUTHORITY=/root/.Xauthority \
    --security-opt apparmor:unconfined \
    -v /home/pi/temp:/root/temp \
    -v "${HOST_WS_DIR}:/root/cgp_ws:rw" \
    --device=/dev/video0 \
    --device=/dev/bus/usb \
    --device=/dev/snd \
    -v /dev/mic:/dev/mic \
    "${IMAGE_NAME}" \
    /bin/bash -lc "cd ~; exec bash"