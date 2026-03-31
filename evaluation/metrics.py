from openapi_spec_validator import validate
from openapi_spec_validator.validation.exceptions import OpenAPIValidationError
from src.utils.logger import DocGenLogger
import re

logger = DocGenLogger(__name__)

   

def evaluate_structural_validity(generated_swagger_dict: dict) -> bool:
    """
    Checks if the generated swagger is a valid OpenAPI schema.
    Returns True if valid, False otherwise.
    """
    try:
        validate(generated_swagger_dict)
        return True
    except OpenAPIValidationError as e:
        logger.warning(f"Swagger structurally invalid: {e.message}")
        return False
    except Exception as e:
        logger.warning(f"Validation verification error: {e}")
        return False

def extract_methods(paths: dict) -> set:
    """
    Extracts methods from the paths dictionary.
    Returns a set of methods in the format "METHOD /path".
    """
    gen_methods_set = {
        f"{method.upper()} {path}"
        for path, methods in paths.items()
        for method in methods.keys()
        if method.lower() != "parameters"
    }
    return gen_methods_set

def evaluate_accuracy(generated_swagger: dict, ground_truth_swagger: dict,date: str) -> dict:
    """
    Compares the generated swagger to the ground truth swagger.
    Normalizes paths before comparing to handle minor differences (like trailing slashes).
    """
    
    # Normalize paths (remove trailing slashes, enforce lowercase for comparison if needed, but usually paths are case-sensitive, just strip trailing slashes)
    def normalize_path(p):
        p = p.rstrip('/')
        if not p.startswith('/'):
            p = '/' + p
        return re.sub(r"\{.*?\}", "dynamic_param", p)

    gen_paths = {normalize_path(k): v for k, v in generated_swagger.get("paths", {}).items()}
    truth_paths = {normalize_path(k): v for k, v in ground_truth_swagger.get("paths", {}).items()}
    
    generated_paths_set = set(gen_paths.keys())
    truth_paths_set = set(truth_paths.keys())
    
    # Path Metrics
    path_intersection = {t for t in truth_paths_set if any(g.endswith(t) for g in generated_paths_set)}
    valid_generated_paths = {g for g in generated_paths_set if any(g.endswith(t) for t in truth_paths_set)}
                
    path_recall = len(path_intersection) / len(truth_paths_set) if truth_paths_set else 1.0
    path_precision = len(valid_generated_paths) / len(generated_paths_set) if generated_paths_set else 1.0
    
    # Method Extraction via Set Comprehension
    gen_methods_set = extract_methods(gen_paths)
    truth_methods_set = extract_methods(truth_paths)
    
    # Method Metrics - Suffix inclusion check via mapping function
    def is_method_match(t_method: str, g_method: str) -> bool:
        t_verb, t_path = t_method.split(" ", 1)
        g_verb, g_path = g_method.split(" ", 1)
        return t_verb == g_verb and g_path.endswith(t_path)
        
    method_intersection = {t for t in truth_methods_set if any(is_method_match(t, g) for g in gen_methods_set)}
    valid_generated_methods = {g for g in gen_methods_set if any(is_method_match(t, g) for t in truth_methods_set)}
                
    method_recall = len(method_intersection) / len(truth_methods_set) if truth_methods_set else 1.0
    method_precision = len(valid_generated_methods) / len(gen_methods_set) if gen_methods_set else 1.0
    
    return {
        "expected_paths_count": len(truth_paths_set),
        "generated_paths_count": len(generated_paths_set),
        "path_match_count": len(path_intersection),
        "path_recall": round(path_recall, 4),
        "path_precision": round(path_precision, 4),
        "expected_methods_count": len(truth_methods_set),
        "generated_methods_count": len(gen_methods_set),
        "method_match_count": len(method_intersection),
        "method_recall": round(method_recall, 4),
        "method_precision": round(method_precision, 4),
        "date": date
    }

def print_metrics_report(metrics: dict):
    print("="*40)
    print("         EVALUATION METRICS")
    print("="*40)
    print(f"Paths Expected:  {metrics['expected_paths_count']}")
    print(f"Paths Generated: {metrics['generated_paths_count']}")
    print(f"Paths Matched:   {metrics['path_match_count']}")
    print(f"Path Recall:     {metrics['path_recall']:.2%}")
    print(f"Path Precision:  {metrics['path_precision']:.2%}")
    print("-" * 40)
    print(f"Methods Matched: {metrics['method_match_count']}")
    print(f"Method Recall:   {metrics['method_recall']:.2%}")
    print(f"Method Precision:{metrics['method_precision']:.2%}")
    print("="*40)
