{
  "scriptFile": "main.py",
  "entryPoint": "run",
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