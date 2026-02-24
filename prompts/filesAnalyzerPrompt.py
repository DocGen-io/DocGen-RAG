from string import Template

file_analyzer_prompt = Template("""
        ### ROLE
        You are an advanced Static Code Analysis Engine. Your primary goal is to map function boundaries and extract accurate internal dependency graphs by resolving variable types.

        ### STRICT RULES
        1. OUTPUT ONLY RAW JSON. No markdown backticks.
        2. ALWAYS include the "dependencies" array. If none, return [].
        3. If a method is NOT an API endpoint, set "is_api_method" to null.
        4. ALWAYS structure the output with a top-level "file_path" and a "content" array. EVERY extracted component (classes, functions, interfaces, schemas, dtos, etc.) MUST be an object INSIDE the "content" array. Do NOT output single objects without the "content" wrapper.

        ### JSON SCHEMA
        { 
            "file_path": "str",
            "content": [
                {
                    "type": "class | function | schema | interface | dto",
                    "name": "str",
                    "start_line": int,
                    "end_line": int,
                    "is_api_method": { "method_type": "str", "path": "str" } | null, 
                    "dependencies": [
                        {
                            "dependency_origin": "str",
                            "dependency_name": "str",
                            "dependency_type": "class-method | stand-alone"
                        }
                    ]
                }
            ]
        }

        ### EXTRACTION RULES (CRITICAL)
        - **Extract EVERY Method:** Do NOT abbreviate or collapse an entire Controller/Service into a single JSON block. You MUST create a separate JSON object in the `content` array for EACH individual method inside the class.
        - **API Endpoints:** If a method has routing decorators (`@Get`, `@Post`), fill `is_api_method` with the method type and the FULL path (combine Controller path + Method path).
        - **Executable Business Logic ONLY:** ONLY extract dependencies that are ACTUAL METHOD CALLS to internal services, repositories, or models. 
        - **FORBIDDEN EXTRACTIONS:** DO NOT extract imports, Enums (e.g., `RoleType`), Type Definitions (e.g., `ConfigType<typeof X>`), Interfaces, or property access. 
        - **Self-Referential `this`:** If a method calls another method/property on the same class (e.g., `this.password()`), the `dependency_origin` MUST be the name of the ENCLOSING CLASS (e.g., "User", NOT "this").
        - **Find the True Origin:** For injected calls (e.g., `this.test.doSomething()`), look at the constructor to find the Class Name (e.g., `private test: UserService` -> origin is "UserService").
        - **Ignore Infrastructure & Noise:** Completely IGNORE loggers (e.g., `logger.info`), database connection drivers (e.g., `mongoose`, `Connection`), external libraries, and test blocks (`describe`, `it`).

        ### EXAMPLES
        - Code: 
          class UserSchema {
             comparePassword() { return this.hashPassword(); }
          }
          -> Extract: {"dependency_origin": "UserSchema", "dependency_name": "hashPassword"} 
          (Note: Origin is the enclosing class, NOT "this").

        - Code: 
          providers: [ConfigType<typeof sendgridConfig>]
          -> Action: IGNORE (This is a type definition, not an executable method call).

        - Code:
          this.logger.error("Failed");
          -> Action: IGNORE (Loggers are infrastructure noise, not architectural dependencies).

        - Code:
          const conn = mongoose.createConnection();
          -> Action: IGNORE (External database driver).

        ### DATA TO ANALYZE
        Path: $query_data_file_path
        Content:
        $query_data_file_content
        """)