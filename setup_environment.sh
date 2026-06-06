#!/bin/bash
# 火山引擎TTS环境快速安装脚本

set -e  # 遇到错误立即退出

echo "========================================"
echo "  火山引擎TTS环境安装脚本"
echo "========================================"
echo ""

# 检查是否已在conda环境中
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "错误: 请先激活conda环境或创建新环境"
    echo ""
    echo "创建新环境的方法:"
    echo "  方法1: conda env create -f environment.yml"
    echo "  方法2: conda create -n volcengine_tts python=3.8 -y"
    echo ""
    echo "然后运行: conda activate volcengine_tts"
    exit 1
fi

echo "当前conda环境: $CONDA_DEFAULT_ENV"
echo ""

# 安装Python包
echo "=== 步骤 1/3: 安装Python包 ==="
echo "安装 websockets..."
pip install websockets>=14.0 -q
echo "✓ Python包安装完成"
echo ""

# 安装Qt和PySide2
echo "=== 步骤 2/3: 安装Qt和PySide2 ==="
conda install -c conda-forge pyside2 -y -q
echo "✓ Qt和PySide2安装完成"
echo ""

# 安装GStreamer和音频支持
echo "=== 步骤 3/3: 安装GStreamer音频支持 ==="
echo "这可能需要几分钟时间..."
conda install -c conda-forge \
    "gst-plugins-good>=1.24" \
    gst-plugins-base \
    gst-plugins-bad \
    gst-plugins-ugly \
    pulseaudio-client \
    "glib=2.80" \
    "libglib=2.80" -y

echo "✓ GStreamer音频支持安装完成"
echo ""

# 验证安装
echo "========================================"
echo "  验证安装"
echo "========================================"
echo ""

echo "检查GStreamer插件..."
if gst-inspect-1.0 wavparse &> /dev/null; then
    echo "✓ WAV解析器: 正常"
else
    echo "✗ WAV解析器: 未找到"
fi

if gst-inspect-1.0 pulsesink &> /dev/null; then
    echo "✓ PulseAudio输出: 正常"
else
    echo "✗ PulseAudio输出: 未找到"
fi

echo ""
echo "========================================"
echo "  安装完成！"
echo "========================================"
echo ""
echo "现在可以运行程序:"
echo "  python tts_gui.py"
echo ""

