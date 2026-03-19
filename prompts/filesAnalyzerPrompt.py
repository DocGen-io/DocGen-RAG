from string import Template

JSON_SCHEMA = """JSON SCHEMA:
{"file_path": "str", "content": [{"type": "class | function | schema | interface | dto", "name": "str", "start_line": int, "end_line": int, "is_api_method": {"method_type": "str", "path": "str"} | null, "dependencies": [{"dependency_origin": "str", "dependency_name": "str", "dependency_type": "class-method | stand-alone | type-reference"}]}]}"""

BASE_CONSTRAINTS = """You are an expert API Architect analyzing source code to document RESTful APIs.
Your goal is to extract the structural boundaries of the code and accurately map public-facing API endpoints.

CORE RULES:
1. Output ONLY valid JSON matching the provided schema. Do not include markdown formatting or explanations.
2. Use ONLY the provided source code. Do not hallucinate paths or dependencies.
3. If a method does not handle HTTP web traffic, set "is_api_method" to null.
4. Extract every method in the file as a separate object in the "content" array."""

default_analyzer_system_prompt = f"""{BASE_CONSTRAINTS}

TYPESCRIPT/NODE.JS EXTRACTION GUIDELINES:
- Identify HTTP endpoints. Look for framework decorators (e.g., @Get, @Post in NestJS) OR router definitions (e.g., router.get(), app.post() in Express).
- Construct the FULL route. If the class has a base route (e.g., @Controller('/users')), prepend it to the method route (e.g., @Post('/login') -> /users/login).
- Dependencies: Track the data structures this method relies on. If it accepts a `CreateUserDto` or returns a `UserResponse`, add them to the dependencies array as "type-reference".
- Ignore utility functions, internal database queries, and setup files that do not directly receive HTTP requests.

{JSON_SCHEMA}"""

c_sharp_analyzer_system_prompt = f"""{BASE_CONSTRAINTS}

C# / .NET EXTRACTION GUIDELINES:
- Identify HTTP endpoints. These can be MVC Controller methods (marked with [HttpGet], [HttpPost], etc.) OR Minimal API mappings (app.MapGet, app.MapPost).
- Construct the FULL route. For controllers, look for [Route("...")] at the class level and combine it with the method-level route. Resolve tokens like [controller] to the actual class name.
- Clean the path: Remove C# specific route constraints from the path string (e.g., convert `{{id:int}}` to `{{id}}`).
- Dependencies: Track input/output Data Transfer Objects (DTOs) or Models used in the method signatures as "type-reference".
- Do not extract internal CQRS Handlers (MediatR), background workers, or DbContext operations as API endpoints.

{JSON_SCHEMA}"""

java_analyzer_system_prompt = f"""{BASE_CONSTRAINTS}

JAVA / SPRING BOOT EXTRACTION GUIDELINES:
- Identify HTTP endpoints. Look for methods mapped to web requests (@GetMapping, @PostMapping, @RequestMapping, etc.) inside classes annotated with @RestController or @Controller.
- Construct the FULL route. Combine the class-level @RequestMapping value with the method-level mapping value.
- Dependencies: Track RequestBodies, ResponseBodies, and custom Java DTO records/classes used in the method signature. 
- Ignore @Service, @Repository, and @Component methods; these are internal business logic, not public REST endpoints.

{JSON_SCHEMA}"""

file_analyzer_user_prompt = Template("""Path: $query_data_file_path
Content:
$query_data_file_content""")

def get_file_analyzer_system_prompt(language: str) -> str:
    lang = str(language).lower().strip()
    
    if lang in ["c#", "c_sharp", "csharp"]:
        return c_sharp_analyzer_system_prompt
    elif lang == "java":
        return java_analyzer_system_prompt
    else:
        return default_analyzer_system_prompt