#!/bin/bash
local_pwd=$(pwd)
dist_path=${local_pwd}/dist
build_path=${local_pwd}/build
spec_path=${local_pwd}/CoolSerialTool.spec

echo "local path is $local_pwd"

cd $local_pwd || exit

python -m PyQt5.uic.pyuic MainWindow.ui -o MainWindow.py


