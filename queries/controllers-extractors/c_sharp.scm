;; ========================================================================
;; C# .NET IMPLEMENTATION (Standardized Variables)
;; ========================================================================

;; ========================================================================
;; PATTERN 1: Class uses INHERITANCE (e.g., : ApiController)
;; ========================================================================
(class_declaration
  ;; 1. Find the class name
  name: (identifier) @class_name
  
  ;; 2. Look AFTER the name for the base class
  (base_list
    [
      (identifier) @class_decorator_type
      (generic_name (identifier) @class_decorator_type)
      (qualified_name name: (identifier) @class_decorator_type)
    ]
    (#match? @class_decorator_type "Controller")
  )

  ;; 3. Extract the methods inside
  body: (declaration_list
    (method_declaration
      (attribute_list
        (attribute
          name: (identifier) @decorator_type
          (#match? @decorator_type "^(HttpGet|HttpPost|HttpPut|HttpDelete|HttpPatch|HttpOptions|HttpHead|Route)$")
          
          (attribute_argument_list
            (attribute_argument
              [
                (string_literal) @decorator_path
                (identifier) @decorator_path
                (member_access_expression) @decorator_path
              ]
            )
          )?
        )
      )
      name: (identifier) @method_name
    ) @method_definition
  )
) @class_node

;; ========================================================================
;; PATTERN 2: Class uses ATTRIBUTES (e.g., [ApiController])
;; ========================================================================
(class_declaration
  ;; 1. Look BEFORE the name for the attribute
  (attribute_list
    (attribute
      name: (identifier) @class_decorator_type
      (#match? @class_decorator_type "^(ApiController|Route|Controller)$")
    )
  )
  
  ;; 2. Find the class name
  name: (identifier) @class_name

  ;; 3. Extract the methods inside
  body: (declaration_list
    (method_declaration
      (attribute_list
        (attribute
          name: (identifier) @decorator_type
          (#match? @decorator_type "^(HttpGet|HttpPost|HttpPut|HttpDelete|HttpPatch|HttpOptions|HttpHead|Route)$")
          
          (attribute_argument_list
            (attribute_argument
              [
                (string_literal) @decorator_path
                (identifier) @decorator_path
                (member_access_expression) @decorator_path
              ]
            )
          )?
        )
      )
      name: (identifier) @method_name
    ) @method_definition
  )
) @class_node

;; ========================================================================
;; PATTERN 3: Class-Level Base Route Extraction
;; ========================================================================
(class_declaration
  (attribute_list
    (attribute
      name: (identifier) @class_decorator_type
      (#eq? @class_decorator_type "Route")
      (attribute_argument_list
        (attribute_argument
          [
            (string_literal) @class_decorator_path
            (member_access_expression) @class_decorator_path
            (identifier) @class_decorator_path
          ]
        )
      )
    )
  )
  name: (identifier) @class_name
) @class_node