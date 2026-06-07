param workspaceName string
param fhirServiceName string
param location string

resource healthWorkspace 'Microsoft.HealthcareApis/workspaces@2023-11-01' = {
  name: workspaceName
  location: location
  properties: {}
}

resource fhirService 'Microsoft.HealthcareApis/workspaces/fhirservices@2023-11-01' = {
  parent: healthWorkspace
  name: fhirServiceName
  location: location
  kind: 'fhir-R4'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    authenticationConfiguration: {
      authority: 'https://login.microsoftonline.com/${subscription().tenantId}'
      audience: 'https://healthcareapis.azure.com'
      smartProxyEnabled: false
    }
    corsConfiguration: {
      allowCredentials: false
      headers: []
      methods: []
      origins: []
      maxAge: 0
    }
  }
}

output fhirEndpoint string = 'https://${workspaceName}-${fhirServiceName}.fhir.azurehealthcareapis.com'
output fhirServiceId string = fhirService.id
