#!/usr/bin/env python3
"""
火山引擎语音合成 Qt GUI 客户端
"""
import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path

import websockets
from PySide2.QtCore import QThread, Signal, Qt, QUrl
from PySide2.QtGui import QFont, QIcon
from PySide2.QtMultimedia import QMediaPlayer, QMediaContent
from PySide2.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QGroupBox,
    QProgressBar,
    QFileDialog,
)

from protocols import MsgType, full_client_request, receive_message

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TTSWorker(QThread):
    """语音合成工作线程"""
    
    finished = Signal(str, bytes)  # 信号：完成 (文件路径, 音频数据)
    error = Signal(str)  # 信号：错误
    progress = Signal(str)  # 信号：进度更新
    
    def __init__(self, appid, access_token, voice_type, text, encoding, endpoint, cluster):
        super().__init__()
        self.appid = appid
        self.access_token = access_token
        self.voice_type = voice_type
        self.text = text
        self.encoding = encoding
        self.endpoint = endpoint
        self.cluster = cluster
    
    def _parse_error_message(self, msg):
        """解析错误消息"""
        try:
            import json
            payload = json.loads(msg.payload.decode('utf-8'))
            code = payload.get('code', msg.error_code)
            message = payload.get('message', '未知错误')
            
            error_tips = {
                403: "权限错误：请检查 Access Token 是否有效或已过期",
                401: "认证失败：请检查 APP ID 和 Access Token 是否正确",
                429: "请求过于频繁：请稍后重试",
                500: "服务器内部错误：请稍后重试",
            }
            
            tip = error_tips.get(code, "")
            error_msg = f"错误 {code}: {message}"
            if tip:
                error_msg += f"\n💡 建议: {tip}"
            
            # 特殊处理 403 错误
            if code == 403:
                error_msg += "\n\n请执行以下检查："
                error_msg += "\n1. 确认 Access Token 是否有效"
                error_msg += "\n2. 确认账户是否有权限使用该音色"
                error_msg += "\n3. 确认服务是否已开通和有余额"
                error_msg += "\n4. 尝试重新获取 Access Token"
            
            return error_msg
        except:
            return f"TTS转换失败: {msg}"
        
    def run(self):
        """运行异步任务"""
        try:
            asyncio.run(self._tts_task())
        except Exception as e:
            logger.exception("TTS任务失败")
            self.error.emit(f"错误: {str(e)}")
    
    async def _tts_task(self):
        """执行TTS任务"""
        try:
            self.progress.emit("正在连接到服务器...")
            
            # 连接到WebSocket服务器
            headers = {
                "Authorization": f"Bearer;{self.access_token}",
            }
            
            websocket = await websockets.connect(
                self.endpoint, 
                extra_headers=headers, 
                max_size=10 * 1024 * 1024
            )
            
            logid = websocket.response_headers.get('x-tt-logid', 'N/A')
            self.progress.emit(f"已连接到服务器 (Logid: {logid})")
            
            try:
                # 准备请求数据
                request = {
                    "app": {
                        "appid": self.appid,
                        "token": self.access_token,
                        "cluster": self.cluster,
                    },
                    "user": {
                        "uid": str(uuid.uuid4()),
                    },
                    "audio": {
                        "voice_type": self.voice_type,
                        "encoding": self.encoding,
                    },
                    "request": {
                        "reqid": str(uuid.uuid4()),
                        "text": self.text,
                        "operation": "submit",
                        "with_timestamp": "1",
                        "extra_param": json.dumps(
                            {
                                "disable_markdown_filter": False,
                            }
                        ),
                    },
                }
                
                self.progress.emit("正在发送请求...")
                
                # 发送请求
                await full_client_request(websocket, json.dumps(request).encode())
                
                self.progress.emit("正在接收音频数据...")
                
                # 接收音频数据
                audio_data = bytearray()
                while True:
                    msg = await receive_message(websocket)
                    
                    if msg.type == MsgType.FrontEndResultServer:
                        continue
                    elif msg.type == MsgType.AudioOnlyServer:
                        audio_data.extend(msg.payload)
                        self.progress.emit(f"已接收: {len(audio_data)} 字节")
                        if msg.sequence < 0:  # 最后一条消息
                            break
                    elif msg.type == MsgType.Error:
                        # 解析错误信息
                        error_detail = self._parse_error_message(msg)
                        raise RuntimeError(error_detail)
                    else:
                        raise RuntimeError(f"TTS转换失败: {msg}")
                
                # 检查是否收到音频数据
                if not audio_data:
                    raise RuntimeError("未收到音频数据")
                
                # 保存音频文件
                filename = f"{self.voice_type}.{self.encoding}"
                filepath = Path(filename).absolute()
                with open(filepath, "wb") as f:
                    f.write(audio_data)
                
                self.progress.emit(f"音频已保存: {filename} ({len(audio_data)} 字节)")
                self.finished.emit(str(filepath), bytes(audio_data))
                
            finally:
                await websocket.close()
                self.progress.emit("连接已关闭")
                
        except Exception as e:
            logger.exception("TTS任务执行失败")
            self.error.emit(f"错误: {str(e)}")


class TTSMainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.media_player = QMediaPlayer()
        self.current_audio_file = None
        self.current_audio_data = None
        
        # 连接播放器错误信号
        self.media_player.error.connect(self.on_media_error)
        self.media_player.stateChanged.connect(self.on_player_state_changed)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("火山引擎语音合成客户端")
        self.setMinimumSize(800, 700)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 标题
        title_label = QLabel("火山引擎语音合成服务")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 配置区域
        config_group = QGroupBox("配置参数")
        config_layout = QVBoxLayout()
        config_group.setLayout(config_layout)
        
        # APP ID
        appid_layout = QHBoxLayout()
        appid_layout.addWidget(QLabel("APP ID:"))
        self.appid_input = QLineEdit()
        self.appid_input.setPlaceholderText("请输入APP ID")
        self.appid_input.setText("6078974950")  # 默认值
        appid_layout.addWidget(self.appid_input)
        config_layout.addLayout(appid_layout)
        
        # Access Token
        token_layout = QHBoxLayout()
        token_layout.addWidget(QLabel("Access Token:"))
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("请输入Access Token")
        self.token_input.setText("4mHMaR3vfgVGPrfxg20z7N01rJt0C8i7")  # 默认值
        token_layout.addWidget(self.token_input)
        config_layout.addLayout(token_layout)
        
        # Voice Type
        voice_layout = QHBoxLayout()
        voice_layout.addWidget(QLabel("音色类型:"))
        self.voice_combo = QComboBox()
        self.voice_combo.addItems([
            "zh_female_cancan_mars_bigtts",
            "zh_male_aojiaobazong_moon_bigtts",
            "zh_female_shuangkuaisisi_moon_bigtts",
            "zh_male_qingxunvsheng_moon_bigtts",
            "zh_male_chunhourugui_moon_bigtts",
            "zh_female_wanwanmanman_moon_bigtts",
        ])
        voice_layout.addWidget(self.voice_combo)
        config_layout.addLayout(voice_layout)
        
        # Encoding
        encoding_layout = QHBoxLayout()
        encoding_layout.addWidget(QLabel("编码格式:"))
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["wav", "mp3", "ogg"])
        encoding_layout.addWidget(self.encoding_combo)
        config_layout.addLayout(encoding_layout)
        
        # Endpoint
        endpoint_layout = QHBoxLayout()
        endpoint_layout.addWidget(QLabel("服务端点:"))
        self.endpoint_input = QLineEdit()
        self.endpoint_input.setText("wss://openspeech.bytedance.com/api/v1/tts/ws_binary")
        endpoint_layout.addWidget(self.endpoint_input)
        config_layout.addLayout(endpoint_layout)
        
        # Cluster
        cluster_layout = QHBoxLayout()
        cluster_layout.addWidget(QLabel("集群名称:"))
        self.cluster_input = QLineEdit()
        self.cluster_input.setPlaceholderText("留空自动检测")
        cluster_layout.addWidget(self.cluster_input)
        config_layout.addLayout(cluster_layout)
        
        main_layout.addWidget(config_group)
        
        # 文本输入区域
        text_group = QGroupBox("合成文本")
        text_layout = QVBoxLayout()
        text_group.setLayout(text_layout)
        
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("请输入要合成的文本...")
        self.text_input.setPlainText("你好，我是火山引擎的语音合成服务。这是一个美好的旅程。")
        self.text_input.setMaximumHeight(100)
        text_layout.addWidget(self.text_input)
        
        main_layout.addWidget(text_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.synthesize_btn = QPushButton("开始合成")
        self.synthesize_btn.clicked.connect(self.start_synthesis)
        self.synthesize_btn.setMinimumHeight(40)
        button_layout.addWidget(self.synthesize_btn)
        
        self.play_btn = QPushButton("播放音频")
        self.play_btn.clicked.connect(self.play_audio)
        self.play_btn.setEnabled(False)
        self.play_btn.setMinimumHeight(40)
        button_layout.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("停止播放")
        self.stop_btn.clicked.connect(self.stop_audio)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumHeight(40)
        button_layout.addWidget(self.stop_btn)
        
        self.save_btn = QPushButton("另存为...")
        self.save_btn.clicked.connect(self.save_audio)
        self.save_btn.setEnabled(False)
        self.save_btn.setMinimumHeight(40)
        button_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(button_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 无限进度模式
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)
        
        # 日志区域
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        main_layout.addWidget(log_group)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
    def get_cluster(self, voice: str) -> str:
        """获取集群名称"""
        if voice.startswith("S_"):
            return "volcano_icl"
        return "volcano_tts"
    
    def start_synthesis(self):
        """开始合成"""
        # 获取输入参数
        appid = self.appid_input.text().strip()
        access_token = self.token_input.text().strip()
        voice_type = self.voice_combo.currentText()
        text = self.text_input.toPlainText().strip()
        encoding = self.encoding_combo.currentText()
        endpoint = self.endpoint_input.text().strip()
        cluster = self.cluster_input.text().strip()
        
        # 验证输入
        if not appid:
            QMessageBox.warning(self, "输入错误", "请输入APP ID")
            return
        
        if not access_token:
            QMessageBox.warning(self, "输入错误", "请输入Access Token")
            return
        
        if not text:
            QMessageBox.warning(self, "输入错误", "请输入要合成的文本")
            return
        
        if not endpoint:
            QMessageBox.warning(self, "输入错误", "请输入服务端点")
            return
        
        # 如果未指定cluster，自动检测
        if not cluster:
            cluster = self.get_cluster(voice_type)
        
        # 禁用按钮
        self.synthesize_btn.setEnabled(False)
        self.play_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.progress_bar.show()
        
        # 清空日志
        self.log_text.clear()
        self.add_log("开始语音合成...")
        
        # 创建工作线程
        self.worker = TTSWorker(
            appid, access_token, voice_type, text, encoding, endpoint, cluster
        )
        self.worker.finished.connect(self.on_synthesis_finished)
        self.worker.error.connect(self.on_synthesis_error)
        self.worker.progress.connect(self.on_progress_update)
        self.worker.start()
        
    def on_synthesis_finished(self, filepath: str, audio_data: bytes):
        """合成完成"""
        self.current_audio_file = filepath
        self.current_audio_data = audio_data
        self.add_log(f"合成成功！文件保存在: {filepath}")
        self.add_log(f"音频文件大小: {len(audio_data)} 字节")
        self.statusBar().showMessage(f"合成成功: {filepath}")
        
        # 启用按钮
        self.synthesize_btn.setEnabled(True)
        self.play_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.progress_bar.hide()
        
        QMessageBox.information(self, "成功", f"语音合成完成！\n文件已保存: {filepath}\n大小: {len(audio_data)} 字节")
        
    def on_synthesis_error(self, error_msg: str):
        """合成错误"""
        self.add_log(f"合成失败: {error_msg}")
        self.statusBar().showMessage("合成失败")
        
        # 启用按钮
        self.synthesize_btn.setEnabled(True)
        self.progress_bar.hide()
        
        QMessageBox.critical(self, "错误", error_msg)
        
    def on_progress_update(self, message: str):
        """进度更新"""
        self.add_log(message)
        self.statusBar().showMessage(message)
        
    def add_log(self, message: str):
        """添加日志"""
        self.log_text.append(message)
        # 滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def play_audio(self):
        """播放音频"""
        if not self.current_audio_file or not Path(self.current_audio_file).exists():
            QMessageBox.warning(self, "警告", "音频文件不存在")
            return
        
        try:
            # 停止之前的播放
            self.media_player.stop()
            
            # 设置媒体文件
            file_path = Path(self.current_audio_file).absolute()
            url = QUrl.fromLocalFile(str(file_path))
            
            self.add_log(f"准备播放: {file_path}")
            self.add_log(f"文件URL: {url.toString()}")
            
            content = QMediaContent(url)
            self.media_player.setMedia(content)
            
            # 设置音量
            self.media_player.setVolume(100)
            
            # 开始播放
            self.media_player.play()
            
            self.play_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.add_log("正在播放音频...")
            
        except Exception as e:
            error_msg = f"播放失败: {str(e)}"
            self.add_log(error_msg)
            QMessageBox.critical(self, "播放错误", error_msg)
            
    def stop_audio(self):
        """停止播放"""
        self.media_player.stop()
        self.play_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.add_log("停止播放")
        
    def on_player_state_changed(self, state):
        """播放器状态改变"""
        state_names = {
            QMediaPlayer.StoppedState: "已停止",
            QMediaPlayer.PlayingState: "正在播放",
            QMediaPlayer.PausedState: "已暂停"
        }
        state_name = state_names.get(state, f"未知状态({state})")
        self.add_log(f"播放器状态: {state_name}")
        
        if state == QMediaPlayer.StoppedState:
            self.play_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
        elif state == QMediaPlayer.PlayingState:
            self.play_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
    
    def on_media_status_changed(self, status):
        """媒体状态改变"""
        status_names = {
            QMediaPlayer.NoMedia: "无媒体",
            QMediaPlayer.LoadingMedia: "加载中",
            QMediaPlayer.LoadedMedia: "已加载",
            QMediaPlayer.StalledMedia: "暂停",
            QMediaPlayer.BufferingMedia: "缓冲中",
            QMediaPlayer.BufferedMedia: "已缓冲",
            QMediaPlayer.EndOfMedia: "播放结束",
            QMediaPlayer.InvalidMedia: "无效媒体"
        }
        status_name = status_names.get(status, f"未知({status})")
        self.add_log(f"媒体状态: {status_name}")
        
        if status == QMediaPlayer.InvalidMedia:
            error = self.media_player.errorString()
            self.add_log(f"媒体错误: {error}")
    
    def on_media_error(self, error):
        """媒体播放错误"""
        error_names = {
            QMediaPlayer.NoError: "无错误",
            QMediaPlayer.ResourceError: "资源错误",
            QMediaPlayer.FormatError: "格式错误",
            QMediaPlayer.NetworkError: "网络错误",
            QMediaPlayer.AccessDeniedError: "访问被拒绝",
            QMediaPlayer.ServiceMissingError: "服务缺失"
        }
        error_name = error_names.get(error, f"未知错误({error})")
        error_string = self.media_player.errorString()
        
        error_msg = f"播放器错误: {error_name}"
        if error_string:
            error_msg += f" - {error_string}"
        
        self.add_log(error_msg)
        
        if error == QMediaPlayer.ServiceMissingError:
            self.add_log("提示: 可能缺少多媒体组件，请运行:")
            self.add_log("  sudo apt-get install python3-pyside2.qtmultimedia libqt5multimedia5-plugins")
            QMessageBox.warning(
                self, 
                "播放器错误", 
                f"{error_msg}\n\n可能缺少多媒体组件，请在终端运行:\n"
                f"sudo apt-get install python3-pyside2.qtmultimedia libqt5multimedia5-plugins"
            )
            
    def save_audio(self):
        """另存为"""
        if not self.current_audio_file:
            return
        
        encoding = self.encoding_combo.currentText()
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "保存音频文件",
            f"output.{encoding}",
            f"Audio Files (*.{encoding});;All Files (*)"
        )
        
        if filename:
            try:
                with open(self.current_audio_file, "rb") as src:
                    with open(filename, "wb") as dst:
                        dst.write(src.read())
                self.add_log(f"文件已保存到: {filename}")
                QMessageBox.information(self, "成功", f"文件已保存到:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用 Fusion 风格
    
    window = TTSMainWindow()
    window.show()
    
    sys.exit(app.exec_())


'''
在线文本转语音服务
'''
if __name__ == "__main__":
    main()

