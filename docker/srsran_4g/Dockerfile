FROM ubuntu:latest

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    pkg-config \
    libfftw3-dev \
    libzmq3-dev \
    libmbedtls-dev \
    libsoapysdr-dev \
    soapysdr-tools \
    libboost-all-dev \
    libsctp-dev \
    lksctp-tools \
    libconfig++-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN mkdir build && cd build && cmake -DCMAKE_CXX_FLAGS="-Wno-error=array-bounds" ..  && make -j"$(nproc)"

# Default command
#CMD ["./build/apps/gnb/gnb", "-c", "/app/configs/gnb_zmq.yaml"]
