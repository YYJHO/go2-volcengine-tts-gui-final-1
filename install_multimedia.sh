#!/bin/bash
# 安装 PyQt5 多媒体组件和依赖

echo "========================================"
echo "  PyQt5 多媒体组件安装脚本"
echo "========================================"
echo ""

# 检查是否为 root 用户
if [ "$EUID" -eq 0 ]; then 
    echo "请不要使用 sudo 运行此脚本"
    echo "脚本会在需要时自动请求权限"
    exit 1
fi

echo "正在检查系统..."
echo ""

# 检查包管理器
if command -v apt-get &> /dev/null; then
    PKG_MGR="apt-get"
    echo "检测到 Debian/Ubuntu 系统"
elif command -v yum &> /dev/null; then
    PKG_MGR="yum"
    echo "检测到 RHEL/CentOS 系统"
else
    echo "错误: 未识别的包管理器"
    exit 1
fi

echo ""
echo "将安装以下组件："
echo "  1. PyQt5 多媒体模块 (Python)"
echo "  2. Qt5 多媒体插件"
echo "  3. GStreamer 插件 (音频/视频编解码器)"
echo ""
read -p "是否继续? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消安装"
    exit 0
fi

echo ""
echo "=== 步骤 1/3: 安装 PyQt5 多媒体模块 ==="
pip3 install --user PyQt5 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ PyQt5 安装成功"
else
    echo "⚠ PyQt5 安装可能失败，请检查"
fi

echo ""
echo "=== 步骤 2/3: 安装系统多媒体组件 ==="
if [ "$PKG_MGR" = "apt-get" ]; then
    sudo apt-get update
    sudo apt-get install -y \
        python3-pyqt5.qtmultimedia \
        libqt5multimedia5 \
        libqt5multimedia5-plugins \
        qtmultimedia5-dev
    
    if [ $? -eq 0 ]; then
        echo "✓ Qt5 多媒体组件安装成功"
    else
        echo "✗ Qt5 多媒体组件安装失败"
        exit 1
    fi
elif [ "$PKG_MGR" = "yum" ]; then
    sudo yum install -y \
        python3-qt5-qtmultimedia \
        qt5-qtmultimedia
    
    if [ $? -eq 0 ]; then
        echo "✓ Qt5 多媒体组件安装成功"
    else
        echo "✗ Qt5 多媒体组件安装失败"
        exit 1
    fi
fi

echo ""
echo "=== 步骤 3/3: 安装 GStreamer 编解码器 ==="
if [ "$PKG_MGR" = "apt-get" ]; then
    sudo apt-get install -y \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-ugly \
        gstreamer1.0-libav \
        gstreamer1.0-tools \
        gstreamer1.0-alsa \
        gstreamer1.0-pulseaudio
    
    if [ $? -eq 0 ]; then
        echo "✓ GStreamer 编解码器安装成功"
    else
        echo "⚠ GStreamer 编解码器安装可能失败"
    fi
elif [ "$PKG_MGR" = "yum" ]; then
    sudo yum install -y \
        gstreamer1-plugins-base \
        gstreamer1-plugins-good \
        gstreamer1-plugins-bad-free \
        gstreamer1-plugins-ugly-free
    
    if [ $? -eq 0 ]; then
        echo "✓ GStreamer 编解码器安装成功"
    else
        echo "⚠ GStreamer 编解码器安装可能失败"
    fi
fi

echo ""
echo "========================================"
echo "  安装完成！"
echo "========================================"
echo ""
echo "现在可以运行以下命令测试音频播放："
echo "  python3 test_audio_player.py"
echo ""
echo "或者直接启动主程序："
echo "  python3 tts_gui.py"
echo ""

