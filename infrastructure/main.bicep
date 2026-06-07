@description('Environment name (dev, staging, prod)')
param environment string = 'dev'

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Prefix for all resource names')
param prefix string = 'hcsc'

var suffix = '${prefix}-${environment}'

module openai 'modules/openai.bicep' = {
  name: 'openai'
  params: {
    name: '${suffix}-oai'
    location: location
    deploymentName: 'gpt-4.1'
  }
}

module aiSearch 'modules/ai_search.bicep' = {
  name: 'aiSearch'
  params: {
    name: '${suffix}-search'
    location: location
  }
}

module fhir 'modules/fhir.bicep' = {
  name: 'fhir'
  params: {
    workspaceName: '${suffix}-health'
    fhirServiceName: 'fhir'
    location: location
  }
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyVault'
  params: {
    name: '${suffix}-kv'
    location: location
  }
}

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    workspaceName: '${suffix}-logs'
    appInsightsName: '${suffix}-appi'
    location: location
  }
}

module apim 'modules/apim.bicep' = {
  name: 'apim'
  params: {
    name: '${suffix}-apim'
    location: location
    publisherEmail: 'admin@hcsc.example.com'
    publisherName: 'HCSC Admin'
    appInsightsId: monitoring.outputs.appInsightsId
    appInsightsKey: monitoring.outputs.appInsightsKey
  }
}

output openAiEndpoint string = openai.outputs.endpoint
output searchEndpoint string = aiSearch.outputs.endpoint
output fhirEndpoint string = fhir.outputs.fhirEndpoint
output keyVaultUri string = keyVault.outputs.uri
output apimGatewayUrl string = apim.outputs.gatewayUrl
