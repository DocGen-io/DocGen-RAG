;; 1a. Class Methods WITH Decorators
(class_declaration
  name: (type_identifier)? @class_name
  body: (class_body
    (decorator
      [
        (identifier) @decorator_type
        (call_expression
          function: (identifier) @decorator_type
          arguments: (arguments)? @decorator_path
        )
      ]
    ) @method_decorator
    .
    (method_definition
      name: (property_identifier) @method_name
    ) @method_definition
  )
)

;; 1b. Class Methods WITHOUT Decorators
;; (This will catch your `findAll()` method)
(class_declaration
  name: (type_identifier)? @class_name
  body: (class_body
    (method_definition
      name: (property_identifier) @method_name
    ) @method_definition
  )
)

;; 2a. Arrow Function Properties WITH Decorators
(class_declaration
  name: (type_identifier)? @class_name
  body: (class_body
    (decorator
      [
        (identifier) @decorator_type
        (call_expression
          function: (identifier) @decorator_type
          arguments: (arguments)? @decorator_path
        )
      ]
    ) @arrow_method_decorator
    .
    (public_field_definition
      name: (property_identifier) @method_name
      value: (arrow_function)
    ) @method_definition
  )
)

;; 2b. Arrow Function Properties WITHOUT Decorators
;; (This will catch your `findOne = (id: string) => {...}` method)
(class_declaration
  name: (type_identifier)? @class_name
  body: (class_body
    (public_field_definition
      name: (property_identifier) @method_name
      value: (arrow_function)
    ) @method_definition
  )
)

;; 3. Class-based DTOs / Data Models
[
  (export_statement
    declaration: (class_declaration
      name: (type_identifier) @interface_name
      (#match? @interface_name "(Dto|Response|Request|Entity|Model|Input|Args)$")
    )
  ) @interface_definition

  (class_declaration
    name: (type_identifier) @interface_name
    (#match? @interface_name "(Dto|Response|Request|Entity|Model|Input|Args)$")
  ) @interface_definition
]

;; 4. Standalone Arrow Functions
[
  (export_statement 
    declaration: (lexical_declaration
      (variable_declarator
        name: (identifier) @method_name
        value: (arrow_function)
      )
    ) 
  ) @method_definition
  
  (lexical_declaration
    (variable_declarator
      name: (identifier) @method_name
      value: (arrow_function)
    )
  ) @method_definition
]

;; 5. Standalone Function Declarations
[
  (export_statement 
    declaration: (function_declaration 
      name: (identifier) @method_name
    ) 
  ) @method_definition
  
  (function_declaration 
    name: (identifier) @method_name
  ) @method_definition
]

;; 6. Interfaces
[
  (export_statement 
    declaration: (interface_declaration 
      name: (type_identifier) @interface_name
    ) 
  ) @interface_definition

  (interface_declaration 
    name: (type_identifier) @interface_name
  ) @interface_definition
]

;; 7. Type Aliases
[
  (export_statement 
    declaration: (type_alias_declaration 
      name: (type_identifier) @interface_name
    ) 
  ) @interface_definition

  (type_alias_declaration 
    name: (type_identifier) @interface_name
  ) @interface_definition
]