from sys import argv
from ComponentClass import ComponentClass
from myhdl import always_seq, always_comb, block, Signal, intbv, ResetSignal


class MaxPoolUnit(ComponentClass):
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
        print(8*" "+"* Creating MaxPoolUnit channel={}..."
              .format(self.channel_id))

    @block
    def rtl(self, clk, reset, en_pool, input, output):
        first_pool0 = Signal(intbv(0)[16:])
        first_pool1 = Signal(intbv(0)[16:])

        @always_comb
        def combinatorial_first_pool():
            if (input[16:0] > input[32:16]):
                first_pool0.next = input[16:0]
            else:
                first_pool0.next = input[32:16]

            if (input[48:32] > input[64:48]):
                first_pool1.next = input[48:32]
            else:
                first_pool1.next = input[64:48]

        @always_seq(clk.posedge, reset=reset)
        def process():
            if (en_pool == 1):
                if (first_pool0 > first_pool1):
                    output.next = first_pool0
                else:
                    output.next = first_pool1

        return process, combinatorial_first_pool

    def get_signals(self):
        return {
            "clk": Signal(False),
            "reset": ResetSignal(0, active=1, isasync=1),
            "en_pool": Signal(False),
            "input": Signal(intbv(0)[4*16:]),
            "output": Signal(intbv(0)[16:])
        }


if __name__ == '__main__':
    if (len(argv) > 2):
        name = argv[1]
        path = argv[2]

        unit = MaxPoolUnit()
        unit.convert(name, path)
    else:
        print("file.py <entityname> <outputfile>")
