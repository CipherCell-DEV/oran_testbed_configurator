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
    iproute2 \
    iputils-ping \
    nano \
    sudo \
    iperf3 \
    netcat-openbsd \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN chmod +x /app/ue_entrypoint.sh

RUN rm -rf build_docker && mkdir -p build_docker && cd build_docker && cmake -DCMAKE_CXX_FLAGS="-Wno-error=array-bounds" ..  && make -j"$(nproc)"

# Default command

#ENTRYPOINT ["/app/entrypoint.sh"]