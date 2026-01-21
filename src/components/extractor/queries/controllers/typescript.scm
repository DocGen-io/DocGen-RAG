; TypeScript Controller Query (NestJS)

(import_statement) @import_statement

(export_statement
  (decorator
    (call_expression
      function: (identifier) @decorator_name
      (#eq? @decorator_name "Controller")
      arguments: (arguments 
        (string (string_fragment) @base_path)
      )?
    )
  )
  (class_declaration
    name: (type_identifier) @class_name
    body: (class_body
      (method_definition
        (decorator
          (call_expression
            function: (identifier) @method_decorator
            arguments: (arguments 
              (string (string_fragment) @method_path)?
            )?
          )
        )?
        name: (property_identifier) @method_name
        body: (statement_block) @method_body
      ) @method_definition
    )
  ) @class_definition
)
