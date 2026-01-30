"""图片消息处理器"""
import json
from datetime import datetime, timedelta
from typing import Any, Dict

from services.feishu_client import FeishuClient
from services.volcano_ai import VolcanoAI
from services.doubao_llm import DoubaoLLM
from utils.logger import get_logger

logger = get_logger(__name__)


class ImageHandler:
    """图片消息处理器"""
    
    def __init__(self, feishu_client: FeishuClient, volcano_ai: VolcanoAI, doubao_llm: DoubaoLLM):
        self.feishu = feishu_client
        self.volcano = volcano_ai
        self.llm = doubao_llm
    
    async def handle(self, event: Dict[str, Any]) -> None:
        """处理图片消息
        
        Args:
            event: 飞书消息事件
        """
        message_id = ""
        try:
            message = event.get("message", {})
            message_id = message.get("message_id", "")
            sender = event.get("sender", {})
            sender_id = sender.get("sender_id", {}).get("open_id", "")
            
            # 提取图片 key
            content = message.get("content", "{}")
            content_obj = json.loads(content)
            image_key = content_obj.get("image_key", "")
            
            if not image_key:
                logger.warning(f"No image_key in message: {message_id}")
                return
            
            logger.info(f"Processing image message: {image_key}")
            
            # 下载图片
            image_bytes = self.feishu.download_file(message_id, image_key, "image")
            if not image_bytes:
                self.feishu.reply_message(message_id, "❌ 无法下载图片，请重新发送")
                return
            
            # OCR识别
            ocr_text = self.volcano.ocr_image(image_bytes)
            if not ocr_text:
                self.feishu.reply_message(message_id, "❌ 无法识别图片中的文字，请发送更清晰的截图")
                return
            
            logger.info(f"OCR result: {ocr_text[:100]}...")
            
            # 提取日程
            schedule = self.llm.extract_schedule(ocr_text)
            
            if not schedule.get("has_schedule"):
                reason = schedule.get("reason", "图片中未找到日程信息")
                self.feishu.reply_message(message_id, f"❌ {reason}\n\n识别到的文字:\n{ocr_text[:200]}...")
                return
            
            # 解析日期时间
            date_str = schedule.get("date", "")
            start_time_str = schedule.get("start_time", "")
            end_time_str = schedule.get("end_time", "")
            title = schedule.get("title", "日程")
            location = schedule.get("location")
            
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
                    f"✅ 从图片中识别并创建日程成功！\n\n"
                    f"📅 {title}\n"
                    f"🕐 {start_dt.strftime('%Y-%m-%d %H:%M')} - {end_dt.strftime('%H:%M')}"
                    f"{location_text}"
                )
            else:
                self.feishu.reply_message(message_id, f"❌ 创建日程失败: {result}")
                
        except Exception as e:
            logger.error(f"Image handler error: {e}", exc_info=True)
            try:
                self.feishu.reply_message(message_id, "❌ 处理图片时出错，请稍后重试")
            except:
                pass
