# 火山引擎语音合成 Qt GUI 客户端

这是一个基于 PyQt5 的图形化界面客户端，用于调用火山引擎的语音合成服务。

## 功能特性

- 🎯 图形化界面，操作简单直观
- 🎤 支持多种音色选择
- 🔊 支持多种音频格式（WAV、MP3、OGG）
- ▶️ 内置音频播放器
- 💾 支持保存音频文件
- 📝 实时日志显示
- ⚙️ 可配置的参数设置

## 安装依赖

```bash
# 方式一：使用 pip 安装
pip install -r requirements.txt

# 方式二：使用 pyproject.toml 安装
pip install -e .
```

## 运行程序

```bash
python3 tts_gui.py
```

或者赋予执行权限后直接运行：

```bash
chmod +x tts_gui.py
./tts_gui.py
```

## 使用说明

### 1. 配置参数

在界面上填写以下必填参数：

- **APP ID**: 你的应用ID（例如：6078974950）
- **Access Token**: 你的访问令牌
- **音色类型**: 从下拉列表中选择喜欢的音色
- **编码格式**: 选择输出音频格式（WAV/MP3/OGG）
- **服务端点**: 通常保持默认即可
- **集群名称**: 留空自动检测，或手动填写

### 2. 输入文本

在"合成文本"区域输入要转换为语音的文字内容。

### 3. 开始合成

点击"开始合成"按钮，程序将：
1. 连接到火山引擎服务器
2. 发送合成请求
3. 接收音频数据
4. 自动保存为本地文件

### 4. 播放音频

合成成功后：
- 点击"播放音频"按钮可以直接播放
- 点击"停止播放"按钮停止播放
- 点击"另存为..."可以将音频保存到指定位置

## 界面预览

程序界面包含以下部分：

```
┌─────────────────────────────────────────┐
│     火山引擎语音合成服务                   │
├─────────────────────────────────────────┤
│ 配置参数                                  │
│  APP ID: [____________]                  │
│  Access Token: [____________]            │
│  音色类型: [下拉选择]                      │
│  编码格式: [WAV ▼]                        │
│  服务端点: [____________]                 │
│  集群名称: [____________]                 │
├─────────────────────────────────────────┤
│ 合成文本                                  │
│  [文本输入框]                             │
├─────────────────────────────────────────┤
│ [开始合成] [播放音频] [停止播放] [另存为...] │
├─────────────────────────────────────────┤
│ 日志                                     │
│  [日志显示区域]                           │
└─────────────────────────────────────────┘
```

## 可用音色

程序预置了以下常用音色：

- `zh_female_cancan_mars_bigtts` - 女声-灿灿
- `zh_male_aojiaobazong_moon_bigtts` - 男声-傲娇霸总
- `zh_female_shuangkuaisisi_moon_bigtts` - 女声-爽快思思
- `zh_male_qingxunvsheng_moon_bigtts` - 男声-青涩女生
- `zh_male_chunhourugui_moon_bigtts` - 男声-醇厚如归
- `zh_female_wanwanmanman_moon_bigtts` - 女声-婉婉漫漫

## 命令行版本

如果需要使用命令行版本，可以运行：

```bash
python3 examples/volcengine/binary.py \
    --appid YOUR_APPID \
    --access_token YOUR_TOKEN \
    --voice_type zh_female_cancan_mars_bigtts \
    --text "你好，我是火山引擎的语音合成服务。"
```

## 常见问题

### 1. 无法播放音频

确保系统已安装音频播放组件：

```bash
# Ubuntu/Debian
sudo apt-get install python3-pyqt5.qtmultimedia libqt5multimedia5-plugins

# 如果仍有问题，尝试安装完整的多媒体支持
sudo apt-get install ubuntu-restricted-extras
```

### 2. 连接超时或失败

- 检查网络连接
- 确认 Access Token 是否有效
- 确认服务端点 URL 是否正确

### 3. 合成失败

- 检查 APP ID 和 Access Token 是否正确
- 查看日志区域的详细错误信息
- 确认文本内容不为空

## 技术架构

- **UI框架**: PyQt5
- **异步通信**: asyncio + websockets
- **协议**: 火山引擎二进制协议
- **音频播放**: QMediaPlayer

## 文件说明

- `tts_gui.py` - Qt GUI 主程序
- `examples/volcengine/binary.py` - 命令行版本
- `protocols/protocols.py` - 协议实现
- `requirements.txt` - 依赖列表

## 许可证

请遵守火山引擎的服务条款和使用协议。

## 支持

如有问题，请联系火山引擎技术支持。

