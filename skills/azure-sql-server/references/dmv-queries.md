# Azure SQL: Dynamic Management View (DMV) Diagnostic Queries

Companion to `azure-sql-server/SKILL.md` (Monitoring and Diagnostics).

```sql
-- Top resource-consuming queries
SELECT TOP 20
    qs.total_worker_time / qs.execution_count AS avg_cpu_us,
    qs.total_logical_reads / qs.execution_count AS avg_reads,
    qs.execution_count,
    SUBSTRING(st.text, (qs.statement_start_offset/2)+1,
        ((CASE qs.statement_end_offset WHEN -1 THEN DATALENGTH(st.text)
          ELSE qs.statement_end_offset END - qs.statement_start_offset)/2)+1) AS query_text
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
ORDER BY avg_cpu_us DESC;

-- Active sessions and blocking
SELECT r.session_id, r.blocking_session_id, r.wait_type, r.wait_time,
    r.cpu_time, r.logical_reads, t.text AS query_text
FROM sys.dm_exec_requests r
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t
WHERE r.session_id > 50;

-- Index usage stats (find unused indexes)
SELECT OBJECT_NAME(i.object_id) AS TableName, i.name AS IndexName,
    ius.user_seeks, ius.user_scans, ius.user_lookups, ius.user_updates
FROM sys.dm_db_index_usage_stats ius
INNER JOIN sys.indexes i ON ius.object_id = i.object_id AND ius.index_id = i.index_id
WHERE OBJECTPROPERTY(i.object_id, 'IsUserTable') = 1
ORDER BY ius.user_seeks + ius.user_scans + ius.user_lookups ASC;

-- Missing index recommendations
SELECT TOP 20
    mid.statement AS TableName,
    mid.equality_columns, mid.inequality_columns, mid.included_columns,
    migs.avg_user_impact, migs.user_seeks
FROM sys.dm_db_missing_index_details mid
INNER JOIN sys.dm_db_missing_index_groups mig ON mid.index_handle = mig.index_handle
INNER JOIN sys.dm_db_missing_index_group_stats migs ON mig.index_group_handle = migs.group_handle
ORDER BY migs.avg_user_impact * migs.user_seeks DESC;
```
