"""Transparent keyword dictionaries for rule-based extraction."""

from __future__ import annotations

# Research areas: English canonical label → multilingual keywords.
RESEARCH_AREA_KEYWORDS: dict[str, list[str]] = {
    "Public Health": ["public health", "公衆衛生", "公共卫生", "kouishu eisei"],
    "Epidemiology": ["epidemiology", "疫学", "流行病学", "epidemiolog"],
    "Biostatistics": ["biostatistics", "生物統計", "生物统计", "biostat"],
    "Bioinformatics": ["bioinformatics", "バイオインフォマティクス", "生物信息", "bioinfo"],
    "Life Sciences": ["life sciences", "life science", "生命科学", "生命科學"],
    "Biomedical Data Science": [
        "biomedical data",
        "medical data science",
        "医学データ科学",
        "生物医学数据",
        "医学数据科学",
    ],
    "Medical AI": [
        "medical ai",
        "medical artificial intelligence",
        "医学ai",
        "医療ai",
        "医学人工智能",
        "医療人工知能",
    ],
    "Medical Engineering": [
        "medical engineering",
        "biomedical engineering",
        "医学工学",
        "医用工学",
        "生物医学工程",
    ],
    "Basic Medicine": ["basic medicine", "基礎医学", "基础医学"],
}

# Signals that a page may contain public admission information (NOT confirmed eligibility).
ADMISSION_KEYWORDS: list[str] = [
    "募集要項",
    "入学案内",
    "出願",
    "受験",
    "研究生",
    "出願期間",
    "募集期間",
    "admission",
    "admissions",
    "application guideline",
    "application guidelines",
    "call for applications",
    "how to apply",
    "eligibility",
    "招募",
    "招生",
    "报名",
    "申请资格",
    "申請資格",
    "国際学生",
    "international students",
    "留学生",
]

DEGREE_KEYWORDS: dict[str, list[str]] = {
    "doctoral": ["博士", "博士後期", "ph.d", "phd", "doctoral", "doctorate"],
    "master": ["修士", "博士前期", "master", "master's", "masters"],
    "research_student": ["研究生", "research student", "non-degree", "聴講"],
    "undergraduate": ["学部", "bachelor", "学部生"],
}

INSTITUTION_PATTERNS: list[str] = [
    r"([\u4e00-\u9fff\u3040-\u30ffA-Za-z0-9・ー\- ]{2,40}大学)",
    r"([\u4e00-\u9fff\u3040-\u30ffA-Za-z0-9・ー\- ]{2,40}大学院)",
    r"((?:The\s+)?University\s+of\s+[A-Z][A-Za-z\- ]+)",
    r"([A-Z][A-Za-z\- ]+ University)",
]

GRADUATE_SCHOOL_PATTERNS: list[str] = [
    r"((?:大学院)?[\u4e00-\u9fff\u3040-\u30ffA-Za-z0-9・ー\- ]{2,40}研究科)",
    r"(Graduate School of [A-Z][A-Za-z&\- ]+)",
    r"([\u4e00-\u9fff]{2,20}学院)",
]
