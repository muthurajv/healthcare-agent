param name string
param location string

resource search 'Microsoft.Search/searchServices@2023-11-01' = {
  name: name
  location: location
  sku: { name: 'standard' }
  properties: {
    replicaCount: 1
    partitionCount: 1
    publicNetworkAccess: 'disabled'
    semanticSearch: 'standard'
  }
}

output endpoint string = 'https://${name}.search.windows.net'
output id string = search.id
