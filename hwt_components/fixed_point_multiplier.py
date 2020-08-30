from sys import argv
import logging

from myhdl import (always_comb, block, Signal, intbv, modbv)


class FixedPointMultiplier():
    """
    This class implements a 16 bits fixed point Q5.11 multiplier. The main
    objective of this component is make able the use of registers inside the
    multipliers in the architecture. At first the multipliers offered by the
    FPGA device were potential critical paths as they are indivisible to the
    pipeline stages. Although not used yet, the reset and clk signals are here
    to make the implementation of the registers less painful.

    :param clk: clock signal
    :type clk: std_logic
    :param reset: reset signal
    :type reset: std_logic
    :param param_a: a value unsigned in fixed point representation
    :type param_a: unsigned (actually a signed value)
    :param param_b: other value unsigned in fixed point representation
    :type param_b: unsigned (actually a signed value)
    :param product: the result of parm_a and param_b multiplication in fixed \
    point representation.
    :type product: unsigned (actually a signed value)
    """
    logger = logging.getLogger(__name__)

    def __init__(self, width=16):
        self.width = width
        self.lower_output_bit = int(width - width/2)
        self.pow = int(2**(width-1)) - 1
        return

    @block
    def concatenator(self, param_a, param_b, index, output):
        @always_comb
        def logic():
            output_var = modbv(0)[self.width*2-2:]
            if (param_a[index] == 1):
                output_var[self.width-1:] = param_b
                if (param_b[self.width-2] == 1):
                    output_var[self.width*2-2:self.width-1] = self.pow
                output_var <<= index
            output.next = output_var
        return logic

    @block
    def rtl(self, clk, reset, param_a, param_b, product):
        concat_value = [Signal(intbv(0)[self.width*2-1:]) for _ in range(15)]
        first_sum = [Signal(intbv(0)[self.width*2-1:]) for _ in range(7)]
        second_sum = [Signal(intbv(0)[self.width*2-1:]) for _ in range(4)]
        third_sum = [Signal(intbv(0)[self.width*2-1:]) for _ in range(2)]
        fourth_sum = Signal(intbv(0)[self.width*2-1:])

        data_a = Signal(intbv(0)[15:])
        data_b = Signal(intbv(0)[15:])
        non_zero_a = Signal(False)
        non_zero_b = Signal(False)
        xor_signals = Signal(False)
        magnitude = Signal(False)

        concatenadores = [self.concatenator(param_a=data_a, param_b=data_b,
                          index=i, output=concat_value[i]) for i in range(15)]

        @always_comb
        def combinatorial_first_sums():
            data_a.next = param_a[self.width-1:]
            data_b.next = param_b[self.width-1:]

            first_sum[0].next = concat_value[0] + concat_value[1]
            first_sum[1].next = concat_value[2] + concat_value[3]
            first_sum[2].next = concat_value[4] + concat_value[5]
            first_sum[3].next = concat_value[6] + concat_value[7]
            first_sum[4].next = concat_value[8] + concat_value[9]
            first_sum[5].next = concat_value[10] + concat_value[11]
            first_sum[6].next = concat_value[12] + concat_value[13]

        @always_comb
        def combinatorial_second_sums():
            non_zero_a.next = False if (data_a == 0) else True
            non_zero_b.next = False if (data_b == 0) else True
            xor_signals.next = param_a[self.width-1] ^ param_b[self.width-1]
            second_sum[0].next = first_sum[0] + first_sum[1]
            second_sum[1].next = first_sum[2] + first_sum[3]
            second_sum[2].next = first_sum[4] + first_sum[5]
            second_sum[3].next = first_sum[6] + concat_value[14]

        @always_comb
        def combinatorial_third_sums():
            magnitude.next = xor_signals & non_zero_a & non_zero_b
            third_sum[0].next = second_sum[0] + second_sum[1]
            third_sum[1].next = second_sum[2] + second_sum[3]

        @always_comb
        def combinatorial_fourth_sum():
            fourth_sum.next = third_sum[0] + third_sum[1]

        @always_comb
        def comb_output():
            product[self.width-1].next = magnitude
            for i in range(self.width-1):
                product[i].next = fourth_sum[self.lower_output_bit+i]

        return (concatenadores, comb_output, combinatorial_first_sums,
                combinatorial_second_sums, combinatorial_third_sums,
                combinatorial_fourth_sum)

    def get_signals(self):
        return {
            "clk": Signal(False),
            "reset": Signal(False),
            "param_a": Signal(intbv(0)[self.width:]),
            "param_b": Signal(intbv(0)[self.width:]),
            "product": Signal(intbv(0)[self.width:]),
        }


if __name__ == '__main__':
    if (len(argv) > 2):
        name = argv[1]
        path = argv[2]

        unit = FixedPointMultiplier(width=8)
        unit.convert(name, path)
    else:
        print("file.py <entityname> <outputfile>")
