import logging

from utils import print_info

from hwt.code import If
from hwt.hdl.types.bits import Bits
from hwt.interfaces.std import Signal, VectSignal
from hwt.synthesizer.unit import Unit
from hwt.synthesizer.hObjList import HObjList


class FixedPointMultiplier(Unit):
    """
    .. hwt-schematic::
    """

    def __init__(self, width=16, pixel_id=0, **kwargs):
        self.logger = logging.getLogger(self.__class__.__name__)

        self.width = width
        self.lower_output_bit = int(width - width/2)
        self.pixel_id = pixel_id
        self.top_entity = False

        print_info(self, **kwargs)
        super().__init__()

    def _declr(self):
        self.clk = Signal()
        self.rst = Signal()
        self.param_a = VectSignal(self.width)
        self.param_b = VectSignal(self.width)
        self.product = VectSignal(self.width)._m()

        self.concat_units = HObjList(ConcatValues(
            index=i, layer_id=self.layer_id, unit_id=self.unit_id,
            channel_id=self.channel_id, process_id=self.process_id,
            pixel_id=self.pixel_id, width=self.width,
            log_level=self.log_level+1) for i in range(15))

        name = ("FixedPointMultiplierL{layer}F{filter}C{channel}Px{pixel}"
                "P{process}").format(
            layer=self.layer_id,
            filter=self.unit_id,
            channel=self.channel_id,
            pixel=self.pixel_id,
            process=self.process_id)
        self._name = name
        self._hdl_module_name = name

    def __calc_tree_adders(self, input_list):
        signal_width = Bits(self.width*2-1)
        first_sum = [self._sig(name=f"first_sum_{i}", dtype=signal_width)
                     for i in range(7)]
        first_sum[0](input_list[0] + input_list[1])
        first_sum[1](input_list[2] + input_list[3])
        first_sum[2](input_list[4] + input_list[5])
        first_sum[3](input_list[6] + input_list[7])
        first_sum[4](input_list[8] + input_list[9])
        first_sum[5](input_list[10] + input_list[11])
        first_sum[6](input_list[12] + input_list[13])

        second_sum = [self._sig(name=f"second_sum_{i}", dtype=signal_width)
                      for i in range(4)]
        second_sum[0](first_sum[0] + first_sum[1])
        second_sum[1](first_sum[2] + first_sum[3])
        second_sum[2](first_sum[4] + first_sum[5])
        second_sum[3](first_sum[6] + input_list[14])

        third_sum = [self._sig(name=f"third_sum_{i}", dtype=signal_width)
                     for i in range(2)]
        third_sum[0](second_sum[0] + second_sum[1])
        third_sum[1](second_sum[2] + second_sum[3])

        fourth_sum = self._sig(name="fourth_sum", dtype=signal_width)
        fourth_sum(third_sum[0] + third_sum[1])
        return fourth_sum

    def _impl(self):
        concat_type = Bits(bit_length=self.width*2-1, force_vector=True)
        concat_inputs = \
            [self._sig(name=f"concat_inputs_{i}", dtype=concat_type)
             for i in range(15)]
        data_type = Bits(bit_length=15, force_vector=True)
        data_a = self._sig(name="data_a", dtype=data_type, def_val=0)
        data_b = self._sig(name="data_b", dtype=data_type, def_val=0)
        non_zero_a = self._sig(name="non_zero_a", dtype=Bits(1))
        non_zero_b = self._sig(name="non_zero_b", dtype=Bits(1))
        xor_signal = self._sig(name="xor_signal", dtype=Bits(1))

        data_a[self.width-1:](self.param_a[self.width-1:])
        data_b[self.width-1:](self.param_b[self.width-1:])

        for i in range(15):
            self.concat_units[i].param_a(data_a)
            self.concat_units[i].param_b(data_b)
            concat_inputs[i](self.concat_units[i].output)
        fourth_sum = self.__calc_tree_adders(concat_inputs)

        If(data_a._eq(0), non_zero_a(0)).Else(non_zero_a(1))
        If(data_b._eq(0), non_zero_b(0)).Else(non_zero_b(1))

        xor_signal(self.param_a[self.width-1] ^ self.param_b[self.width-1])

        self.product[self.width-1](xor_signal & non_zero_a & non_zero_b)
        self.product[self.width-1:](
            fourth_sum[self.lower_output_bit+self.width-1:
                       self.lower_output_bit])


class ConcatValues(Unit):
    """
    .. hwt-schematic::
    """

    def __init__(self, index=0, pixel_id=0, width=0, **kwargs):
        self.logger = logging.getLogger(self.__class__.__name__)

        self.index = index
        self.pixel_id = pixel_id
        self.width = width
        self.pow = int(2**(width-1)) - 1

        print_info(self, **kwargs)
        super().__init__()
        pass

    def _declr(self):
        self.param_a = VectSignal(15)
        self.param_b = VectSignal(15)
        self.output = VectSignal(self.width*2-1)._m()

        name = ("ConcatValuesL{layer}F{filter}C{channel}Px{pixel}"
                "I{index}P{process}").format(
            layer=self.layer_id,
            filter=self.unit_id,
            channel=self.channel_id,
            pixel=self.pixel_id,
            index=self.index,
            process=self.process_id)
        self._name = name
        self._hdl_module_name = name

    def _impl(self):
        output_dtype = Bits(bit_length=self.width*2-1)
        output_var = self._sig(name="output_var", dtype=output_dtype,
                               def_val=0)

        If(
            self.param_a[self.index],
            output_var[self.width-1:](self.param_b[self.width-1:]),
            If(
                self.param_b[self.width-2],
                output_var[self.width*2-1:self.width-1](self.pow)
            ).Else(
                output_var[self.width*2-1:self.width-1](0)
            )
        ).Else(
            output_var(0)
        )

        if (self.index > 0):
            If(
                self.param_a[self.index],
                self.output[self.width*2-1:self.index](
                    output_var[self.width*2-1-self.index:]),
                self.output[self.index:](0)
            ).Else(
                self.output(0)
            )
        else:
            If(
                self.param_a[self.index],
                self.output[self.width*2-1:self.index](
                    output_var[self.width*2-1-self.index:])
            ).Else(
                self.output(0)
            )


"""
você recebeu cigaro do So7 (_̅_̅_̅(̅_̅_̅_̅_̅_̅_̅_̅()ڪے~ de um pega
e passa adiante
"""


if __name__ == '__main__':
    from sys import argv
    from utils import to_vhdl, get_std_logger

    if (len(argv) > 1):
        path = argv[1]

        get_std_logger()
        unit = FixedPointMultiplier(width=16)
        to_vhdl(unit, path, name="FixedPointMultiplierL0F0C0Px0P0")
    else:
        print("file.py <outputpath>")
