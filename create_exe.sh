#!/bin/bash
local_pwd=$(pwd)
dist_path=${local_pwd}/app_exe/dist
build_path=${local_pwd}/app_exe/build
spec_path=${local_pwd}/app_exe/BleTool.spec

echo "local path is $local_pwd"

if [ -d "$dist_path" ]; then
echo "delete $dist_path"
rm -rf $dist_path
fi

if [ -d "$build_path" ]; then
echo "delete $build_path"
rm -rf $build_path
fi

if [ -f "$spec_path" ]; then
echo "delete $spec_path"
rm $spec_path
fi

cd $local_pwd/app_exe || exit
#打包成界面工具
pyinstaller -D -w -i $local_pwd/logo/app_logo.ico $local_pwd/BleTool.py
#高版本不支持logo.ico.改为log.icns
# png转ico网站 https://www.aconvert.com/cn/icon/jpg-to-ico/ 大小选择64x64
#ValueError: Received icon image '/Users/didi/python/LOCK_PY_NEW_FRAME/NewSerialPortTool/logo.ico'
#which exists but is not in the correct format. On this platform, only ('icns',) images may be used as icons.
#If Pillow is installed, automatic conversion will be attempted.
#Please install Pillow or convert your 'ico' file to one of ('icns',) and try again.
#打包成可执行文件
#pyinstaller -F  didilog.py