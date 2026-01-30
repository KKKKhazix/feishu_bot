"""飞书客户端封装"""
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from urllib.parse import quote, urlencode
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from lark_oapi.api.calendar.v4 import *

from utils.logger import get_logger

# 北京时区 UTC+8
BEIJING_TZ = timezone(timedelta(hours=8))

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
        # 注意：飞书applink需要UTC时间戳（秒），传入的datetime是北京时间，需要转换
        
        # 如果datetime是naive的（没有时区信息），假设它是北京时间
        if start_time.tzinfo is None:
            start_time_aware = start_time.replace(tzinfo=BEIJING_TZ)
        else:
            start_time_aware = start_time
            
        if end_time.tzinfo is None:
            end_time_aware = end_time.replace(tzinfo=BEIJING_TZ)
        else:
            end_time_aware = end_time
        
        # 转换为UTC时间戳（秒）
        # 注意：飞书 AppLink 只接受秒级时间戳，不能传毫秒！
        start_ts = int(start_time_aware.timestamp())
        end_ts = int(end_time_aware.timestamp())
        
        logger.debug(f"Calendar link timestamps: start={start_ts}, end={end_ts}")
        
        # 飞书 AppLink 参数：
        # - startTime/endTime: 秒级时间戳（驼峰命名，iOS客户端用这个）
        # - summary: 标题
        # - description: 描述（用于放地点信息，因为location参数可能不被支持）
        params = [
            ("startTime", str(start_ts)),
            ("endTime", str(end_ts)),
            ("summary", title),
        ]

        # 地点信息：尝试多种参数格式（优先地点字段，备选描述字段）
        # 根据飞书SDK分析，location可能需要用点号分隔格式
        if location:
            # 方案1：点号分隔格式（最可能生效）
            params.append(("location.name", location))
            # 方案2：简单字符串格式（备选）
            params.append(("location", location))
            # 方案3：描述字段兜底（确保地点信息不丢失）
            params.append(("description", f"📍 地点: {location}"))

        query = urlencode(params, quote_via=quote)
        calendar_url = f"https://applink.feishu.cn/client/calendar/event/create?{query}"
        
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

    def get_user_primary_calendar_id(self, user_open_id: str) -> Optional[str]:
        """获取用户的主日历 ID
        
        Args:
            user_open_id: 用户的 open_id
            
        Returns:
            日历ID，失败返回None
        """
        try:
            # 获取用户的主日历信息
            # 使用 CalendarListRequest 获取日历列表
            request = ListCalendarRequest.builder() \
                .page_size(50) \
                .build()
            
            response = self.client.calendar.v4.calendar.list(request)
            
            if not response.success():
                logger.error(f"Get calendar list failed: {response.code}, {response.msg}")
                return None
            
            if response.data and response.data.calendar_list:
                # 查找主日历（类型为 primary 或第一个自己的日历）
                for cal in response.data.calendar_list:
                    # 返回第一个日历的 ID
                    calendar_id = cal.calendar_id
                    logger.info(f"Got calendar: {calendar_id}, type: {cal.type}")
                    if cal.type == "primary":
                        return calendar_id
                # 如果没有 primary，返回第一个
                if response.data.calendar_list:
                    return response.data.calendar_list[0].calendar_id
            
            return None
            
        except Exception as e:
            logger.error(f"Get calendar list error: {e}", exc_info=True)
            return None

    def create_calendar_event(
        self,
        user_open_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        location: Optional[str] = None,
        description: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """使用日历 API 创建日程
        
        Args:
            user_open_id: 用户的 open_id（用于获取主日历）
            title: 日程标题
            start_time: 开始时间
            end_time: 结束时间
            location: 地点（可选）
            description: 描述（可选）
            
        Returns:
            (是否成功, 日程event_id或错误信息)
        """
        try:
            # 如果datetime是naive的（没有时区信息），假设它是北京时间
            if start_time.tzinfo is None:
                start_time_aware = start_time.replace(tzinfo=BEIJING_TZ)
            else:
                start_time_aware = start_time
                
            if end_time.tzinfo is None:
                end_time_aware = end_time.replace(tzinfo=BEIJING_TZ)
            else:
                end_time_aware = end_time
            
            # 转换为时间戳字符串（秒）
            start_ts = str(int(start_time_aware.timestamp()))
            end_ts = str(int(end_time_aware.timestamp()))
            
            # 构建日程事件
            event_builder = CalendarEvent.builder() \
                .summary(title) \
                .start_time(TimeInfo.builder()
                    .timestamp(start_ts)
                    .timezone("Asia/Shanghai")
                    .build()) \
                .end_time(TimeInfo.builder()
                    .timestamp(end_ts)
                    .timezone("Asia/Shanghai")
                    .build())
            
            # 添加地点
            if location:
                event_builder = event_builder.location(
                    EventLocation.builder()
                        .name(location)
                        .build()
                )
            
            # 添加描述
            if description:
                event_builder = event_builder.description(description)
            
            event = event_builder.build()
            
            # 先获取用户的主日历 ID
            # 注意：使用 tenant_access_token 时，不能直接用 "primary"
            # 需要先查询用户的日历列表获取真实的 calendar_id
            calendar_id = self.get_user_primary_calendar_id(user_open_id)
            if not calendar_id:
                # 如果无法获取用户日历，尝试使用共享日历或返回错误
                logger.warning(f"Cannot get user calendar for {user_open_id}, trying primary")
                calendar_id = "primary"  # 降级尝试
            
            request = CreateCalendarEventRequest.builder() \
                .calendar_id(calendar_id) \
                .user_id_type("open_id") \
                .request_body(event) \
                .build()
            
            response = self.client.calendar.v4.calendar_event.create(request)
            
            if not response.success():
                error_msg = f"code: {response.code}, msg: {response.msg}"
                logger.error(f"Create calendar event failed: {error_msg}")
                return (False, error_msg)
            
            event_id = response.data.event.event_id if response.data and response.data.event else None
            logger.info(f"Calendar event created successfully: {title}, event_id: {event_id}")
            
            # 创建成功后，将用户添加为日程参与人
            # 这样日程才会出现在用户的日历中
            if event_id and user_open_id:
                self._add_event_attendee(calendar_id, event_id, user_open_id)
            
            # 返回 (成功, calendar_id, event_id) 用于生成详情链接
            return (True, calendar_id, event_id)
            
        except Exception as e:
            logger.error(f"Create calendar event error: {e}", exc_info=True)
            return (False, None, str(e))

    def _add_event_attendee(self, calendar_id: str, event_id: str, user_open_id: str) -> bool:
        """将用户添加为日程参与人
        
        Args:
            calendar_id: 日历ID
            event_id: 日程ID
            user_open_id: 用户的 open_id
            
        Returns:
            是否成功
        """
        try:
            # 构建参与人
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
                    .need_notification(True)  # 给用户发通知
                    .build()) \
                .build()
            
            response = self.client.calendar.v4.calendar_event_attendee.create(request)
            
            if not response.success():
                logger.error(f"Add attendee failed: {response.code}, {response.msg}")
                return False
            
            logger.info(f"Added user {user_open_id} as attendee to event {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Add attendee error: {e}", exc_info=True)
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
        """回复日程创建成功的卡片
        
        Args:
            message_id: 要回复的消息ID
            title: 日程标题
            start_time: 开始时间
            end_time: 结束时间
            location: 地点（可选）
            source: 来源描述（如"图片"、"文字"）
            calendar_id: 日历ID（用于生成详情链接）
            event_id: 日程ID（用于生成详情链接）
            
        Returns:
            是否发送成功
        """
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
        
        # 如果有日程详情，添加「查看详情」按钮
        if calendar_id and event_id:
            # 飞书 AppLink 日程详情页
            # 格式: https://applink.feishu.cn/client/calendar/event/detail?calendarId=xxx&key=xxx
            detail_url = f"https://applink.feishu.cn/client/calendar/event/detail?calendarId={quote(calendar_id)}&key={quote(event_id)}"
            elements.append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "📅 查看日程详情"
                        },
                        "type": "primary",
                        "url": detail_url
                    }
                ]
            })
        
        # 添加提示
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
            "config": {
                "wide_screen_mode": True
            },
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
            
        response = self.client.im.v1.message.reply(request)
        
        if not response.success():
            logger.error(f"Reply card failed, code: {response.code}, msg: {response.msg}")
            return False
        
        logger.info(f"Schedule created card sent for: {title}")
        return True
