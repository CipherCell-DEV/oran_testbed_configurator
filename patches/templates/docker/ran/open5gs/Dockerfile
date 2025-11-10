FROM ubuntu:latest as base

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python dependencies
    python3-pip \
    python3-setuptools \
    python3-wheel \
    python3-pymongo \
    python3-click \
    python3-iptables \
    python3-pyroute2 \
    # Build tools
    ninja-build \
    build-essential \
    cmake \
    meson \
    flex \
    bison \
    # VCS tools
    git \
    mercurial \
    # System utilities
    curl \
    gettext \
    gdb \
    sudo \
    # Network tools
    iproute2 \
    iptables \
    iputils-ping \
    netcat-openbsd \
    iperf \
    iperf3 \
    # Development libraries
    libsctp-dev \
    libgnutls28-dev \
    libgcrypt-dev \
    libssl-dev \
    libidn11-dev \
    libmongoc-dev \
    libbson-dev \
    libyaml-dev \
    libnghttp2-dev \
    libmicrohttpd-dev \
    libcurl4-gnutls-dev \
    libtins-dev \
    libtalloc-dev \
    libpq-dev \
    libmysqlclient-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV PYTHONPATH=/app
WORKDIR /app
COPY . .

# Build Open5GS 5gc
RUN mkdir -p build \
    && meson build --prefix=$(pwd)/install \
    && ninja -C build \
    && ninja -C build install

# Install implementation of the diameter protocol
RUN git clone https://github.com/open5gs/freeDiameter.git && \
    mkdir -p fDbuild && \
    cd fDbuild && \
    cmake ../freeDiameter && \
    make -j"$(nproc)" && \
    make install


FROM base AS open5gs

WORKDIR /open5gs
COPY config/open5gs-5gc.yml open5gs-5gc.yml.in
COPY config/open5gs_entrypoint.sh config/add_users.py config/setup_tun.py subscriber_db.cs[v] ./

ENTRYPOINT ["bash", "./open5gs_entrypoint.sh"]

