library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;
use std.textio.all;

entity top is
    port (
        clk        : in  std_logic;
        reset      : in  std_logic;
        en_bias    : in  std_logic;
        en_mult    : in  std_logic;
        en_sum     : in  std_logic;
        en_channel : in  std_logic;
        en_batch   : in  std_logic;
        en_act     : in  std_logic;
        input0     : in  unsigned(3*16-1 downto 0);
        input1     : in  unsigned(3*16-1 downto 0);
        input2     : in  unsigned(3*16-1 downto 0);
        output     : out unsigned(255 downto 0)
    );
end entity;

architecture top of top is
    signal reg00, reg01, reg02:  unsigned(3*16-1 downto 0);
    signal reg10, reg11, reg12:  unsigned(3*16-1 downto 0);
    signal reg20, reg21, reg22:  unsigned(3*16-1 downto 0);

    component ConvLayer
        port (
            clk        : in  std_logic;
            reset      : in  std_logic;
            input      : in  unsigned(431 downto 0);
            output     : out  unsigned(255 downto 0);
            en_mult    : in  std_logic;
            en_sum     : in  std_logic;
            en_channel : in  std_logic;
            en_batch   : in  std_logic;
            en_act     : in  std_logic
        );
    end component ConvLayer;

begin
    process(clk)
    begin
        if rising_edge(clk) then
            reg00 <= input0;
            reg10 <= input1;
            reg20 <= input2;

            reg01 <= reg00;
            reg11 <= reg10;
            reg21 <= reg20;

            reg02 <= reg01;
            reg12 <= reg11;
            reg22 <= reg21;
        end if;
    end process;

    ConvLayer_i : ConvLayer
    port map (
        clk        => clk,
        reset      => reset,
        input      => reg00 & reg01 & reg02 & reg10 & reg11 & reg12 & reg20 & reg21 & reg22,
        output     => output,
        en_mult    => en_mult,
        en_sum     => en_sum,
        en_channel => en_channel,
        en_batch   => en_batch,
        en_act     => en_act
    );

end architecture;
