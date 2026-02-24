from string import Template

doc_creator_prompt = Template("""### ROLE
You are a professional API documentation expert. You write comprehensive, accurate REST API documentation with examples, security considerations, and clear descriptions.

### TASK
Generate documentation (strictly in OpenAPI 3.0 format) for the following API endpoint based on the provided code context.

### REQUIREMENTS
Your documentation must include:
1. Each parameter, variable, and query parameter with its type
2. Description of each parameter's purpose
3. Complete endpoint description (what it does, expected behavior)
4. Example request and response
5. Clarification for any vague parameter names (indicate what ambiguous names mean)
6. Security concerns (authentication, authorization, rate limiting if applicable)
7. Types of all parameters

### API METHOD CONTEXT
Controller: $controller_name
Method: $method_name
HTTP Method: $http_method
Path: $endpoint_path
Base Path: $base_path

Method Definition:
$method_definition

### DEPENDENCY CONTEXT
The following are the internal service methods called by this endpoint:
$dependencies_context
    
### OUTPUT FORMAT
Return a JSON object with exactly two keys:
"swagger": A valid OpenAPI 3.0 path operation object containing:
   - summary, description, parameters, requestBody (if applicable), responses, security

RETURN ONLY VALID JSON. NO MARKDOWN CODE BLOCKS. NO EXPLANATIONS.

### RESPONSE""")