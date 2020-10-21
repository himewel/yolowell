conv_unit:
	python3 components/conv_unit.py ConvUnit generated

bin_conv_unit:
	python3 components/bin_conv_unit.py BinConvUnit generated

multichannel:
	python3 components/multi_channel_conv_unit.py MultiChannelConvUnit generated; \

multiplier:
	python3 components/fixed_point_multiplier.py Multiplier generated

conv_layer:
	python3 components/conv_layer.py ConvLayer ./generated

pool_layer:
	python3 components/max_pool_layer.py MaxPoolLayer generated

bin_max_pool_unit:
	python3 components/bin_max_pool_unit.py BinMaxPoolUnit generated

kernel:
	python3 components/kernel_rom.py KernelROM generated

tri_scatter:
	python3 components/tri_scatter_unit.py TriScatterUnit generated

dual_scatter:
	python3 components/dual_scatter_unit.py DualScatterUnit generated

mono_scatter:
	python3 components/mono_scatter_unit.py MonoScatterUnit generated

buffer_layer:
	python3 components/buffer_layer.py BufferLayer generated
