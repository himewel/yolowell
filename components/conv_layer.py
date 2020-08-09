from sys import argv
from base_component import BaseComponent
from multi_channel_conv_unit import MultiChannelConvUnit
from utils import read_floats
from myhdl import always_comb, block, Signal, intbv, ResetSignal


class ConvLayer(BaseComponent):
    """
    This class gather some MultiChannelConvUnits sharing the same inputs and
    makes your outputs availables to an external unit, probably a BufferLayer.
    The number MultiChannelConvUnits instantiated is this class is defined in
    the constants of the BaseComponent.

    :param filters: number of filters in this layer (outputs).
    :type filter: int
    :param channels: number of channels to be convolved (inputs)
    :type channels: int
    :param weights: array with weights to be distributed in conv units
    :type weights: List()
    :param binary: flag setting if will be used BinConvUnit or ConvUnit
    :type binary: bool
    :param bin_input: flag setting if the input is truncated to 1 bit
    :type bin_input: bool
    :param bin_output: flag setting if the output will be truncated to 1 bit
    :type bin_output: bool
    """
    def __init__(self, size=3, channels=0, filters=0, binary=False,
                 bin_input=False, bin_output=False, weights=[], **kwargs):
        super().__init__(**kwargs)
        print("%-24s%-10i%-10i%-16i%-10i%-10s" % ("Convlayer",
              self.layer_id, self.unit_id, self.channel_id, channels, "-"))
        self.channels = channels
        self.filters = filters

        # sort weights in buckets of 9 values
        bucket_weights = []
        for i in range(0, 9*channels*filters, 9*channels):
            bucket_weights.append(weights[i:i+9*channels])

        # set input and output width
        self.INPUT_WIDTH = 1 if bin_input else 16
        self.OUTPUT_WIDTH = 1 if bin_output else 16

        self.mult_channel_conv_units = [MultiChannelConvUnit(
            layer_id=self.layer_id, unit_id=i, channels=self.channels,
            binary=binary, bin_input=bin_input, bin_output=bin_output,
            weights=bucket_weights[i]) for i in range(self.filters)]
        return

    @block
    def rtl(self, clk, reset, input, output, en_mult, en_sum, en_channel,
            en_batch, en_act):
        """
        This function implements the combinational and sequential blocks of
        this block.

        :param clk: clock signal
        :type clk: Signal()
        :param reset: reset signal
        :type reset: ResetSignal()
        :param en_mult: enable signal
        :type en_mult: Signal()
        :param en_sum: enable signal
        :type en_sum: Signal()
        :param en_channel: enable signal
        :type en_channel: Signal()
        :param en_batch: enable signal
        :type en_batch: Signal()
        :param en_act: enable signal
        :type en_act: Signal()
        :param input: vector with the nine input values concatenated, each \
value should be an signed value with 16 bits width
        :type input: Signal(intbv()[:])
        :param output: the output value of the convolutions
        :type output: Signal(intbv()[:])
        :return: logic of this block
        :rtype: @block method
        """
        wire_channel_outputs = [Signal(intbv(0)[self.INPUT_WIDTH:])
                                for _ in range(self.filters)]
        mult_channel_conv_units = [self.mult_channel_conv_units[i].rtl(
            clk=clk, reset=reset, input=input, en_mult=en_mult, en_sum=en_sum,
            en_channel=en_channel, en_batch=en_batch, en_act=en_act,
            output=wire_channel_outputs[i]
        ) for i in range(self.filters)]

        @always_comb
        def process():
            aux = intbv(0)[self.filters*self.OUTPUT_WIDTH:]
            for i in range(self.filters):
                aux[(i+1)*self.OUTPUT_WIDTH:i*self.OUTPUT_WIDTH] = \
                    wire_channel_outputs[i]
            output.next = aux

        return (mult_channel_conv_units, process)

    def get_signals(self):
        """
        This function return the necessair signals to instantiate the rtl
        block and convert the python method to a vhdl file.

        :return: a dict specifying the input and outputs signals of the block.
        :rtype: dict of myhdl.Signal

        **Python definition of inputs and ouputs:**

        .. code-block:: python

            def get_signals(self):
                return {
                    "clk": Signal(False),
                    "reset": ResetSignal(0, active=1, isasync=1),
                    "input": Signal(intbv(0)[9*self.channels*16:]),
                    "output": Signal(intbv(0)[self.filters*16:]),
                    "en_mult": Signal(False),
                    "en_sum": Signal(False),
                    "en_channel": Signal(False),
                    "en_batch": Signal(False),
                    "en_act": Signal(False)
                }

        **VHDL component generated:**

        .. code-block:: vhdl

            component ConvLayer
                port (
                    clk        : in  std_logic;
                    reset      : in  std_logic;
                    input      : in  unsigned(9*self.channels*16 downto 0);
                    output     : out  unsigned(self.filters*16 downto 0);
                    en_mult    : in  std_logic;
                    en_sum     : in  std_logic;
                    en_channel : in  std_logic;
                    en_batch   : in  std_logic;
                    en_act     : in  std_logic
                );
            end component ConvLayer;

        """
        return {
            "clk": Signal(False),
            "reset": ResetSignal(0, active=1, isasync=1),
            "input": Signal(intbv(0)[9*self.channels*self.INPUT_WIDTH:]),
            "output": Signal(intbv(0)[self.filters*self.OUTPUT_WIDTH:]),
            "en_mult": Signal(False),
            "en_sum": Signal(False),
            "en_channel": Signal(False),
            "en_batch": Signal(False),
            "en_act": Signal(False)
        }


if (__name__ == '__main__'):
    if (len(argv) > 2):
        name = argv[1]
        path = argv[2]

        file = "yolov3_tiny/yolov3_tiny_weights.h"
        path = "/home/welberthime/Documentos/nios-darknet/include"
        f_index = 9 * 32 * 16
        weights = read_floats(path, file, final=f_index+9)

        header = ("component\t\tlayer_id\tunit_id\tchannel_id\tchannels\t" +
                  "filters")
        print("\n" + "%-24s%-10s%-10s%-16s%-10s%-10s" % ("component",
              "layer_id", "unit_id", "channel_id", "channels", "filters"))
        print(80*"-")
        unit = ConvLayer(channels=3, filters=16, binary=False, bin_input=False,
                         bin_output=True, weights=weights)
        unit.convert(name)
    else:
        print("file.py <entityname> <outputfile>")
