(class_declaration
  (modifiers
    [
      (marker_annotation
        name: (identifier) @class_decorator_type
      )
      (annotation
        name: (identifier) @class_decorator_type
        arguments: (annotation_argument_list (string_literal) @class_decorator_path)?
      )
    ]
  )? @class_decorator
  name: (identifier) @class_name
) @class_definition

(method_declaration
  (modifiers
    [
      (marker_annotation
        name: (identifier) @decorator_type
      )
      (annotation
        name: (identifier) @decorator_type
        arguments: (annotation_argument_list (string_literal) @decorator_path)?
      )
    ]
  ) @method_decorator
  name: (identifier) @method_name
) @method_definition

(method_declaration
  name: (identifier) @method_name
) @method_definition

(interface_declaration
  name: (identifier) @interface_name
) @interface_definition


(record_declaration (identifier)@record_name)@record_definition