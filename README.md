<p align="center">
<img src="dummy/title.gif" alt="yolowell"/>
</p>

*yolowell* is a lib to generate VHDL code of convolutional networks and becomes part of a co-design hardware/software with a simplified version of Darknet running in a NIOS II processor. To improve parameter passing and generate different versions of the architecture better then with TCL or other type of script, we implement all the code in python language with HWToolKit.

## How to use

To generate the VHDL code, you will need to extract the weights, bias, and batch normalization params from your Darknet model and write him in binary format. After this, you can set a yaml config file as the following example.

``` yaml
weights: "yolov3_tiny_weights.bin"
output_path: "./generated"
width: 416
channels: 3
layer_groups:
- filters: 16
  layers:
  - type: "conv_layer"
    parallelism: 4
    size: 3
    binary: False
    bin_input: False
    bin_output: True
  - type: "max_pool_layer"
    binary: False
- filters: 32
  layers:
  - type: "conv_layer"
    size: 3
    binary: True
    bin_input: True
    bin_output: True
  - type: "max_pool_layer"
    binary: False
```

So, you need to set come variables:

* *output_path*: path to the generate vhdl files;
* *weight_path*: file path to the extracted weight values;
* *bias_path*: file path to the extracted bias values;
* *ssi_coef_path*: file path to the extracted ssi_coef values;
* *bn_coef_path*: file path to the extracted bn_coef values;
* *width*: width of the input image;
* *channels*: set the input channels of the architecture;
* *filters*: number of filters in the current block of layers (layer_groups will a list of dicts);
* *type*: "conv_layer" or "max_pool_layer";
* *size*: size of the filters (e.g., 3x3 -> 3, 1x1 -> 1);
* *binary*: type of operations, `false` to use multipliers, `true` to use xor gates;

If you are still here, import NetworkParser and be happy (or not):

```python
from components.network_parser import NetworkParser
from utils import get_std_logger, to_vhdl

get_std_logger()
net = NetworkParser("config_example.yaml")
layers = net.parse_network()
net.generate(layers, to_vhdl)
```

## References

* Darknet: https://github.com/AlexeyAB/darknet;
* HWToolKit: https://github.com/Nic30/hwt;
