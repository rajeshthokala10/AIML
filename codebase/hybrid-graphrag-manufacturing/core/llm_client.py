import time
from typing import Optional

from config import OPENAI_API_KEY, LLM_MODEL

_client = None


def _get_client():
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            return None
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 1500,
    model: Optional[str] = None,
) -> str:
    client = _get_client()
    model = model or LLM_MODEL

    if client is None:
        return _mock_llm_response(system_prompt, user_prompt)

    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    elapsed = time.time() - start

    result = response.choices[0].message.content
    usage = response.usage

    return result


def call_llm_with_metrics(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 1500,
    model: Optional[str] = None,
) -> dict:
    client = _get_client()
    model = model or LLM_MODEL

    if client is None:
        return {
            "response": _mock_llm_response(system_prompt, user_prompt),
            "latency_ms": 150,
            "prompt_tokens": len(user_prompt.split()) * 2,
            "completion_tokens": 200,
            "total_tokens": len(user_prompt.split()) * 2 + 200,
            "model": "mock-llm",
            "cost_estimate": 0.0,
        }

    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    elapsed_ms = (time.time() - start) * 1000

    usage = response.usage
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0

    cost_per_1k_input = 0.00015
    cost_per_1k_output = 0.0006
    if "gpt-4o" in model and "mini" not in model:
        cost_per_1k_input = 0.0025
        cost_per_1k_output = 0.01
    elif "gpt-4" in model:
        cost_per_1k_input = 0.03
        cost_per_1k_output = 0.06

    cost = (prompt_tokens * cost_per_1k_input + completion_tokens * cost_per_1k_output) / 1000

    return {
        "response": response.choices[0].message.content,
        "latency_ms": elapsed_ms,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "model": model,
        "cost_estimate": cost,
    }


def _mock_llm_response(system_prompt: str, user_prompt: str) -> str:
    user_lower = user_prompt.lower()

    if "verdict" in system_prompt.lower() or "critic" in system_prompt.lower():
        return """VERDICT: PASS
CONFIDENCE: 0.85
ISSUES: None
SUGGESTION: Answer is well-grounded in the provided evidence."""

    if "p-203" in user_lower or "pump" in user_lower:
        return """Based on the maintenance documentation and work order history:

**Equipment:** Centrifugal Pump P-203

**Diagnosis:**
The high vibration on pump P-203 is most commonly caused by:
1. **Bearing wear** on the drive-end (DE) side — this is the most frequent root cause per work order history (WO-2024-012, WO-2024-028)
2. **Impeller imbalance** due to erosion or cavitation damage
3. **Misalignment** between pump and motor coupling

**Recommended Procedure:**
1. Check vibration readings at both DE and NDE bearings (spec: < 4.5 mm/s)
2. Inspect mechanical seal for leakage (ALM-P003)
3. Verify coupling alignment using dial indicator (tolerance: 0.05mm)
4. If bearing replacement needed, use SP-1003 (SKF 6310-2RS)

**Citations:** [pump_maintenance_manual, chunks 3-5] [work_orders, rows 12, 28]

**Safety Note:** Follow LOTO procedure before any internal inspection. Ensure pump is fully depressurized."""

    if "conveyor" in user_lower or "cv-" in user_lower or "belt" in user_lower:
        return """Based on the conveyor system documentation:

**Equipment:** Belt Conveyor System CV-300 Series

**Diagnosis:**
Belt tracking issues on the CV-301 main line are typically caused by:
1. **Uneven belt tension** — tensioner roller misalignment
2. **Material buildup** on rollers causing asymmetric friction
3. **Worn roller bearings** creating uneven rotation

**Recommended Procedure:**
1. Inspect belt tension at tensioner station (spec: 2-3% elongation)
2. Clean all return rollers and check for material buildup
3. Verify roller alignment using laser alignment tool
4. Check VFD speed settings (should be 1.2 m/s for CV-301)

**Citations:** [conveyor_system_guide, chunks 4-7] [alarm_history, ALM-C002]"""

    if "hydraulic" in user_lower or "hp-" in user_lower or "press" in user_lower:
        return """Based on the hydraulic press manual and maintenance records:

**Equipment:** Hydraulic Press HP-401/HP-402

**Diagnosis:**
Pressure loss in the hydraulic system can be attributed to:
1. **Servo valve wear** — internal leakage past rated specs
2. **Hydraulic fluid contamination** — particle count exceeding ISO 18/16/13
3. **Cylinder seal degradation** — common after 5000+ cycle hours

**Recommended Procedure:**
1. Check system pressure at main gauge (spec: 280 bar operating)
2. Take fluid sample for contamination analysis
3. Inspect servo valve response time (< 15ms)
4. Check accumulator pre-charge pressure (spec: 140 bar nitrogen)

**Citations:** [hydraulic_press_manual, chunks 5-8] [work_orders, WO-2024-035]

**Safety:** LOTO required. Relieve all hydraulic pressure before maintenance."""

    return """Based on the available manufacturing documentation and operational data:

**Analysis:**
The query relates to manufacturing equipment maintenance and troubleshooting. Based on the indexed documentation:

1. Review the relevant equipment maintenance manual for detailed specifications
2. Check alarm history for recurring patterns
3. Consult work order history for similar past incidents
4. Verify spare parts availability before scheduling maintenance

**Recommendation:**
Schedule a detailed inspection following the preventive maintenance procedure outlined in the equipment manual. Cross-reference with recent alarm events to identify any developing failure patterns.

**Citations:** [maintenance_manual] [work_orders] [alarm_history]

Please provide specific equipment ID or alarm code for more targeted diagnostics."""
