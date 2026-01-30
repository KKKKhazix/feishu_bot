"""飞书客户端封装"""
import json
from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import quote
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from lark_oapi.api.calendar.v4 import *

from utils.logger import get_logger

logger = get_logger(__name__)


class FeishuClient:
    """飞书API客户端封装"""
    
    def __init__(self, app_id: str, app_secret: str):
        """初始化客户端
        
        Args:
            app_id: 飞书应用 App ID
            app_secret: 飞书应用 App Secret
        """
        self.client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.DEBUG) \
            .build()
        self.app_id = app_id
        self.app_secret = app_secret
        logger.info("FeishuClient initialized")
    
    def reply_message(self, message_id: str, text: str) -> bool:
        """回复消息
        
        Args:
            message_id: 要回复的消息ID
            text: 回复内容
            
        Returns:
            是否发送成功
        """
        request = ReplyMessageRequest.builder() \
            .message_id(message_id) \
            .request_body(ReplyMessageRequestBody.builder() \
                .msg_type("text") \
                .content(json.dumps({"text": text})) \
                .build()) \
            .build()
            
        response = self.client.im.v1.message.reply(request)
        
        if not response.success():
            logger.error(f"Reply message failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}")
            return False
            
        return True
    
    def send_message(self, receive_id: str, text: str, receive_id_type: str = "open_id") -> bool:
        """发送消息
        
        Args:
            receive_id: 接收者ID (open_id, user_id, chat_id等)
            text: 消息内容
            receive_id_type: ID类型，默认open_id
            
        Returns:
            是否发送成功
        """
        request = CreateMessageRequest.builder() \
            .receive_id_type(receive_id_type) \
            .request_body(CreateMessageRequestBody.builder() \
                .receive_id(receive_id) \
                .msg_type("text") \
                .content(json.dumps({"text": text})) \
                .build()) \
            .build()
            
        response = self.client.im.v1.message.create(request)
        
        if not response.success():
            logger.error(f"Send message failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}")
            return False
            
        return True
    
    def download_file(self, message_id: str, file_key: str, file_type: str) -> Optional[bytes]:
        """下载消息中的文件（图片或语音）
        
        Args:
            message_id: 消息ID
            file_key: 文件key
            file_type: 文件类型 (image/file/audio)
            
        Returns:
            文件二进制内容，失败返回None
        """
        request = GetMessageResourceRequest.builder() \
            .message_id(message_id) \
            .file_key(file_key) \
            .type(file_type) \
            .build()
            
        response = self.client.im.v1.message_resource.get(request)
        
        if not response.success():
            logger.error(f"Download file failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}")
            return None
            
        return response.file.read()
    
    def reply_schedule_card(
        self, 
        message_id: str, 
        title: str, 
        start_time: datetime,
        end_time: datetime,
        location: Optional[str] = None,
        source: str = "消息"
    ) -> bool:
        """回复日程卡片，包含「添加到日历」按钮
        
        Args:
            message_id: 要回复的消息ID
            title: 日程标题
            start_time: 开始时间
            end_time: 结束时间
            location: 地点（可选）
            source: 来源描述（如"图片"、"文字"）
            
        Returns:
            是否发送成功
        """
        # 构建飞书日程创建链接
        # URL格式: https://applink.feishu.cn/client/calendar/event/create?start_time=时间戳&end_time=时间戳&summary=标题
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())
        
        calendar_url = f"https://applink.feishu.cn/client/calendar/event/create?start_time={start_ts}&end_time={end_ts}&summary={quote(title)}"
        if location:
            calendar_url += f"&location={quote(location)}"
        
        # 格式化时间显示
        start_str = start_time.strftime('%Y-%m-%d %H:%M')
        end_str = end_time.strftime('%H:%M')
        
        # 构建卡片元素
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**📅 {title}**"
                }
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"🕐 **时间**: {start_str} - {end_str}"
                }
            }
        ]
        
        # 如果有地点，添加地点信息
        if location:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"📍 **地点**: {location}"
                }
            })
        
        # 添加分割线
        elements.append({"tag": "hr"})
        
        # 添加「添加到日历」按钮
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "📅 添加到日历"
                    },
                    "type": "primary",
                    "url": calendar_url
                }
            ]
        })
        
        # 添加提示
        elements.append({
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": f"从{source}中识别 · 点击按钮即可添加到您的日历"
                }
            ]
        })
        
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "blue",
                "title": {
                    "tag": "plain_text",
                    "content": "📋 识别到日程信息"
                }
            },
            "elements": elements
        }
        
        request = ReplyMessageRequest.builder() \
            .message_id(message_id) \
            .request_body(ReplyMessageRequestBody.builder() \
                .msg_type("interactive") \
                .content(json.dumps(card)) \
                .build()) \
            .build()
            
        response = self.client.im.v1.message.reply(request)
        
        if not response.success():
            logger.error(f"Reply card failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}")
            return False
        
        logger.info(f"Schedule card sent successfully for: {title}")
        return True
