import os
import abc
from typing import List, Optional

class FrameworkStrategy(abc.ABC):
    @abc.abstractmethod
    def matches(self, file_content: str, filename: str) -> bool:
        pass

    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

class DjangoStrategy(FrameworkStrategy):
    @property
    def name(self) -> str:
        return "Django"

    def matches(self, file_content: str, filename: str) -> bool:
        return "from django.urls" in file_content or "from django.http" in file_content or "django.conf" in file_content

class FastAPIStrategy(FrameworkStrategy):
    @property
    def name(self) -> str:
        return "FastAPI"

    def matches(self, file_content: str, filename: str) -> bool:
        return "from fastapi" in file_content or "APIRouter" in file_content

class NestJSStrategy(FrameworkStrategy):
    @property
    def name(self) -> str:
        return "NestJS"

    def matches(self, file_content: str, filename: str) -> bool:
        return "@Controller" in file_content or "@Get" in file_content or "@Post" in file_content

class SpringBootStrategy(FrameworkStrategy):
    @property
    def name(self) -> str:
        return "SpringBoot"

    def matches(self, file_content: str, filename: str) -> bool:
        return "@RestController" in file_content or "@SpringBootApplication" in file_content

class DotNetStrategy(FrameworkStrategy):
    @property
    def name(self) -> str:
        return ".NET"

    def matches(self, file_content: str, filename: str) -> bool:
        return "Microsoft.AspNetCore.Mvc" in file_content or "[ApiController]" in file_content

class ExpressStrategy(FrameworkStrategy):
    @property
    def name(self) -> str:
        return "Express"

    def matches(self, file_content: str, filename: str) -> bool:
        return "require('express')" in file_content or 'import express' in file_content or 'require("express")' in file_content

class LaravelStrategy(FrameworkStrategy):
    @property
    def name(self) -> str:
        return "Laravel"

    def matches(self, file_content: str, filename: str) -> bool:
        return "Illuminate\\Support\\Facades\\Route" in file_content or "namespace App\\Http\\Controllers" in file_content

class FrameworkDetector:
    """
    Detects the framework used in a project by scanning files and using strategies.
    """

    def __init__(self):
        self.strategies: List[FrameworkStrategy] = [
            DjangoStrategy(),
            FastAPIStrategy(),
            NestJSStrategy(),
            SpringBootStrategy(),
            DotNetStrategy(),
            ExpressStrategy(),
            LaravelStrategy()
        ]

    def detect(self, project_path: str) -> str:
        """
        Scans the project path to detect the framework.
        Returns the framework name or 'Unknown'.
        """
        # Limit the walk to avoid scanning node_modules or huge directories unnecessarily deep
        # For now, we'll scan everything but we could optimize
        
        for root, dirs, files in os.walk(project_path):
            if 'node_modules' in dirs:
                dirs.remove('node_modules')
            if '.git' in dirs:
                dirs.remove('.git')
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')

            for file in files:
                file_path = os.path.join(root, file)
                print(file_path)
                if os.path.isdir(file_path):
                   return  self.detect(file_path)

                
                # Skip large files or binaries
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(10000) # Read first 10kb covers most imports/decorators
                        
                        for strategy in self.strategies:
                            if strategy.matches(content, file):
                                return strategy.name
                except Exception:
                    continue
                    
        return "Unknown"
