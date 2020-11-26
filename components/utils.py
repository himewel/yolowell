from hwt.serializer.store_manager import StoreManager, SaveToStream, SaveToFilesFlat


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
        if name != self.entity:
            return
        f_name = name + self.serializer_cls.fileExtension
        fp = os.path.join(self.root, f_name)
        self.filepath = fp

        with open(fp, 'w') as f:
            s = SaveToStream(self.serializer_cls, f, self.filter, self.name_scope)
            s.write(obj)


def read_floats(file_path=""):
    """
    This function reads the file passed by the parameters and return the
    float list of values readed in the file.
    """
    import pickle

    weights = []
    with open("{}".format(file_path), "rb") as binary_stream:
        weights = pickle.load(binary_stream)
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

        str_decimal = ""
        while len(str_decimal) < decimal_portion:
            str_decimal += "1" if int(decimal * 2) == 1 else "0"
            decimal = abs(int(decimal * 2) - float(decimal * 2))

        integer_mask = '{0:0' + str(integer_portion) + 'b}'
        num = "{}{}".format(integer_mask.format(inteiro), str_decimal)

        if sinal == 1:
            num = num.replace("0", "-")
            num = num.replace("1", "0")
            num = num.replace("-", "1")
            num = int(num, 2) + 1
        else:
            num = int(num, 2)

        fixed_weight_mask = '{0:0' + str(integer_portion + decimal_portion) + 'b}'
        binary_value = "{signal}{integer_value}".format(
            signal='{0:01b}'.format(sinal),
            integer_value=fixed_weight_mask.format(int(num)),
        )
        int_fixed_weight = int(binary_value, 2)
        if int_fixed_weight > 2 ** (integer_portion + decimal_portion + 1):
            if sinal == 0:
                int_fixed_weight = 2 ** (integer_portion + decimal_portion + 1) - 1
            else:
                int_fixed_weight = 2 ** (integer_portion + decimal_portion + 1)

        fixed_weights.append(int_fixed_weight)
    return fixed_weights


def print_info(self, **kwargs):
    self.process_id = kwargs.get("process_id", 0)
    self.layer_id = kwargs.get("layer_id", 0)
    self.unit_id = kwargs.get("unit_id", 0)
    self.channel_id = kwargs.get("channel_id", 0)
    self.log_level = kwargs.get("log_level", 0)

    if self.log_level < 2:
        self.logger.info(
            f"Process {self.process_id} Layer {self.layer_id} "
            f"Unit {self.unit_id} Channel {self.channel_id} "
            "PARSER"
        )


def get_file_logger():
    import logging

    format = "%(asctime)s %(name)s:%(lineno)d - %(message)s"
    logging.basicConfig(
        filename="network_parser.log",
        filemode="w",
        format=format,
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)
    return logger


def get_std_logger():
    import logging
    import coloredlogs

    coloredlogs.install()
    format = "%(asctime)s %(name)s:%(lineno)d - %(message)s"
    logging.basicConfig(
        format=format, level=logging.CRITICAL, datefmt="%Y-%m-%d %H:%M:%S"
    )
    logger = logging.getLogger(__name__)
    return logger


def to_vhdl(unit=None, path=".", name=""):
    print("Converting hdl file... ", end="")
    from hwt.serializer.vhdl import Vhdl2008Serializer

    file = save_file(unit, Vhdl2008Serializer, path, name)
    print("Ok!")
    return file


def to_verilog(unit=None, path=".", name=""):
    print("Converting hdl file... ", end="")
    from hwt.serializer.verilog import VerilogSerializer

    file = save_file(unit, VerilogSerializer, path, name)
    print("Ok!")
    return file


def to_systemc(unit=None, path=".", name=""):
    from hwt.serializer.systemC import SystemCSerializer

    print("Converting hdl file... ", end="")
    file = save_file(unit, SystemCSerializer, path, name)
    print("Ok!")
    return file


def save_file(unit, serializer, path, name):
    from hwt.synthesizer.utils import to_rtl
    import os

    os.makedirs(path, exist_ok=True)
    unit.logger.info(f"Worker healthcheck: PID {os.getpid()}")

    file_extension = serializer.fileExtension
    unit.logger.info(
        f"Process {unit.process_id} Layer {unit.layer_id} "
        f"Unit {unit.unit_id} Channel {unit.channel_id} WRITER"
    )
    unit.logger.info(f"Converting to {file_extension} in {path}/{name}{file_extension}")

    if unit.top_entity:
        store_manager = SaveTopEntity(serializer, path, name)
        to_rtl(unit, store_manager)
        return store_manager.filepath
    else:
        store_manager = SaveToFilesFlat(serializer, path)
        to_rtl(unit, store_manager)
        # code = to_rtl_str(unit, serializer_cls=serializer)
        # with open(f"{path}/{name}{file_extension}", "w") as file:
        #     file.write(code)
        return f"{path}/{name}{file_extension}"
