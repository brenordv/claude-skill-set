# Azure SQL: Partitioning, Temporal Tables, JSON

Companion to `azure-sql-server/SKILL.md` (Query Optimization).

## Partitioning

```sql
-- Create partition function and scheme
CREATE PARTITION FUNCTION pf_OrderDate (DATETIMEOFFSET)
AS RANGE RIGHT FOR VALUES ('2024-01-01', '2025-01-01', '2026-01-01');

CREATE PARTITION SCHEME ps_OrderDate
AS PARTITION pf_OrderDate ALL TO ([PRIMARY]);

-- Create partitioned table
CREATE TABLE dbo.Orders (
    OrderId BIGINT IDENTITY PRIMARY KEY NONCLUSTERED,
    OrderDate DATETIMEOFFSET NOT NULL,
    CustomerId INT NOT NULL,
    TotalAmount DECIMAL(12,2) NOT NULL
) ON ps_OrderDate(OrderDate);

-- Clustered index on partition key for partition elimination
CREATE CLUSTERED INDEX CIX_Orders_OrderDate ON dbo.Orders(OrderDate)
ON ps_OrderDate(OrderDate);
```

## Temporal Tables

```sql
CREATE TABLE dbo.Products (
    ProductId INT PRIMARY KEY,
    Name NVARCHAR(100) NOT NULL,
    Price DECIMAL(10,2) NOT NULL,
    ValidFrom DATETIME2 GENERATED ALWAYS AS ROW START NOT NULL,
    ValidTo DATETIME2 GENERATED ALWAYS AS ROW END NOT NULL,
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = dbo.ProductsHistory));

-- Query historical data
SELECT * FROM dbo.Products FOR SYSTEM_TIME AS OF '2025-06-15T00:00:00';
SELECT * FROM dbo.Products FOR SYSTEM_TIME BETWEEN '2025-01-01' AND '2025-12-31';
```

## JSON Support

```sql
-- Store and query JSON
SELECT OrderId, JSON_VALUE(Metadata, '$.source') AS Source,
    JSON_QUERY(Metadata, '$.items') AS Items
FROM dbo.Orders
WHERE ISJSON(Metadata) = 1
  AND JSON_VALUE(Metadata, '$.priority') = 'high';

-- Computed column for indexing JSON properties
ALTER TABLE dbo.Orders
ADD Source AS JSON_VALUE(Metadata, '$.source');

CREATE INDEX IX_Orders_Source ON dbo.Orders(Source);

-- OPENJSON for shredding JSON arrays
SELECT o.OrderId, item.ProductName, item.Quantity
FROM dbo.Orders o
CROSS APPLY OPENJSON(o.Metadata, '$.items')
    WITH (ProductName NVARCHAR(100), Quantity INT) AS item;
```
