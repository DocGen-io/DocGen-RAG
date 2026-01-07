import re
from typing import List, Dict

class SecurityAnalyzer:
    """
    Analyzes API endpoint definitions for basic security concerns.
    """

    @staticmethod
    def analyze_endpoint(path: str, method: str, full_url: str = "") -> List[str]:
        alerts = []

        # Check for HTTP usage if full_url is provided (often implicit in Swagger, but good for description)
        if full_url and full_url.startswith("http://"):
            alerts.append(f"SECURITY ALERT: Endpoint {method} {path} is using HTTP. Use HTTPS for secure communication.")

        # Check for tokens/api_key in path
        # Matches patterns like /users/{token}, /api_key/{key}, etc.
        token_patterns = [
            r"token",
            r"key",
            r"secret",
            r"auth",
            r"password",
            r"credential"
        ]
        
        path_lower = path.lower()
        for pattern in token_patterns:
            # We look for the pattern inside braces {} indicating a path parameter, or just generally in the path segments
            if re.search(f"{{.*{pattern}.*}}", path_lower) or re.search(f"/{pattern}/", path_lower):
                alerts.append(f"SECURITY ALERT: Endpoint {method} {path} seems to be passing a '{pattern}' in the URL path. Sensitive data should be passed in headers or body.")

        # Check query parameters (simulated here as we might parse them later)
        # In a real scenario, this would check the 'parameters' list of the operation
        
        return alerts

    @staticmethod
    def analyze_global(base_url: str) -> List[str]:
        alerts = []
        if base_url.startswith("http://"):
             alerts.append("GLOBAL SECURITY ALERT: Base URL is using HTTP. All endpoints are potentially insecure.")
        return alerts
