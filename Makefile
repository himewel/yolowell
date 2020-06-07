conv_unit:
	python3 components/ConvUnit.py ConvUnit generated

multichannel:
	( \
		python3 components/MultiChannelConvUnit.py MultiChannelConvUnit generated; \
		sed -i -e 's/acc(i) </acc(i) :/g' generated/MultiChannelConvUnit.vhd; \
		sed -i -e 's/acc((output_index + i)) </acc((output_index + i)) :/g' generated/MultiChannelConvUnit.vhd; \
	)

multiplier:
	python3 components/FixedPointMultiplier.py Multiplier generated

conv_layer:
	( \
		python3 components/ConvLayer.py ConvLayer generated; \
		sed -i -e 's/acc(i) </acc(i) :/g' generated/ConvLayer.vhd; \
		sed -i -e 's/acc((output_index + i)) </acc((output_index + i)) :/g' generated/ConvLayer.vhd; \
	)

pool_layer:
	python3 components/MaxPoolLayer.py MaxPoolLayer generated

kernel:
	python3 components/KernelROM.py KernelROM generated

scatter:
	python3 components/TriScatterUnit.py TriScatterUnit generated

docs:
	(\
		rm -rf ./docs; \
		sphinx-build -M html docsrc docsrc/_build; \
		cp -rf docsrc/_build/html docs; \
		echo "" >> docs/.nojekyll; \
	)
