;; ========================================================================
;; ========================================================================
;; ========================================================================
;; NEST JS IMPLEMENTATION
;; ========================================================================
;; ========================================================================
;; ========================================================================

;; ========================================================================
;; 1. EXPORTED CONTROLLERS (Absolute Parent)
;; ========================================================================
(export_statement
  ;; 1A. Enforce that the class has a @Controller decorator
  (decorator
    (call_expression 
      function: (identifier) @class_decorator_name (#eq? @class_decorator_name "Controller")
      ;; 1B. Capture ANY argument type: (), ('users'), (['users']), or ({ path: '...' })
      arguments: (arguments 
        [(string) (array) (object)] @class_decorator_path
      )?
    )
  ) @class_decorator
  
  ;; 1C. Enter the class declaration
  declaration: (class_declaration
    name: (type_identifier) @class_name
    
    ;; 1D. Search the body ONLY for REST endpoints
    body: (class_body
      [
        ;; --- STANDARD METHODS ---
        (
          (decorator
            (call_expression
              function: (identifier) @decorator_type
              (#match? @decorator_type "^(Get|Post|Put|Delete|Patch|Options|Head|All)$")
              arguments: (arguments [(string) (array)] @decorator_path)?
            )
          )
          (decorator)* ;; Magic Bridge for sandwiched decorators (e.g., @HttpCode)
          .
          (method_definition
            name: (property_identifier) @method_name
            body: (statement_block) @method_definition
          )
        )
        
        ;; --- ARROW FUNCTIONS (Public Fields) ---
        (
          (decorator
            (call_expression
              function: (identifier) @decorator_type
              (#match? @decorator_type "^(Get|Post|Put|Delete|Patch|Options|Head|All)$")
              arguments: (arguments [(string) (array)] @decorator_path)?
            )
          )
          (decorator)* ;; Magic Bridge
          .
          (public_field_definition
            name: (property_identifier) @method_name
            value: (arrow_function) @method_definition
          )
        )
      ]
    )
  )
) @class_node


;; ========================================================================
;; 2. NON-EXPORTED CONTROLLERS (Absolute Parent)
;; ========================================================================
(class_declaration
  ;; 2A. Enforce that the class has a @Controller decorator
  (decorator
    (call_expression 
      function: (identifier) @class_decorator_name (#eq? @class_decorator_name "Controller")
      ;; 2B. Capture ANY argument type
      arguments: (arguments 
        [(string) (array) (object)] @class_decorator_path
      )?
    )
  ) @class_decorator
  
  name: (type_identifier) @class_name
  
  ;; 2C. Search the body ONLY for REST endpoints
  body: (class_body
    [
      ;; --- STANDARD METHODS ---
      (
        (decorator
          (call_expression
            function: (identifier) @decorator_type
            (#match? @decorator_type "^(Get|Post|Put|Delete|Patch|Options|Head|All)$")
            arguments: (arguments [(string) (array)] @decorator_path)?
          )
        )
        (decorator)* ;; Magic Bridge
        .
        (method_definition
          name: (property_identifier) @method_name
          body: (statement_block) @method_definition
        )
      )
      
      ;; --- ARROW FUNCTIONS (Public Fields) ---
      (
        (decorator
          (call_expression
            function: (identifier) @decorator_type
            (#match? @decorator_type "^(Get|Post|Put|Delete|Patch|Options|Head|All)$")
            arguments: (arguments [(string) (array)] @decorator_path)?
          )
        )
        (decorator)* ;; Magic Bridge
        .
        (public_field_definition
          name: (property_identifier) @method_name
          value: (arrow_function) @method_definition
        )
      )
    ]
  )
) @class_node

