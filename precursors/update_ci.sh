#!/bin/bash
set -e

wget https://ci.betrusted.io/latest-ci/loader.bin -O loader.bin

wget https://ci.betrusted.io/latest-ci/xous.img -O xous.img

wget https://ci.betrusted.io/latest-ci/soc_csr.bin -O soc_csr.bin

wget https://ci.betrusted.io/latest-ci/ec_fw.bin -O ec_fw.bin
wget https://ci.betrusted.io/latest-ci/bt-ec.bin -O bt-ec.bin
wget https://ci.betrusted.io/latest-ci/wfm_wf200_C0.sec -O wfm_wf200_C0.sec
wget https://ci.betrusted.io/latest-ci/wf200_fw.bin -O wf200_fw.bin
