(import_statement) @imports
(class_declaration (type_identifier) @class_name) @class_body
(abstract_class_declaration (type_identifier)@class_name) @class_body
(method_definition (property_identifier) @method_name) @method_body
(function_declaration (identifier)  @method_name) @method_body
(variable_declarator (identifier )@method_name (arrow_function)@method_body)
(decorator) @decorator