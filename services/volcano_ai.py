"""火山引擎AI服务封装（OCR + ASR）"""
import base64
from typing import Optional
from openai import OpenAI

from utils.logger import get_logger

logger = get_logger(__name__)


class VolcanoAI:
    """火山引擎AI服务封装
    
    由于用户可能只开通了火山方舟(大模型服务)，而未开通视觉智能/语音技术服务，
    本实现使用豆包多模态模型作为OCR的替代方案。
    
    如需使用原生OCR/ASR服务，需要单独开通火山引擎视觉智能和语音技术服务。
    """
    
    def __init__(self, api_key: str, access_key: Optional[str] = None, secret_key: Optional[str] = None):
        """初始化
        
        Args:
            api_key: 豆包 API Key（用于多模态识别）
            access_key: 火山引擎 Access Key（用于原生OCR/ASR，可选）
            secret_key: 火山引擎 Secret Key（用于原生OCR/ASR，可选）
        """
        # 使用豆包多模态模型作为OCR替代
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://ark.cn-beijing.volces.com/api/v3"
        )
        self.vision_model = "doubao-1-5-vision-pro-32k-250115"
        
        # 火山引擎原生服务凭证（如果配置了的话）
        self.access_key = access_key
        self.secret_key = secret_key
        
        logger.info("VolcanoAI initialized (using Doubao Vision for OCR)")
    
    def ocr_image(self, image_bytes: bytes) -> Optional[str]:
        """OCR识别图片中的文字
        
        使用豆包多模态模型识别图片中的文字内容。
        
        Args:
            image_bytes: 图片二进制数据
            
        Returns:
            识别出的文字，失败返回None
        """
        try:
            # 将图片转为base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # 使用豆包视觉模型识别
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请仔细阅读这张图片中的所有文字内容，完整提取出来。只需要返回图片中的文字，不需要任何解释或分析。如果是聊天记录截图，请按对话顺序提取。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000
            )
            
            text = response.choices[0].message.content
            logger.info(f"OCR result (first 100 chars): {text[:100]}...")
            return text
            
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return None
    
    def asr_audio(self, audio_bytes: bytes, audio_format: str = "mp3") -> Optional[str]:
        """语音转文字
        
        注意: 当前使用的是豆包API，暂不支持原生语音识别。
        如需语音识别功能，需要开通火山引擎语音技术服务。
        
        Args:
            audio_bytes: 音频二进制数据
            audio_format: 音频格式 (mp3, wav, ogg等)
            
        Returns:
            识别出的文字，失败返回None
        """
        # TODO: 实现火山引擎语音识别
        # 需要用户开通语音技术服务并提供 Access Key
        
        if not self.access_key or not self.secret_key:
            logger.warning("ASR requires Volcano Engine Access Key and Secret Key")
            return None
        
        try:
            # 火山引擎ASR实现
            # 参考: https://www.volcengine.com/docs/6561/80818
            
            # 暂时返回提示信息
            logger.warning("ASR not implemented yet - need Volcano Engine credentials")
            return None
            
        except Exception as e:
            logger.error(f"ASR failed: {e}")
            return None
