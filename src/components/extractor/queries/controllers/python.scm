; Python Query

; Imports
(import_from_statement) @import_statement
(import_statement) @import_statement

; Decorated Class (e.g. Django Views with @method_decorator)
(decorated_definition
  (decorator) @class_decorator
  definition: (class_definition
    name: (identifier) @class_name
    body: (block
      [
        (function_definition
          name: (identifier) @method_name
        )
        (decorated_definition
          definition: (function_definition
             name: (identifier) @method_name
          )
        )
      ] @method
    )
  )
) @class_definition

; Undecorated Class Definition
; Note: We use a distinct pattern to catch classes that don't have decorators.
; The structure inside 'block' uses alternation [] to match either plain or decorated methods.
(class_definition
  name: (identifier) @class_name
  body: (block
    [
      (function_definition
        name: (identifier) @method_name
      )
      (decorated_definition
        definition: (function_definition
           name: (identifier) @method_name
        )
      )
    ] @method
  )
) @class_definition

; FastAPI Router (Definition)
(assignment
  left: (identifier) @class_name
  right: (call
    function: (identifier) @callee
    (#eq? @callee "APIRouter")
    arguments: (argument_list
      (keyword_argument
        name: (identifier) @arg_name
        (#eq? @arg_name "prefix")
        value: (string) @base_path
      )?
    )
  )
) @class_definition

; FastAPI Routes (Standalone)
(decorated_definition
  (decorator
    (call
      function: (attribute
         object: (identifier) @router_ref
         attribute: (identifier) @http_verb
      )
      arguments: (argument_list
         (string) @method_path
      )?
    )
  )
  definition: (function_definition
    name: (identifier) @method_name
  )
) @method
