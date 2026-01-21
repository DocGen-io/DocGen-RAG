; Java Controller Query
(program
  (import_declaration) @import_statement

  (class_declaration
    (modifiers
      (annotation
        name: (identifier) @annotation_name
        arguments: (annotation_argument_list
          (string_literal) @base_path
        )?
        (#match? @annotation_name "Request(Mapping|Controller)")
      )
    )
    name: (identifier) @class_name
    body: (class_body
      (method_declaration
        (modifiers
          (annotation
            name: (identifier) @method_annotation
            arguments: (annotation_argument_list
              (string_literal) @method_path
            )?
          )
        )
        name: (identifier) @method_name
      ) @method_definition
    )
  ) @class_definition
)
