(class_declaration
  (attribute_list
    (attribute
      name: (identifier) @class_decorator_type
      (attribute_argument_list 
        (attribute_argument 
          (string_literal) @class_decorator_path
        )
      )?
    )
  )* @class_decorator
  name: (identifier) @class_name
) @class_node

(method_declaration
  (attribute_list
    (attribute
      name: (identifier) @decorator_type
      (attribute_argument_list 
        (attribute_argument 
          (string_literal) @decorator_path
        )
      )?
    )
  ) @method_decorator
  name: (identifier) @method_name
) @method_definition

(method_declaration
  name: (identifier) @method_name
) @method_definition

(interface_declaration
  name: (identifier) @interface_name
) @interface_definition