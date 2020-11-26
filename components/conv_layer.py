import logging
from math import sqrt

from .utils import print_info, float2fixed
from .multi_channel_conv_unit import MultiChannelConvUnit

from hwt.interfaces.std import Signal, VectSignal
from hwt.synthesizer.unit import Unit
from hwt.hdl.types.bits import Bits
from hwt.synthesizer.hObjList import HObjList
from hwt.interfaces.utils import propagateClkRst, addClkRst


class ConvLayer(Unit):
    """
    .. hwt-schematic::
    """

    def __init__(
        self,
        size=3,
        width=16,
        channels=3,
        filters=16,
        binary=False,
        bin_input=False,
        bin_output=False,
        weights=[],
        biases=[],
        mean=[],
        scale=[],
        variance=[],
        top_entity=False,
        parallelism=1,
        **kwargs,
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.size = size * size
        self.channels = channels
        self.filters = filters
        self.width = width
        self.binary = binary
        self.bin_input = bin_input
        self.bin_output = bin_output
        self.top_entity = top_entity
        self.parallelism = parallelism
        self.weights = weights
        self.biases = biases
        self.mean = mean
        self.scale = scale
        self.variance = variance

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
        self.output = VectSignal(self.filters * self.OUTPUT_WIDTH)._m()

        if self.top_entity:
            output_width = int(self.filters / self.parallelism) * self.OUTPUT_WIDTH
            # instantiate empty ConvLayerPart
            self.conv_layer_part = HObjList(
                ConvLayerPart(
                    input_width=self.size * self.channels * self.INPUT_WIDTH,
                    output_width=output_width,
                    layer_id=self.layer_id,
                    process_id=i,
                    log_level=0,
                )
                for i in range(self.parallelism)
            )
            name = f"ConvLayerL{self.layer_id}"
        else:
            # instantiate dynamically multichannel units
            self.conv_layer_part = HObjList(
                MultiChannelConvUnit(
                    layer_id=self.layer_id,
                    unit_id=i,
                    width=self.width,
                    channels=self.channels,
                    binary=self.binary,
                    size=self.size,
                    bin_input=self.bin_input,
                    bin_output=self.bin_output,
                    process_id=self.process_id,
                    log_level=self.log_level + 1,
                )
                for i in range(self.filters)
            )
            name = f"ConvLayerL{self.layer_id}P{self.process_id}"
        self._hdl_module_name = name
        self._name = name

    def _impl(self):
        propagateClkRst(self)
        if self.top_entity:
            offset = int(self.filters / self.parallelism) * self.OUTPUT_WIDTH
            range_limit = self.parallelism
        else:
            self.logger.debug(f"weights in this part {len(self.weights)}")
            # multi channel instantiation
            self.bucket_weights = []
            offset = self.size * self.channels
            for i in range(self.filters):
                weight_part = self.weights[i * offset : (i + 1) * offset]
                self.bucket_weights.append(weight_part)

            offset = self.OUTPUT_WIDTH
            range_limit = self.filters

        # print(range_limit, len(self.scale), len(self.biases))
        for i in range(range_limit):
            conv_layer_part = self.conv_layer_part[i]
            conv_layer_part.en_mult(self.en_mult)
            conv_layer_part.en_sum(self.en_sum)
            conv_layer_part.en_channel(self.en_channel)
            conv_layer_part.en_batch(self.en_batch)
            conv_layer_part.en_act(self.en_act)
            conv_layer_part.input(self.input)

            if not self.top_entity:
                # multi channel conv units instantiation
                weights = self.bucket_weights[i]
                integer_portion = 4 if self.width == 16 else 3
                decimal_portion = 11 if self.width == 16 else 4
                self.logger.debug("bucket list length " f"{len(self.bucket_weights)}")
                self.logger.debug(f"weights list length {len(weights)}")
                ssi_coef = self.scale[i] / sqrt(self.variance[i])
                bn_coef = self.biases[i] / ssi_coef - self.mean[i]
                # print(ssi_coef, bn_coef)
                ssi_coef = float2fixed(
                    weights=[ssi_coef],
                    integer_portion=integer_portion,
                    decimal_portion=decimal_portion,
                )[0]
                bn_coef = float2fixed(
                    weights=[bn_coef],
                    integer_portion=integer_portion,
                    decimal_portion=decimal_portion,
                )[0]
                # print(ssi_coef, bn_coef)

                conv_layer_part.ssi_coef(ssi_coef)
                conv_layer_part.bn_coef(bn_coef)

                for j in range(self.channels):
                    channel_weights = weights[j * self.size : (j + 1) * self.size]
                    self.logger.debug("weights by channel " f"{len(channel_weights)}")

                    sum_weights = sum(channel_weights)
                    avg_weights = 0 if not sum_weights else sum_weights / self.size
                    convert_list = [avg_weights] if self.binary else channel_weights

                    kernel = float2fixed(
                        weights=convert_list,
                        integer_portion=integer_portion,
                        decimal_portion=decimal_portion,
                    )
                    kernel_sig_list = [str(int(w < 0)) for w in channel_weights]
                    kernel_sig = int("".join(kernel_sig_list), 2)

                    if self.binary:
                        getattr(conv_layer_part, f"kernel_abs_{j}")(kernel[0])
                        getattr(conv_layer_part, f"kernel_sig_{j}")(kernel_sig)
                    else:
                        for k in range(self.size):
                            kernel_port = getattr(
                                conv_layer_part, f"kernel_{j*self.size+k}"
                            )
                            kernel_port(kernel[k])

            self.output[(i + 1) * offset : i * offset](conv_layer_part.output)


class ConvLayerPart(Unit):
    def __init__(
        self,
        input_width=9,
        output_width=1,
        layer_id=0,
        width=16,
        process_id=0,
        **kwargs,
    ):
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
            self._sig(
                name="dummy_signal",
                def_val=1,
                dtype=Bits(self.output_width, force_vector=True),
            )
        )


if __name__ == '__main__':
    from sys import argv
    from utils import get_std_logger, to_vhdl

    if len(argv) > 1:
        path = argv[1]

        get_std_logger()
        unit = ConvLayer(
            channels=3,
            filters=16,
            binary=True,
            bin_input=False,
            width=16,
            bin_output=False,
            weights=5000 * [10],
            size=3,
            top_entity=True,
            parallelism=4,
        )
        to_vhdl(unit, path)
    else:
        print("file.py <outputpath>")
