from __future__ import annotations

import statistics
import uuid
from typing import Any, Dict, List, Optional, Tuple


SUPPORTED_TYPES = {"text", "textarea", "single", "multi", "rating", "slider"}
ROSTER_REPEAT_TOKEN = "__roster_members__"
REPEAT_FILTERS = {"all", "self", "peer"}
RULE_OPS = {
    "equals",
    "not_equals",
    "contains",
    "in",
    "gt",
    "gte",
    "lt",
    "lte",
    "not_empty",
    "empty",
}
COMPARE_OPS = {"equals", "not_equals", "gt", "gte", "lt", "lte"}
RULE_TYPES = {"sum_compare", "count_compare", "option_hit_compare", "question_compare"}


def make_question_id() -> str:
    return f"q_{uuid.uuid4().hex[:8]}"


def _normalize_repeat_filter(value: Any) -> str:
    v = str(value or "all").strip().lower()
    return v if v in REPEAT_FILTERS else "all"


def _normalize_positive_int(raw: Any, fallback: int = 0) -> int:
    try:
        val = int(raw)
    except (TypeError, ValueError):
        val = fallback
    return max(0, val)


def _normalize_int(raw: Any, fallback: int = 0) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return fallback


def _to_number(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except Exception:
            return None
    return None


def _compare_values(actual: Any, op: str, expected: Any) -> bool:
    op2 = str(op or "equals").strip().lower()
    if op2 == "equals":
        return actual == expected
    if op2 == "not_equals":
        return actual != expected
    if op2 in {"gt", "gte", "lt", "lte"}:
        a = _to_number(actual)
        b = _to_number(expected)
        if a is None or b is None:
            return False
        if op2 == "gt":
            return a > b
        if op2 == "gte":
            return a >= b
        if op2 == "lt":
            return a < b
        if op2 == "lte":
            return a <= b
    return False


def _flatten_values(value: Any) -> List[Any]:
    if isinstance(value, dict):
        out: List[Any] = []
        for item in value.values():
            out.extend(_flatten_values(item))
        return out
    if isinstance(value, list):
        out2: List[Any] = []
        for item in value:
            out2.extend(_flatten_values(item))
        return out2
    return [value]


def _flatten_numeric_values(value: Any) -> List[float]:
    out: List[float] = []
    for item in _flatten_values(value):
        num = _to_number(item)
        if num is not None:
            out.append(num)
    return out


def _aggregate_numeric(values: List[float], agg: str) -> Optional[float]:
    if not values:
        return None
    agg2 = str(agg or "sum").strip().lower()
    if agg2 == "sum":
        return float(sum(values))
    if agg2 == "avg":
        return float(sum(values) / len(values))
    if agg2 == "max":
        return float(max(values))
    if agg2 == "min":
        return float(min(values))
    if agg2 == "count":
        return float(len(values))
    return float(sum(values))


def _parse_repeat_source_item(item: Any) -> Tuple[str, bool]:
    if isinstance(item, dict):
        key = (
            str(item.get("key", "")).strip()
            or str(item.get("value", "")).strip()
            or str(item.get("member_key", "")).strip()
        )
        return key, bool(item.get("is_self", False))
    return str(item).strip(), False


def _repeat_item_passes_filter(repeat_filter: str, is_self: bool) -> bool:
    if repeat_filter == "self":
        return is_self
    if repeat_filter == "peer":
        return not is_self
    return True


def _normalize_rule(rule: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(rule, dict):
        return None
    if "all" in rule and isinstance(rule["all"], list):
        return {"all": [_normalize_rule(item) for item in rule["all"] if _normalize_rule(item)]}
    if "any" in rule and isinstance(rule["any"], list):
        return {"any": [_normalize_rule(item) for item in rule["any"] if _normalize_rule(item)]}
    if "not" in rule:
        nested = _normalize_rule(rule["not"])
        return {"not": nested} if nested else None

    question_id = str(rule.get("question_id", "")).strip()
    if not question_id:
        return None

    if "equals" in rule:
        return {"question_id": question_id, "op": "equals", "value": rule.get("equals")}
    if "contains" in rule:
        return {"question_id": question_id, "op": "contains", "value": rule.get("contains")}

    op = str(rule.get("op", "equals")).strip().lower()
    if op not in RULE_OPS:
        op = "equals"
    return {
        "question_id": question_id,
        "op": op,
        "value": rule.get("value"),
    }


def _evaluate_rule(rule: Optional[Dict[str, Any]], answers: Dict[str, Any]) -> bool:
    if not rule:
        return True
    if "all" in rule:
        return all(_evaluate_rule(item, answers) for item in rule.get("all", []))
    if "any" in rule:
        return any(_evaluate_rule(item, answers) for item in rule.get("any", []))
    if "not" in rule:
        return not _evaluate_rule(rule.get("not"), answers)

    question_id = str(rule.get("question_id", "")).strip()
    op = str(rule.get("op", "equals")).strip().lower()
    expected = rule.get("value")
    actual = answers.get(question_id)

    if op == "equals":
        return actual == expected
    if op == "not_equals":
        return actual != expected
    if op == "contains":
        if isinstance(actual, list):
            return expected in actual
        if isinstance(actual, str):
            return str(expected) in actual
        return actual == expected
    if op == "in":
        if isinstance(expected, list):
            return actual in expected
        return False
    if op == "gt":
        try:
            return float(actual) > float(expected)
        except Exception:
            return False
    if op == "gte":
        try:
            return float(actual) >= float(expected)
        except Exception:
            return False
    if op == "lt":
        try:
            return float(actual) < float(expected)
        except Exception:
            return False
    if op == "lte":
        try:
            return float(actual) <= float(expected)
        except Exception:
            return False
    if op == "not_empty":
        if actual is None:
            return False
        if isinstance(actual, str):
            return bool(actual.strip())
        if isinstance(actual, list):
            return len(actual) > 0
        if isinstance(actual, dict):
            return len(actual) > 0
        return True
    if op == "empty":
        return not _evaluate_rule({"question_id": question_id, "op": "not_empty"}, answers)
    return True


def normalize_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    questions_raw = schema.get("questions", [])
    questions = questions_raw if isinstance(questions_raw, list) else []
    raw_meta = schema.get("meta")
    schema_meta = raw_meta if isinstance(raw_meta, dict) else {}
    normalized_questions: List[Dict[str, Any]] = []
    for index, raw_question in enumerate(questions):
        raw = raw_question if isinstance(raw_question, dict) else {}
        qtype = str(raw.get("type", "text")).lower()
        if qtype not in SUPPORTED_TYPES:
            qtype = "text"
        qid = str(raw.get("id") or f"q_{index + 1}")
        question = {
            "id": qid,
            "title": str(raw.get("title", f"问题 {index + 1}")).strip(),
            "type": qtype,
            "required": bool(raw.get("required", False)),
            "required_if": _normalize_rule(raw.get("required_if")),
            "options": [str(opt).strip() for opt in raw.get("options", []) if str(opt).strip()],
            "max_select": _normalize_positive_int(raw.get("max_select", 1), fallback=1) if qtype == "multi" else None,
            "min_select": _normalize_positive_int(raw.get("min_select", 0), fallback=0) if qtype == "multi" else None,
            "min": _normalize_int(raw.get("min", 1), fallback=1) if qtype in {"rating", "slider"} else None,
            "max": _normalize_int(raw.get("max", 5), fallback=5) if qtype in {"rating", "slider"} else None,
            "step": max(1, _normalize_positive_int(raw.get("step", 1), fallback=1)) if qtype in {"rating", "slider"} else None,
            "min_length": _normalize_positive_int(raw.get("min_length", 0)) if qtype in {"text", "textarea"} else None,
            "max_length": _normalize_positive_int(raw.get("max_length", 0)) if qtype in {"text", "textarea"} else None,
            "min_words": _normalize_positive_int(raw.get("min_words", 0)) if qtype in {"text", "textarea"} else None,
            "max_words": _normalize_positive_int(raw.get("max_words", 0)) if qtype in {"text", "textarea"} else None,
            "max_lines": _normalize_positive_int(raw.get("max_lines", 0)) if qtype == "textarea" else None,
            "visible_if": _normalize_rule(raw.get("visible_if")),
            "repeat_from": str(raw.get("repeat_from", "")).strip(),
            "repeat_filter": _normalize_repeat_filter(raw.get("repeat_filter", "all")),
        }
        normalized_questions.append(question)
    return {
        "version": _normalize_int(schema.get("version", 1), fallback=1),
        "intro": str(schema.get("intro", "")).strip(),
        "meta": schema_meta,
        "questions": normalized_questions,
    }


def _is_visible(question: Dict[str, Any], answers: Dict[str, Any]) -> bool:
    return _evaluate_rule(question.get("visible_if"), answers)


def _is_required(question: Dict[str, Any], answers: Dict[str, Any]) -> bool:
    if question.get("required_if"):
        return _evaluate_rule(question.get("required_if"), answers)
    return bool(question.get("required", False))


def _validate_single(question: Dict[str, Any], value: Any, errors: List[str]) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        errors.append(f"{question['title']} 的答案格式不正确。")
        return None
    options = question.get("options", [])
    if options and value not in options:
        errors.append(f"{question['title']} 的选项无效。")
        return None
    return value


def _validate_multi(question: Dict[str, Any], value: Any, errors: List[str]) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append(f"{question['title']} 需要为多选列表。")
        return []
    options = set(question.get("options", []))
    cleaned: List[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        if options and item not in options:
            errors.append(f"{question['title']} 包含无效选项：{item}")
            continue
        cleaned.append(item)
    max_select = question.get("max_select")
    if isinstance(max_select, int) and max_select > 0 and len(cleaned) > max_select:
        errors.append(f"{question['title']} 最多可选 {max_select} 项。")
    min_select = question.get("min_select")
    if isinstance(min_select, int) and min_select > 0 and 0 < len(cleaned) < min_select:
        errors.append(f"{question['title']} 至少需选择 {min_select} 项。")
    return cleaned


def _validate_rating(question: Dict[str, Any], value: Any, errors: List[str]) -> Optional[int]:
    if value is None:
        return None
    numeric = _to_number(value)
    if numeric is None:
        errors.append(f"{question['title']} 评分必须是整数。")
        return None
    if abs(numeric - round(numeric)) > 1e-9:
        errors.append(f"{question['title']} 评分必须是整数。")
        return None
    score = int(round(numeric))
    min_score = _normalize_int(question.get("min", 1), fallback=1)
    max_score = _normalize_int(question.get("max", 5), fallback=5)
    if score < min_score or score > max_score:
        errors.append(f"{question['title']} 评分范围为 {min_score}-{max_score}。")
        return None
    step = max(1, _normalize_positive_int(question.get("step", 1), fallback=1))
    if step <= 0:
        step = 1
    if (score - min_score) % step != 0:
        errors.append(f"{question['title']} 的步进值不正确。")
        return None
    return score


def _validate_text(question: Dict[str, Any], value: Any, errors: List[str]) -> str:
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        return ""
    min_length = _normalize_positive_int(question.get("min_length", 0), fallback=0)
    max_length = _normalize_positive_int(question.get("max_length", 0), fallback=0)
    if min_length > 0 and len(text) < min_length:
        errors.append(f"{question['title']} 至少需要 {min_length} 个字符。")
    if max_length > 0 and len(text) > max_length:
        errors.append(f"{question['title']} 最多允许 {max_length} 个字符。")

    words = [w for w in text.replace("\n", " ").split(" ") if w.strip()]
    min_words = _normalize_positive_int(question.get("min_words", 0), fallback=0)
    max_words = _normalize_positive_int(question.get("max_words", 0), fallback=0)
    if min_words > 0 and len(words) < min_words:
        errors.append(f"{question['title']} 至少需要 {min_words} 个词。")
    if max_words > 0 and len(words) > max_words:
        errors.append(f"{question['title']} 最多允许 {max_words} 个词。")

    if question.get("type") == "textarea":
        max_lines = _normalize_positive_int(question.get("max_lines", 0), fallback=0)
        if max_lines > 0:
            line_count = len(text.splitlines()) if text else 0
            if line_count > max_lines:
                errors.append(f"{question['title']} 最多允许 {max_lines} 行。")
    return text


def _validate_value(question: Dict[str, Any], value: Any, errors: List[str]) -> Any:
    qtype = question["type"]
    if qtype in {"text", "textarea"}:
        return _validate_text(question, value, errors)
    if qtype == "single":
        return _validate_single(question, value, errors)
    if qtype == "multi":
        return _validate_multi(question, value, errors)
    if qtype in {"rating", "slider"}:
        return _validate_rating(question, value, errors)
    return value


def _question_numeric_pool(answers: Dict[str, Any], question_ids: List[str]) -> List[float]:
    pool: List[float] = []
    for qid in question_ids:
        qid2 = str(qid).strip()
        if not qid2:
            continue
        value = answers.get(qid2)
        pool.extend(_flatten_numeric_values(value))
    return pool


def _rule_count_compare(values: List[float], value_rule: Dict[str, Any]) -> int:
    op = str(value_rule.get("op", "gte")).strip().lower()
    threshold = value_rule.get("value")
    return len([v for v in values if _compare_values(v, op, threshold)])


def _option_hit_count(answers: Dict[str, Any], question_ids: List[str], options: List[str]) -> int:
    opts = {str(item).strip() for item in options if str(item).strip()}
    if not opts:
        return 0
    hit = 0
    for qid in question_ids:
        qid2 = str(qid).strip()
        if not qid2:
            continue
        value = answers.get(qid2)
        for item in _flatten_values(value):
            if isinstance(item, str) and item in opts:
                hit += 1
    return hit


def _resolve_question_metric(answers: Dict[str, Any], question_id: str, agg: str) -> Optional[float]:
    qid = str(question_id).strip()
    if not qid:
        return None
    values = _flatten_numeric_values(answers.get(qid))
    return _aggregate_numeric(values, agg)


def _evaluate_validation_rules(schema: Dict[str, Any], answers: Dict[str, Any], errors: List[str]) -> None:
    meta = schema.get("meta", {})
    if not isinstance(meta, dict):
        return
    rules = meta.get("validation_rules", [])
    if not isinstance(rules, list):
        return
    for idx, rule in enumerate(rules, start=1):
        if not isinstance(rule, dict):
            continue
        rule_type = str(rule.get("type", "")).strip().lower()
        if rule_type not in RULE_TYPES:
            continue
        when_rule = _normalize_rule(rule.get("when"))
        if when_rule and not _evaluate_rule(when_rule, answers):
            continue
        op = str(rule.get("op", "lte")).strip().lower()
        if op not in COMPARE_OPS:
            op = "lte"
        message = str(rule.get("message", "")).strip() or f"联合规则 #{idx} 未通过。"

        if rule_type == "sum_compare":
            qids = rule.get("question_ids", [])
            if not isinstance(qids, list):
                continue
            pool = _question_numeric_pool(answers, qids)
            actual = sum(pool) if pool else 0
            if not _compare_values(actual, op, rule.get("value", 0)):
                errors.append(message)
            continue

        if rule_type == "count_compare":
            qids2 = rule.get("question_ids", [])
            if not isinstance(qids2, list):
                continue
            pool2 = _question_numeric_pool(answers, qids2)
            value_rule = rule.get("value_rule", {})
            if not isinstance(value_rule, dict):
                value_rule = {"op": "gte", "value": 0}
            actual_count = _rule_count_compare(pool2, value_rule)
            if not _compare_values(actual_count, op, rule.get("value", 0)):
                errors.append(message)
            continue

        if rule_type == "option_hit_compare":
            qids3 = rule.get("question_ids", [])
            opts = rule.get("options", [])
            if not isinstance(qids3, list) or not isinstance(opts, list):
                continue
            actual_hit = _option_hit_count(answers, qids3, opts)
            if not _compare_values(actual_hit, op, rule.get("value", 0)):
                errors.append(message)
            continue

        if rule_type == "question_compare":
            left_q = str(rule.get("left_question", "")).strip()
            right_q = str(rule.get("right_question", "")).strip()
            if not left_q or not right_q:
                continue
            left_agg = str(rule.get("left_agg", "sum")).strip().lower()
            right_agg = str(rule.get("right_agg", "sum")).strip().lower()
            left_value = _resolve_question_metric(answers, left_q, left_agg)
            right_value = _resolve_question_metric(answers, right_q, right_agg)
            if left_value is None or right_value is None:
                continue
            if not _compare_values(left_value, op, right_value):
                errors.append(message)


def validate_answers(schema: Dict[str, Any], answers: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
    normalized = normalize_schema(schema)
    errors: List[str] = []
    cleaned_answers: Dict[str, Any] = {}

    for question in normalized["questions"]:
        qid = question["id"]
        if not _is_visible(question, answers):
            continue
        required = _is_required(question, answers)
        repeat_from = question.get("repeat_from", "")
        repeat_filter = _normalize_repeat_filter(question.get("repeat_filter", "all"))

        if repeat_from:
            repeat_source = answers.get(repeat_from, [])
            if not isinstance(repeat_source, list):
                repeat_source = []
            repeat_keys: List[str] = []
            seen_repeat_keys: set[str] = set()
            for source_item in repeat_source:
                key, is_self = _parse_repeat_source_item(source_item)
                if not key or key in seen_repeat_keys:
                    continue
                if not _repeat_item_passes_filter(repeat_filter, is_self):
                    continue
                seen_repeat_keys.add(key)
                repeat_keys.append(key)
            raw_map = answers.get(qid, {})
            if raw_map is None:
                raw_map = {}
            if not isinstance(raw_map, dict):
                errors.append(f"{question['title']} 的循环答案格式不正确。")
                raw_map = {}
            cleaned_map: Dict[str, Any] = {}
            missing_items: List[str] = []
            for key in repeat_keys:
                raw_value = raw_map.get(key)
                value = _validate_value(question, raw_value, errors)
                empty = value in ("", None, []) or (isinstance(value, list) and len(value) == 0)
                if required and empty:
                    missing_items.append(key)
                if not empty:
                    cleaned_map[key] = value
            if missing_items:
                errors.append(f"{question['title']} 在循环项中存在未填写内容。")
            if cleaned_map:
                cleaned_answers[qid] = cleaned_map
            continue

        raw_value = answers.get(qid)
        value = _validate_value(question, raw_value, errors)
        empty = value in ("", None, []) or (isinstance(value, list) and len(value) == 0)
        if required and empty:
            errors.append(f"{question['title']} 为必填项。")
            continue
        if not empty:
            cleaned_answers[qid] = value

    _evaluate_validation_rules(normalized, cleaned_answers, errors)

    return (len(errors) == 0, errors, cleaned_answers)


def _collect_question_values(question: Dict[str, Any], answers_list: List[Dict[str, Any]]) -> List[Any]:
    qid = question["id"]
    values: List[Any] = []
    for answers in answers_list:
        value = answers.get(qid)
        if isinstance(value, dict):
            values.extend(list(value.values()))
        elif value is not None:
            values.append(value)
    return values


def _collect_repeat_entries(question: Dict[str, Any], payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    qid = question["id"]
    entries: List[Dict[str, Any]] = []
    for payload in payloads:
        answers = payload.get("answers", {})
        if not isinstance(answers, dict):
            continue
        raw_map = answers.get(qid)
        if not isinstance(raw_map, dict):
            continue
        verified = payload.get("verified", {})
        verified_member_key = str(verified.get("member_key", "")).strip() if isinstance(verified, dict) else ""
        for raw_key, raw_value in raw_map.items():
            key = str(raw_key).strip()
            if not key:
                continue
            entries.append(
                {
                    "key": key,
                    "value": raw_value,
                    "is_self": bool(verified_member_key and key == verified_member_key),
                }
            )
    return entries


def _rating_stats(scores: List[int]) -> Dict[str, Any]:
    if not scores:
        return {"count": 0}
    return {
        "count": len(scores),
        "average": round(sum(scores) / len(scores), 3),
        "median": statistics.median(scores),
        "min": min(scores),
        "max": max(scores),
    }


def _question_stats_methods(question: Dict[str, Any]) -> List[str]:
    qtype = str(question.get("type", "")).strip()
    default_map = {
        "single": ["count", "ratio", "top_n"],
        "multi": ["count", "ratio", "top_n"],
        "rating": ["count", "average", "median", "min", "max", "stddev"],
        "slider": ["count", "average", "median", "min", "max", "stddev"],
        "text": ["filled", "fill_rate", "length_avg"],
        "textarea": ["filled", "fill_rate", "length_avg"],
    }
    allowed_map = {
        "single": {"count", "ratio", "top_n", "bottom_n"},
        "multi": {"count", "ratio", "top_n", "bottom_n"},
        "rating": {"count", "average", "median", "min", "max", "stddev", "sum", "range"},
        "slider": {"count", "average", "median", "min", "max", "stddev", "sum", "range"},
        "text": {"filled", "fill_rate", "length_avg", "length_min", "length_max"},
        "textarea": {"filled", "fill_rate", "length_avg", "length_min", "length_max"},
    }
    methods = question.get("stats_methods", [])
    if isinstance(methods, list):
        cleaned = [str(item).strip().lower() for item in methods if str(item).strip()]
        if cleaned:
            allowed = allowed_map.get(qtype, set())
            filtered = [item for item in cleaned if item in allowed]
            if filtered:
                return filtered
    return default_map.get(qtype, ["count"])


def _ratio_map(counts: Dict[str, int]) -> Dict[str, float]:
    total = sum(counts.values())
    if total <= 0:
        return {k: 0.0 for k in counts}
    return {k: round((v / total) * 100, 2) for k, v in counts.items()}


def _top_bottom_items(counts: Dict[str, int], top_n: int, bottom_n: int) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int]]]:
    sorted_items = sorted(counts.items(), key=lambda kv: (-kv[1], str(kv[0])))
    asc_items = sorted(counts.items(), key=lambda kv: (kv[1], str(kv[0])))
    return (sorted_items[: max(1, top_n)], asc_items[: max(1, bottom_n)])


def _text_length_stats(values: List[Any]) -> Dict[str, Any]:
    texts = [str(v).strip() for v in values if isinstance(v, str) and str(v).strip()]
    if not texts:
        return {"count": 0}
    lengths = [len(text) for text in texts]
    return {
        "count": len(texts),
        "length_avg": round(sum(lengths) / len(lengths), 3),
        "length_min": min(lengths),
        "length_max": max(lengths),
    }


def calculate_statistics(schema: Dict[str, Any], payloads: List[Dict[str, Any]]) -> Dict[str, Any]:
    normalized = normalize_schema(schema)
    answers_list = [payload.get("answers", {}) for payload in payloads]
    question_stats: Dict[str, Any] = {}
    expanded_question_stats: Dict[str, Any] = {}
    grouped_stats: Dict[str, Dict[str, Any]] = {}
    overall_question_ids: List[str] = []
    excluded_question_ids: List[str] = []

    for question in normalized["questions"]:
        qid = question["id"]
        qtype = question["type"]
        methods = _question_stats_methods(question)
        stats_group = str(question.get("stats_group", "")).strip()
        exclude_from_overall = bool(question.get("exclude_from_overall", False))
        if exclude_from_overall:
            excluded_question_ids.append(qid)
        else:
            overall_question_ids.append(qid)
        values = _collect_question_values(question, answers_list)
        repeat_entries = _collect_repeat_entries(question, payloads)
        has_repeat_entries = len(repeat_entries) > 0

        if qtype in {"single", "multi"}:
            counts: Dict[str, int] = {opt: 0 for opt in question.get("options", [])}
            self_counts: Dict[str, int] = {opt: 0 for opt in question.get("options", [])}
            peer_counts: Dict[str, int] = {opt: 0 for opt in question.get("options", [])}
            for value in values:
                if qtype == "single":
                    if isinstance(value, str):
                        counts[value] = counts.get(value, 0) + 1
                else:
                    if isinstance(value, list):
                        for item in value:
                            counts[item] = counts.get(item, 0) + 1
            if has_repeat_entries:
                for entry in repeat_entries:
                    value = entry.get("value")
                    target = self_counts if entry.get("is_self") else peer_counts
                    if qtype == "single":
                        if isinstance(value, str):
                            target[value] = target.get(value, 0) + 1
                    elif isinstance(value, list):
                        for item in value:
                            target[item] = target.get(item, 0) + 1
            item = {"type": qtype, "title": question["title"], "counts": counts}
            if "ratio" in methods:
                item["ratios"] = _ratio_map(counts)
            top_n = max(1, _normalize_positive_int(question.get("stats_top_n", 3), fallback=3))
            bottom_n = max(1, _normalize_positive_int(question.get("stats_bottom_n", 3), fallback=3))
            top_items, bottom_items = _top_bottom_items(counts, top_n, bottom_n)
            if "top_n" in methods:
                item["top_items"] = [{"option": k, "count": v} for k, v in top_items]
            if "bottom_n" in methods:
                item["bottom_items"] = [{"option": k, "count": v} for k, v in bottom_items]
            if has_repeat_entries:
                self_items = len([x for x in repeat_entries if x.get("is_self")])
                peer_items = len(repeat_entries) - self_items
                item["repeat_total"] = len(repeat_entries)
                item["repeat_self"] = self_items
                item["repeat_peer"] = peer_items
                item["self_counts"] = self_counts
                item["peer_counts"] = peer_counts
                if "ratio" in methods:
                    item["self_ratios"] = _ratio_map(self_counts)
                    item["peer_ratios"] = _ratio_map(peer_counts)
                expanded: Dict[str, Any] = {}
                grouped_repeat: Dict[str, List[Dict[str, Any]]] = {}
                for entry in repeat_entries:
                    key = str(entry.get("key", "")).strip()
                    if not key:
                        continue
                    grouped_repeat.setdefault(key, []).append(entry)
                for repeat_key, bucket in grouped_repeat.items():
                    iter_counts: Dict[str, int] = {opt: 0 for opt in question.get("options", [])}
                    iter_self_counts: Dict[str, int] = {opt: 0 for opt in question.get("options", [])}
                    iter_peer_counts: Dict[str, int] = {opt: 0 for opt in question.get("options", [])}
                    for entry in bucket:
                        value = entry.get("value")
                        target = iter_self_counts if entry.get("is_self") else iter_peer_counts
                        if qtype == "single":
                            if isinstance(value, str):
                                iter_counts[value] = iter_counts.get(value, 0) + 1
                                target[value] = target.get(value, 0) + 1
                        else:
                            if isinstance(value, list):
                                for val in value:
                                    iter_counts[val] = iter_counts.get(val, 0) + 1
                                    target[val] = target.get(val, 0) + 1
                    iter_item: Dict[str, Any] = {
                        "type": qtype,
                        "title": question["title"],
                        "repeat_key": repeat_key,
                        "counts": iter_counts,
                        "repeat_total": len(bucket),
                        "repeat_self": len([x for x in bucket if x.get("is_self")]),
                        "repeat_peer": len([x for x in bucket if not x.get("is_self")]),
                        "self_counts": iter_self_counts,
                        "peer_counts": iter_peer_counts,
                        "stats_methods": methods,
                        "stats_group": stats_group,
                        "exclude_from_overall": exclude_from_overall,
                    }
                    if "ratio" in methods:
                        iter_item["ratios"] = _ratio_map(iter_counts)
                        iter_item["self_ratios"] = _ratio_map(iter_self_counts)
                        iter_item["peer_ratios"] = _ratio_map(iter_peer_counts)
                    top_i, bottom_i = _top_bottom_items(iter_counts, top_n, bottom_n)
                    if "top_n" in methods:
                        iter_item["top_items"] = [{"option": k, "count": v} for k, v in top_i]
                    if "bottom_n" in methods:
                        iter_item["bottom_items"] = [{"option": k, "count": v} for k, v in bottom_i]
                    expanded[repeat_key] = iter_item
                    expanded_question_stats[f"{qid}::{repeat_key}"] = iter_item
                item["expanded_iterations"] = expanded
                item["expanded_count"] = len(expanded)
            item["stats_methods"] = methods
            item["stats_group"] = stats_group
            item["exclude_from_overall"] = exclude_from_overall
            question_stats[qid] = item
            if stats_group:
                grouped_stats.setdefault(stats_group, {})[qid] = item
            continue

        if qtype in {"rating", "slider"}:
            scores: List[int] = []
            for value in values:
                if isinstance(value, int):
                    scores.append(value)
            item: Dict[str, Any] = {"type": qtype, "title": question["title"]}
            item.update(_rating_stats(scores))
            if "sum" in methods:
                item["sum"] = sum(scores) if scores else 0
            if "stddev" in methods:
                if len(scores) >= 2:
                    item["stddev"] = round(statistics.stdev(scores), 4)
                else:
                    item["stddev"] = 0.0
            if "range" in methods:
                item["range"] = (max(scores) - min(scores)) if scores else 0
            if has_repeat_entries:
                self_scores: List[int] = []
                peer_scores: List[int] = []
                for entry in repeat_entries:
                    value = entry.get("value")
                    if not isinstance(value, int):
                        continue
                    if entry.get("is_self"):
                        self_scores.append(value)
                    else:
                        peer_scores.append(value)
                item["self"] = _rating_stats(self_scores)
                item["peer"] = _rating_stats(peer_scores)
                if "stddev" in methods:
                    item["self"]["stddev"] = round(statistics.stdev(self_scores), 4) if len(self_scores) >= 2 else 0.0
                    item["peer"]["stddev"] = round(statistics.stdev(peer_scores), 4) if len(peer_scores) >= 2 else 0.0
                if "sum" in methods:
                    item["self"]["sum"] = sum(self_scores) if self_scores else 0
                    item["peer"]["sum"] = sum(peer_scores) if peer_scores else 0
                if "range" in methods:
                    item["self"]["range"] = (max(self_scores) - min(self_scores)) if self_scores else 0
                    item["peer"]["range"] = (max(peer_scores) - min(peer_scores)) if peer_scores else 0
                item["repeat_total"] = len(repeat_entries)
                item["repeat_self"] = len(self_scores)
                item["repeat_peer"] = len(peer_scores)
                expanded_rating: Dict[str, Any] = {}
                grouped_repeat: Dict[str, List[Dict[str, Any]]] = {}
                for entry in repeat_entries:
                    key = str(entry.get("key", "")).strip()
                    if not key:
                        continue
                    grouped_repeat.setdefault(key, []).append(entry)
                for repeat_key, bucket in grouped_repeat.items():
                    bucket_scores: List[int] = []
                    bucket_self: List[int] = []
                    bucket_peer: List[int] = []
                    for entry in bucket:
                        value = entry.get("value")
                        if not isinstance(value, int):
                            continue
                        bucket_scores.append(value)
                        if entry.get("is_self"):
                            bucket_self.append(value)
                        else:
                            bucket_peer.append(value)
                    iter_item: Dict[str, Any] = {
                        "type": qtype,
                        "title": question["title"],
                        "repeat_key": repeat_key,
                        "stats_methods": methods,
                        "stats_group": stats_group,
                        "exclude_from_overall": exclude_from_overall,
                    }
                    iter_item.update(_rating_stats(bucket_scores))
                    iter_item["self"] = _rating_stats(bucket_self)
                    iter_item["peer"] = _rating_stats(bucket_peer)
                    iter_item["repeat_total"] = len(bucket)
                    iter_item["repeat_self"] = len(bucket_self)
                    iter_item["repeat_peer"] = len(bucket_peer)
                    if "sum" in methods:
                        iter_item["sum"] = sum(bucket_scores) if bucket_scores else 0
                        iter_item["self"]["sum"] = sum(bucket_self) if bucket_self else 0
                        iter_item["peer"]["sum"] = sum(bucket_peer) if bucket_peer else 0
                    if "stddev" in methods:
                        iter_item["stddev"] = round(statistics.stdev(bucket_scores), 4) if len(bucket_scores) >= 2 else 0.0
                        iter_item["self"]["stddev"] = round(statistics.stdev(bucket_self), 4) if len(bucket_self) >= 2 else 0.0
                        iter_item["peer"]["stddev"] = round(statistics.stdev(bucket_peer), 4) if len(bucket_peer) >= 2 else 0.0
                    if "range" in methods:
                        iter_item["range"] = (max(bucket_scores) - min(bucket_scores)) if bucket_scores else 0
                        iter_item["self"]["range"] = (max(bucket_self) - min(bucket_self)) if bucket_self else 0
                        iter_item["peer"]["range"] = (max(bucket_peer) - min(bucket_peer)) if bucket_peer else 0
                    expanded_rating[repeat_key] = iter_item
                    expanded_question_stats[f"{qid}::{repeat_key}"] = iter_item
                item["expanded_iterations"] = expanded_rating
                item["expanded_count"] = len(expanded_rating)
            item["stats_methods"] = methods
            item["stats_group"] = stats_group
            item["exclude_from_overall"] = exclude_from_overall
            question_stats[qid] = item
            if stats_group:
                grouped_stats.setdefault(stats_group, {})[qid] = item
            continue

        text_count = 0
        for value in values:
            if isinstance(value, str) and value.strip():
                text_count += 1
        item2: Dict[str, Any] = {"type": qtype, "title": question["title"], "filled": text_count}
        if "fill_rate" in methods:
            total = len(payloads)
            item2["fill_rate"] = round((text_count / total) * 100, 2) if total else 0.0
        if any(m in methods for m in {"length_avg", "length_min", "length_max"}):
            item2.update(_text_length_stats(values))
        if has_repeat_entries:
            self_filled = 0
            peer_filled = 0
            self_text_values: List[Any] = []
            peer_text_values: List[Any] = []
            for entry in repeat_entries:
                value = entry.get("value")
                filled = False
                if isinstance(value, str):
                    filled = bool(value.strip())
                elif isinstance(value, list):
                    filled = len(value) > 0
                elif value is not None:
                    filled = True
                if not filled:
                    continue
                if entry.get("is_self"):
                    self_filled += 1
                    self_text_values.append(value)
                else:
                    peer_filled += 1
                    peer_text_values.append(value)
            item2["repeat_total"] = len(repeat_entries)
            item2["repeat_self"] = len([x for x in repeat_entries if x.get("is_self")])
            item2["repeat_peer"] = len(repeat_entries) - item2["repeat_self"]
            item2["self_filled"] = self_filled
            item2["peer_filled"] = peer_filled
            if any(m in methods for m in {"length_avg", "length_min", "length_max"}):
                item2["self_length"] = _text_length_stats(self_text_values)
                item2["peer_length"] = _text_length_stats(peer_text_values)
            expanded_text: Dict[str, Any] = {}
            grouped_repeat: Dict[str, List[Dict[str, Any]]] = {}
            for entry in repeat_entries:
                key = str(entry.get("key", "")).strip()
                if not key:
                    continue
                grouped_repeat.setdefault(key, []).append(entry)
            for repeat_key, bucket in grouped_repeat.items():
                bucket_values = [entry.get("value") for entry in bucket]
                bucket_filled = 0
                bucket_self_filled = 0
                bucket_peer_filled = 0
                bucket_self_values: List[Any] = []
                bucket_peer_values: List[Any] = []
                for entry in bucket:
                    value = entry.get("value")
                    filled = False
                    if isinstance(value, str):
                        filled = bool(value.strip())
                    elif isinstance(value, list):
                        filled = len(value) > 0
                    elif value is not None:
                        filled = True
                    if filled:
                        bucket_filled += 1
                        if entry.get("is_self"):
                            bucket_self_filled += 1
                            bucket_self_values.append(value)
                        else:
                            bucket_peer_filled += 1
                            bucket_peer_values.append(value)
                iter_item: Dict[str, Any] = {
                    "type": qtype,
                    "title": question["title"],
                    "repeat_key": repeat_key,
                    "filled": bucket_filled,
                    "repeat_total": len(bucket),
                    "repeat_self": len([x for x in bucket if x.get("is_self")]),
                    "repeat_peer": len([x for x in bucket if not x.get("is_self")]),
                    "self_filled": bucket_self_filled,
                    "peer_filled": bucket_peer_filled,
                    "stats_methods": methods,
                    "stats_group": stats_group,
                    "exclude_from_overall": exclude_from_overall,
                }
                if "fill_rate" in methods:
                    total = len(payloads)
                    iter_item["fill_rate"] = round((bucket_filled / total) * 100, 2) if total else 0.0
                if any(m in methods for m in {"length_avg", "length_min", "length_max"}):
                    iter_item.update(_text_length_stats(bucket_values))
                    iter_item["self_length"] = _text_length_stats(bucket_self_values)
                    iter_item["peer_length"] = _text_length_stats(bucket_peer_values)
                expanded_text[repeat_key] = iter_item
                expanded_question_stats[f"{qid}::{repeat_key}"] = iter_item
            item2["expanded_iterations"] = expanded_text
            item2["expanded_count"] = len(expanded_text)
        item2["stats_methods"] = methods
        item2["stats_group"] = stats_group
        item2["exclude_from_overall"] = exclude_from_overall
        question_stats[qid] = item2
        if stats_group:
            grouped_stats.setdefault(stats_group, {})[qid] = item2

    return {
        "total_responses": len(payloads),
        "questions": question_stats,
        "expanded_questions": expanded_question_stats,
        "groups": grouped_stats,
        "overall_question_ids": overall_question_ids,
        "excluded_question_ids": excluded_question_ids,
    }
