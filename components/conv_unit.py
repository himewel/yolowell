import logging

from .utils import print_info
from .fixed_point_multiplier import FixedPointMultiplier

from hwt.code import If
from hwt.hdl.types.bits import Bits
from hwt.interfaces.std import Signal, VectSignal
from hwt.synthesizer.unit import Unit
from hwt.synthesizer.hObjList import HObjList
from hwt.serializer.mode import serializeParamsUniq


@serializeParamsUniq
class ConvUnit(Unit):
    """
    .. hwt-schematic::
    """

    def __init__(self, size=9, width=16, **kwargs):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.size = size
        self.width = width
        self.top_entity = False

        print_info(self, **kwargs)
        super().__init__()

    def _declr(self):
        self.clk = Signal()
        self.rst = Signal()
        self.en_mult = Signal()
        self.en_sum = Signal()
        self.input = VectSignal(self.width * self.size)
        self.output = VectSignal(self.width, signed=True)._m()

        for i in range(self.size):
            setattr(self, f"kernel_{i}", VectSignal(self.width))

        self.multiplier = HObjList(
            FixedPointMultiplier(
                width=self.width,
                layer_id=self.layer_id,
                unit_id=self.unit_id,
                channel_id=self.channel_id,
                process_id=self.process_id,
                pixel_id=i,
                log_level=self.log_level + 1,
            )
            for i in range(self.size)
        )

        name = f"ConvUnitL{self.layer_id}"
        self._name = name
        self._hdl_module_name = name

    def __calc_tree_adders(self, signal_list, signal_width):
        first_sum = [
            self._sig(name=f"first_sum_{i}", dtype=signal_width) for i in range(4)
        ]
        first_sum[0](signal_list[0] + signal_list[1])
        first_sum[1](signal_list[2] + signal_list[3])
        first_sum[2](signal_list[4] + signal_list[5])
        first_sum[3](signal_list[6] + signal_list[7])

        second_sum = [
            self._sig(name=f"second_sum_{i}", dtype=signal_width) for i in range(2)
        ]
        second_sum[0](first_sum[0] + first_sum[1])
        second_sum[1](first_sum[2] + first_sum[3])

        third_sum = self._sig(name="third_sum", dtype=signal_width)
        third_sum(second_sum[0] + second_sum[1] + signal_list[8])
        return third_sum

    def _impl(self):
        signal_width = Bits(bit_length=self.width)
        product_list = [
            self._sig(name=f"product_{i}", dtype=signal_width) for i in range(self.size)
        ]

        for i in range(self.size):
            multiplier = self.multiplier[i]
            multiplier.clk(self.clk)
            multiplier.rst(self.rst)
            multiplier.param_a(self.input[self.width * (i + 1) : self.width * i])
            multiplier.param_b(getattr(self, f"kernel_{i}"))

            If(self.rst, product_list[i](0)).Else(
                If(
                    self.clk._onRisingEdge(),
                    If(self.en_mult, product_list[i](multiplier.product)),
                )
            )

        if self.size == 9:
            third_sum = self.__calc_tree_adders(product_list, signal_width)

            If(self.rst, self.output(0)).Else(
                If(self.clk._onRisingEdge(), If(self.en_sum, self.output(third_sum)))
            )
        else:
            If(self.rst, self.output(0)).Else(
                If(
                    self.clk._onRisingEdge(),
                    If(self.en_sum, self.output(product_list[0])),
                )
            )


if __name__ == '__main__':
    from sys import argv
    from utils import to_vhdl, get_std_logger

    if len(argv) > 1:
        path = argv[1]

        get_std_logger()
        unit = ConvUnit(size=1, width=16)
        to_vhdl(unit, path)
    else:
        print("file.py <outputpath>")
