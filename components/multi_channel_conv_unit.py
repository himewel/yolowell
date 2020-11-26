import logging
from math import log, ceil

from .utils import print_info
from .bin_conv_unit import BinConvUnit
from .conv_unit import ConvUnit
from .fixed_point_multiplier import FixedPointMultiplier

from hwt.code import If
from hwt.hdl.types.bits import Bits
from hwt.interfaces.std import Signal, VectSignal
from hwt.synthesizer.unit import Unit
from hwt.interfaces.utils import propagateClkRst, addClkRst
from hwt.synthesizer.hObjList import HObjList
from hwt.serializer.mode import serializeOnce


@serializeOnce
class MultiChannelConvUnit(Unit):
    """
    .. hwt-schematic::
    """

    def __init__(
        self,
        channels=3,
        width=16,
        size=9,
        binary=True,
        bin_input=False,
        bin_output=False,
        **kwargs,
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.channels = channels
        self.size = size
        self.width = width
        self.bin_input = bin_input
        self.binary = binary
        self.lower_output_bit = int(width - width / 2)
        self.top_entity = False

        # set coeficients to build the tree adders
        if self.channels & (self.channels - 1) == 0:
            self.tree_cond = 0
            self.acc_id = self.channels - 1
        else:
            self.tree_cond = 1
            self.acc_id = 2 ** ceil(log(self.channels) / log(2)) - 1
        self.half_elements = int((self.acc_id + 1) / 2)

        # set input and output width
        self.INPUT_WIDTH = 1 if bin_input else self.width
        self.OUTPUT_WIDTH = 1 if bin_output else self.width

        print_info(self, **kwargs)
        super().__init__()

    def _declr(self):
        addClkRst(self)
        self.en_mult = Signal()
        self.en_sum = Signal()
        self.en_channel = Signal()
        self.en_batch = Signal()
        self.en_act = Signal()
        self.input = VectSignal(self.size * self.channels * self.INPUT_WIDTH)
        self.output = VectSignal(self.OUTPUT_WIDTH, signed=True)._m()

        self.ssi_coef = VectSignal(self.INPUT_WIDTH)
        self.bn_coef = VectSignal(self.INPUT_WIDTH)

        # self.multiplier = FixedPointMultiplier(
        #     width=self.width,
        #     layer_id=self.layer_id,
        #     unit_id=self.unit_id,
        #     channel_id=self.channel_id,
        #     process_id=self.process_id,
        #     pixel_id=0,
        #     log_level=self.log_level + 1,
        # )

        conv_units_list = []
        # instantiate binary conv unit if it is setted
        if self.binary:
            for i in range(self.channels):
                setattr(self, f'kernel_abs_{i}', VectSignal(self.width))
                setattr(self, f'kernel_sig_{i}', VectSignal(self.size))
                conv_unit = BinConvUnit(
                    layer_id=self.layer_id,
                    channel_id=i,
                    unit_id=self.unit_id,
                    bin_input=self.bin_input,
                    width=self.width,
                    size=self.size,
                    process_id=self.process_id,
                    log_level=self.log_level + 1,
                )
                conv_units_list.append(conv_unit)
        else:
            for i in range(self.channels):
                for j in range(self.size):
                    setattr(self, f'kernel_{i*self.size+j}', VectSignal(self.width))
                conv_unit = ConvUnit(
                    layer_id=self.layer_id,
                    channel_id=i,
                    unit_id=self.unit_id,
                    bin_input=self.bin_input,
                    width=self.width,
                    size=self.size,
                    process_id=self.process_id,
                    log_level=self.log_level + 1,
                )
                conv_units_list.append(conv_unit)
        self.conv_units = HObjList(conv_units_list)

        name = f"MultiChannelConvUnitL{self.layer_id}"
        self._name = name
        self._hdl_module_name = name

    def __map_conv_signals(self, data_width):
        output_list = []

        for i in range(self.channels):
            conv_unit = self.conv_units[i]
            conv_unit.en_mult(self.en_mult)
            conv_unit.en_sum(self.en_sum)
            conv_unit.input(
                self.input[
                    (i + 1)
                    * self.INPUT_WIDTH
                    * self.size : i
                    * self.INPUT_WIDTH
                    * self.size
                ]
            )

            if self.binary:
                kernel_abs = getattr(self, f"kernel_abs_{i}")
                kernel_sig = getattr(self, f"kernel_sig_{i}")
                conv_unit.kernel_abs(kernel_abs)
                conv_unit.kernel_sig(kernel_sig)
            else:
                for j in range(self.size):
                    conv_kernel_port = getattr(conv_unit, f'kernel_{j}')
                    parent_kernel_port = getattr(self, f'kernel_{i*self.size+j}')
                    conv_kernel_port(parent_kernel_port)

            output = self._sig(name=f"wire_outputs_{i}", dtype=data_width)
            output(conv_unit.output)
            output_list.append(output)
        return output_list

    def __tree_conv_adders(self, data_width, conv_outputs):
        acc = [
            self._sig(name=f"acc_{i}", dtype=data_width, def_val=0)
            for i in range(self.acc_id + 1)
        ]

        if self.tree_cond:
            for i in range(self.half_elements):
                if self.acc_id - 1 - i < self.channels and self.acc_id - 1 - i != i:
                    acc[i](conv_outputs[i] + conv_outputs[self.acc_id - 1 - i])
                else:
                    acc[i](conv_outputs[i])
        else:
            for i in range(self.half_elements):
                acc[i](conv_outputs[i] + conv_outputs[self.channels - 1 - i])

        n_elements = self.half_elements
        output_index = self.half_elements
        input_index = 0

        while n_elements > 0:
            for i in range(int(n_elements / 2)):
                acc[output_index + i](
                    acc[input_index + i] + acc[input_index + n_elements - i - 1]
                )
            n_elements = int(n_elements / 2)
            input_index = output_index
            output_index += n_elements

        return acc[self.acc_id - 1]

    def __right_shift(self, signed_value, shift_offset):
        mask_dtype = Bits(bit_length=self.width, force_vector=True)
        mask_value = 2 ** (self.width - 1) - 2 ** (shift_offset)
        shift_mask = self._sig(name="shift_mask", dtype=mask_dtype, def_val=mask_value)
        shift_value = self._sig(name="shift_value", dtype=mask_dtype)

        negative_fill_value = 2 ** (self.width) - 2 ** (self.width - shift_offset - 1)
        negative_fill = self._sig(
            name="negative_fill", dtype=mask_dtype, def_val=negative_fill_value
        )
        unsigned_mask = shift_mask._convSign(False)
        unsigned_value = signed_value._convSign(False)
        unsigned_fill = negative_fill._convSign(False)
        shift_value((unsigned_mask & unsigned_value) + unsigned_fill)
        return shift_value

    def _impl(self):
        propagateClkRst(self)
        data_width = Bits(bit_length=self.width, signed=True)
        double_width = Bits(bit_length=self.width * 2, signed=True)
        conv_outputs = self.__map_conv_signals(data_width)

        reg_batch = self._sig(name="reg_batch", dtype=data_width)
        reg_accumulator = self._sig(name="reg_accumulator", dtype=data_width)

        bn_product = self._sig(name="bn_product", dtype=data_width)

        # self.multiplier.param_a(reg_accumulator)
        # self.multiplier.param_b(self.ssi_coef)
        # bn_product(self.multiplier.product)
        mult = self._sig(name="mult", dtype=double_width)
        mult(reg_accumulator * self.ssi_coef._convSign(True))
        bn_product[self.width - 1](mult[2 * self.width - 1])
        bn_product[self.width - 1 : 0](
            mult[self.lower_output_bit + self.width - 1 : self.lower_output_bit]
        )

        # If(self.rst, reg_batch(0), reg_accumulator(0)).Else(
        #     If(
        #         self.clk._onRisingEdge(),
        #         If(
        # self.en_batch,
        reg_batch(bn_product + self.bn_coef)
        # ),
        # If(
        # self.en_channel,
        reg_accumulator(self.__tree_conv_adders(data_width, conv_outputs))
        #         ),
        #     )
        # )

        if self.OUTPUT_WIDTH == 1:
            # If(self.rst, self.output(0)).Else(
            #     If(
            #         self.clk._onRisingEdge(),
            # If(self.en_act,
            self.output(reg_batch[self.width - 1])
            # ),
        #     )
        # )
        else:
            # If(self.rst, self.output(0)).Else(
            #     If(
            #         self.clk._onRisingEdge(),
            #         If(
            #             self.en_act,
            If(~reg_batch[self.width - 1], self.output(reg_batch)).Else(
                self.output(self.__right_shift(reg_batch, 3))
            )
        #         ),
        #     )
        # )


if __name__ == '__main__':
    from sys import argv
    from utils import get_std_logger, to_vhdl

    if len(argv) > 1:
        path = argv[1]

        get_std_logger()
        unit = MultiChannelConvUnit(channels=32, size=9, binary=True)
        to_vhdl(unit, path, name="MultiChannelConvUnitL0F0P0")
    else:
        print("file.py <outputpath>")
