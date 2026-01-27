;; 1. Match Classes with optional decorators (Handles Controller/Service/Utility)
(
  (export_statement
    (decorator
      (call_expression 
        function: (identifier) @class_decorator_name
        arguments: (arguments (string) @class_decorator_path)?
      )
    )? @class_decorator
    declaration: (class_declaration
      name: (type_identifier) @class_name
    ) @class_node
  )
)

;; 2. Match Methods WITH decorators (regular method_definition)
(class_body
  (decorator
    (call_expression
      function: (identifier) @method_decorator_name
      arguments: (arguments (string) @method_decorator_path)?
    )
  ) @method_decorator
  .
  (method_definition
    name: (property_identifier) @method_name
  ) @method_definition
)

;; 3. Match Methods WITHOUT decorators (regular method_definition)
(class_body
  (method_definition
    name: (property_identifier) @plain_method_name
  ) @plain_method_definition
)

;; 4. Match Arrow Function Methods WITH decorators (public_field_definition)
(class_body
  (decorator
    (call_expression
      function: (identifier) @arrow_method_decorator_name
      arguments: (arguments (string) @arrow_method_decorator_path)?
    )
  ) @arrow_method_decorator
  .
  (public_field_definition
    name: (property_identifier) @arrow_method_name
    value: (arrow_function)
  ) @arrow_method_definition
)

;; 5. Match Arrow Function Methods WITHOUT decorators (public_field_definition)
(class_body
  (public_field_definition
    name: (property_identifier) @plain_arrow_method_name
    value: (arrow_function)
  ) @plain_arrow_method_definition
)