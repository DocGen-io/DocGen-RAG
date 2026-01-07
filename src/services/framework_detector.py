import os
from typing import Optional

class FrameworkDetector:
    """
    Detects the framework used in the input project directory.
    """
    
    FRAMEWORK_INDICATORS = {
        "NestJS": ["nest-cli.json", "nestjs"],
        "SpringBoot": ["pom.xml", "build.gradle", "mvnw"], # Looking for java files + these
        "FastAPI": ["fastapi", "main.py"], # Heuristic, check requirements.txt content if possible
        "Django": ["manage.py", "django"],
        "Flask": ["flask", "app.py"],
        ".NET": [".csproj", ".sln", "Program.cs", "Startup.cs"],
        "Express": ["package.json", "express"]
    }

    @staticmethod
    def detect(project_path: str) -> str:
        """
        Scans the project path for indicators.
        Returns the name of the framework or 'Unknown'.
        """
        # Walk through the directory to get a file list (limit depth to avoid huge trees)
        root_files = []
        try:
            for root, dirs, files in os.walk(project_path):
                root_files.extend(files)
                # Check for dependencies in package.json or requirements.txt if found
                # For now, simple file existence check
                if "package.json" in files:
                   # Simplistic check - strict implementation would read the file
                   pass 
                break # Only checking root level for now for file existence, but recursive for some
        except Exception:
            return "Unknown"

        # Check explicit file markers
        for framework, markers in FrameworkDetector.FRAMEWORK_INDICATORS.items():
            for marker in markers:
                if marker in root_files:
                    return framework
                
        # Deep check (e.g. for Python frameworks defined in requirements)
        # TODO: Implement deep dependency parsing
        
        return "Unknown"
