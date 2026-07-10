# Azure Event Hubs: Infrastructure as Code

Companion to `../SKILL.md`. Bicep and Terraform provisioning examples.

## Bicep
```bicep
resource ehNamespace 'Microsoft.EventHub/namespaces@2024-01-01' = {
  name: 'myNamespace'
  location: resourceGroup().location
  sku: { name: 'Standard', tier: 'Standard', capacity: 1 }
}

resource eventHub 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = {
  parent: ehNamespace
  name: 'myHub'
  properties: { partitionCount: 4, messageRetentionInDays: 7 }
}
```

## Terraform
```hcl
resource "azurerm_eventhub_namespace" "eh" {
  name                = "myNamespace"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "Standard"
  capacity            = 1
}

resource "azurerm_eventhub" "hub" {
  name                = "myHub"
  namespace_name      = azurerm_eventhub_namespace.eh.name
  resource_group_name = azurerm_resource_group.rg.name
  partition_count     = 4
  message_retention   = 7
}
```
