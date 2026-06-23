"""
eBay Tool — AI Service (localhost:8001)
LLM backend — switch between SiliconFlow/DeepSeek and eBay HubGPT via env vars:
  HUBGPT_API_KEY  : HubGPT token (if set, uses HubGPT)
  SF_API_KEY      : SiliconFlow fallback
  HUBGPT_BASE_URL : override base URL (default: HubGPT internal endpoint)
  LLM_MODEL       : override model name
"""

import os
import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI(title="eBay Tool AI Service", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── LLM 配置：优先 HubGPT，回退 SiliconFlow ──────────────────────
_HUBGPT_KEY = os.environ.get("HUBGPT_API_KEY", "")
_SF_KEY      = os.environ.get("SF_API_KEY", "")

if _HUBGPT_KEY:
    _API_KEY  = _HUBGPT_KEY
    _BASE_URL = os.environ.get("HUBGPT_BASE_URL", "https://hubgpt.corp.ebay.com/v1")
    _MODEL    = os.environ.get("LLM_MODEL", "gpt-4o")
else:
    _API_KEY  = _SF_KEY
    _BASE_URL = "https://api.siliconflow.cn/v1"
    _MODEL    = os.environ.get("LLM_MODEL", "deepseek-ai/DeepSeek-V3")

client = OpenAI(api_key=_API_KEY, base_url=_BASE_URL)


class AdviceRequest(BaseModel):
    category: str
    product_name: str = ""
    site: str = "US"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ebay-tool-ai",
        "backend": "HubGPT" if _HUBGPT_KEY else "SiliconFlow",
        "model": _MODEL,
        "base_url": _BASE_URL,
    }


@app.post("/ai-advice")
async def ai_advice(req: AdviceRequest):
    if not client.api_key:
        raise HTTPException(status_code=500, detail="SF_API_KEY not configured")

    prompt = f"""eBay {req.site} listing expert. Return ONLY valid JSON, no markdown, no extra text.

Category: {req.category}
Product: {req.product_name or req.category}

Return this exact JSON structure with real values:
{{"title":{{"formula":"[Brand]+[Year/Model]+[Key Feature]+[Position/Spec]","mustKeywords":["keyword1","keyword2","keyword3","keyword4","keyword5"],"bonusKeywords":["bonus1","bonus2","bonus3"],"minLen":65,"maxLen":80}},"priceRanges":[{{"label":"Budget","min":10,"max":30,"note":"entry level"}},{{"label":"Mid","min":31,"max":80,"note":"mainstream"}},{{"label":"Premium","min":81,"max":200,"note":"high-end"}}],"images":[{{"slot":"1","type":"Main","rule":"white bg #FFFFFF, product 85%+, no watermark","required":true}},{{"slot":"2-4","type":"Multi-angle","rule":"front/side/back/detail","required":true}},{{"slot":"5-6","type":"Detail","rule":"key close-ups specific to this part type","required":true}},{{"slot":"7-8","type":"Installed","rule":"product installed on vehicle","required":false}}],"specifics":[{{"key":"Brand","priority":"P0","note":"brand name"}},{{"key":"Fitment Type","priority":"P0","note":"Direct Replacement"}},{{"key":"Placement on Vehicle","priority":"P0","note":"Front/Rear/Left/Right"}},{{"key":"Part Name","priority":"P0","note":"exact part name"}},{{"key":"OE/OEM Part Number","priority":"P0","note":"OEM number"}},{{"key":"Manufacturer Part Number","priority":"P1","note":"MPN"}},{{"key":"Warranty","priority":"P1","note":"1 Year / Lifetime"}},{{"key":"Material","priority":"P1","note":"material type"}},{{"key":"Color","priority":"P2","note":"color"}},{{"key":"Country of Manufacture","priority":"P2","note":"country"}}]}}

Replace the example values with accurate ones for the {req.category} category. Use real eBay item specifics field names."""

    try:
        response = client.chat.completions.create(
            model=_MODEL,
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        result = json.loads(raw)
        return result

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"API error: {str(e)}")


class CompetitorRequest(BaseModel):
    competitor_title: str = ""
    competitor_details: str = ""
    competitors: list = []
    my_title: str = ""
    my_brand: str = ""
    my_desc: str = ""
    category: str = ""
    site: str = "US"


@app.post("/competitor-compare")
async def competitor_compare(req: CompetitorRequest):
    if not client.api_key:
        raise HTTPException(status_code=500, detail="SF_API_KEY not configured")

    my_text = " | ".join(filter(None, [req.my_title, req.my_brand, req.my_desc]))
    has_my = bool(my_text.strip())

    # Build competitor section — support both single and multi-competitor
    comp_list = req.competitors if req.competitors else [{"title": req.competitor_title, "details": req.competitor_details}]
    comp_list = [c for c in comp_list if c.get("title")]
    if not comp_list:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="At least one competitor title is required")

    if len(comp_list) == 1:
        comp_section = f"COMPETITOR LISTING:\nTitle: {comp_list[0]['title']}\nDetails: {comp_list[0].get('details') or '(not provided)'}"
    else:
        parts = []
        for i, c in enumerate(comp_list, 1):
            parts.append(f"COMPETITOR {i}:\nTitle: {c['title']}\nDetails: {c.get('details') or '(not provided)'}")
        comp_section = "\n\n".join(parts)

    prompt = f"""You are an eBay listing expert for auto parts. Analyze the following listing(s) for the eBay {req.site} market.

Category: {req.category or "Auto Parts"}

{comp_section}

{"SELLER LISTING:" + chr(10) + my_text if has_my else "(Seller listing not provided — analyze competitor strengths only)"}

Return ONLY valid JSON, no markdown, no extra text:
{{
  "summary": "一句话总结（中文）",
  "competitor_strengths": [
    {{"item": "优势点名称", "detail": "为什么这对买家重要"}}
  ],
  "seller_gaps": [
    {{"priority": "P0", "item": "缺失项名称", "action": "具体操作建议", "example": "标题示例片段"}}
  ],
  "seller_advantages": [
    {{"item": "你的优势", "detail": "说明"}}
  ],
  "competitor_weaknesses": [
    {{"item": "竞品弱点", "detail": "你可以在这里超越"}}
  ]
}}

Rules:
- P0 = 直接影响搜索排名或转化率的缺失（兼容车型、核心规格等）
- P1 = 重要但不紧急
- P2 = 加分项
- If seller listing not provided: leave seller_gaps and seller_advantages as empty arrays
- All text fields must be in Chinese
- Be specific to the actual content provided, not generic advice"""

    try:
        response = client.chat.completions.create(
            model=_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        result = json.loads(raw)
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"API error: {str(e)}")


class SmartAdviceRequest(BaseModel):
    product_name: str
    category: str = ""
    site: str = "US"


@app.post("/smart-advice")
async def smart_advice(req: SmartAdviceRequest):
    if not client.api_key:
        raise HTTPException(status_code=500, detail="SF_API_KEY not configured")

    prompt = f"""你是 eBay 汽配品类资深运营专家。
卖家在 eBay {req.site} 站点销售：「{req.product_name}」（类目：{req.category or req.product_name}）

生成针对此具体产品的全面 Listing 优化建议。仅返回纯 JSON，不要 markdown 代码块，不要多余文字：
{{
  "product_summary": "一句话描述该产品eBay市场定位和核心竞争点（30字内）",
  "sections": [
    {{
      "id": "actions",
      "icon": "🎯",
      "title": "立即行动清单（Top 5）",
      "color": "#E53238",
      "items": [
        {{"priority": "P0", "label": "行动标题", "detail": "为什么重要 + 具体操作步骤", "example": "（可选）标题/内容示例片段"}}
      ]
    }},
    {{
      "id": "pricing",
      "icon": "💰",
      "title": "定价与竞争策略",
      "color": "#0064D2",
      "items": [
        {{"label": "建议名称", "detail": "具体说明与数据参考"}}
      ]
    }},
    {{
      "id": "specifics",
      "icon": "📋",
      "title": "关键 Item Specifics",
      "color": "#7C3AED",
      "items": [
        {{"priority": "P0", "label": "字段名（英文）", "detail": "为什么对此产品特别重要 + 推荐填写内容"}}
      ]
    }},
    {{
      "id": "description",
      "icon": "📝",
      "title": "描述页必写内容",
      "color": "#27ae60",
      "items": [
        {{"label": "内容模块", "detail": "具体要写什么 + 格式建议"}}
      ]
    }},
    {{
      "id": "shipping",
      "icon": "🚚",
      "title": "配送与售后政策",
      "color": "#F5AF02",
      "items": [
        {{"label": "建议名称", "detail": "具体标准与对排名的影响"}}
      ]
    }}
  ]
}}

规则：
- 所有 detail/label 用中文，字段名英文保留
- "立即行动"固定5项，按 P0→P1→P2 排序
- 其他每节 3-5 项
- 必须针对「{req.product_name}」的产品特性，禁止通用套话
- 安全件（刹车/悬挂）：重点强调认证和兼容车型；灯具：强调安装方式和配光认证；改装件：强调适配和质保
- Top Seller 的核心制胜要素必须体现在"立即行动"中"""

    try:
        response = client.chat.completions.create(
            model=_MODEL,
            max_tokens=1800,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        result = json.loads(raw)
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"API error: {str(e)}")


@app.get("/search")
def search(q: str = "", site: str = "US", top_k: int = 100):
    return []


if __name__ == "__main__":
    import uvicorn, sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 50)
    print("eBay Tool AI Service starting...")
    print(f"Backend : {'HubGPT' if _HUBGPT_KEY else 'SiliconFlow (fallback)'}")
    print(f"Model   : {_MODEL}")
    print(f"Base URL: {_BASE_URL}")
    print(f"API Key : {'OK' if (_HUBGPT_KEY or _SF_KEY) else 'MISSING!'}")
    print("URL: http://localhost:8001")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8001)
