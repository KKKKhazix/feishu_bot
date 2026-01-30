"""语音消息处理器"""
import json
from datetime import datetime, timedelta
from typing import Any, Dict

from services.feishu_client import FeishuClient
from services.volcano_ai import VolcanoAI
from services.doubao_llm import DoubaoLLM
from utils.logger import get_logger

logger = get_logger(__name__)


class VoiceHandler:
    """语音消息处理器"""
    
    def __init__(self, feishu_client: FeishuClient, volcano_ai: VolcanoAI, doubao_llm: DoubaoLLM):
        self.feishu = feishu_client
        self.volcano = volcano_ai
        self.llm = doubao_llm
    
    async def handle(self, event: Dict[str, Any]) -> None:
        """处理语音消息
        
        Args:
            event: 飞书消息事件
        """
        message_id = ""
        try:
            message = event.get("message", {})
            message_id = message.get("message_id", "")
            sender = event.get("sender", {})
            sender_id = sender.get("sender_id", {}).get("open_id", "")
            
            # 提取语音key
            content = message.get("content", "{}")
            content_obj = json.loads(content)
            file_key = content_obj.get("file_key", "")
            
            if not file_key:
                logger.warning(f"No file_key in voice message: {message_id}")
                return
            
            logger.info(f"Processing voice message: {file_key}")
            
            # 下载语音文件
            audio_bytes = self.feishu.download_file(message_id, file_key, "file")
            if not audio_bytes:
                self.feishu.reply_message(message_id, "❌ 无法下载语音，请重新发送")
                return
            
            # ASR识别
            asr_text = self.volcano.asr_audio(audio_bytes)
            if not asr_text:
                # ASR功能暂未开通时的友好提示
                self.feishu.reply_message(
                    message_id, 
                    "❌ 语音识别功能暂不可用\n\n"
                    "请直接发送文字消息，例如：\n"
                    "「明天下午3点开会」"
                )
                return
            
            logger.info(f"ASR result: {asr_text}")
            
            # 提取日程
            schedule = self.llm.extract_schedule(asr_text)
            
            if not schedule.get("has_schedule"):
                reason = schedule.get("reason", "语音中未找到日程信息")
                self.feishu.reply_message(message_id, f"❌ {reason}\n\n识别到的内容:\n{asr_text}")
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
                    f"✅ 从语音中识别并创建日程成功！\n\n"
                    f"📅 {title}\n"
                    f"🕐 {start_dt.strftime('%Y-%m-%d %H:%M')} - {end_dt.strftime('%H:%M')}"
                    f"{location_text}"
                )
            else:
                self.feishu.reply_message(message_id, f"❌ 创建日程失败: {result}")
                
        except Exception as e:
            logger.error(f"Voice handler error: {e}", exc_info=True)
            try:
                self.feishu.reply_message(message_id, "❌ 处理语音时出错，请稍后重试")
            except:
                pass
