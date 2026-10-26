"""
SakuraScope Streamlit dashboard (Chinese-first UI).

Launch:
  python -m sakurascope dashboard
  streamlit run src/sakurascope/dashboard/app.py
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import streamlit as st

from sakurascope import __version__
from sakurascope.dashboard.data import load_dashboard_data
from sakurascope.filtering.classify import FilterCriteria
from sakurascope.reporting.service import ReportOptions, generate_reports

PAGES = [
    "总览",
    "研究机会列表",
    "大学与研究室",
    "机会详情与证据",
    "页面变化记录",
    "采集运行日志",
    "来源管理",
    "导出报告",
]

DEFAULT_AREAS = [
    "Public Health",
    "Epidemiology",
    "Biostatistics",
    "Bioinformatics",
    "Life Sciences",
    "Biomedical Data Science",
    "Medical AI",
    "Medical Engineering",
    "Basic Medicine",
]


def _config_path() -> Path | None:
    raw = os.environ.get("SAKURASCOPE_CONFIG_PATH")
    return Path(raw) if raw else None


def main() -> None:
    st.set_page_config(
        page_title="SakuraScope",
        page_icon="🌸",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.2rem; max-width: 1100px; }
        div[data-testid="stMetricValue"] { font-size: 1.4rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("SakuraScope")
    st.caption(
        f"Japan Research & Graduate Opportunity Intelligence · v{__version__}  \n"
        "本地查询界面 · 主题相关 ≠ 正在招生 ≠ 资格已确认"
    )

    area_options = list(DEFAULT_AREAS)
    try:
        bootstrap = load_dashboard_data(_config_path())
        area_options = [a.name for a in bootstrap.area_config.areas] or area_options
    except Exception:  # noqa: BLE001 — sidebar still works offline
        pass

    with st.sidebar:
        st.header("导航")
        page = st.radio("页面", PAGES, label_visibility="collapsed")
        st.divider()
        st.subheader("筛选")
        query = st.text_input("关键词", placeholder="标题 / 方向 / URL…")
        areas = st.multiselect("研究方向", area_options)
        degree = st.multiselect(
            "学位层次",
            ["doctoral", "master", "research_student", "undergraduate"],
        )
        review = st.multiselect(
            "核验状态",
            [
                "insufficient_info",
                "research_topic_may_match",
                "public_admission_info_found",
                "needs_review",
            ],
        )
        admission = st.selectbox(
            "是否存在公开招生信息",
            ["全部", "仅有公开招生用语", "仅无公开招生用语"],
        )
        deadline_from = st.text_input("截止日期起 (YYYY-MM-DD)", value="")
        deadline_to = st.text_input("截止日期止 (YYYY-MM-DD)", value="")
        seen_days = st.number_input("最近发现（天内，0=不限）", min_value=0, value=0, step=1)
        st.caption("主题相关分仅表示关键词匹配，不是录取概率。")

    if admission == "仅有公开招生用语":
        require_admission: bool | None = True
    elif admission == "仅无公开招生用语":
        require_admission = False
    else:
        require_admission = None

    criteria = FilterCriteria(
        research_areas=areas or None,
        degree_levels=degree or None,
        review_statuses=review or None,
        require_public_admission_info=require_admission,
        deadline_from=deadline_from or None,
        deadline_to=deadline_to or None,
        query=query or None,
    )
    st.session_state["sakurascope_criteria"] = criteria

    try:
        data = load_dashboard_data(_config_path(), criteria=criteria)
    except Exception as exc:  # noqa: BLE001
        st.error(f"无法加载数据：{exc}")
        st.stop()

    if seen_days and seen_days > 0:
        cutoff = datetime.now(UTC) - timedelta(days=int(seen_days))
        data.opportunities = [
            item
            for item in data.opportunities
            if item.opportunity.last_seen_at and item.opportunity.last_seen_at >= cutoff
        ]

    if page == "总览":
        _page_overview(data)
    elif page == "研究机会列表":
        _page_opportunity_list(data)
    elif page == "大学与研究室":
        _page_institutions(data)
    elif page == "机会详情与证据":
        _page_opportunity_detail(data)
    elif page == "页面变化记录":
        _page_changes(data)
    elif page == "采集运行日志":
        _page_runs(data)
    elif page == "来源管理":
        _page_sources(data)
    else:
        _page_export(data)


def _page_overview(data) -> None:
    st.header("总览")
    o = data.overview
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("机会数", o.opportunities)
    c2.metric("快照数", o.snapshots)
    c3.metric("证据条数", o.evidence)
    c4.metric("变化事件", o.change_events)
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("配置来源", o.sources_configured)
    c6.metric("已启用来源", o.sources_enabled)
    c7.metric("有公开招生用语", o.with_admission_language)
    c8.metric("仅主题相关", o.topic_match_only)
    st.info(
        f"数据库：`{o.database_path}`  \n"
        f"当前筛选后机会数：**{len(data.opportunities)}**  \n"
        "抓取失败不等于该校没有招生；主题匹配不等于开放申请。"
    )
    if o.opportunities == 0:
        st.warning(
            "本地库中尚无机会记录。请先配置公开来源并运行 "
            "`python -m sakurascope collect`。（示例 sources 默认禁用且为 MOCK）"
        )


def _page_opportunity_list(data) -> None:
    st.header("研究机会列表")
    if not data.opportunities:
        st.write("没有符合当前筛选条件的机会。")
        return
    rows = [
        {
            "标题": item.opportunity.title,
            "研究方向": item.opportunity.research_area,
            "学位": item.opportunity.degree_level,
            "类型": item.opportunity.opportunity_type,
            "截止日期": item.opportunity.application_deadline,
            "公开招生用语": "是" if item.opportunity.has_public_admission_language else "否",
            "核验状态": item.opportunity.review_status,
            "主题相关分": item.topic_relevance_score,
            "最近发现": item.opportunity.last_seen_at.isoformat()
            if item.opportunity.last_seen_at
            else "",
            "来源URL": item.opportunity.official_source_url,
            "ID": item.opportunity.opportunity_id,
        }
        for item in data.opportunities
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption("主题相关分 = 关键词权重均值，不是录取概率。")


def _page_institutions(data) -> None:
    st.header("大学与研究室")
    st.caption("由机会记录中的机构/研究科候选项汇总；未核实字段不会凭空补齐。")
    if not data.institutions:
        st.write("暂无机构候选项。")
        return
    for inst in data.institutions:
        with st.expander(f"{inst.label}（{inst.opportunity_count}）"):
            st.write("研究方向：", ", ".join(inst.research_areas) or "（未知）")
            for url in inst.sample_urls:
                st.write(url)


def _page_opportunity_detail(data) -> None:
    st.header("机会详情与证据")
    if not data.opportunities:
        st.write("没有可展示的机会。")
        return
    labels = {
        f"{item.opportunity.title or '(无标题)'} [{item.opportunity.opportunity_id[:8]}]": item
        for item in data.opportunities
    }
    choice = st.selectbox("选择机会", list(labels.keys()))
    item = labels[choice]
    opp = item.opportunity
    st.subheader(opp.title or "(无标题)")
    st.write("**核验状态：**", f"`{opp.review_status}`")
    st.write("**分桶：**", ", ".join(f"`{b}`" for b in item.buckets))
    st.write("**研究科/机构候选：**", opp.graduate_school_candidate or "（未知）")
    st.write("**研究方向：**", opp.research_area or "（未知）")
    st.write("**学位层次：**", opp.degree_level or "（未知）")
    st.write("**截止日期（有证据才填写）：**", opp.application_deadline or "（未抽取）")
    st.write("**官方来源：**", opp.official_source_url or "（未知）")
    st.write("**首次发现 / 最近检查：**", f"{opp.first_seen_at} / {opp.last_seen_at}")
    st.markdown("#### 招生相关原文摘录")
    st.write(opp.eligibility_text or "（无）")
    st.markdown("#### 证据片段")
    if item.evidence:
        for ev in item.evidence:
            st.markdown(f"- **{ev.field_name}**：{ev.quoted_text}")
    else:
        st.write("（无证据行）")
    st.markdown("#### 需要人工确认")
    for exp in item.explanations:
        st.write(f"- {exp}")
    if opp.open_questions:
        for q in opp.open_questions.split(" | "):
            st.write(f"- {q}")


def _page_changes(data) -> None:
    st.header("页面变化记录")
    if not data.change_events:
        st.write("暂无变化事件。")
        return
    rows = [
        {
            "时间": e.detected_at.isoformat() if e.detected_at else "",
            "类型": e.change_kind,
            "说明": e.message,
            "实体": e.entity_id,
            "来源": e.source_id,
        }
        for e in data.change_events
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption("page_unreachable / collect_failed 表示抓取问题，不表示招生已关闭。")


def _page_runs(data) -> None:
    st.header("采集运行日志")
    if not data.run_logs:
        st.write("暂无运行记录。")
        return
    rows = [
        {
            "run_id": r.run_id,
            "开始": r.started_at.isoformat() if r.started_at else "",
            "结束": r.completed_at.isoformat() if r.completed_at else "",
            "尝试": r.sources_attempted,
            "成功": r.sources_succeeded,
            "失败": r.sources_failed,
            "页面": r.pages_processed,
            "新建": r.new_records,
            "更新": r.updated_records,
            "重复": r.duplicates_found,
            "错误摘要": r.error_summary,
        }
        for r in data.run_logs
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _page_sources(data) -> None:
    st.header("来源管理")
    st.subheader("配置文件中的来源")
    st.caption(
        f"文件：`{data.settings.paths.sources_file}`（只读展示；请编辑 YAML 后重新 collect）"
    )
    if data.sources_config:
        st.dataframe(
            [
                {
                    "source_id": s.source_id,
                    "名称": s.source_name,
                    "启用": s.enabled,
                    "策略": s.collection_strategy,
                    "类型": s.source_type,
                    "URL": str(s.source_url),
                    "备注": s.notes,
                }
                for s in data.sources_config
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.write("配置中无来源。")

    st.subheader("数据库中的来源状态")
    if data.sources_db:
        st.dataframe(
            [
                {
                    "source_id": s.source_id,
                    "名称": s.source_name,
                    "启用": s.enabled,
                    "最近尝试": s.last_attempt_at.isoformat() if s.last_attempt_at else "",
                    "最近成功": s.last_success_at.isoformat() if s.last_success_at else "",
                    "HTTP": s.last_http_status,
                    "错误": s.last_error,
                    "URL": s.source_url,
                }
                for s in data.sources_db
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.write("数据库中尚无来源行（运行 collect 后会出现）。")


def _page_export(data) -> None:
    st.header("导出报告")
    st.write("将按**当前侧边栏筛选条件**生成报告到本地 reports 目录。")
    formats = st.multiselect(
        "格式",
        ["markdown", "csv", "json"],
        default=["markdown", "csv", "json"],
    )
    if st.button("生成报告", type="primary"):
        if not formats:
            st.error("请至少选择一种格式。")
            return
        criteria = st.session_state.get("sakurascope_criteria") or FilterCriteria()
        try:
            result = generate_reports(
                data.settings,
                ReportOptions(formats=formats, criteria=criteria),
            )
            st.success(f"已生成 {result.opportunity_count} 条机会的报告。")
            for name, path in result.files.items():
                st.write(f"- **{name}**：`{path}`")
        except Exception as exc:  # noqa: BLE001
            st.error(f"导出失败：{exc}")
    st.caption("报告生成时间 ≠ 公告发布日期；请核对证据字段。")


if __name__ == "__main__":
    main()
