{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "type": "eventHubTrigger",
      "name": "event",
      "direction": "in",
      "eventHubName": "${eventHubName}",
      "connection": "${connection}",
      "cardinality": "many",
      "consumerGroup": "$Default"
    }
  ]
}