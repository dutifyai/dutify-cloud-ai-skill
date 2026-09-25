# Unified Dutify connector

Read [connector compatibility](hub/connector.md) for endpoint, credential, selection and naming rules; that reference is shared with the independently usable Hub skill.

For a new setup after the connector release:

```json
{
  "mcpServers": {
    "dutify": {
      "url": "https://mcp.dutify.ai/unified",
      "headers": { "X-API-Key": "<personal key from your secret source>" }
    }
  }
}
```

Use the client's supported secret substitution; the placeholder is not a credential. Leave workspace unset for discovery and pass it on data calls. Confirm `tools/list` includes `pm_get_task` and `hub_list_calls`.

Existing `/mcp` configurations retain URLs, keys and tool names. Do not change a working configuration unless requested.
