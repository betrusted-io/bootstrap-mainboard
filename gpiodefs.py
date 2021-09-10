FONT_HEIGHT=12
GPIO_START=20   # this is active high
GPIO_FUNC=16    # this is active low
GPIO_BSIM=26    # when high, the battery simulator is powered on
GPIO_ISENSE=37  # when high, current sense mode is high
GPIO_VBUS=21    # when high VBUS is applied to DUT
GPIO_UART_SOC=18 # when high, the UART is routed to the SoC; when low, to the EC
GPIO_PROG_B=24  # when low, the FPGA PROG_B line is asserted
GPIO_CRESET_N=25 # when low, the EC reset line is asserted
GPIO_AUD_HPR=0  # when high, the right headphone is looped back to the mic
GPIO_AUD_HPL=5  # when high, the left headphone is looped back to the mic
GPIO_AUD_SPK=26 # when high, the speaker output is looped back to the mic. Note left digital channel == speaker

GPIO_DRV_UP5K_N=23
GPIO_UP5K_MOSI=10
GPIO_UP5K_MISO=9
GPIO_UP5K_SCK=11
GPIO_UP5K_CSN=8

GPIO_JTAG_TCK=4
GPIO_JTAG_TMS=17
GPIO_JTAG_TDI=27
GPIO_JTAG_TDO=22


HAT_RED_LED = 12
HAT_GREEN_LED = 16
HAT_WHITE_LED = 20
HAT_START = 7

