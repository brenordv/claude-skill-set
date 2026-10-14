# Azure Cosmos DB: Security

Companion to `../SKILL.md`. Identity, data-plane RBAC, key lockdown, and network access for the
NoSQL API.

## Data-Plane RBAC

Cosmos DB NoSQL has its own data-plane role system, separate from Azure RBAC. Control-plane roles
(Owner, Contributor) grant no data access, and data-plane assignments cannot be made through the
portal IAM blade; use `az cosmosdb sql role assignment create`, PowerShell, or ARM.
([Grant data-plane RBAC](https://learn.microsoft.com/azure/cosmos-db/nosql/security/how-to-grant-data-plane-role-based-access))

Built-in roles
([reference](https://learn.microsoft.com/azure/cosmos-db/reference-data-plane-security)):

| Role | ID | Grants |
|------|----|--------|
| Cosmos DB Built-in Data Reader | `00000000-0000-0000-0000-000000000001` | `readMetadata`, item point reads, queries, change feed |
| Cosmos DB Built-in Data Contributor | `00000000-0000-0000-0000-000000000002` | `readMetadata` plus all container and item operations |

Two gotchas from the same reference: every SDK connection needs the
`Microsoft.DocumentDB/databaseAccounts/readMetadata` action (the SDK reads account and partition
metadata at startup), and `notDataActions` is not supported; anything not explicitly allowed is
denied.

Scope assignments as narrowly as the workload allows: `/` (account), `/dbs/<database>`, or
`/dbs/<database>/colls/<container>`:

```bash
# Read-only app, scoped to one container
az cosmosdb sql role assignment create \
    --account-name <account> \
    --resource-group <resource-group> \
    --role-definition-id "00000000-0000-0000-0000-000000000001" \
    --principal-id <app-principal-id> \
    --scope "/dbs/<database>/colls/<container>"
```

Give each application, developer, and pipeline its own identity and the minimum role at the
narrowest scope. Custom role definitions can narrow further (for example query-only without point
reads) via `az cosmosdb sql role definition create`.

## Managed Identity

Authenticate applications with Microsoft Entra ID instead of keys. `DefaultAzureCredential` keeps
one code path from local development to production; in deployed environments, configure it so it
resolves the workload's managed identity deliberately rather than relying on whatever the
credential chain falls back to. Per-language client setup is in each language reference.

## Disable Key-Based Auth

With RBAC in place, disable keys entirely so every caller must use Entra ID
([how-to](https://learn.microsoft.com/azure/cosmos-db/nosql/security/how-to-disable-key-based-authentication)):

```bash
az resource update \
    --resource-type "Microsoft.DocumentDB/databaseAccounts" \
    --resource-group <resource-group> \
    --name <account> \
    --set properties.disableLocalAuth=true
```

Bicep: set `disableLocalAuth: true` in the account properties. After this, key and resource-token
access fails; validate by attempting a key-based connection and expecting an error.

## Network Access

Prefer private endpoints or virtual-network rules, and restrict public access with the IP firewall
(`--ip-range-filter`, or `ipRules` in templates). Avoid the portal's "Accept connections from
within Azure datacenters" toggle (it adds `0.0.0.0` to the allowlist): the official guidance is
that it "configures the firewall to allow all requests from Azure, including requests from the
subscriptions of other customers", which largely defeats the firewall. Use it only when callers
genuinely have no static IP or subnet.
([Configure IP firewall](https://learn.microsoft.com/azure/cosmos-db/how-to-configure-firewall))

## Backup Posture

Use continuous backup for point-in-time restore (see "Backup and Restore" in `../SKILL.md`). One
caveat worth planning for: a restore always creates a new target account, and unless you pass
`--public-network-access Disabled` the restored account comes up reachable from the public network
regardless of the source account's settings.
([Restore with continuous backup](https://learn.microsoft.com/azure/cosmos-db/restore-account-continuous-backup))
