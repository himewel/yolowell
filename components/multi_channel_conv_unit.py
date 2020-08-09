from sys import argv
from math import log, ceil
from myhdl import (always_seq, always_comb, block, Signal, intbv, bin,
                   ResetSignal)

from fixed_point_multiplier import FixedPointMultiplier
from base_component import BaseComponent
from conv_unit import ConvUnit
from bin_conv_unit import BinConvUnit
from bn_rom import BnROM


class MultiChannelConvUnit(BaseComponent):
    """
    This block gather CHANNELS convolutional units receiveing CHANNEL bus
    inputs concatenated in one port, the same for the outputs. The kernel, bias
    and batch normalization values ​​are provided inside this unit for each
    convolutional unit input, except the control signs comes from a external
    control unit. Therefore, this constant values are updated to the
    convolutional units just in the right cicles. The same happens with the
    convolution units signs, so, the convolution units at principle runs
    synchronous with each other.

    The output port of this block is the result of the multichannel convolution
    operation with different kernel values and input channels. After the
    individual process of convolution between kernel values and input channels,
    the results are normalized and added with a bias value. Before the output
    be updated, the value pass in a leaky relu activation function.

    :param filters: number of filters in this layer (outputs).
    :type filter: int
    :param channels: number of channels to be convolved (inputs)
    :type channels: int
    :param weights: array with weights to be distributed in conv units
    :type weights: List()
    :param binary: flag setting if will be used BinConvUnit or ConvUnit
    :type binary: bool
    :param bin_input: flag setting if the input is be truncated to 1 bit
    :type bin_input: bool
    :param bin_output: flag setting if the output will be truncated to 1 bit
    :type bin_output: bool
    """
    def __init__(self, channels=0, size=3, binary=False, bin_input=False,
                 bin_output=False, weights=[], **kwargs):
        super().__init__(**kwargs)
        print("%-24s%-10i%-10i%-16i%-10i%-10s" % ("MultiChannelConvUnit",
              self.layer_id, self.unit_id, self.channel_id, channels, "-"))

        self.channels = channels
        self.size = size*size

        # set coeficients to build the tree adders
        if (self.channels & (self.channels - 1) == 0):
            self.tree_cond = 0
            self.acc_id = self.channels-1
        else:
            self.tree_cond = 1
            self.acc_id = 2 ** ceil(log(self.channels)/log(2))-1
        self.half_elements = int((self.acc_id+1)/2)

        # sort the weights in buckets to each conv unit
        bucket_weights = []
        for i in range(0, self.size*channels, self.size):
            bucket_weights.append(weights[i:i+self.size])

        # set input and output width
        self.INPUT_WIDTH = 1 if bin_input else 16
        self.OUTPUT_WIDTH = 1 if bin_output else 16

        # instantiate binary conv unit if it is setted
        if (binary):
            self.conv_units = [BinConvUnit(
                layer_id=self.layer_id, channel_id=i, unit_id=self.unit_id,
                weights=bucket_weights[i], bin_input=bin_input, size=size)
                for i in range(self.channels)]
        else:
            self.conv_units = [ConvUnit(
                layer_id=self.layer_id, channel_id=i, unit_id=self.unit_id,
                weights=bucket_weights[i], size=size)
                for i in range(self.channels)]

        # instantiate batch normalization units
        self.bn_rom = BnROM(layer_id=self.layer_id, unit_id=self.unit_id)
        self.bn_multiplier = FixedPointMultiplier()
        return

    def get_signals(self):
        return {
            "clk": Signal(False),
            "reset": ResetSignal(0, active=1, isasync=1),
            "input":
                Signal(intbv(0)[self.size*self.channels*self.INPUT_WIDTH:]),
            "output": Signal(intbv(0)[self.OUTPUT_WIDTH:]),
            "en_mult": Signal(False),
            "en_sum": Signal(False),
            "en_channel": Signal(False),
            "en_batch": Signal(False),
            "en_act": Signal(False)
        }

    @block
    def rtl(self, clk, reset, input, output, en_mult, en_sum, en_channel,
            en_batch, en_act):
        """
        :param clk: clock signal
        :type clk: std_logic
        :param reset: reset signal
        :type reset: std_logic
        :param en_mult: enable signal
        :type en_mult: std_logic
        :param en_sum: enable signal
        :type en_sum: std_logic
        :param input: vector with the nine input values cancatenated, each value \
        should be an signed value with 16 bits width
        :type input: std_logic_vector
        :param output: the output value of the convolutions
        :type output: unsigned
        """
        # 11 fractional bits 0.125 leaky constant value
        leaky_constant = Signal(intbv(bin("0000000010000000"))[16:])

        # treatment to generic number of inputs
        wire_conv_outputs = [Signal(intbv(0)[16:])
                             for _ in range(self.channels)]
        wire_inputs = [Signal(intbv(0)[self.size*self.INPUT_WIDTH:])
                       for _ in range(self.channels)]

        # signals readed from ROMs
        ssi_coef = Signal(intbv(0)[16:])
        bn_coef = Signal(intbv(0)[16:])

        # pipeline registers
        reg_accumulator = Signal(intbv(0)[16:])
        reg_batch = Signal(intbv(0)[16:])

        # convolutinal units instatiation
        conv_units = [self.conv_units[i].rtl(
                clk=clk, reset=reset, en_mult=en_mult, en_sum=en_sum,
                input=wire_inputs[i], output=wire_conv_outputs[i],
            ) for i in range(self.channels)]

        # batch normalization units
        bn_product = Signal(intbv(0)[16:])
        bn_rom = self.bn_rom.rtl(clk=clk, q_bn=bn_coef, q_ssi=ssi_coef)
        bn_multiplier = self.bn_multiplier.rtl(
            clk=clk, reset=reset, param_a=reg_accumulator, param_b=ssi_coef,
            product=bn_product)

        @always_comb
        def combinational_wire_inputs():
            for i in range(self.channels):
                min_index = (i+1)*self.INPUT_WIDTH*self.size
                max_index = i*self.INPUT_WIDTH*self.size
                wire_inputs[i].next = input[min_index:max_index]

        @always_seq(clk.posedge, reset=reset)
        def acc_process():
            acc = [intbv(0)[16:] for _ in range(self.acc_id)]
            if (en_channel == 1):
                n_elements = self.half_elements
                input_index = 0
                output_index = n_elements

                if (self.tree_cond == 1):
                    for i in range(self.half_elements):
                        if (self.acc_id-1-i < self.channels):
                            acc[i].next = wire_conv_outputs[i] + \
                                wire_conv_outputs[self.acc_id-1-i]
                        else:
                            acc[i].next = wire_conv_outputs[i]
                else:
                    for i in range(self.half_elements):
                        acc[i].next = wire_conv_outputs[i] + \
                            wire_conv_outputs[self.channels-1-i]

                while (n_elements > 1):
                    n_elements = int(n_elements//2)
                    for i in range(n_elements):
                        acc[output_index+i].next = acc[input_index+i] + \
                            acc[input_index+n_elements-i]
                    input_index = output_index
                    output_index += n_elements

                reg_accumulator.next = acc[self.acc_id-1]

        @always_seq(clk.posedge, reset=reset)
        def batch_process():
            if (en_batch == 1):
                reg_batch.next = bn_product  + bn_coef

        @always_seq(clk.posedge, reset=reset)
        def act_process():
            if (en_act == 1):
                if (self.OUTPUT_WIDTH == 1):
                    output.next = reg_batch[15]
                else:
                    if (reg_batch[15] == 0):
                        output.next = reg_batch
                    else:
                        output.next = reg_batch * leaky_constant

        return (acc_process, conv_units, bn_rom, bn_multiplier,
                combinational_wire_inputs, batch_process, act_process)


if __name__ == '__main__':
    if (len(argv) > 2):
        name = argv[1]
        path = argv[2]

        unit = MultiChannelConvUnit(channels=3, size=1, weights=[], binary=True)
        unit.convert(name, path)
    else:
        print("file.py <entityname> <outputfile>")
