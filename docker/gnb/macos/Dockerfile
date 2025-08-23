FROM ubuntu:latest

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libdw-dev \
    binutils-dev \ 
    libdwarf-dev \
    libelf-dev \
    pkg-config \
    libfftw3-dev \
    libyaml-cpp-dev \
    libmbedtls-dev \
    doxygen \
    libsctp-dev \
    libzmq3-dev \
    libzmq5 \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN mkdir build && cd build && cmake .. \
  -DENABLE_UHD=OFF \
  -DENABLE_ARMPL=OFF \
  -DENABLE_EXPORT=ON \
  -DENABLE_ZEROMQ=ON \
  -DCMAKE_CXX_FLAGS="-Wno-error=pessimizing-move" \
  && make -j"$(nproc)"

# Default command
CMD ["./build/apps/gnb/gnb", "-c", "/app/configs/gnb_zmq.yaml"]
