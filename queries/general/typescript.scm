(export_statement
  (decorator
    (call_expression 
      function: (identifier) @class_decorator_name
      arguments: (arguments (string) @class_decorator_path)?
    )
  )? @class_decorator
  declaration: (class_declaration
    name: (type_identifier) @class_name
    [
    (class_body
      (method_definition
        name: (property_identifier) @method_name
      ) @method_definition
    )
    

    (class_body
      (decorator
        (call_expression
          function: (identifier) @decorator_name
          arguments: (arguments (string) @decorator_path)?
        )
      ) @arrow_method_decorator
      .
      (public_field_definition
        name: (property_identifier) @method_name
        value: (arrow_function)
      ) @method_definition
    )

	(class_body
        (decorator
          (call_expression
            function: (identifier) @decorator_name
            arguments: (arguments (string) @decorator_path)?
          )
        ) @method_decorator
        .
        (method_definition
          name: (property_identifier) @method_name
        ) @method_definition
      )

		(class_body
          (public_field_definition
            name: (property_identifier) @method_name
            value: (arrow_function)
          ) @method_definition
    	)


    ]
    
  ) @class_node
)





(lexical_declaration
  (variable_declarator
    name: (identifier) @method_name
    (_)*
    (arrow_function) @method_definition
  )
)

(function_declaration (identifier)@method_name)@method_definition

(interface_declaration (type_identifier)@interface_name)@interface_definition
