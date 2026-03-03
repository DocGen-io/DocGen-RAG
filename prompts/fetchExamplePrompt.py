from string import Template

fetch_example_prompt = Template("""Generate code examples to call this API endpoint. Use all variables, query params, headers, and request body from the specification.

Endpoint: $http_method $endpoint_path
Summary: $summary
Parameters: $parameters
Request Body: $request_body

Return a JSON object with keys: "javascript" (fetch API), "python" (requests lib), "curl". Each value is a complete, ready-to-run code string.

RETURN ONLY VALID JSON. NO MARKDOWN CODE BLOCKS.

### RESPONSE""")
