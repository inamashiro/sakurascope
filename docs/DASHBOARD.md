# Streamlit Dashboard (Phase 5)

## Start

```powershell
python -m sakurascope dashboard
# or
python -m sakurascope dashboard --port 8501
```

Optional: `SAKURASCOPE_CONFIG_PATH` points the UI at a specific settings YAML.

## Pages

1. 总览  
2. 研究机会列表  
3. 大学与研究室（由机会候选项汇总，不编造校名）  
4. 机会详情与证据  
5. 页面变化记录  
6. 采集运行日志  
7. 来源管理（配置 YAML 只读 + DB 状态）  
8. 导出报告  

Sidebar filters: research area, degree, review status, admission language, deadlines, recent discovery, keyword.

## Design notes

- Chinese-first labels; original JA/EN field values preserved  
- Topic relevance is never shown as admission odds  
- Empty database is an honest empty state, not fake sample schools  
