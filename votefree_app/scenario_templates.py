from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Dict, List, Optional

from .survey_engine import ROSTER_REPEAT_TOKEN


@dataclass(frozen=True)
class ScenarioTemplate:
    key: str
    name: str
    category: str
    archetype: str
    support_level: str  # direct / assisted / planned
    description: str
    tags: List[str]


SUPPORT_TEXT = {
    "direct": "可直接使用",
    "assisted": "可用（需调整）",
    "planned": "规划中",
}


SCENARIO_GROUPS: List[tuple[str, str, List[str]]] = [
    (
        "信息登记",
        "info",
        [
            "单人基础信息登记",
            "多人批量信息采集",
            "身份核验后信息填报",
            "实名信息登记",
            "匿名信息登记",
            "附件型信息采集",
            "多次补充更新型登记",
            "一次性封存型登记",
            "家庭/成员关联信息采集",
            "分字段权限采集",
        ],
    ),
    (
        "报名管理",
        "registration",
        [
            "普通开放报名",
            "限定对象报名",
            "白名单报名",
            "黑名单过滤报名",
            "限额报名",
            "候补报名",
            "先到先得报名",
            "审核通过后生效报名",
            "支持撤销的报名",
            "支持修改的报名",
        ],
    ),
    (
        "预约管理",
        "reservation",
        [
            "单时段预约",
            "多时段预约",
            "单资源预约",
            "多资源并行预约",
            "容量控制型预约",
            "冲突检测型预约",
            "重复预约限制",
            "指定身份可预约",
            "审批通过后预约",
            "自动分配时段预约",
        ],
    ),
    (
        "评价关系",
        "evaluation",
        [
            "自评",
            "互评",
            "自评+互评",
            "上级评价下级",
            "下级评价上级",
            "同级互评",
            "跨组互评",
            "指定对象评分",
            "随机分配评分对象",
            "多轮评价",
        ],
    ),
    (
        "评分评审",
        "scoring",
        [
            "单评委评分",
            "多评委独立评分",
            "多评委汇总评分",
            "专家评审",
            "领导评分",
            "老师评分",
            "学生评分",
            "分角色加权评分",
            "评分后自动排名",
            "评分后自动淘汰筛选",
        ],
    ),
    (
        "投票选举",
        "voting",
        [
            "实名投票",
            "匿名投票",
            "单选投票",
            "多选投票",
            "限票数投票",
            "分组投票",
            "分身份投票",
            "差额投票",
            "排序投票",
            "多轮晋级投票",
        ],
    ),
    (
        "满意度调查",
        "satisfaction",
        [
            "普通满意度调查",
            "服务满意度调查",
            "活动满意度调查",
            "课程满意度调查",
            "产品满意度调查",
            "满意度+意见反馈",
            "满意度+投诉建议",
            "满意度对比调查",
            "阶段前后满意度跟踪",
            "匿名满意度测评",
        ],
    ),
    (
        "调研分析",
        "research",
        [
            "需求调研",
            "偏好调研",
            "使用习惯调研",
            "背景情况调研",
            "问题现状调研",
            "原因分析调研",
            "市场意向调研",
            "方案选择调研",
            "可行性预调研",
            "调研后自动分群",
        ],
    ),
    (
        "反馈上报",
        "feedback",
        [
            "意见征集",
            "建议收集",
            "吐槽/问题反馈",
            "投诉受理",
            "事件上报",
            "异常情况填报",
            "风险隐患上报",
            "进度回报",
            "日报/周报/月报填报",
            "回访问卷",
        ],
    ),
    (
        "答题测评",
        "quiz",
        [
            "在线答题",
            "客观题测验",
            "主观题作答",
            "混合题型测试",
            "限时答题",
            "随机抽题测试",
            "分数自动判定",
            "测后分层分组",
            "测评量表",
        ],
    ),
    (
        "综合流程",
        "composite",
        [
            "综合流程型问卷",
        ],
    ),
]


PLANNED_KEYWORDS = {
    "分字段权限",
    "附件型",
    "随机抽题",
    "综合流程",
}

ASSISTED_KEYWORDS = {
    "候补",
    "先到先得",
    "审核",
    "审批",
    "自动分配",
    "冲突检测",
    "随机分配",
    "多轮",
    "加权",
    "自动排名",
    "自动淘汰",
    "排序",
    "晋级",
    "对比",
    "阶段前后",
    "自动分群",
    "限时",
    "判定",
    "分层",
    "封存",
}


def _support_level_by_name(name: str) -> str:
    if any(k in name for k in PLANNED_KEYWORDS):
        return "planned"
    if any(k in name for k in ASSISTED_KEYWORDS):
        return "assisted"
    return "direct"


def _tags_by_name(name: str, archetype: str) -> List[str]:
    tags: List[str] = [archetype]
    if "实名" in name:
        tags.append("实名")
    if "匿名" in name:
        tags.append("匿名")
    if any(k in name for k in ["白名单", "限定对象", "指定身份", "身份核验"]):
        tags.append("名单校验")
    if any(k in name for k in ["互评", "上级", "下级", "同级", "跨组", "评委", "老师", "学生", "领导", "专家"]):
        tags.append("评价关系")
    if any(k in name for k in ["限额", "容量", "限票"]):
        tags.append("限额控制")
    if any(k in name for k in ["候补"]):
        tags.append("候补")
    if any(k in name for k in ["审核", "审批"]):
        tags.append("审批流程")
    if any(k in name for k in ["多轮"]):
        tags.append("多轮")
    if any(k in name for k in ["排序", "排名"]):
        tags.append("排序/排名")
    if any(k in name for k in ["附件"]):
        tags.append("附件")
    if any(k in name for k in ["调研", "调查"]):
        tags.append("调研")
    if "报名" in name:
        tags.append("报名")
    if "预约" in name:
        tags.append("预约")
    if "投票" in name:
        tags.append("投票")
    return sorted(set(tags))


def _make_key(index: int, name: str) -> str:
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8].upper()
    return f"TPL{index:03d}_{digest}"


def _build_catalog() -> List[ScenarioTemplate]:
    items: List[ScenarioTemplate] = []
    index = 1
    for category, archetype, names in SCENARIO_GROUPS:
        for name in names:
            support = _support_level_by_name(name)
            tags = _tags_by_name(name, archetype)
            description = f"{category}场景模板：{name}"
            items.append(
                ScenarioTemplate(
                    key=_make_key(index, name),
                    name=name,
                    category=category,
                    archetype=archetype,
                    support_level=support,
                    description=description,
                    tags=tags,
                )
            )
            index += 1
    return items


CATALOG: List[ScenarioTemplate] = _build_catalog()
CATALOG_BY_KEY: Dict[str, ScenarioTemplate] = {item.key: item for item in CATALOG}
CATALOG_BY_NAME: Dict[str, ScenarioTemplate] = {item.name: item for item in CATALOG}


RECOMMENDED_TEMPLATE_NAMES = [
    "单人基础信息登记",
    "普通开放报名",
    "限额报名",
    "单时段预约",
    "自评+互评",
    "实名投票",
    "多选投票",
    "普通满意度调查",
    "需求调研",
    "意见征集",
    "在线答题",
]


def list_templates() -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for item in CATALOG:
        result.append(
            {
                "key": item.key,
                "name": item.name,
                "category": item.category,
                "archetype": item.archetype,
                "support_level": item.support_level,
                "support_text": SUPPORT_TEXT.get(item.support_level, item.support_level),
                "description": item.description,
                "tags": list(item.tags),
            }
        )
    return result


def list_categories() -> List[str]:
    return sorted({item.category for item in CATALOG})


def get_template_by_key(template_key: str) -> Optional[Dict[str, Any]]:
    item = CATALOG_BY_KEY.get(template_key)
    if not item:
        return None
    return {
        "key": item.key,
        "name": item.name,
        "category": item.category,
        "archetype": item.archetype,
        "support_level": item.support_level,
        "support_text": SUPPORT_TEXT.get(item.support_level, item.support_level),
        "description": item.description,
        "tags": list(item.tags),
    }


def get_template_by_name(name: str) -> Optional[Dict[str, Any]]:
    item = CATALOG_BY_NAME.get(name)
    if not item:
        return None
    return get_template_by_key(item.key)


def _to_int(value: Any, fallback: int, low: Optional[int] = None, high: Optional[int] = None) -> int:
    try:
        v = int(str(value).strip())
    except Exception:
        v = fallback
    if low is not None:
        v = max(low, v)
    if high is not None:
        v = min(high, v)
    return v


def _identity_defaults(identity_mode: str) -> Dict[str, Any]:
    return {
        "collect_name": True,
        "collect_code": True,
        "name_required": True,
        "code_required": True,
    }


def _default_identity_mode(name: str) -> str:
    _ = name
    return "realname"


def _default_auth_mode(name: str) -> str:
    if any(k in name for k in ["白名单", "限定对象", "身份核验", "指定身份", "分身份"]):
        return "roster_code"
    return "open"


def _default_allow_repeat(name: str) -> bool:
    return any(k in name for k in ["多次补充", "日报", "周报", "月报", "回访", "多轮"])


def _default_requires_roster(name: str, auth_mode: str) -> bool:
    if auth_mode != "open":
        return True
    return any(k in name for k in ["互评", "上级", "下级", "同级", "跨组", "评委", "老师", "学生", "领导", "专家", "分组投票", "指定对象"])


def _default_use_roster_loop(name: str) -> bool:
    return any(
        k in name
        for k in [
            "互评",
            "上级评价下级",
            "下级评价上级",
            "同级互评",
            "跨组互评",
            "指定对象评分",
            "随机分配评分对象",
            "单评委评分",
            "多评委独立评分",
            "多评委汇总评分",
            "专家评审",
            "领导评分",
            "老师评分",
            "学生评分",
            "分角色加权评分",
        ]
    )


def _workflow_meta(name: str, options: Dict[str, Any]) -> Dict[str, Any]:
    def read_bool(key: str, fallback: bool) -> bool:
        if key in options:
            return bool(options.get(key))
        return fallback

    limit_default = 0
    if any(k in name for k in ["限额报名", "容量控制型预约", "限票数投票"]):
        limit_default = 50
    workflow = {
        "submission_limit": _to_int(options.get("submission_limit", limit_default), limit_default, 0, 1000000),
        "waitlist_enabled": read_bool("waitlist_enabled", "候补" in name),
        "first_come_enabled": read_bool("first_come_enabled", "先到先得" in name),
        "approval_required": read_bool("approval_required", any(k in name for k in ["审核通过", "审批通过"])),
        "allow_withdraw": read_bool("allow_withdraw", "撤销" in name),
        "allow_modify": read_bool("allow_modify", "支持修改" in name),
        "conflict_check_enabled": read_bool("conflict_check_enabled", "冲突检测" in name),
        "repeat_limit_enabled": read_bool("repeat_limit_enabled", "重复预约限制" in name),
        "auto_assign_slot": read_bool("auto_assign_slot", "自动分配时段预约" in name),
        "random_target_assignment": read_bool("random_target_assignment", "随机分配评分对象" in name),
        "multi_round_enabled": read_bool("multi_round_enabled", "多轮" in name),
        "weighted_scoring": read_bool("weighted_scoring", "加权" in name),
        "auto_ranking": read_bool("auto_ranking", "自动排名" in name),
        "auto_elimination": read_bool("auto_elimination", "自动淘汰" in name),
        "attachment_required": read_bool("attachment_required", "附件型" in name),
    }
    return workflow


def _make_info_questions(name: str) -> List[Dict[str, Any]]:
    questions: List[Dict[str, Any]] = [
        {"id": "tpl_q1", "title": "姓名", "type": "text", "required": True},
        {"id": "tpl_q2", "title": "编号（学号/工号）", "type": "text", "required": True},
        {"id": "tpl_q3", "title": "联系电话", "type": "text", "required": False},
        {"id": "tpl_q4", "title": "备注信息", "type": "textarea", "required": False},
    ]
    if "家庭/成员关联" in name:
        questions.append(
            {
                "id": "tpl_q5",
                "title": "家庭/成员关系信息（每行一条：姓名-关系-联系方式）",
                "type": "textarea",
                "required": True,
            }
        )
    if "附件型" in name:
        questions.append({"id": "tpl_q6", "title": "附件链接（云盘/系统路径）", "type": "text", "required": True})
    return questions


def _make_registration_questions(name: str, max_select: int) -> List[Dict[str, Any]]:
    questions: List[Dict[str, Any]] = [
        {
            "id": "tpl_q1",
            "title": "是否报名本次活动",
            "type": "single",
            "required": True,
            "options": ["报名", "不报名"],
        },
        {"id": "tpl_q2", "title": "联系手机号", "type": "text", "required": True},
        {"id": "tpl_q3", "title": "特殊说明", "type": "textarea", "required": False},
    ]
    if "多" in name or "分组" in name:
        questions.insert(
            1,
            {
                "id": "tpl_qx",
                "title": "报名意向组别",
                "type": "multi",
                "required": False,
                "options": ["A组", "B组", "C组"],
                "max_select": max_select,
            },
        )
    return questions


def _make_reservation_questions(name: str, max_select: int) -> List[Dict[str, Any]]:
    multi_slot = "多时段" in name
    multi_res = "多资源" in name
    slot_type = "multi" if multi_slot else "single"
    resource_type = "multi" if multi_res else "single"
    questions: List[Dict[str, Any]] = [
        {"id": "tpl_q1", "title": "预约日期（YYYY-MM-DD）", "type": "text", "required": True},
        {
            "id": "tpl_q2",
            "title": "预约时段",
            "type": slot_type,
            "required": True,
            "options": ["09:00-10:00", "10:00-11:00", "14:00-15:00", "15:00-16:00"],
            "max_select": max_select if slot_type == "multi" else None,
        },
        {
            "id": "tpl_q3",
            "title": "预约资源",
            "type": resource_type,
            "required": True,
            "options": ["资源A", "资源B", "资源C"],
            "max_select": max_select if resource_type == "multi" else None,
        },
        {"id": "tpl_q4", "title": "预约备注", "type": "textarea", "required": False},
    ]
    return questions


def _make_eval_questions(name: str, rating_min: int, rating_max: int, roster_loop: bool) -> List[Dict[str, Any]]:
    relation_options = []
    if "自评+互评" in name:
        relation_options = ["自评", "互评"]
    elif "自评" in name:
        relation_options = ["自评"]
    elif any(k in name for k in ["互评", "上级", "下级", "同级", "跨组"]):
        relation_options = ["互评"]

    repeat_from = ROSTER_REPEAT_TOKEN if roster_loop else ""
    if roster_loop and "自评+互评" in name:
        return [
            {
                "id": "tpl_q1_self",
                "title": "自评：综合评分",
                "type": "rating",
                "required": True,
                "min": rating_min,
                "max": rating_max,
                "repeat_from": repeat_from,
                "repeat_filter": "self",
            },
            {
                "id": "tpl_q2_self",
                "title": "自评：补充说明",
                "type": "textarea",
                "required": False,
                "repeat_from": repeat_from,
                "repeat_filter": "self",
            },
            {
                "id": "tpl_q3_peer",
                "title": "互评：综合评分",
                "type": "rating",
                "required": True,
                "min": rating_min,
                "max": rating_max,
                "repeat_from": repeat_from,
                "repeat_filter": "peer",
            },
            {
                "id": "tpl_q4_peer",
                "title": "互评：评价意见",
                "type": "textarea",
                "required": False,
                "repeat_from": repeat_from,
                "repeat_filter": "peer",
            },
        ]

    questions: List[Dict[str, Any]] = []
    if relation_options and not roster_loop:
        questions.append(
            {
                "id": "tpl_q0",
                "title": "评价类型",
                "type": "single",
                "required": True,
                "options": relation_options,
            }
        )

    repeat_filter = "all"
    if roster_loop:
        if "自评" in name and "互评" not in name:
            repeat_filter = "self"
        elif any(k in name for k in ["互评", "上级", "下级", "同级", "跨组"]):
            repeat_filter = "peer"

    score_question: Dict[str, Any] = {
        "id": "tpl_q1",
        "title": "综合评分",
        "type": "rating",
        "required": True,
        "min": rating_min,
        "max": rating_max,
        "repeat_from": repeat_from,
    }
    comment_question: Dict[str, Any] = {
        "id": "tpl_q2",
        "title": "评价意见",
        "type": "textarea",
        "required": False,
        "repeat_from": repeat_from,
    }
    if repeat_filter != "all":
        score_question["repeat_filter"] = repeat_filter
        comment_question["repeat_filter"] = repeat_filter
    questions.append(score_question)
    questions.append(comment_question)
    return questions


def _make_voting_questions(name: str, max_select: int) -> List[Dict[str, Any]]:
    options = ["候选项A", "候选项B", "候选项C", "候选项D"]
    if "单选" in name or "实名投票" in name or "匿名投票" in name:
        return [
            {
                "id": "tpl_q1",
                "title": "请选择 1 个候选项",
                "type": "single",
                "required": True,
                "options": options,
            },
            {"id": "tpl_q2", "title": "投票说明（可选）", "type": "textarea", "required": False},
        ]
    if "排序投票" in name:
        return [
            {"id": "tpl_q1", "title": "请按偏好顺序填写候选项（示例：A>B>C>D）", "type": "text", "required": True},
            {"id": "tpl_q2", "title": "排序理由（可选）", "type": "textarea", "required": False},
        ]
    return [
        {
            "id": "tpl_q1",
            "title": "请选择候选项",
            "type": "multi",
            "required": True,
            "options": options,
            "max_select": max_select,
        },
        {"id": "tpl_q2", "title": "投票说明（可选）", "type": "textarea", "required": False},
    ]


def _make_satisfaction_questions(name: str, rating_min: int, rating_max: int) -> List[Dict[str, Any]]:
    questions: List[Dict[str, Any]] = [
        {
            "id": "tpl_q1",
            "title": "整体满意度",
            "type": "rating",
            "required": True,
            "min": rating_min,
            "max": rating_max,
        },
        {
            "id": "tpl_q2",
            "title": "最满意的方面",
            "type": "multi",
            "required": False,
            "options": ["服务态度", "流程效率", "体验质量", "性价比", "沟通反馈"],
            "max_select": 2,
        },
        {"id": "tpl_q3", "title": "改进建议", "type": "textarea", "required": False},
    ]
    if "投诉建议" in name:
        questions.insert(
            2,
            {
                "id": "tpl_q2b",
                "title": "是否有投诉事项",
                "type": "single",
                "required": True,
                "options": ["无", "有"],
            },
        )
    return questions


def _make_research_questions(name: str, max_select: int) -> List[Dict[str, Any]]:
    return [
        {"id": "tpl_q1", "title": f"{name}核心问题", "type": "single", "required": True, "options": ["选项A", "选项B", "选项C"]},
        {
            "id": "tpl_q2",
            "title": "你更倾向的选择（可多选）",
            "type": "multi",
            "required": False,
            "options": ["方向1", "方向2", "方向3", "方向4"],
            "max_select": max_select,
        },
        {"id": "tpl_q3", "title": "补充描述", "type": "textarea", "required": False},
    ]


def _make_feedback_questions(name: str) -> List[Dict[str, Any]]:
    questions = [
        {"id": "tpl_q1", "title": "问题标题", "type": "text", "required": True},
        {
            "id": "tpl_q2",
            "title": "紧急程度",
            "type": "single",
            "required": True,
            "options": ["低", "中", "高", "紧急"],
        },
        {"id": "tpl_q3", "title": "详细描述", "type": "textarea", "required": True},
        {"id": "tpl_q4", "title": "附件链接（可选）", "type": "text", "required": False},
    ]
    if "日报/周报/月报" in name:
        questions.insert(0, {"id": "tpl_q0", "title": "本次汇报周期", "type": "single", "required": True, "options": ["日报", "周报", "月报"]})
    return questions


def _make_quiz_questions(name: str) -> List[Dict[str, Any]]:
    if "主观题" in name:
        return [
            {"id": "tpl_q1", "title": "请围绕主题进行作答", "type": "textarea", "required": True},
            {"id": "tpl_q2", "title": "补充说明", "type": "textarea", "required": False},
        ]
    if "测评量表" in name:
        return [
            {"id": "tpl_q1", "title": "维度1评分", "type": "rating", "required": True, "min": 1, "max": 5},
            {"id": "tpl_q2", "title": "维度2评分", "type": "rating", "required": True, "min": 1, "max": 5},
            {"id": "tpl_q3", "title": "维度3评分", "type": "rating", "required": True, "min": 1, "max": 5},
        ]
    if "混合题型" in name:
        return [
            {"id": "tpl_q1", "title": "客观题：请选择正确选项", "type": "single", "required": True, "options": ["A", "B", "C", "D"]},
            {"id": "tpl_q2", "title": "主观题：简述你的理解", "type": "textarea", "required": True},
            {"id": "tpl_q3", "title": "自评掌握度", "type": "rating", "required": False, "min": 1, "max": 5},
        ]
    return [
        {"id": "tpl_q1", "title": "单选题示例", "type": "single", "required": True, "options": ["A", "B", "C", "D"]},
        {"id": "tpl_q2", "title": "多选题示例", "type": "multi", "required": True, "options": ["A", "B", "C", "D"], "max_select": 2},
        {"id": "tpl_q3", "title": "简答题示例", "type": "textarea", "required": False},
    ]


def _make_composite_questions() -> List[Dict[str, Any]]:
    return [
        {"id": "tpl_q1", "title": "流程环节选择", "type": "single", "required": True, "options": ["环节A", "环节B", "环节C"]},
        {"id": "tpl_q2", "title": "过程评分", "type": "rating", "required": True, "min": 1, "max": 10},
        {"id": "tpl_q3", "title": "改进建议", "type": "textarea", "required": False},
    ]


def _build_questions(archetype: str, name: str, options: Dict[str, Any], use_roster_loop: bool) -> List[Dict[str, Any]]:
    rating_min = _to_int(options.get("rating_min", 1), 1, 0, 100)
    rating_max = _to_int(options.get("rating_max", 10), 10, 1, 100)
    if rating_max <= rating_min:
        rating_max = rating_min + 1
    max_select = _to_int(options.get("max_select", 2), 2, 1, 20)

    if archetype == "info":
        return _make_info_questions(name)
    if archetype == "registration":
        return _make_registration_questions(name, max_select=max_select)
    if archetype == "reservation":
        return _make_reservation_questions(name, max_select=max_select)
    if archetype == "evaluation":
        return _make_eval_questions(name, rating_min=rating_min, rating_max=rating_max, roster_loop=use_roster_loop)
    if archetype == "scoring":
        return _make_eval_questions(name, rating_min=rating_min, rating_max=rating_max, roster_loop=use_roster_loop)
    if archetype == "voting":
        return _make_voting_questions(name, max_select=max_select)
    if archetype == "satisfaction":
        return _make_satisfaction_questions(name, rating_min=rating_min, rating_max=rating_max)
    if archetype == "research":
        return _make_research_questions(name, max_select=max_select)
    if archetype == "feedback":
        return _make_feedback_questions(name)
    if archetype == "quiz":
        return _make_quiz_questions(name)
    return _make_composite_questions()


def build_payload(template_key: str, options: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    tpl = CATALOG_BY_KEY.get(template_key)
    if not tpl:
        return None
    opts = dict(options or {})
    name = tpl.name

    identity_mode = str(opts.get("identity_mode") or _default_identity_mode(name)).strip().lower() or "realname"
    if identity_mode != "realname":
        identity_mode = "realname"
    auth_mode = str(opts.get("auth_mode") or _default_auth_mode(name)).strip() or "open"
    allow_repeat = bool(opts.get("allow_repeat", _default_allow_repeat(name)))
    use_roster_loop = bool(opts.get("use_roster_loop", _default_use_roster_loop(name)))
    requires_roster = _default_requires_roster(name, auth_mode) or use_roster_loop

    title_override = str(opts.get("title_override", "")).strip()
    title = title_override or name
    description = f"{tpl.description}。你可以在问卷编辑器继续修改每一道题。"
    intro = "模板已生成，可按实际需要改题目、改逻辑、改字段。"

    relation_type_options: List[str] = []
    if "自评+互评" in name:
        relation_type_options = ["自评", "互评"]
    elif "自评" in name:
        relation_type_options = ["自评"]
    elif any(k in name for k in ["互评", "上级", "下级", "同级", "跨组"]):
        relation_type_options = ["互评"]

    questions = _build_questions(tpl.archetype, name, opts, use_roster_loop=use_roster_loop)
    schema_meta: Dict[str, Any] = {
        "template_key": tpl.key,
        "template_name": tpl.name,
        "template_category": tpl.category,
        "template_support_level": tpl.support_level,
        "template_support_text": SUPPORT_TEXT.get(tpl.support_level, tpl.support_level),
        "capabilities": list(tpl.tags),
        "workflow": _workflow_meta(name, opts),
        "relation_type_required": bool(relation_type_options),
        "relation_type_options": relation_type_options,
    }

    passcode = str(opts.get("passcode", "")).strip()

    return {
        "key": tpl.key,
        "name": tpl.name,
        "title": title,
        "description": description,
        "intro": intro,
        "identity_mode": identity_mode,
        "allow_repeat": allow_repeat,
        "auth_mode": auth_mode,
        "identity_fields": _identity_defaults(identity_mode),
        "requires_roster": bool(requires_roster),
        "passcode": passcode,
        "schema": {
            "intro": intro,
            "meta": schema_meta,
            "questions": questions,
        },
    }
