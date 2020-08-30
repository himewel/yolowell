from hwt.serializer.store_manager import StoreManager, SaveToStream


class SaveTopEntity(StoreManager):
    def __init__(self, serializer_cls=None, root="", entity=""):
        super(SaveTopEntity, self).__init__(serializer_cls)
        self.root = root
        self.entity = entity
        import os
        os.makedirs(root, exist_ok=True)

    def write(self, obj):
        import os
        name = obj.module_name.val
        if (name != self.entity):
            return
        f_name = name + self.serializer_cls.fileExtension
        fp = os.path.join(self.root, f_name)

        with open(fp, 'w') as f:
            s = SaveToStream(self.serializer_cls, f, self.filter,
                             self.name_scope)
            s.write(obj)


def read_floats(file_path="", start=0, final=0):
    """
    This function reads the file passed by the parameters and return the
    float list of values readed in the file.
    """
    weights = []
    with open("{}".format(file_path), "r") as file:
        text = file.read().replace("\n", "").replace("\t", "")
        text = text.split("{")
        text = text[1].split("}")
        text = text[0].split(",")

        try:
            for i in range(start, len(text) if final == 0 else final):
                weights.append(float(text[i]))
        except Exception:
            pass

    return weights


def float2fixed(weights=[], integer_portion=4, decimal_portion=11):
    """
    This funtion receives a list of weights and convert each one of the
    values to fixed point representation. By default, the decimal portion
    of the values are represented with 11 bits while the int portion is
    represented with 4 bits. One bit is reserved to the magnitude
    representation, totalizing 16 bits of fixed point representation.
    """
    fixed_weights = []
    for w in weights:
        sinal = 0 if w >= 0 else 1
        inteiro = int(abs(w))
        decimal = abs(w - inteiro)

        while (decimal*(decimal_portion-1) <= 2**decimal_portion
               and decimal != 0):
            decimal *= 10

        integer_mask = '{0:0' + str(integer_portion) + 'b}'
        decimal_mask = '{0:0' + str(decimal_portion) + 'b}'
        num = "{}{}".format(integer_mask.format(inteiro),
                            decimal_mask.format(int(decimal)))

        if (sinal == 1):
            num = num.replace("0", "-")
            num = num.replace("1", "0")
            num = num.replace("-", "1")
            num = int(num, 2) + 1
            num &= 0b1111111
        else:
            num = int(num, 2)

        fixed_weight_mask = \
            '{0:0' + str(integer_portion + decimal_portion) + 'b}'
        fixed_weights.append(
            int("{}{}".format('{0:01b}'.format(sinal),
                              fixed_weight_mask.format(int(num))), 2))
    return fixed_weights


def print_info(self, **kwargs):
    self.process_id = kwargs.get("process_id", 0)
    self.layer_id = kwargs.get("layer_id", 0)
    self.unit_id = kwargs.get("unit_id", 0)
    self.channel_id = kwargs.get("channel_id", 0)
    self.logger.info(f"Process {self.process_id} Layer {self.layer_id} "
                     f"Unit {self.unit_id} Channel {self.channel_id} PARSER")


def get_file_logger():
    import logging
    format = "%(asctime)s %(name)s:%(lineno)d - %(message)s"
    logging.basicConfig(filename="spellnet_parser.log", filemode="w",
                        format=format, level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    return logger


def get_std_logger():
    import logging
    import coloredlogs
    coloredlogs.install()
    format = "%(asctime)s %(name)s:%(lineno)d - %(message)s"
    logging.basicConfig(format=format, level=logging.CRITICAL)
    logger = logging.getLogger(__name__)
    return logger


def to_vhdl(unit=None, path="", name=""):
    from hwt.synthesizer.utils import to_rtl, to_rtl_str
    from hwt.serializer.vhdl import Vhdl2008Serializer
    import os
    os.makedirs(path, exist_ok=True)
    unit.logger.info(f"Healthcheck: PID {os.getpid()}")

    print("Converting hdl file... ", end="")
    unit.logger.info(f"Process {unit.process_id} Layer {unit.layer_id} "
                     f"Unit {unit.unit_id} Channel {unit.channel_id} WRITER")
    unit.logger.info(f"Converting to VHDL in {path}/{name}.vhd")

    if (unit.top_entity):
        store_manager = SaveTopEntity(Vhdl2008Serializer, path, name)
        to_rtl(unit, store_manager)
    else:
        code = to_rtl_str(unit, serializer_cls=Vhdl2008Serializer)
        unit.logger.info(f"Converting to VHDL in {path}/{name}.vhd")
        with open(f"{path}/{name}.vhd", "w") as file:
            file.write(code)
    print("Ok!")


def to_verilog(unit=None, path=""):
    from hwt.synthesizer.utils import to_rtl, to_rtl_str
    from hwt.serializer.verilog import VerilogSerializer
    from hwt.synthesizer.dummyPlatform import DummyPlatform

    healthcheck(unit)
    name = unit._name if unit._name else unit._getDefaultName()

    print("Converting hdl file... ", end="")
    unit.logger.info(f"Process {unit.process_id} Layer {unit.layer_id} "
                     f"Unit {unit.unit_id} Channel {unit.channel_id} WRITER")
    unit.logger.info(f"Converting to Verilog in {path}/{name}.v")

    if (unit.top_entity):
        store_manager = SaveTopEntity(VerilogSerializer, path, name)
        to_rtl(unit, store_manager, None, DummyPlatform())
    else:
        code = to_rtl_str(unit, serializer_cls=VerilogSerializer)
        with open(f"{path}/{unit._name}.v", "w") as file:
            file.write(code)
    print("Ok!")


def to_systemc(unit=None, path=""):
    from hwt.synthesizer.utils import to_rtl, to_rtl_str
    from hwt.serializer.systemC import SystemCSerializer
    from hwt.synthesizer.dummyPlatform import DummyPlatform

    healthcheck(unit)
    name = unit._name if unit._name else unit._getDefaultName()

    print("Converting hdl file... ", end="")
    unit.logger.info(f"Process {unit.process_id} Layer {unit.layer_id} "
                     f"Unit {unit.unit_id} Channel {unit.channel_id} WRITER")
    unit.logger.info(f"Converting to SystemC in {path}/{name}.cpp")

    if (unit.top_entity):
        store_manager = SaveTopEntity(SystemCSerializer, path, name)
        to_rtl(unit, store_manager, None, DummyPlatform())
    else:
        code = to_rtl_str(unit, serializer_cls=SystemCSerializer)
        with open(f"{path}/{unit._name}.cpp", "w") as file:
            file.write(code)
    print("Ok!")
