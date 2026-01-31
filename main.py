"""飞书日程机器人 - 主入口"""
import json
import time
from typing import Optional
import lark_oapi as lark
from lark_oapi.api.im.v1 import P2ImMessageReceiveV1

from utils.config import Config
from utils.logger import get_logger
from services.feishu_client import FeishuClient
from services.volcano_ai import VolcanoAI
from services.doubao_llm import DoubaoLLM
from handlers.text_handler import TextHandler
from handlers.image_handler import ImageHandler
from handlers.voice_handler import VoiceHandler

logger = get_logger(__name__)

# 全局服务实例
config: Optional[Config] = None
feishu_client: Optional[FeishuClient] = None
volcano_ai: Optional[VolcanoAI] = None
doubao_llm: Optional[DoubaoLLM] = None
text_handler: Optional[TextHandler] = None
image_handler: Optional[ImageHandler] = None
voice_handler: Optional[VoiceHandler] = None

# 消息去重：存储已处理的消息ID和时间戳
processed_messages: dict[str, float] = {}
MESSAGE_DEDUP_WINDOW = 60 * 60  # 1小时内的重复消息会被忽略
MAX_PROCESSED_MESSAGES = 2000


def init_services():
    """初始化所有服务"""
    global config, feishu_client, volcano_ai, doubao_llm
    global text_handler, image_handler, voice_handler
    
    logger.info("Initializing services...")
    
    # 加载配置
    config = Config()
    
    # 初始化服务
    feishu_client = FeishuClient(config.feishu_app_id, config.feishu_app_secret)
    # VolcanoAI 需要 doubao_api_key 做 OCR，以及可选的 volcano keys 做 ASR
    volcano_ai = VolcanoAI(
        api_key=config.doubao_api_key, 
        access_key=config.volcano_access_key, 
        secret_key=config.volcano_secret_key
    )
    doubao_llm = DoubaoLLM(config.doubao_api_key, config.doubao_model_id)
    
    # 初始化处理器
    text_handler = TextHandler(feishu_client, doubao_llm)
    image_handler = ImageHandler(feishu_client, volcano_ai, doubao_llm)
    voice_handler = VoiceHandler(feishu_client, volcano_ai, doubao_llm)
    
    logger.info("All services initialized")


def cleanup_old_messages():
    """清理过期的消息记录，防止内存泄漏"""
    global processed_messages
    current_time = time.time()
    expired_keys = [
        msg_id for msg_id, timestamp in processed_messages.items()
        if current_time - timestamp > MESSAGE_DEDUP_WINDOW
    ]
    for key in expired_keys:
        del processed_messages[key]


def handle_message_event(data: P2ImMessageReceiveV1):
    """处理消息接收事件
    
    Args:
        data: 飞书消息事件数据
    """
    global processed_messages
    
    try:
        if not all([text_handler, image_handler, voice_handler, feishu_client]):
            logger.error("Services not initialized")
            return

        event = data.event
        message = event.message
        message_type = message.message_type
        message_id = message.message_id
        
        # 消息去重检查
        current_time = time.time()
        if message_id in processed_messages:
            logger.warning(f"Duplicate message ignored: {message_id}")
            return
        
        # 标记消息已处理
        processed_messages[message_id] = current_time
        
        # 定期清理过期记录
        if len(processed_messages) > MAX_PROCESSED_MESSAGES:
            cleanup_old_messages()
        
        logger.info(f"Received message: type={message_type}, id={message_id}")
        
        # 构建事件数据字典，保持与 Handler 中期待的结构一致
        event_dict = {
            "message": {
                "message_id": message.message_id,
                "chat_id": message.chat_id,
                "message_type": message_type,
                "content": message.content,
            },
            "sender": {
                "sender_id": {
                    "open_id": event.sender.sender_id.open_id if event.sender.sender_id else "",
                    "user_id": event.sender.sender_id.user_id if event.sender.sender_id else "",
                }
            }
        }
        
        # 根据消息类型路由到对应处理器（同步调用）
        if message_type == "text" and text_handler:
            text_handler.handle(event_dict)
        elif message_type == "image" and image_handler:
            image_handler.handle(event_dict)
        elif message_type == "audio" and voice_handler:
            voice_handler.handle(event_dict)
        else:
            logger.warning(f"Unsupported message type: {message_type}")
            # 回复用户提示不支持的消息类型
            if feishu_client:
                feishu_client.reply_message(
                    message.message_id,
                    f"暂不支持该消息类型 ({message_type})\n\n"
                    "请发送：\n"
                    "📝 文字消息\n"
                    "🖼️ 图片（微信截图等）\n"
                    "🎤 语音消息"
                )
            
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("Starting Feishu Calendar Bot...")
    logger.info("=" * 50)
    
    # 初始化服务
    init_services()
    
    if not config:
        logger.error("Failed to load configuration")
        return

    # 创建事件分发器
    # 注意: 长连接模式下，encrypt_key 和 verification_token 传空字符串
    event_handler = lark.EventDispatcherHandler.builder("", "") \
        .register_p2_im_message_receive_v1(handle_message_event) \
        .build()
    
    # 创建 WebSocket 客户端
    ws_client = lark.ws.Client(
        app_id=config.feishu_app_id,
        app_secret=config.feishu_app_secret,
        event_handler=event_handler,
        log_level=lark.LogLevel.DEBUG
    )
    
    logger.info("WebSocket client created, starting connection...")
    logger.info("Bot is running! Press Ctrl+C to stop.")
    
    # 启动 WebSocket 连接（阻塞）
    ws_client.start()


if __name__ == "__main__":
    main()
