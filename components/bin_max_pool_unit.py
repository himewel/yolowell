from sys import argv
from base_component import BaseComponent
from myhdl import always_seq, always_comb, block, Signal, intbv, ResetSignal


class BinMaxPoolUnit(BaseComponent):
    """
    This block describes a max pooling unit. Four inputs feeds three
    comparators organized in tree format. The output of this block is the input
    value with the greater value. The en_pool signal enables the output
    register to be stored.

    :param clk: clock signal
    :type clk: std_logic
    :param reset: reset signal
    :type reset: std_logic
    :param en_pool: enable signal
    :type en_pool: std_logic
    :param input: vector with the four input values cancatenated, each value \
    should be an signed value with 16 bits width
    :type input: std_logic_vector
    :param output: the output value of the comparations
    :type output: unsigned
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print("%-24s%-10i%-10i%-16i%-10s%-10s" % ("BinMaxPoolUnit",
              self.layer_id, self.unit_id, self.channel_id, "-", "-"))

    @block
    def rtl(self, clk, reset, en_pool, input, output):
        first_pool0 = Signal(False)
        first_pool1 = Signal(False)

        @always_comb
        def combinatorial_first_pool():
            first_pool0.next = input[0] & input[1]
            first_pool1.next = input[3] & input[2]

        @always_seq(clk.posedge, reset=reset)
        def process():
            if (en_pool == 1):
                output.next = first_pool0 & first_pool1

        return process, combinatorial_first_pool

    def get_signals(self):
        return {
            "clk": Signal(False),
            "reset": ResetSignal(0, active=1, isasync=1),
            "en_pool": Signal(False),
            "input": Signal(intbv(0)[4:]),
            "output": Signal(False)
        }


if __name__ == '__main__':
    if (len(argv) > 2):
        name = argv[1]
        path = argv[2]

        unit = BinMaxPoolUnit()
        unit.convert(name, path)
    else:
        print("file.py <entityname> <outputfile>")
