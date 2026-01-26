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

;; 2. Match Methods with optional decorators
(class_body
  (decorator
    (call_expression
      function: (identifier) @method_decorator_name
      arguments: (arguments (string) @method_decorator_path)?
    )
  )? @method_decorator
  .
  (method_definition
    name: (property_identifier) @method_name
  ) @method_definition
)