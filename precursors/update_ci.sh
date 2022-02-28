#!/bin/bash
set -e

echo "Updating to latest stabilized release"

wget https://ci.betrusted.io/releases/latest/loader.bin -O loader.bin

wget https://ci.betrusted.io/releases/latest/xous.img -O xous.img

wget https://ci.betrusted.io/releases/latest/soc_csr.bin -O soc_csr.bin

wget https://ci.betrusted.io/releases/latest/ec_fw.bin -O ec_fw.bin
wget https://ci.betrusted.io/releases/latest/bt-ec.bin -O bt-ec.bin
wget https://ci.betrusted.io/releases/latest/wfm_wf200_C0.sec -O wfm_wf200_C0.sec
wget https://ci.betrusted.io/releases/latest/wf200_fw.bin -O wf200_fw.bin
