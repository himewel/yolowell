conv_unit:
	python3 components/conv_unit.py ConvUnit generated

bin_conv_unit:
	python3 components/bin_conv_unit.py BinConvUnit generated

multichannel:
	( \
		python3 components/multi_channel_conv_unit.py MultiChannelConvUnit generated; \
		sed -i -e 's/acc(i) </acc(i) :/g' generated/MultiChannelConvUnit.vhd; \
		sed -i -e 's/acc((output_index + i)) </acc((output_index + i)) :/g' generated/MultiChannelConvUnit.vhd; \
	)

multiplier:
	python3 components/fixed_point_multiplier.py Multiplier generated

conv_layer:
	( \
		python3 components/conv_layer.py ConvLayer ./generated; \
		sed -i -e 's/acc(i) </acc(i) :/g' generated/ConvLayer.vhd; \
		sed -i -e 's/acc((output_index + i)) </acc((output_index + i)) :/g' generated/ConvLayer.vhd; \
	)

pool_layer:
	python3 components/max_pool_layer.py MaxPoolLayer generated

bin_max_pool_unit:
	python3 components/bin_max_pool_unit.py BinMaxPoolUnit generated

kernel:
	python3 components/kernel_rom.py KernelROM generated

scatter:
	python3 components/tri_scatter_unit.py TriScatterUnit generated

docs:
	(\
		rm -rf ./docs ./docsrc/_build; \
		sphinx-build -M html docsrc docsrc/_build; \
		cp -rf docsrc/_build/html docs; \
		echo "" >> docs/.nojekyll; \
	)
