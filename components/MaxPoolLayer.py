from sys import argv
from ComponentClass import ComponentClass
from MaxPoolUnit import MaxPoolUnit
from myhdl import always_comb, block, Signal, intbv, ResetSignal


class MaxPoolLayer(ComponentClass):
    """
    This class gather some MaxPoolUnits with different channel input and
    outputs. Both inputs are concatenated in one signal to the layer. The same
    to the outputs.

    :param clk: clock signal
    :type clk: std_logic
    :param reset: reset signal
    :type reset: std_logic
    :param en_pool: enable signal
    :type en_pool: std_logic
    :param input: vector with the all channel inputs to the layer concatenated,
    each channel input gather four input values concatenated to form a
    input channel, each value should be an signed value with 16 bits width
    :type input: std_logic_vector
    :param output: the concatenated output values of the comparations
    :type output: unsigned
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print("Creating MaxPoolLayer layer={}...".format(self.layer_id))

        self.n_inputs = self.n_filters[self.layer_id]
        self.n_outputs = self.n_filters[self.layer_id]

        self.max_pool_units = [MaxPoolUnit(channel_id=i)
                               for i in range(self.n_outputs)]
        return

    @block
    def rtl(self, clk, reset, input, output, en_pool):
        wire_channel_inputs = [Signal(intbv(0)[4*16:])
                               for _ in range(self.n_inputs)]
        wire_channel_outputs = [Signal(intbv(0)[16:])
                                for _ in range(self.n_outputs)]
        max_pool_units = [self.max_pool_units[i].rtl(
            clk=clk, reset=reset, input=wire_channel_inputs[i],
            en_pool=en_pool, output=wire_channel_outputs[i]
        ) for i in range(self.n_outputs)]

        @always_comb
        def comb_wire_inputs():
            for i in range(self.n_inputs):
                wire_channel_inputs[i].next = input[4*16*(i+1):4*16*i]

        @always_comb
        def comb_wire_outputs():
            aux = intbv(0)[self.n_outputs*16:]
            for i in range(self.n_outputs):
                aux[(i+1)*16:i*16] = wire_channel_outputs[i]
            output.next = aux

        return (max_pool_units, comb_wire_outputs, comb_wire_inputs)

    def get_signals(self):
        return {
            "clk": Signal(False),
            "reset": ResetSignal(0, active=1, isasync=1),
            "input": Signal(intbv(0)[4*self.n_inputs*16:]),
            "output": Signal(intbv(0)[self.n_outputs*16:]),
            "en_pool": Signal(False),
        }


if (__name__ == '__main__'):
    if (len(argv) > 2):
        name = argv[1]
        path = argv[2]

        unit = MaxPoolLayer(layer_id=0)
        unit.convert(name, path)
    else:
        print("file.py <entityname> <outputfile>")
