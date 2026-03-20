(class_declaration
  ;; ========================================================================
  ;; 1. CLASS LEVEL ANNOTATIONS & BASE PATH EXTRACTION
  ;; ========================================================================
  
  ;; A. Gatekeeper: Must have the [ApiController] attribute
  (attribute_list
    (attribute
      name: (identifier) @class_decorator_name
      (#match? @class_decorator_name "^(ApiController|Controller)$")
    )
  ) @class_decorator
  
  ;; B. Capture the class-level [Route] base path (Optional)
  (attribute_list
    (attribute
      name: (identifier) @class_mapping_name
      (#eq? @class_mapping_name "Route")
      (attribute_argument_list
        (attribute_argument
          [
            ;; Case 1: Direct string literal -> [Route("api/users")]
            (string_literal) @class_decorator_path
            
            ;; Case 2: Constants -> [Route(ApiRoutes.Base)]
            (member_access_expression) @class_decorator_path
            (identifier) @class_decorator_path
          ]
        )
      )
    )
  )? 
  
  ;; C. Extract Class Name
  name: (identifier) @class_name
  
  ;; ========================================================================
  ;; 2. METHOD EXTRACTION
  ;; ========================================================================
  
  ;; In C#, the class body is parsed as a 'declaration_list'
  body: (declaration_list
    (method_declaration
      ;; Search the method's attributes for routing
      (attribute_list
        (attribute
          ;; Extract 1: Decorator Type (e.g., HttpGet, HttpPost)
          name: (identifier) @decorator_type
          (#match? @decorator_type "^(HttpGet|HttpPost|HttpPut|HttpDelete|HttpPatch|HttpOptions|HttpHead|Route)$")
          
          ;; Extract 2: Decorator Path (Optional)
          (attribute_argument_list
            (attribute_argument
              [
                ;; Case A: Direct arguments -> [HttpPost("create")] or [HttpPatch(ApiRoutes.PatchStatus)]
                (string_literal) @decorator_path
                (member_access_expression) @decorator_path
                (identifier) @decorator_path
                
                ;; Case B: Property assignments -> [HttpPut(Template = "update/{id}")]
                ;; Matches AST: assignment_expression -> right
                (assignment_expression
                  right: [
                    (string_literal) @decorator_path
                    (member_access_expression) @decorator_path
                    (identifier) @decorator_path
                  ]
                )
              ]
            )
          )?
        )
      )
      
      ;; Extract 3: Method Name
      name: (identifier) @method_name
      
      ;; Extract 4: Method Definition
      ;; Alternation block to handle standard { } methods AND expression-bodied => methods
      [
        body: (block) @method_definition
        body: (arrow_expression_clause) @method_definition
      ]
      
    ) @method_node
  )
) @class_node