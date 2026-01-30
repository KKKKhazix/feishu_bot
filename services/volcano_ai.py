"""火山引擎AI服务封装（OCR + ASR + 日程提取）"""
import base64
import json
from datetime import datetime
from typing import Optional, Dict, Any
from openai import OpenAI

from utils.logger import get_logger

logger = get_logger(__name__)


# 图片日程提取的系统提示词
VISION_SCHEDULE_PROMPT = """你是一个专业的日程信息提取助手。请仔细分析这张图片（通常是聊天记录截图），从中提取日程相关信息。

## 重要提取规则：

### 标题格式（非常重要！）
标题必须包含"与谁做什么"的信息：
- 优先提取**人名**（如：刘星、张三、李总）
- 如果没有人名，提取**公司/品牌名**（如：字节跳动、星巴克）
- 格式示例：「与刘星、雷磊聚餐」「和张总开会」「字节跳动面试」

### 日期时间
- 识别具体日期或相对日期（如"明天"、"周日"、"1月31号"）
- 识别具体时间，如"下午3点"、"15:00"、"11点"
- 如果只说"3点"没有上下午，默认为下午15:00
- 如果没有结束时间，默认持续1小时

### 地点
- 提取餐厅名、公司名、地址等（如：肥福排档(北投奥园1314店)）

## 输出格式（必须是JSON）：
```json
{{
  "has_schedule": true,
  "title": "与XXX做什么",
  "date": "YYYY-MM-DD",
  "start_time": "HH:MM",
  "end_time": "HH:MM",
  "location": "地点（没有则为null）",
  "participants": ["人名1", "人名2"],
  "confidence": 0.0-1.0
}}
```

如果图片中没有日程信息，返回：
```json
{{
  "has_schedule": false,
  "reason": "原因"
}}
```

今天是 {today}。请直接返回JSON，不要有其他内容。"""


class VolcanoAI:
    """火山引擎AI服务封装
    
    使用豆包 flash 模型实现快速的图片日程提取。
    """
    
    def __init__(self, api_key: str, access_key: Optional[str] = None, secret_key: Optional[str] = None):
        """初始化
        
        Args:
            api_key: 豆包 API Key（用于多模态识别）
            access_key: 火山引擎 Access Key（用于原生OCR/ASR，可选）
            secret_key: 火山引擎 Secret Key（用于原生OCR/ASR，可选）
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://ark.cn-beijing.volces.com/api/v3"
        )
        # 使用豆包1.8（多模态Agent优化，支持关闭深度思考）
        self.vision_model = "doubao-seed-1-8-251228"
        
        # 火山引擎原生服务凭证（如果配置了的话）
        self.access_key = access_key
        self.secret_key = secret_key
        
        logger.info(f"VolcanoAI initialized with model: {self.vision_model}")
    
    def extract_schedule_from_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """从图片直接提取日程信息（合并OCR+日程提取，更快）
        
        Args:
            image_bytes: 图片二进制数据
            
        Returns:
            日程信息字典，包含 has_schedule, title, date, start_time 等字段
        """
        try:
            # 将图片转为base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # 构建提示词，注入当前日期
            today = datetime.now().strftime("%Y年%m月%d日 %A")
            prompt = VISION_SCHEDULE_PROMPT.format(today=today)
            
            # 使用标准 chat.completions API，关闭深度思考
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
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
                max_tokens=1000,
                # 关闭深度思考，直接输出结果
                extra_body={
                    "thinking": {
                        "type": "disabled"
                    }
                }
            )
            
            # 获取响应内容（标准格式）
            content = response.choices[0].message.content
            
            logger.info(f"Vision model raw response: {content[:500] if content else 'None'}")
            
            if not content:
                logger.error("Vision model returned empty content")
                return {"has_schedule": False, "reason": "模型返回空内容"}
            
            # 解析JSON - 更健壮的处理
            # 1. 去除可能存在的 markdown 代码块标记
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end != -1:
                    content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                if end != -1:
                    content = content[start:end].strip()
            
            # 2. 尝试找到 JSON 对象的起始和结束位置
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                content = content[start_idx:end_idx]
            
            logger.debug(f"Cleaned JSON content: {content[:300]}")
            
            result = json.loads(content)
            logger.info(f"Schedule extracted from image: {result}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse vision model response as JSON: {e}, content was: {content[:200] if 'content' in dir() else 'N/A'}")
            return {"has_schedule": False, "reason": "模型响应格式错误"}
        except Exception as e:
            import traceback
            logger.error(f"Vision schedule extraction failed: {type(e).__name__}: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {"has_schedule": False, "reason": f"提取失败: {str(e)}"}
    
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
