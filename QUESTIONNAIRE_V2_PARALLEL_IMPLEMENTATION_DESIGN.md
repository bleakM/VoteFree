# VoteFree 问卷系统 V2 并行实施设计蓝图

## 1. 目标与边界

1. 将问卷创建从“操作台 + 题目列表”升级为“展板式设计器”。
2. 以块（Block）作为流程单元，循环仅允许在块级生效。
3. 支持块变量与题目变量注入（名单项、循环项、身份上下文等）。
4. 支持完整逻辑系统（显示、必填、跳转、分支、计算字段）。
5. 支持“自评 + 互评”在同一循环中并行，基于 `is_self` 分流。
6. 重做导出统计页面：每题按题型选择计算方式，支持块内组合计算与条件计算。
7. 保持旧问卷兼容读取，兼容局域网模式与离线票据模式。

## 2. 顶层架构

1. 设计层（Designer）：展板 UI、块与题目的可视化编排。
2. 模型层（Schema V2）：`schema.blocks[*].questions[*]` 的结构化定义。
3. 执行层（Runner）：问卷渲染、循环展开、逻辑求值、答案校验。
4. 存储层（Vote Envelope）：仍使用 `.vote` 加密封装。
5. 分析层（Export Studio）：可配置指标、过滤器、分组器、组合器。

## 3. Schema V2 结构定义

```json
{
  "version": 2,
  "intro": "string",
  "meta": {
    "designer_version": "2.x",
    "capability_flags": ["blocks", "loop", "logic", "export_plan"]
  },
  "blocks": [
    {
      "id": "b_xxx",
      "title": "块标题",
      "description": "块说明",
      "visible_if": {"op":"..."},
      "repeat": {
        "enabled": true,
        "source": "roster|question|static",
        "source_question_id": "q_xxx",
        "static_items": [{"key":"A","label":"A"}],
        "alias": "loop",
        "include_self": true
      },
      "variables": [
        {"name":"loop_name","expr":"loop.label"},
        {"name":"is_self","expr":"context.is_self"}
      ],
      "questions": [
        {
          "id": "q_xxx",
          "type": "single|multi|rating|text|textarea|number|date|matrix|ranking",
          "title": "题目标题，可含变量 {{loop.label}}",
          "required": true,
          "visible_if": {"op":"..."},
          "required_if": {"op":"..."},
          "repeat_filter": "all|self|peer",
          "options": [],
          "rows": [],
          "min": 1,
          "max": 10,
          "max_select": 2,
          "validation": {"regex":"", "min_len":0, "max_len":0},
          "export": {"default_agg":"count"}
        }
      ]
    }
  ],
  "export_plan": {
    "metrics": [],
    "filters": [],
    "group_by": []
  }
}
```

## 4. 展板式设计器交互

1. 左侧题型库：点击加号将题目插入到当前块。
2. 中间展板：块从上到下排列，块内题目卡片从上到下排列。
3. 右侧属性面板：当前选中块/题的全部属性编辑。
4. 块操作：新增、复制、删除、上移、下移、循环设置、变量管理。
5. 题操作：新增、复制、删除、上移、下移、改题型、逻辑配置、校验配置。
6. 逻辑可视化：显示条件、必填条件、跳转条件统一 DSL。

## 5. 循环与变量模型

1. 单题不允许独立循环，只有块可循环。
2. 块循环来源支持：
   - 名单循环（Roster）
   - 来自前题选项/列表
   - 静态列表
3. 循环上下文变量：
   - `loop.key`、`loop.label`、`loop.index`
   - `context.respondent_*`
   - `context.is_self`
4. 变量可注入：
   - 题目标题
   - 选项文案
   - 逻辑表达式

## 6. 自评 + 互评并行逻辑

1. 在名单循环块中，系统计算每个循环项的 `is_self`。
2. 题目可设置 `repeat_filter`：
   - `self`：只在 `is_self = true` 时显示并计算
   - `peer`：只在 `is_self = false` 时显示并计算
   - `all`：全部循环项显示
3. 提交落库时记录：
   - 循环对象 key
   - `is_self`
   - 关系标签（可选）
4. 导出时可直接按 `is_self` 分层统计。

## 7. 导出统计页面（Export Studio）设计

1. 导出方案（Profile）可保存与复用。
2. 题级指标按题型可选：
   - single/multi：计数、占比、TopN、有效率
   - rating/number：均值、中位数、分位数、方差、加权均值
   - text/textarea：填写率、长度统计、关键词频次
   - matrix：行列分布、行均值、列均值
   - ranking：首选率、平均名次、Borda 分
3. 块级组合指标：
   - 求和、平均、加权、标准化后汇总
   - 多题组合评分（如综合素质分）
4. 条件化统计：
   - 按逻辑条件过滤
   - 按角色/组别/身份过滤
   - 按 `is_self` 分离自评互评
5. 输出：
   - 明细表
   - 指标汇总表
   - 分组对比表
   - 自评互评拆分表

## 8. 与大型平台兼容能力映射

1. 问卷星类能力：
   - 题型库扩展
   - 条件显示与跳转
   - 分块与循环
   - 多维统计
2. 微软问卷类能力：
   - 简洁流程化设计
   - 题目分支逻辑
   - 汇总与图表友好导出
3. VoteFree V2 增强能力：
   - 本地加密 `.vote` 离线/局域网双模式
   - 名单驱动互评 + 自评并行
   - 块级循环变量注入

## 9. 七阶段并行实施（工作流）

1. UI 工作流：展板设计器与属性面板重构。
2. Schema 工作流：V2 结构、V1 兼容迁移、保存与加载。
3. Runner 工作流：循环展开、逻辑引擎、变量替换、校验。
4. Self/Peer 工作流：`is_self` 判定与分流策略。
5. Export 工作流：指标引擎、条件过滤、组合计算。
6. Offline 工作流：离线 HTML 渲染与加密票据兼容 V2。
7. QA 工作流：迁移测试、回归测试、压力测试、打包验证。

## 10. 验收清单

1. 新建问卷可在展板中完成块与题目的编排。
2. 块循环可由名单或前题驱动，且变量注入生效。
3. 同一份问卷支持自评与互评分流且统计可分离。
4. 导出页面可按题型和块设置不同计算方式。
5. 旧问卷可加载并可继续使用，不丢历史数据。
6. 局域网模式与离线 `.vote` 均可正常提交与归票。

## 11. 工程现实说明

1. 该范围已接近完整产品重构，建议按并行工作流实施，但以里程碑验收逐批合并。
2. “一次提交覆盖所有大平台能力且零缺陷”不符合工程规律，必须通过可验证增量落地。
3. 本文档即为后续代码实施的唯一蓝图，确保每个能力都有归属和验收口径。

