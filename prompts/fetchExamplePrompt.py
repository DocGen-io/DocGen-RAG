from string import Template

# System prompt: static rules
fetch_example_system_prompt = """You generate code examples to call REST API endpoints. Use ONLY the provided specification — do NOT invent parameters, URLs, headers, or request body fields.

If uncertain about a value, use a placeholder like "<YOUR_VALUE>" and note it.
Return a list of code examples (Latest) in the following format :
[
    {
        "framework": "<framework>",
        "code": "<code_string>"
    }
]

I want you to output the following languages
1- Python (requests)
2- JavaScript (fetch)
3- cURL
4- C# (.NET)
5- Java (OkHttp)
6- Go (net/http)

"""

# User prompt: dynamic endpoint data
fetch_example_user_prompt = Template("""Endpoint: $http_method $endpoint_path
Summary: $summary
Parameters: $parameters
Request Body: $request_body""")
