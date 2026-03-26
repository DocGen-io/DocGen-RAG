(class_declaration
  ;; ========================================================================
  ;; 1. CLASS LEVEL ANNOTATIONS & BASE PATH EXTRACTION
  ;; ========================================================================
  (modifiers
    ;; A. Capture the class-level @RequestMapping if it exists to get the base path
    (annotation
      name: (identifier) @class_mapping_name
      (#eq? @class_mapping_name "RequestMapping")
      arguments: (annotation_argument_list
        [
          ;; Case 1: Direct string -> @RequestMapping("/api/users")
          (string_literal) @class_decorator_path
          
          ;; Case 2: Key-Value or Array -> @RequestMapping(path = {"/api/v1", "/api/v2"})
          (element_value_pair
            value: [
              (string_literal) @class_decorator_path
              (element_value_array_initializer) @class_decorator_path
            ]
          )
        ]
      )
    )? @class_decorator
  )
  
  ;; B. Extract Class Name
  name: (identifier) @class_name
  
  ;; ========================================================================
  ;; 2. METHOD EXTRACTION
  ;; ========================================================================
  body: (class_body
    (method_declaration
      (modifiers
        [
          ;; Case A: Method decorators WITHOUT arguments (e.g., @GetMapping)
          (marker_annotation
            name: (identifier) @decorator_type
            (#match? @decorator_type "^(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)$")
          )
          
          ;; Case B: Method decorators WITH arguments (e.g., @PostMapping("/create"))
          (annotation
            name: (identifier) @decorator_type
            (#match? @decorator_type "^(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)$")
            
            ;; Capture the path arguments
            arguments: (annotation_argument_list
              [
                (string_literal) @decorator_path
                (element_value_pair
                  value: [
                    (string_literal) @decorator_path
                    (element_value_array_initializer) @decorator_path
                  ]
                )
              ]
            )
          )
        ]
      )
      
      ;; Extract 3: Method Name
      name: (identifier) @method_name
      
      ;; Extract 4: Method Definition (Captures the block { ... })
      body: (block) @method_definition
      
    ) @method_node
  )
) @class_node