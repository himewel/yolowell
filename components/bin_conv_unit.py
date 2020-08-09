from sys import argv
from base_component import BaseComponent
from kernel_rom import KernelROM
from fixed_point_multiplier import FixedPointMultiplier
from utils import convert_fixed
from myhdl import always_seq, always_comb, block, Signal, intbv, ResetSignal


class BinConvUnit(BaseComponent):
    """
    This class implements a block of binary convolutional unit used in this
    architecture. The block contains nine inputs from the input image channel,
    nine inputs from the kernel values, some control signals to the pipeline
    registers and an output representing a convolved pixel.

    The en_mult signal enables the multiplications with inputs and kernel
    values to be storaged in registers. The en_sum signal enables the calcule
    of the sums(organized in tree format) between the product of each calue
    calculated to be propagate to the outputs. The convolutions are maked using
    only the magnitude signal as in binary convolution networks.
    """
    def __init__(self, bin_input=False, weights=[], **kwargs):
        super().__init__(**kwargs)
        print("%-24s%-10i%-10i%-16i%-10s%-10s" % ("BinConvUnit", self.layer_id,
              self.unit_id, self.channel_id, "-", "-"))

        # quantify weights
        sum_weights = sum(weights)
        avg_weights = 0 if not sum_weights else sum_weights/len(weights)
        self.kernel = convert_fixed([avg_weights])[0]

        # set input and output width
        self.INPUT_WIDTH = 1 if bin_input else 16
        self.SIGNAL_BIT = self.INPUT_WIDTH - 1

        self.mult = FixedPointMultiplier()
        return

    @block
    def rtl(self, clk, reset, en_mult, en_sum, input, output):
        """
        This function implements the combinational and sequential blocks of
        this block.

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
        wire_inputs = [Signal(intbv(0)[self.INPUT_WIDTH:]) for _ in range(9)]

        xor_list = [Signal(intbv(0)[3:]) for _ in range(9)]
        first_sum = [Signal(intbv(0)[4:]) for _ in range(4)]
        second_sum = [Signal(intbv(0)[5:]) for _ in range(2)]
        third_sum = Signal(intbv(0)[6:])

        kernel = Signal(intbv(self.kernel)[16:])
        delta = Signal(intbv(0)[16:])
        mult_ouput = Signal(intbv(0)[16:])

        multplier_unit = self.mult.rtl(
            clk=clk, reset=reset, param_a=delta, param_b=kernel,
            product=mult_ouput
        )

        @always_comb
        def combinatorial_wires():
            for i in range(9):
                wire_inputs[i].next = \
                    input[self.INPUT_WIDTH*(i+1):self.INPUT_WIDTH*i]

        @always_comb
        def combinational_xor():
            for i in range(9):
                if (wire_inputs[i][self.SIGNAL_BIT] ^ kernel[15]):
                    xor_list[i].next = 1
                else:
                    xor_list[i].next = -1

        @always_comb
        def combinatorial_first_sums():
            first_sum[0].next = xor_list[0] + xor_list[1]
            first_sum[1].next = xor_list[2] + xor_list[3]
            first_sum[2].next = xor_list[4] + xor_list[5]
            first_sum[3].next = xor_list[6] + xor_list[7]

        @always_comb
        def combinatorial_second_sums():
            second_sum[0].next = first_sum[0] + first_sum[1]
            second_sum[1].next = first_sum[2] + first_sum[3]

        @always_comb
        def combinatorial_third_sum():
            third_sum.next = second_sum[0] + second_sum[1] + xor_list[8]

        @always_seq(clk.posedge, reset=reset)
        def process():
            if (en_mult == 1):
                for i in range(5, 15):
                    delta[i].next = 0
                delta[15].next = third_sum[5]
                delta[4].next = third_sum[4]
                delta[3].next = third_sum[3]
                delta[2].next = third_sum[2]
                delta[1].next = third_sum[1]
                delta[0].next = third_sum[0]
            if (en_sum == 1):
                output.next = mult_ouput

        return (combinatorial_wires, multplier_unit, combinational_xor,
                process, combinatorial_first_sums, combinatorial_second_sums,
                combinatorial_third_sum)

    def get_signals(self):
        """
        This function returns the signals necessairly to instantiate the rtl
        block and convert the python method to a vhdl file.

        :return: a dict specifying the input and outputs signals of the block.
        :rtype: dict of myhdl.Signal

        **Python definition of inputs and ouputs:**

        .. code-block:: python

            def get_signals(self):
                return {
                    "clk": Signal(False),
                    "reset": ResetSignal(0, active=1, isasync=1),
                    "en_mult": Signal(False),
                    "en_sum": Signal(False),
                    "input": Signal(intbv(0)[9*16:]),
                    "output": Signal(intbv(0)[16:])
                }

        **VHDL component generated:**

        .. code-block:: vhdl

            component BinConvUnit
                port (
                    clk: in std_logic;
                    reset: in std_logic;
                    en_mult: in std_logic;
                    en_sum: in std_logic;
                    input: in unsigned(143 downto 0);
                    output: out unsigned(15 downto 0)
                );
            end component BinConvUnit;

        """
        return {
            "clk": Signal(False),
            "reset": ResetSignal(0, active=1, isasync=1),
            "en_mult": Signal(False),
            "en_sum": Signal(False),
            "input": Signal(intbv(0)[9*self.INPUT_WIDTH:]),
            "output": Signal(intbv(0)[16:])
        }


if __name__ == '__main__':
    if (len(argv) > 2):
        name = argv[1]
        path = argv[2]

        unit = BinConvUnit(weights=[15.58], bin_input=True)
        unit.convert(name, path)
    else:
        print("file.py <entityname> <outputfile>")
