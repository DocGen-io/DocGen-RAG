[
  ;; Matches: from .services import AuthService
  (import_from_statement 
    module_name: [
      (dotted_name) @import-path
      (relative_import) @import-path
    ])

  ;; Matches: import json
  (import_statement 
    name: (dotted_name) @import-path)
]