import logging

from utils import print_info

from hwt.code import If
from hwt.hdl.types.bits import Bits
from hwt.interfaces.std import Signal, VectSignal
from hwt.synthesizer.unit import Unit


class MaxPoolUnit(Unit):
    """
    .. hwt-schematic::
    """

    def __init__(self, width=16, binary=False, **kwargs):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.width = width
        self.binary = binary
        self.top_entity = False
        print_info(self, **kwargs)
        super().__init__()

    def _declr(self):
        self.clk = Signal()
        self.rst = Signal()
        self.en_pool = Signal()
        self.input = VectSignal(self.width*4)
        self.output = VectSignal(self.width)._m()

        name = "MaxPoolUnitL{layer}F{filter}C{channel}P{process}".format(
            layer=self.layer_id,
            filter=self.unit_id,
            channel=self.channel_id,
            process=self.process_id)
        self._name = name
        self._hdl_module_name = name

    def __comparison(self, param_a, param_b, out):
        If(
            param_a > param_b,
            out(param_a)
        ).Else(
            out(param_b)
        )

    def __bin_comparison(self, param_a, param_b, out):
        If(
            param_a & param_b,
            out(param_a)
        ).Else(
            out(param_b)
        )

    def _impl(self):
        signal_width = Bits(bit_length=self.width, force_vector=True)
        first_pool0 = self._sig(name="first_pool0", dtype=signal_width)
        first_pool1 = self._sig(name="first_pool1", dtype=signal_width)

        if self.binary:
            compare_function = self.__bin_comparison
        else:
            compare_function = self.__comparison

        compare_function(
            self.input[self.width:],
            self.input[2*self.width:self.width],
            first_pool0)
        compare_function(
            self.input[4*self.width:3*self.width],
            self.input[3*self.width:2*self.width],
            first_pool1)

        If(
            self.rst,
            self.output(0)
        ).Else(
            self.clk._onRisingEdge(),
            If(
                self.en_pool,
                compare_function(first_pool0, first_pool1, self.output)
            )
        )


if __name__ == '__main__':
    from sys import argv
    from utils import to_vhdl, get_std_logger

    if (len(argv) > 1):
        path = argv[1]

        get_std_logger()
        unit = MaxPoolUnit(width=16)
        to_vhdl(unit, path)
    else:
        print("file.py <outputpath>")
