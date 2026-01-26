; Python Controller/Service Query
(module
  (decorated_definition
    (class_definition
      name: (identifier) @class_name
      superclasses: (argument_list
        (identifier) @superclass
      )?
      body: (block
        (function_definition
          name: (identifier) @method_name
          body: (block) @method_body
        ) @method_definition
      )
    ) @class_node
  )
)

(module
  (class_definition
    name: (identifier) @class_name
    superclasses: (argument_list
      (identifier) @superclass
    )?
    body: (block
      (function_definition
        name: (identifier) @method_name
        body: (block) @method_body
      ) @method_definition
    )
  ) @class_node
)
