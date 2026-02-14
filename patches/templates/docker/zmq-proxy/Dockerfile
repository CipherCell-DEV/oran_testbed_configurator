FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    python3 python3-pip gnuradio \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# This prevents the "vmcircbuf_prefs::get" error on startup
RUN mkdir -p /root/.gnuradio/prefs && \
    echo "gr_vmcircbuf_sysv_shm_factory" > /root/.gnuradio/prefs/vmcircbuf_default_factory

WORKDIR /app

COPY zmq_proxy.py .

CMD ["bash"]
