#!/bin/bash
set -e

echo "Updating to latest stabilized release"
wget https://ci.betrusted.io/releases/LATEST -O /tmp/LATEST
REV=`cat /tmp/LATEST`
REVISION="releases/${REV}"

wget https://ci.betrusted.io/$REVISION/loader.bin -O loader.bin

wget https://ci.betrusted.io/$REVISION/xous.img -O xous.img

wget https://ci.betrusted.io/$REVISION/soc_csr.bin -O soc_csr.bin

wget https://ci.betrusted.io/$REVISION/ec_fw.bin -O ec_fw.bin
wget https://ci.betrusted.io/$REVISION/bt-ec.bin -O bt-ec.bin
wget https://ci.betrusted.io/$REVISION/wfm_wf200_C0.sec -O wfm_wf200_C0.sec
wget https://ci.betrusted.io/$REVISION/wf200_fw.bin -O wf200_fw.bin
