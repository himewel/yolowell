import logging

from utils import print_info
from multi_channel_conv_unit import MultiChannelConvUnit

from hwt.interfaces.std import Signal, VectSignal
from hwt.synthesizer.unit import Unit
from hwt.hdl.types.bits import Bits
from hwt.synthesizer.hObjList import HObjList


class ConvLayer(Unit):
    """
    .. hwt-schematic::
    """

    def __init__(self, size=3, width=16, channels=3, filters=16, binary=False,
                 bin_input=False, bin_output=False, weights=[],
                 top_entity=False, parallelism=1, **kwargs):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.size = size*size
        self.channels = channels
        self.filters = filters
        self.width = width
        self.binary = binary
        self.bin_input = bin_input
        self.bin_output = bin_output
        self.top_entity = top_entity
        self.parallelism = parallelism

        # sort weights in buckets of size^2 values
        self.bucket_weights = []
        if not top_entity:
            for i in range(0, self.size*channels*filters, self.size*channels):
                self.bucket_weights.append(weights[i:i+self.size*channels])

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
        self.input = VectSignal(self.size*self.channels*self.INPUT_WIDTH)
        self.output = VectSignal(self.filters*self.OUTPUT_WIDTH)._m()

        if (self.top_entity):
            output_width = int(self.filters/self.parallelism)*self.OUTPUT_WIDTH
            # instantiate empty ConvLayerPart
            self.conv_layer_part = HObjList(ConvLayerPart(
                input_width=self.size*self.channels*self.INPUT_WIDTH,
                output_width=output_width,
                layer_id=self.layer_id, process_id=i)
                for i in range(self.parallelism))
            name = f"ConvLayerL{self.layer_id}"
        else:
            # instantiate dynamically multichannel units
            self.conv_layer_part = HObjList(MultiChannelConvUnit(
                layer_id=self.layer_id, unit_id=i, width=self.width,
                channels=self.channels, binary=self.binary, size=self.size,
                bin_input=self.bin_input, bin_output=self.bin_output,
                weights=self.bucket_weights[i], process_id=self.process_id)
                for i in range(self.filters))
            name = f"ConvLayerL{self.layer_id}P{self.process_id}"
        self._hdl_module_name = name
        self._name = name

    def _impl(self):
        if self.top_entity:
            offset = int(self.filters/self.parallelism)*self.OUTPUT_WIDTH
            range_limit = self.parallelism
        else:
            offset = self.OUTPUT_WIDTH
            range_limit = self.filters

        for i in range(range_limit):
            conv_layer_part = self.conv_layer_part[i]
            conv_layer_part.clk(self.clk)
            conv_layer_part.rst(self.rst)
            conv_layer_part.en_mult(self.en_mult)
            conv_layer_part.en_sum(self.en_sum)
            conv_layer_part.en_channel(self.en_channel)
            conv_layer_part.en_batch(self.en_batch)
            conv_layer_part.en_act(self.en_act)
            conv_layer_part.input(self.input)

            self.output[(i+1)*offset:i*offset](conv_layer_part.output)


class ConvLayerPart(Unit):
    def __init__(self, input_width=9, output_width=1, layer_id=0,
                 process_id=0):
        self.input_width = input_width
        self.output_width = output_width

        super().__init__()
        name = f"ConvLayerL{layer_id}P{process_id}"
        self._hdl_module_name = name
        self._name = name

    def _declr(self):
        self.clk = Signal()
        self.rst = Signal()
        self.en_mult = Signal()
        self.en_sum = Signal()
        self.en_channel = Signal()
        self.en_batch = Signal()
        self.en_act = Signal()
        self.input = VectSignal(self.input_width)
        self.output = VectSignal(self.output_width)._m()

    def _impl(self):
        self.output(
            self._sig(name="dummy_signal", def_val=1,
                      dtype=Bits(self.output_width, force_vector=True)))


if __name__ == '__main__':
    from sys import argv
    from utils import get_logger, to_vhdl

    if (len(argv) > 1):
        path = argv[1]

        get_logger()
        unit = ConvLayer(channels=3, filters=16, binary=True, bin_input=False,
                         width=16, bin_output=False, weights=5000*[10], size=3,
                         top_entity=True, parallelism=4)
        to_vhdl(unit, path)
    else:
        print("file.py <outputpath>")
