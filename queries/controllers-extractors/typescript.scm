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
      function: (identifier) @class_decorator_type (#eq? @class_decorator_type "Controller")
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
      function: (identifier) @class_decorator_type (#eq? @class_decorator_type "Controller")
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




;; ========================================================================
;; EXPRESS JS CONTROLLER / ROUTER IMPLEMENTATION
;; ========================================================================

;; 1. STANDARD ROUTING (e.g., router.post('/path', handler))
(call_expression
  function: (member_expression
    object: [(identifier) (member_expression)]
    property: (property_identifier) @http_method
    (#match? @http_method "^(get|post|put|delete|patch|options|head|all)$")
  )
  arguments: (arguments
    [(string) (template_string)] @route_path
    (_)*
    [(arrow_function) (function_expression) (identifier) (member_expression)] @route_handler
  )
) @route_definition

;; ========================================================================
;; 2. CHAINED ROUTING (router.route('/path').get().put().patch().delete())
;; Unrolled up to 5 levels of depth to capture full REST implementations.
;; ========================================================================

;; --- DEPTH 1 ---
(call_expression
  function: (member_expression
    object: (call_expression function: (member_expression property: (property_identifier) @r1 (#eq? @r1 "route")) arguments: (arguments [(string) (template_string)] @route_path))
    property: (property_identifier) @http_method (#match? @http_method "^(get|post|put|delete|patch|options|head|all)$")
  )
  arguments: (arguments (_)* [(arrow_function) (function_expression) (identifier) (member_expression)] @route_handler)
) @route_definition

;; --- DEPTH 2 ---
(call_expression
  function: (member_expression
    object: (call_expression function: (member_expression object: (call_expression function: (member_expression property: (property_identifier) @r2 (#eq? @r2 "route")) arguments: (arguments [(string) (template_string)] @route_path))))
    property: (property_identifier) @http_method (#match? @http_method "^(get|post|put|delete|patch|options|head|all)$")
  )
  arguments: (arguments (_)* [(arrow_function) (function_expression) (identifier) (member_expression)] @route_handler)
) @route_definition

;; --- DEPTH 3 ---
(call_expression
  function: (member_expression
    object: (call_expression function: (member_expression object: (call_expression function: (member_expression object: (call_expression function: (member_expression property: (property_identifier) @r3 (#eq? @r3 "route")) arguments: (arguments [(string) (template_string)] @route_path))))))
    property: (property_identifier) @http_method (#match? @http_method "^(get|post|put|delete|patch|options|head|all)$")
  )
  arguments: (arguments (_)* [(arrow_function) (function_expression) (identifier) (member_expression)] @route_handler)
) @route_definition

;; --- DEPTH 4 (Captures the .delete in your example) ---
(call_expression
  function: (member_expression
    object: (call_expression function: (member_expression object: (call_expression function: (member_expression object: (call_expression function: (member_expression object: (call_expression function: (member_expression property: (property_identifier) @r4 (#eq? @r4 "route")) arguments: (arguments [(string) (template_string)] @route_path))))))))
    property: (property_identifier) @http_method (#match? @http_method "^(get|post|put|delete|patch|options|head|all)$")
  )
  arguments: (arguments (_)* [(arrow_function) (function_expression) (identifier) (member_expression)] @route_handler)
) @route_definition

;; --- DEPTH 5 ---
(call_expression
  function: (member_expression
    object: (call_expression function: (member_expression object: (call_expression function: (member_expression object: (call_expression function: (member_expression object: (call_expression function: (member_expression object: (call_expression function: (member_expression property: (property_identifier) @r5 (#eq? @r5 "route")) arguments: (arguments [(string) (template_string)] @route_path))))))))))
    property: (property_identifier) @http_method (#match? @http_method "^(get|post|put|delete|patch|options|head|all)$")
  )
  arguments: (arguments (_)* [(arrow_function) (function_expression) (identifier) (member_expression)] @route_handler)
) @route_definition