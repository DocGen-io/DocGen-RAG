; C# Controller Query
(compilation_unit
  (using_directive) @import_statement

  (namespace_declaration
    (declaration_list
      (class_declaration
        (attribute_list
          (attribute
            name: (identifier) @attr_name
            (attribute_argument_list
              (attribute_argument
                (string_literal) @base_path
              )
            )?
            (#eq? @attr_name "Route")
          )
        )
        name: (identifier) @class_name
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
            )
            name: (identifier) @method_name
          ) @method_definition
        )
      ) @class_definition
    )
  )
)
