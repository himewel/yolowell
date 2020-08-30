import logging
from math import log, ceil

from utils import print_info
from bin_conv_unit import BinConvUnit

from hwt.code import If
from hwt.hdl.types.bits import Bits
from hwt.interfaces.std import Signal, VectSignal
from hwt.synthesizer.unit import Unit
from hwt.synthesizer.hObjList import HObjList


class MultiChannelConvUnit(Unit):
    """
    .. hwt-schematic::
    """

    def __init__(self, channels=3, width=16, size=9, binary=True,
                 bin_input=False, bin_output=False, weights=27*[20], **kwargs):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.channels = channels
        self.size = size
        self.width = width
        self.bin_input = bin_input
        self.binary = binary
        self.lower_output_bit = int(width - width/2)

        # set coeficients to build the tree adders
        if (self.channels & (self.channels - 1) == 0):
            self.tree_cond = 0
            self.acc_id = self.channels-1
        else:
            self.tree_cond = 1
            self.acc_id = 2 ** ceil(log(self.channels)/log(2))-1
        self.half_elements = int((self.acc_id+1)/2)

        # sort the weights in buckets to each conv unit
        self.bucket_weights = []
        for i in range(0, self.size*channels, self.size):
            self.bucket_weights.append(weights[i:i+self.size])
        self.ssi_coef = 20
        self.bn_coef = 30

        # set input and output width
        self.INPUT_WIDTH = 1 if bin_input else self.width
        self.OUTPUT_WIDTH = 1 if bin_output else self.width

        print_info(self, **kwargs)
        super().__init__()

    def _declr(self):
        self.clk = Signal()
        self.rst = Signal()
        self.en_mult = Signal()
        self.en_sum = Signal()
        self.en_channel = Signal()
        self.en_batch = Signal()
        self.en_act = Signal()
        self.input = VectSignal(self.size*self.channels*self.INPUT_WIDTH, )
        self.output = VectSignal(self.OUTPUT_WIDTH, signed=True)._m()

        # instantiate binary conv unit if it is setted
        if (self.binary):
            self.conv_units = HObjList(BinConvUnit(
                layer_id=self.layer_id, channel_id=i, unit_id=self.unit_id,
                weights=self.bucket_weights[i], bin_input=self.bin_input,
                width=self.width, size=self.size, process_id=self.process_id)
                for i in range(self.channels))
        else:
            pass

        name = "MultiChannelConvUnitL{layer}F{filter}P{process}".format(
            layer=self.layer_id,
            filter=self.unit_id,
            process=self.process_id)
        self._name = name
        self._hdl_module_name = name
        self.__free()

    def __free(self):
        i = 0
        while len(self.bucket_weights) > 0:
            del self.bucket_weights[i]

    def __map_conv_signals(self, data_width):
        outputs = [self._sig(name=f"wire_outputs_{i}", dtype=data_width)
                   for i in range(self.channels)]

        for i in range(self.channels):
            conv_unit = self.conv_units[i]
            conv_unit.clk(self.clk)
            conv_unit.rst(self.rst)
            conv_unit.en_mult(self.en_mult)
            conv_unit.en_sum(self.en_sum)
            conv_unit.input(
                self.input[(i+1)*self.INPUT_WIDTH*self.size:
                           i*self.INPUT_WIDTH*self.size])
            outputs[i](conv_unit.output)
        return outputs

    def __tree_conv_adders(self, data_width, conv_outputs):
        acc = [self._sig(name=f"acc_{i}", dtype=data_width)
               for i in range(self.acc_id)]

        n_elements = self.half_elements
        input_index = 0
        output_index = n_elements

        if (self.tree_cond == 1):
            for i in range(self.half_elements):
                if (self.acc_id-1-i < self.channels):
                    acc[i](conv_outputs[i] + conv_outputs[self.acc_id-1-i])
                else:
                    acc[i].next = conv_outputs[i]
        else:
            for i in range(self.half_elements):
                acc[i](conv_outputs[i] + conv_outputs[self.channels-1-i])

        while (n_elements > 1):
            n_elements = int(n_elements//2)
            for i in range(n_elements):
                acc[output_index+i](
                    acc[input_index+i] + acc[input_index+n_elements-i])
            input_index = output_index
            output_index += n_elements

        return acc[self.acc_id-1]

    def __right_shift(self, signed_value, shift_offset):
        mask_dtype = Bits(bit_length=self.width,
                          force_vector=True)
        mask_value = 2**(self.width - 1) - 2**(shift_offset)
        shift_mask = self._sig(name="shift_mask", dtype=mask_dtype,
                               def_val=mask_value)
        shift_value = self._sig(name="shift_value", dtype=mask_dtype)

        negative_fill_value = 2**(self.width) - \
            2**(self.width - shift_offset - 1)
        negative_fill = self._sig(name="negative_fill", dtype=mask_dtype,
                                  def_val=negative_fill_value)
        unsigned_mask = shift_mask._convSign(False)
        unsigned_value = signed_value._convSign(False)
        unsigned_fill = negative_fill._convSign(False)
        shift_value((unsigned_mask & unsigned_value) + unsigned_fill)
        return shift_value

    def _impl(self):
        data_width = Bits(bit_length=self.width, signed=True)
        mult_data_width = Bits(bit_length=2*self.width, signed=True)
        conv_outputs = self.__map_conv_signals(data_width)

        reg_batch = self._sig(name="reg_batch", dtype=data_width)
        reg_accumulator = self._sig(name="reg_accumulator", dtype=data_width)

        bn_product = self._sig(name="bn_product", dtype=data_width)
        ssi_coef = self._sig(name="ssi_coef", dtype=data_width,
                             def_val=self.ssi_coef)
        bn_coef = self._sig(name="ssi_coef", dtype=data_width,
                            def_val=self.bn_coef)
        cast = self._sig(name="cast_mult", dtype=mult_data_width)
        cast(reg_accumulator * ssi_coef)
        bn_product(
            cast[self.lower_output_bit+self.width:self.lower_output_bit])

        If(
            self.rst,
            reg_batch(0),
            reg_accumulator(0)
        ).Else(
            If(
                self.clk._onRisingEdge(),
                If(self.en_batch, reg_batch(bn_product + bn_coef)),
                If(self.en_channel, reg_accumulator(
                    self.__tree_conv_adders(data_width, conv_outputs)))
            )
        )

        if (self.OUTPUT_WIDTH == 1):
            If(
                self.rst,
                self.output(0)
            ).Else(
                If(
                    self.clk._onRisingEdge(),
                    If(self.en_act, self.output(reg_batch[self.width-1]))
                )
            )
        else:
            If(
                self.rst,
                self.output(0)
            ).Else(
                If(
                    self.clk._onRisingEdge(),
                    If(
                        self.en_act,
                        If(
                            ~reg_batch[self.width-1],
                            self.output(reg_batch)
                        ).Else(
                            self.output(self.__right_shift(reg_batch, 3))
                        )
                    )
                )
            )


if __name__ == '__main__':
    from sys import argv
    from utils import get_logger, to_vhdl

    if (len(argv) > 1):
        path = argv[1]

        get_logger()
        unit = MultiChannelConvUnit(channels=3, size=9, weights=36*[30],
                                    binary=True, bin_input=False)
        to_vhdl(unit, path)
    else:
        print("file.py <outputpath>")
