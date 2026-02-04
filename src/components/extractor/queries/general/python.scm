(decorator (identifier)@decorator)
(import_from_statement) @imports
(class_definition (identifier)@class_name) @class_body
(function_definition (identifier)@method_name)@method_body
(call function:(identifier )@method_call (#eq? @method_call "path"))@urls