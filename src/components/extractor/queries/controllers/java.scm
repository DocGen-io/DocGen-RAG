; Java Controller/Service Query
(program
  (import_declaration
    (scoped_identifier) @import_path
  ) @import_statement

  (class_declaration
    (modifiers
      [
        (marker_annotation
          name: (identifier) @class_decorator_name
          (#match? @class_decorator_name "^(RestController|Service|Controller|Component)$")
        )
        (annotation
          name: (identifier) @class_decorator_name
          arguments: (annotation_argument_list
             (string_literal
               (string_fragment) @class_decorator_path
             )
          )?
          (#match? @class_decorator_name "^(RestController|Service|Controller|Component)$")
        )
      ]
    )?
    (modifiers
      (annotation
        name: (identifier) @route_annotation_name
        arguments: (annotation_argument_list
           (string_literal
             (string_fragment) @class_decorator_path
           )
        )
        (#match? @route_annotation_name "^RequestMapping$")
      )
    )?
    name: (identifier) @class_name
    body: (class_body
      (method_declaration
        (modifiers
          [
            (marker_annotation
              name: (identifier) @method_decorator_name
            )
            (annotation
              name: (identifier) @method_decorator_name
              arguments: (annotation_argument_list
                (string_literal
                  (string_fragment) @method_decorator_path
                )
              )?
            )
          ]?
        )
        name: (identifier) @method_name
        body: (block) @method_body
      ) @method_definition
    )
  ) @class_node
)
