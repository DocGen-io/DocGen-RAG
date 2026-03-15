from string import Template

# System prompt: static rules
fetch_example_system_prompt = """You generate code examples to call REST API endpoints. Use ONLY the provided specification — do NOT invent parameters, URLs, headers, or request body fields.

If uncertain about a value, use a placeholder like "<YOUR_VALUE>" and note it.

Return a JSON object with keys: "javascript" (fetch API), "python" (requests lib), "curl". Each value is a complete, ready-to-run code string.

RETURN ONLY VALID JSON. NO MARKDOWN."""

# User prompt: dynamic endpoint data
fetch_example_user_prompt = Template("""Endpoint: $http_method $endpoint_path
Summary: $summary
Parameters: $parameters
Request Body: $request_body""")
