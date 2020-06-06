from sys import argv
from ComponentClass import ComponentClass
from MultiChannelConvUnit import MultiChannelConvUnit
from myhdl import always_comb, block, Signal, intbv, ResetSignal


class ConvLayer(ComponentClass):
    """
    This class gather some MultiChannelConvUnits sharing the same inputs and
    makes your outputs availables to an external unit, probably a BufferLayer.
    The number MultiChannelConvUnits instantiated is this class is defined in
    the constants of the ComponentClass.

    :param clk: clock signal
    :type clk: std_logic
    :param reset: reset signal
    :type reset: std_logic
    :param en_mult: enable signal
    :type en_mult: std_logic
    :param en_sum: enable signal
    :type en_sum: std_logic
    :param input: vector with the nine input values cancatenated, each
    value should be an signed value with 16 bits width
    :type input: std_logic_vector
    :param output: the output value of the convolutions
    :type output: unsigned
    """
    def __init__(self, layer_id=0, **kwargs):
        super().__init__(**kwargs)
        print("Creating ConvLayer layer={}...".format(
            self.layer_id, self.unit_id, self.channel_id))

        self.n_inputs = self.n_channels[layer_id]
        self.n_outputs = self.n_filters[layer_id]
        self.layer_id = layer_id

        self.mult_channel_conv_units = [MultiChannelConvUnit(
            layer_id=self.layer_id,
            unit_id=i
        ) for i in range(self.n_outputs)]
        return

    @block
    def rtl(self, clk, reset, input, output, en_mult, en_sum, en_channel,
            en_batch, en_act):
        wire_channel_outputs = [Signal(intbv(0)[16:])
                                for _ in range(self.n_outputs)]
        mult_channel_conv_units = [self.mult_channel_conv_units[i].rtl(
            clk=clk, reset=reset, input=input, en_mult=en_mult, en_sum=en_sum,
            en_channel=en_channel, en_batch=en_batch, en_act=en_act,
            output=wire_channel_outputs[i]
        ) for i in range(self.n_outputs)]

        @always_comb
        def process():
            aux = intbv(0)[self.n_outputs*16:]
            for i in range(self.n_outputs):
                aux[(i+1)*16:i*16] = wire_channel_outputs[i]
            output.next = aux

        return (mult_channel_conv_units, process)

    def get_signals(self):
        return {
            "clk": Signal(False),
            "reset": ResetSignal(0, active=1, isasync=1),
            "input": Signal(intbv(0)[9*self.n_inputs*16:]),
            "output": Signal(intbv(0)[self.n_outputs*16:]),
            "en_mult": Signal(False),
            "en_sum": Signal(False),
            "en_channel": Signal(False),
            "en_batch": Signal(False),
            "en_act": Signal(False)
        }


if __name__ == '__main__':
    if (len(argv) > 2):
        name = argv[1]
        path = argv[2]

        unit = ConvLayer(layer_id=0)
        unit.convert(name, path)
    else:
        print("file.py <entityname> <outputfile>")
