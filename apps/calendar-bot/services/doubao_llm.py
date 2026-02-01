"""豆包大模型服务封装"""
import json
from datetime import datetime
from typing import Optional, Dict, Any
from openai import OpenAI

from utils.logger import get_logger

logger = get_logger(__name__)


# 系统提示词模板
SYSTEM_PROMPT = """你是一个专业的日程信息提取助手。你的任务是从用户提供的文本中提取日程相关信息。

## 提取规则：
1. **日期**: 识别具体日期或相对日期（如"明天"、"下周三"、"1月31号"）
2. **时间**: 识别具体时间，如"下午3点"、"15:00"、"上午10点半"
3. **标题**: 提取事件的主题或内容
4. **地点**: 如果有提及地点，提取出来

## 默认规则：
- 如果只说"3点"没有上下午，默认为下午15:00
- 如果没有结束时间，默认持续1小时
- 所有时间都按北京时间(UTC+8)处理
- 如果有多个日程，只提取第一个

## 输出格式：
必须返回JSON格式，包含以下字段：
```json
{{
  "has_schedule": true/false,
  "title": "事件标题",
  "date": "YYYY-MM-DD",
  "start_time": "HH:MM",
  "end_time": "HH:MM",
  "location": "地点（可选，没有则为null）",
  "confidence": 0.0-1.0
}}
```

如果无法识别出有效的日程信息，返回：
```json
{{
  "has_schedule": false,
  "reason": "无法识别的原因"
}}
```

今天是 {today}。
"""


class DoubaoLLM:
    """豆包大模型封装"""
    
    def __init__(self, api_key: str, model_id: Optional[str] = None):
        """初始化豆包客户端
        
        Args:
            api_key: 豆包 API Key
            model_id: 模型ID（可选，默认使用 doubao-1-5-pro-32k）
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://ark.cn-beijing.volces.com/api/v3"
        )
        # 豆包模型ID，需要用户配置或使用默认值
        self.model_id = model_id or "doubao-1-5-pro-32k-250115"
        logger.info(f"DoubaoLLM initialized with model: {self.model_id}")
    
    def extract_schedule(self, text: str) -> Dict[str, Any]:
        """从文本中提取日程信息
        
        Args:
            text: 包含日程信息的文本
            
        Returns:
            提取结果字典，包含 has_schedule, title, date, start_time, end_time, location 等字段
        """
        try:
            # 构建系统提示词，注入当前日期
            today = datetime.now().strftime("%Y年%m月%d日 %A")
            system_prompt = SYSTEM_PROMPT.format(today=today)
            
            # 调用豆包API
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请从以下文本中提取日程信息：\n\n{text}"}
                ],
                temperature=0.1,  # 低温度以获得更稳定的输出
                response_format={"type": "json_object"}  # 强制JSON输出
            )
            
            # 解析响应
            content = response.choices[0].message.content
            logger.debug(f"LLM raw response: {content}")
            
            # 去除可能存在的 markdown 代码块标记
            if content.startswith("```"):
                # 寻找第一个换行符
                first_newline = content.find('\n')
                if first_newline != -1:
                    # 去除开头的 ```json 或 ```
                    content = content[first_newline:].strip()
                # 去除结尾的 ```
                if content.endswith("```"):
                    content = content[:-3].strip()
                
            result = json.loads(content)
            
            logger.info(f"Schedule extracted: {result}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return {"has_schedule": False, "reason": "LLM响应格式错误"}
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {"has_schedule": False, "reason": f"提取失败: {str(e)}"}
    
    def __bool__(self):
        return bool(self.client and self.model_id)
