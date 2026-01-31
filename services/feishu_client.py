"""飞书客户端封装"""
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Any, cast
from urllib.parse import quote, urlencode
import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    ReplyMessageRequest, ReplyMessageRequestBody,
    CreateMessageRequest, CreateMessageRequestBody,
    GetMessageResourceRequest
)
from lark_oapi.api.calendar.v4 import (
    ListCalendarRequest, ListCalendarEventRequest,
    CalendarEvent, TimeInfo, EventLocation,
    CreateCalendarEventRequest, CalendarEventAttendee,
    CreateCalendarEventAttendeeRequest, CreateCalendarEventAttendeeRequestBody
)

from utils.logger import get_logger

# 北京时区 UTC+8
BEIJING_TZ = timezone(timedelta(hours=8))

logger = get_logger(__name__)


class FeishuClient:
    """飞书API客户端封装"""
    client: lark.Client
    app_id: str
    app_secret: str
    
    def __init__(self, app_id: str, app_secret: str):
        """初始化客户端
        
        Args:
            app_id: 飞书应用 App ID
            app_secret: 飞书应用 App Secret
        """
        # cast to lark.Client to help LSP understand nested attributes
        self.client = cast(lark.Client, lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.DEBUG) \
            .build())
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
            
        # Using cast to avoid "None" member access warnings if stubs are missing
        im_service = cast(Any, self.client.im)
        response = im_service.v1.message.reply(request)
        
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
            
        im_service = cast(Any, self.client.im)
        response = im_service.v1.message.create(request)
        
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
            
        im_service = cast(Any, self.client.im)
        response = im_service.v1.message_resource.get(request)
        
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
        if start_time.tzinfo is None:
            start_time_aware = start_time.replace(tzinfo=BEIJING_TZ)
        else:
            start_time_aware = start_time
            
        if end_time.tzinfo is None:
            end_time_aware = end_time.replace(tzinfo=BEIJING_TZ)
        else:
            end_time_aware = end_time
        
        start_ts = int(start_time_aware.timestamp())
        end_ts = int(end_time_aware.timestamp())
        
        params = [
            ("startTime", str(start_ts)),
            ("endTime", str(end_ts)),
            ("summary", title),
        ]

        if location:
            params.append(("location.name", location))
            params.append(("location", location))
            params.append(("description", f"📍 地点: {location}"))

        query = urlencode(params, quote_via=quote)
        calendar_url = f"https://applink.feishu.cn/client/calendar/event/create?{query}"
        
        start_str = start_time.strftime('%Y-%m-%d %H:%M')
        end_str = end_time.strftime('%H:%M')
        
        elements: list[dict[str, Any]] = [
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
        
        if location:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"📍 **地点**: {location}"
                }
            })
        
        elements.append({"tag": "hr"})
        
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
            
        im_service = cast(Any, self.client.im)
        response = im_service.v1.message.reply(request)
        
        if not response.success():
            logger.error(f"Reply card failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}")
            return False
        
        return True

    def get_user_primary_calendar_id(self, user_open_id: str) -> Optional[str]:
        """获取用户的主日历 ID
        
        Args:
            user_open_id: 用户的 open_id
            
        Returns:
            日历ID，失败返回None
        """
        try:
            request = ListCalendarRequest.builder() \
                .page_size(50) \
                .build()
            
            calendar_service = cast(Any, self.client.calendar)
            response = calendar_service.v4.calendar.list(request)
            
            if not response.success():
                logger.error(f"Get calendar list failed: {response.code}, {response.msg}")
                return None
            
            if response.data and response.data.calendar_list:
                for cal in response.data.calendar_list:
                    calendar_id = cal.calendar_id
                    if cal.type == "primary":
                        return calendar_id
                if response.data.calendar_list:
                    return response.data.calendar_list[0].calendar_id
            
            return None
            
        except Exception as e:
            logger.error(f"Get calendar list error: {e}", exc_info=True)
            return None

    def check_duplicate_event(
        self,
        calendar_id: str,
        title: str,
        start_time: datetime
    ) -> Tuple[bool, Optional[str]]:
        """检查是否已存在相同的日程
        
        Args:
            calendar_id: 日历ID
            title: 日程标题
            start_time: 开始时间
            
        Returns:
            (是否重复, 已存在的event_id或None)
        """
        try:
            if start_time.tzinfo is None:
                start_time_aware = start_time.replace(tzinfo=BEIJING_TZ)
            else:
                start_time_aware = start_time
            
            query_start = start_time_aware - timedelta(days=1)
            query_end = start_time_aware + timedelta(days=1)
            
            query_start_ts = str(int(query_start.timestamp()))
            query_end_ts = str(int(query_end.timestamp()))
            
            request = ListCalendarEventRequest.builder() \
                .calendar_id(calendar_id) \
                .start_time(query_start_ts) \
                .end_time(query_end_ts) \
                .page_size(100) \
                .build()
            
            calendar_service = cast(Any, self.client.calendar)
            response = calendar_service.v4.calendar_event.list(request)
            
            if not response.success():
                logger.error(f"Query calendar events failed: {response.code}, {response.msg}")
                return (False, None)
            
            if response.data and response.data.items:
                target_ts = str(int(start_time_aware.timestamp()))
                for event in response.data.items:
                    if (event.summary == title and 
                        event.start_time and 
                        event.start_time.timestamp == target_ts):
                        return (True, event.event_id)
            
            return (False, None)
            
        except Exception as e:
            logger.error(f"Check duplicate event error: {e}", exc_info=True)
            return (False, None)

    def create_calendar_event(
        self,
        user_open_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        location: Optional[str] = None,
        description: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """使用日历 API 创建日程
        
        Args:
            user_open_id: 用户的 open_id（用于获取主日历）
            title: 日程标题
            start_time: 开始时间
            end_time: 结束时间
            location: 地点（可选）
            description: 描述（可选）
            
        Returns:
            (是否成功, 日程calendar_id或错误信息, 日程event_id或错误详情)
        """
        try:
            # 1. 获取用户的主日历 ID
            calendar_id = self.get_user_primary_calendar_id(user_open_id)
            if not calendar_id:
                calendar_id = "primary"
            
            # 2. 检查是否已存在相同日程 (BEFORE event builder)
            is_duplicate, existing_event_id = self.check_duplicate_event(
                calendar_id, title, start_time
            )
            if is_duplicate:
                return (False, "duplicate", existing_event_id)

            # 3. 时间处理
            if start_time.tzinfo is None:
                start_time_aware = start_time.replace(tzinfo=BEIJING_TZ)
            else:
                start_time_aware = start_time
                
            if end_time.tzinfo is None:
                end_time_aware = end_time.replace(tzinfo=BEIJING_TZ)
            else:
                end_time_aware = end_time
            
            start_ts = str(int(start_time_aware.timestamp()))
            end_ts = str(int(end_time_aware.timestamp()))
            
            # 4. 构建日程事件
            event_builder = CalendarEvent.builder() \
                .summary(title) \
                .start_time(TimeInfo.builder()
                    .timestamp(start_ts)
                    .timezone("Asia/Shanghai")
                    .build()) \
                .end_time(TimeInfo.builder()
                    .timestamp(end_ts)
                    .timezone("Asia/Shanghai")
                    .build()) \
                .attendee_ability("can_modify_event")
            
            if location:
                event_builder = event_builder.location(
                    EventLocation.builder().name(location).build()
                )
            
            if description:
                event_builder = event_builder.description(description)
            
            event = event_builder.build()
            
            # 5. 调用接口创建
            request = CreateCalendarEventRequest.builder() \
                .calendar_id(calendar_id) \
                .user_id_type("open_id") \
                .request_body(event) \
                .build()
            
            calendar_service = cast(Any, self.client.calendar)
            response = calendar_service.v4.calendar_event.create(request)
            
            if not response.success():
                error_msg = f"code: {response.code}, msg: {response.msg}"
                return (False, error_msg, None)
            
            event_id = response.data.event.event_id if response.data and response.data.event else None
            
            if event_id and user_open_id:
                self._add_event_attendee(calendar_id, event_id, user_open_id)
            
            return (True, calendar_id, event_id)
            
        except Exception as e:
            logger.error(f"Create calendar event error: {e}", exc_info=True)
            return (False, None, str(e))

    def _add_event_attendee(self, calendar_id: str, event_id: str, user_open_id: str) -> bool:
        """将用户添加为日程参与人"""
        try:
            attendee = CalendarEventAttendee.builder() \
                .type("user") \
                .user_id(user_open_id) \
                .build()
            
            request = CreateCalendarEventAttendeeRequest.builder() \
                .calendar_id(calendar_id) \
                .event_id(event_id) \
                .user_id_type("open_id") \
                .request_body(CreateCalendarEventAttendeeRequestBody.builder()
                    .attendees([attendee])
                    .need_notification(True)
                    .build()) \
                .build()
            
            calendar_service = cast(Any, self.client.calendar)
            response = calendar_service.v4.calendar_event_attendee.create(request)
            
            if not response.success():
                return False
            
            return True
        except Exception:
            return False

    def reply_schedule_created_card(
        self, 
        message_id: str, 
        title: str, 
        start_time: datetime,
        end_time: datetime,
        location: Optional[str] = None,
        source: str = "消息",
        calendar_id: Optional[str] = None,
        event_id: Optional[str] = None
    ) -> bool:
        """回复日程创建成功的卡片"""
        start_str = start_time.strftime('%Y-%m-%d %H:%M')
        end_str = end_time.strftime('%H:%M')
        
        elements: list[dict[str, Any]] = [
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
        
        if location:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"📍 **地点**: {location}"
                }
            })
        
        elements.append({"tag": "hr"})
        
        elements.append({
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": f"从{source}中识别并自动添加到您的日历"
                }
            ]
        })
        
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "green",
                "title": {
                    "tag": "plain_text",
                    "content": "✅ 已添加到日历"
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
            
        im_service = cast(Any, self.client.im)
        response = im_service.v1.message.reply(request)
        return response.success()
