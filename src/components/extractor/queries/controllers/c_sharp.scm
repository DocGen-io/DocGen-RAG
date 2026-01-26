; C# Controller and Service Query
(compilation_unit
  (namespace_declaration
    (declaration_list
      (class_declaration
        (attribute_list
          (attribute
            name: (identifier) @class_attr
            (attribute_argument_list
              (attribute_argument
                (string_literal) @base_path
              )
            )?
          )
        )*
        name: (identifier) @class_name
        (base_list
             (identifier) @superclass
        )?
        body: (declaration_list
          (method_declaration
            (attribute_list
              (attribute
                name: (identifier) @method_attr
                (attribute_argument_list
                  (attribute_argument
                    (string_literal) @method_path
                  )
                )?
              )
            )*
            name: (identifier) @method_name
          ) @method_definition
        )
      ) @class_definition
    )
  )
)
