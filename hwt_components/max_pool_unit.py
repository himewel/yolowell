import logging

from utils import print_info

from hwt.code import If
from hwt.hdl.types.bits import Bits
from hwt.interfaces.std import Signal, VectSignal
from hwt.synthesizer.unit import Unit
from hwt.serializer.mode import serializeParamsUniq


@serializeParamsUniq
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
        self.output = VectSignal(self.width, signed=True)._m()

        name = "MaxPoolUnitL{layer}F{filter}C{channel}P{process}".format(
            layer=self.layer_id,
            filter=self.unit_id,
            channel=self.channel_id,
            process=self.process_id)
        self._name = name
        self._hdl_module_name = name

    def __comparison(self, param_a, param_b, out):
        return If(param_a > param_b, out(param_a)).Else(out(param_b))

    def __bin_comparison(self, param_a, param_b, out):
        return If(param_a & param_b, out(param_a)).Else(out(param_b))

    def _impl(self):
        signal_width = Bits(bit_length=self.width, force_vector=True)
        inputs = [self._sig(name=f"input{i}", dtype=signal_width)
                  for i in range(4)]
        for i in range(4):
            inputs[i](self.input[(i+1)*self.width:i*self.width])

        first_pool0 = self._sig(name="first_pool0", dtype=signal_width)
        first_pool1 = self._sig(name="first_pool1", dtype=signal_width)
        pool_result = self._sig(name="pool_result", dtype=signal_width)

        comparison = self.__bin_comparison if self.binary \
            else self.__comparison

        comparison(inputs[0], inputs[1], first_pool0)
        comparison(inputs[2], inputs[3], first_pool1)

        If(
            self.rst,
            pool_result(0)
        ).Else(
            If(
                self.clk._onRisingEdge(),
                If(
                    self.en_pool,
                    comparison(first_pool0, first_pool1, pool_result)
                )
            )
        )

        self.output(pool_result)


if __name__ == '__main__':
    from sys import argv
    from utils import to_vhdl, get_std_logger

    if (len(argv) > 1):
        path = argv[1]

        get_std_logger()
        unit = MaxPoolUnit(width=8, binary=True)
        to_vhdl(unit, path)
    else:
        print("file.py <outputpath>")
