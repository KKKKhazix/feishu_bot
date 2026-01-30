"""文字消息处理器"""
import json
from datetime import datetime, timedelta
from typing import Any, Dict

from services.feishu_client import FeishuClient
from services.doubao_llm import DoubaoLLM
from utils.logger import get_logger

logger = get_logger(__name__)


class TextHandler:
    """文字消息处理器"""
    
    def __init__(self, feishu_client: FeishuClient, doubao_llm: DoubaoLLM):
        self.feishu = feishu_client
        self.llm = doubao_llm
    
    async def handle(self, event: Dict[str, Any]) -> None:
        """处理文字消息
        
        Args:
            event: 飞书消息事件
        """
        message_id = ""
        try:
            # 提取消息信息
            message = event.get("message", {})
            message_id = message.get("message_id", "")
            chat_id = message.get("chat_id", "")
            sender = event.get("sender", {})
            sender_id = sender.get("sender_id", {}).get("open_id", "")
            
            # 提取文本内容
            content = message.get("content", "{}")
            content_obj = json.loads(content)
            text = content_obj.get("text", "")
            
            if not text:
                logger.warning(f"Empty text message: {message_id}")
                return
            
            logger.info(f"Processing text message: {text[:50]}...")
            
            # 调用LLM提取日程
            schedule = self.llm.extract_schedule(text)
            
            if not schedule.get("has_schedule"):
                reason = schedule.get("reason", "无法识别日程信息")
                self.feishu.reply_message(message_id, f"❌ {reason}\n\n请尝试发送类似：\n「明天下午3点开会」\n「1月31号上午10点和张三吃饭」")
                return
            
            # 解析日期时间
            date_str = schedule.get("date", "")
            start_time_str = schedule.get("start_time", "")
            end_time_str = schedule.get("end_time", "")
            title = schedule.get("title", "日程")
            location = schedule.get("location")
            
            # 构建datetime对象
            start_dt = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M")
            if end_time_str:
                end_dt = datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M")
            else:
                end_dt = start_dt + timedelta(hours=1)
            
            # 创建日历事件
            success, result = self.feishu.create_calendar_event(
                user_id=sender_id,
                summary=title,
                start_time=start_dt,
                end_time=end_dt,
                location=location
            )
            
            if success:
                location_text = f"\n📍 地点: {location}" if location else ""
                self.feishu.reply_message(
                    message_id,
                    f"✅ 日程创建成功！\n\n"
                    f"📅 {title}\n"
                    f"🕐 {start_dt.strftime('%Y-%m-%d %H:%M')} - {end_dt.strftime('%H:%M')}"
                    f"{location_text}"
                )
            else:
                self.feishu.reply_message(message_id, f"❌ 创建日程失败: {result}")
                
        except Exception as e:
            logger.error(f"Text handler error: {e}", exc_info=True)
            try:
                self.feishu.reply_message(message_id, f"❌ 处理消息时出错，请稍后重试")
            except:
                pass
