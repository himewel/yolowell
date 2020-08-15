from sys import argv
from base_component import BaseComponent
from kernel_rom import KernelROM
from fixed_point_multiplier import FixedPointMultiplier
from utils import convert_fixed
from myhdl import always_seq, always_comb, block, Signal, intbv, ResetSignal


class ConvUnit(BaseComponent):
    """
    This class implements a block of convolutional unit used in this
    architecture. The block contains nine inputs from the input image channel,
    nine inputs from the kernel values, some control signals to the pipeline
    registers and an output representing a convolved pixel.

    The en_mult signal enables the multiplications with inputs and kernel
    values to be storaged in registers. The en_sum signal enables the calcule
    of the sums(organized in tree format) between the product of each calue
    calculated to be propagate to the outputs.

    :param weights: an array with the weights to be filled in KernelROM
    :type weights: List()
    """
    def __init__(self, size=3, width=16, weights=[], **kwargs):
        super().__init__(**kwargs)
        print("%-24s%-10i%-10i%-16i%-10s%-10s" % ("ConvUnit", self.layer_id,
              self.unit_id, self.channel_id, "-", "-"))

        self.size = size*size
        self.width = width

        if (width == 16):
            self.kernel_rom = tuple(
                convert_fixed(
                    weights=weights,
                    integer_portion=4,
                    decimal_portion=11))
        else:
            self.kernel_rom = tuple(
                convert_fixed(
                    weights=weights,
                    integer_portion=3,
                    decimal_portion=4))

        self.mult = [FixedPointMultiplier(width=width)
                     for i in range(self.size)]
        return

    @block
    def rtl(self, clk, reset, en_mult, en_sum, input, output):
        wire_inputs = [Signal(intbv(0)[self.width:]) for _ in range(self.size)]
        wire_kernels = [Signal(intbv(0)[self.width:])
                        for _ in range(self.size)]

        partial_mult = [Signal(intbv(0)[self.width:]) for _ in range(9)]
        mult_ouputs = [Signal(intbv(0)[self.width:]) for _ in range(9)]

        first_sum = [Signal(intbv(0)[self.width:]) for _ in range(4)]
        second_sum = [Signal(intbv(0)[self.width:]) for _ in range(2)]
        third_sum = Signal(intbv(0)[self.width:])

        kernel = self.kernel_rom

        # external unit instantiation
        multiplier_units = [self.mult[i].rtl(
            clk=clk, reset=reset, param_a=wire_inputs[i],
            param_b=wire_kernels[i], product=mult_ouputs[i])
            for i in range(self.size)]

        @always_comb
        def combinatorial_wires():
            for i in range(self.size):
                wire_inputs[i].next = input[self.width*(i+1):self.width*i]
                wire_kernels[i].next = kernel[i]

        @always_comb
        def combinatorial_first_sums():
            first_sum[0].next = partial_mult[0] + partial_mult[1]
            first_sum[1].next = partial_mult[2] + partial_mult[3]
            first_sum[2].next = partial_mult[4] + partial_mult[5]
            first_sum[3].next = partial_mult[6] + partial_mult[7]

        @always_comb
        def combinatorial_second_sums():
            second_sum[0].next = first_sum[0] + first_sum[1]
            second_sum[1].next = first_sum[2] + first_sum[3]

        @always_comb
        def combinatorial_third_sum():
            third_sum.next = second_sum[0] + second_sum[1] + partial_mult[8]

        @always_seq(clk.posedge, reset=reset)
        def process():
            if (en_mult == 1):
                for i in range(9):
                    partial_mult[i].next = mult_ouputs[i]
            if (en_sum == 1):
                if (self.size == 9):
                    output.next = third_sum
                else:
                    output.next = partial_mult[0]

        return (multiplier_units, combinatorial_wires, process,
                combinatorial_first_sums, combinatorial_second_sums,
                combinatorial_third_sum)

    def get_signals(self):
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
        return {
            "clk": Signal(False),
            "reset": ResetSignal(0, active=1, isasync=1),
            "en_mult": Signal(False),
            "en_sum": Signal(False),
            "input": Signal(intbv(0)[self.size*self.width:]),
            "output": Signal(intbv(0)[self.width:])
        }


if __name__ == '__main__':
    if (len(argv) > 2):
        name = argv[1]
        path = argv[2]

        unit = ConvUnit(weights=9*[2.59], size=3, width=8)
        unit.convert(name, path)
    else:
        print("file.py <entityname> <outputfile>")
