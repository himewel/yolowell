import logging

from utils import print_info

from hwt.code import If
from hwt.hdl.types.bits import Bits
from hwt.interfaces.std import Signal, VectSignal
from hwt.serializer.mode import serializeOnce
from hwt.synthesizer.unit import Unit


@serializeOnce
class BinConvUnit(Unit):
    """
    .. hwt-schematic::
    """

    def __init__(self, size=9, width=16, bin_input=False, **kwargs):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.width = width
        self.lower_output_bit = int(width - width/2)
        # set input and output width
        self.INPUT_WIDTH = 1 if bin_input else self.width
        self.SIGNAL_BIT = self.INPUT_WIDTH - 1
        self.SIZE = size
        self.top_entity = False
        print_info(self, **kwargs)
        super().__init__()

    def _declr(self):
        self.clk = Signal()
        self.rst = Signal()
        self.en_mult = Signal()
        self.en_sum = Signal()
        self.input = VectSignal(self.INPUT_WIDTH*self.SIZE)
        self.output = VectSignal(self.width, signed=True)._m()
        self.kernel = VectSignal(self.width)

        name = f"BinConvUnitL{self.layer_id}"
        self._name = name
        self._hdl_module_name = name

    def __calc_xor_inputs(self, data_width, kernel):
        xor_list = [self._sig(name=f"xor_{i}", dtype=data_width)
                    for i in range(9)]
        const_one = self._sig(name="one", dtype=data_width, def_val=1)
        for i in range(self.SIZE):
            If(
                self.input[self.INPUT_WIDTH*(i+1)-1] ^ kernel[self.width-1],
                xor_list[i](~const_one + const_one)
            ).Else(
                xor_list[i](const_one)
            )
        return xor_list

    def __calc_tree_adders(self, xor_list, signal_width):
        first_sum = [self._sig(name=f"first_sum_{i}", dtype=signal_width)
                     for i in range(4)]
        first_sum[0](xor_list[0] + xor_list[1])
        first_sum[1](xor_list[2] + xor_list[3])
        first_sum[2](xor_list[4] + xor_list[5])
        first_sum[3](xor_list[6] + xor_list[7])

        second_sum = [self._sig(name=f"second_sum_{i}", dtype=signal_width)
                      for i in range(2)]
        second_sum[0](first_sum[0] + first_sum[1])
        second_sum[1](first_sum[2] + first_sum[3])

        third_sum = self._sig(name="third_sum", dtype=signal_width)
        third_sum(second_sum[0] + second_sum[1] + xor_list[8])
        return third_sum

    def _impl(self):
        # declare signal widths
        bit_adders_width = Bits(bit_length=self.width, signed=True)
        mult_width = Bits(bit_length=2*self.width, signed=True)
        # declaring registers
        delta = self._sig(name="delta", dtype=bit_adders_width)
        mult = self._sig(name="mult", dtype=bit_adders_width)
        # declaring kernel constant
        kernel = self.kernel
        # declaring signal casting multiplication
        cast = self._sig(name="cast_mult", dtype=mult_width)

        xor_list = self.__calc_xor_inputs(bit_adders_width, kernel)
        tree_adders_result = self.__calc_tree_adders(
            xor_list, bit_adders_width)

        signed_kernel = kernel._convSign(True)
        cast(delta * signed_kernel)
        resized_cast = cast[self.lower_output_bit+self.width:
                            self.lower_output_bit]

        # different cases to different number of inputs
        if (self.SIZE == 9):
            If(
                self.rst,
                delta(0),
                mult(0)
            ).Else(
                If(
                    self.clk._onRisingEdge(),
                    If(self.en_mult, delta(tree_adders_result)),
                    If(
                        self.en_sum,
                        mult(resized_cast)
                    )
                )
            )
        else:
            If(
                self.rst,
                delta(0),
                mult(0)
            ).Else(
                If(
                    self.clk._onRisingEdge(),
                    If(self.en_mult, delta(xor_list[0])),
                    If(
                        self.en_sum,
                        If(
                            delta[self.SIGNAL_BIT],
                            mult(signed_kernel)
                        ).Else(
                            mult(-signed_kernel))
                    )
                )
            )

        # output has the same reg to receive
        self.output(mult)


if __name__ == "__main__":
    from sys import argv
    from utils import to_vhdl, get_std_logger

    if (len(argv) > 1):
        path = argv[1]

        get_std_logger()
        unit = BinConvUnit(size=1, width=16, bin_input=False)
        to_vhdl(unit, path)
    else:
        print("file.py <outputpath>")
