"""飞书客户端封装"""
import json
from datetime import datetime
from typing import Optional, Tuple
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
    
    def create_calendar_event(
        self,
        user_id: str,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        location: Optional[str] = None,
        description: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """在用户日历上创建事件
        
        Args:
            user_id: 用户的 open_id
            summary: 事件标题
            start_time: 开始时间
            end_time: 结束时间
            location: 地点（可选）
            description: 描述（可选）
            
        Returns:
            (是否成功, 事件ID或错误信息)
        """
        start_time_str = str(int(start_time.timestamp()))
        end_time_str = str(int(end_time.timestamp()))
        
        event = CalendarEvent.builder() \
            .summary(summary) \
            .description(description or "") \
            .start_time(TimeInfo.builder().timestamp(start_time_str).timezone("Asia/Shanghai").build()) \
            .end_time(TimeInfo.builder().timestamp(end_time_str).timezone("Asia/Shanghai").build()) \
            .build()
            
        if location:
            event.location = EventLocation.builder().name(location).build()
            
        request = CreateCalendarEventRequest.builder() \
            .calendar_id("primary") \
            .user_id_type("open_id") \
            .request_body(event) \
            .build()
            
        response = self.client.calendar.v4.calendar_event.create(request)
        
        if not response.success():
            logger.error(f"Create calendar event failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}")
            return False, response.msg
            
        return True, response.data.event.event_id
