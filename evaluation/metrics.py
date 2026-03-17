from openapi_schema_validator import validate
from jsonschema.exceptions import ValidationError
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)

def evaluate_structural_validity(generated_swagger_dict: dict) -> bool:
    """
    Checks if the generated swagger is a valid OpenAPI schema.
    Returns True if valid, False otherwise.
    """
    try:
        validate(generated_swagger_dict)
        return True
    except ValidationError as e:
        logger.warning(f"Swagger structurally invalid: {e.message}")
        return False
    except Exception as e:
        logger.warning(f"Validation verification error: {e}")
        return False

def evaluate_accuracy(generated_swagger: dict, ground_truth_swagger: dict) -> dict:
    """
    Compares the generated swagger to the ground truth swagger.
    Normalizes paths before comparing to handle minor differences (like trailing slashes).
    """
    
    # Normalize paths (remove trailing slashes, enforce lowercase for comparison if needed, but usually paths are case-sensitive, just strip trailing slashes)
    def normalize_path(p):
        p = p.rstrip('/')
        if not p.startswith('/'):
            p = '/' + p
        return p

    gen_paths = {normalize_path(k): v for k, v in generated_swagger.get("paths", {}).items()}
    truth_paths = {normalize_path(k): v for k, v in ground_truth_swagger.get("paths", {}).items()}
    
    generated_paths_set = set(gen_paths.keys())
    truth_paths_set = set(truth_paths.keys())
    
    # Path Metrics
    path_intersection = generated_paths_set.intersection(truth_paths_set)
    path_recall = len(path_intersection) / len(truth_paths_set) if truth_paths_set else 1.0
    path_precision = len(path_intersection) / len(generated_paths_set) if generated_paths_set else 1.0
    
    # Method Metrics
    generated_methods = []
    for path, methods in gen_paths.items():
        if path in truth_paths_set: # Only count methods if the path itself is a match? Let's count all methods globally.
            pass
        for method in methods.keys():
            if method.lower() != "parameters":
                generated_methods.append(f"{method.upper()} {path}")
                
    truth_methods = []
    for path, methods in truth_paths.items():
        for method in methods.keys():
            if method.lower() != "parameters":
                truth_methods.append(f"{method.upper()} {path}")
            
    gen_methods_set = set(generated_methods)
    truth_methods_set = set(truth_methods)
    
    method_intersection = gen_methods_set.intersection(truth_methods_set)
    method_recall = len(method_intersection) / len(truth_methods_set) if truth_methods_set else 1.0
    method_precision = len(method_intersection) / len(gen_methods_set) if gen_methods_set else 1.0
    
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
        "method_precision": round(method_precision, 4)
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
