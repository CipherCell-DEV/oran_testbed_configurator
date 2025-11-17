#!/usr/bin/env python3

from gnuradio import blocks
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import zeromq
import threading


class multi_ue_scenario(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "srsRAN_multi_UE", catch_exceptions=True)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.zmq_timeout = zmq_timeout = 100
        self.zmq_hwm = zmq_hwm = -1
        self.ue3_path_loss_db = ue3_path_loss_db = 20
        self.ue2_path_loss_db = ue2_path_loss_db = 10
        self.ue1_path_loss_db = ue1_path_loss_db = 0
        self.slow_down_ratio = slow_down_ratio = 4
        self.samp_rate = samp_rate = 11520000

        ##################################################
        # Blocks
        ##################################################

        self.zeromq_req_source_1_0 = zeromq.req_source(gr.sizeof_gr_complex, 1, 'tcp://10.45.1.3:2201', zmq_timeout,
                                                       False, zmq_hwm, False)
        self.zeromq_req_source_1 = zeromq.req_source(gr.sizeof_gr_complex, 1, 'tcp://10.45.1.2:2101', zmq_timeout,
                                                     False, zmq_hwm, False)
        self.zeromq_req_source_0 = zeromq.req_source(gr.sizeof_gr_complex, 1, 'tcp://10.45.1.1:2000', zmq_timeout,
                                                     False, zmq_hwm, False)
        self.zeromq_rep_sink_0_1 = zeromq.rep_sink(gr.sizeof_gr_complex, 1, 'tcp://0.0.0.0:2001', zmq_timeout, False,
                                                   zmq_hwm, True)
        self.zeromq_rep_sink_0_0 = zeromq.rep_sink(gr.sizeof_gr_complex, 1, 'tcp://0.0.0.0:2200', zmq_timeout, False,
                                                   zmq_hwm, True)
        self.zeromq_rep_sink_0 = zeromq.rep_sink(gr.sizeof_gr_complex, 1, 'tcp://0.0.0.0:2100', zmq_timeout, False,
                                                 zmq_hwm, True)
        self.blocks_throttle_0 = blocks.throttle(gr.sizeof_gr_complex * 1, (1.0 * samp_rate / (1.0 * slow_down_ratio)),
                                                 True)
        self.blocks_multiply_const_vxx_0_1_1 = blocks.multiply_const_cc(10 ** (-1.0 * ue2_path_loss_db / 20.0))
        self.blocks_multiply_const_vxx_0_1 = blocks.multiply_const_cc(10 ** (-1.0 * ue1_path_loss_db / 20.0))
        self.blocks_multiply_const_vxx_0_0 = blocks.multiply_const_cc(10 ** (-1.0 * ue2_path_loss_db / 20.0))
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_cc(10 ** (-1.0 * ue1_path_loss_db / 20.0))
        self.blocks_add_xx_0 = blocks.add_vcc(1)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_add_xx_0, 0), (self.zeromq_rep_sink_0_1, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.blocks_add_xx_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0_0, 0), (self.blocks_add_xx_0, 1))
        self.connect((self.blocks_multiply_const_vxx_0_1, 0), (self.zeromq_rep_sink_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0_1_1, 0), (self.zeromq_rep_sink_0_0, 0))
        self.connect((self.blocks_throttle_0, 0), (self.blocks_multiply_const_vxx_0_1, 0))
        self.connect((self.blocks_throttle_0, 0), (self.blocks_multiply_const_vxx_0_1_1, 0))
        self.connect((self.zeromq_req_source_0, 0), (self.blocks_throttle_0, 0))
        self.connect((self.zeromq_req_source_1, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.zeromq_req_source_1_0, 0), (self.blocks_multiply_const_vxx_0_0, 0))

    def get_zmq_timeout(self):
        return self.zmq_timeout

    def set_zmq_timeout(self, zmq_timeout):
        self.zmq_timeout = zmq_timeout

    def get_zmq_hwm(self):
        return self.zmq_hwm

    def set_zmq_hwm(self, zmq_hwm):
        self.zmq_hwm = zmq_hwm

    def get_ue3_path_loss_db(self):
        return self.ue3_path_loss_db

    def set_ue3_path_loss_db(self, ue3_path_loss_db):
        self.ue3_path_loss_db = ue3_path_loss_db

    def get_ue2_path_loss_db(self):
        return self.ue2_path_loss_db

    def set_ue2_path_loss_db(self, ue2_path_loss_db):
        self.ue2_path_loss_db = ue2_path_loss_db
        self.blocks_multiply_const_vxx_0_0.set_k(10 ** (-1.0 * self.ue2_path_loss_db / 20.0))
        self.blocks_multiply_const_vxx_0_1_1.set_k(10 ** (-1.0 * self.ue2_path_loss_db / 20.0))

    def get_ue1_path_loss_db(self):
        return self.ue1_path_loss_db

    def set_ue1_path_loss_db(self, ue1_path_loss_db):
        self.ue1_path_loss_db = ue1_path_loss_db
        self.blocks_multiply_const_vxx_0.set_k(10 ** (-1.0 * self.ue1_path_loss_db / 20.0))
        self.blocks_multiply_const_vxx_0_1.set_k(10 ** (-1.0 * self.ue1_path_loss_db / 20.0))

    def get_slow_down_ratio(self):
        return self.slow_down_ratio

    def set_slow_down_ratio(self, slow_down_ratio):
        self.slow_down_ratio = slow_down_ratio
        self.blocks_throttle_0.set_sample_rate((1.0 * self.samp_rate / (1.0 * self.slow_down_ratio)))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.blocks_throttle_0.set_sample_rate((1.0 * self.samp_rate / (1.0 * self.slow_down_ratio)))


def main(top_block_cls=multi_ue_scenario, options=None):
    tb = top_block_cls()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()
    tb.flowgraph_started.set()

    try:
        input('Press Enter to quit: ')
    except EOFError:
        pass
    tb.stop()
    tb.wait()


if __name__ == '__main__':
    main()
