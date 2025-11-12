FROM ubuntu:24.04

WORKDIR /flexric

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        build-essential \
        git \
        autoconf \
        automake \
        autotools-dev \
        libtool \
        bison \
        byacc \
        flex \
        cmake \
        cmake-curses-gui \
        gcc-13 \
        g++-13 \
        cpp-13 \
        libsctp-dev \
        libpcre2-dev \
        python3 \
        python3-pip \
        python3-dev \
        python3.12-venv && \
    update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-13 100 \
        --slave /usr/bin/g++ g++ /usr/bin/g++-13 \
        --slave /usr/bin/gcov gcov /usr/bin/gcov-13 && \
    update-alternatives --config gcc && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv .venv
ENV PATH="/flexric/.venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir matplotlib tikzplotlib


RUN git clone https://github.com/swig/swig.git
RUN cd swig && git checkout release-4.1 && ./autogen.sh && ./configure --prefix=/usr/ && make -j8 && make install

RUN git clone https://github.com/OpenAirInterface/asn1c.git
RUN cd asn1c && autoreconf -i && ./configure --prefix=/usr/ && make && make install

COPY . /flexric/

# TODO ugly hack just to disable eq_ptr_assert otherwise it is not compiling with gcc-13
RUN sed -i 's/#define eq_ptr_assert.*$/#define eq_ptr_assert(x,f) ((void)0)/' /flexric/src/util/eq.h

RUN mkdir -p build && cd build && cmake -DKPM_VERSION=KPM_V3_00 -DXAPP_MULTILANGUAGE=ON .. && make && make install

ENTRYPOINT ["bash", "./flexric_entrypoint.sh"]