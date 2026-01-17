import os
import pytest
from src.services.framework_detector import FrameworkFinder

class TestFrameworkFinder:
    @pytest.fixture
    def finder(self):
        return FrameworkFinder()

    def test_detect_django(self, tmp_path, finder):
        d = tmp_path / "django_project"
        d.mkdir()
        (d / "views.py").write_text("from django.http import HttpResponse")
        assert finder.detect(str(d)) == "Django"

    def test_detect_fastapi(self, tmp_path, finder):
        d = tmp_path / "fastapi_project"
        d.mkdir()
        (d / "main.py").write_text("from fastapi import FastAPI")
        assert finder.detect(str(d)) == "FastAPI"

    def test_detect_nestjs(self, tmp_path, finder):
        d = tmp_path / "nest_project"
        d.mkdir()
        (d / "app.controller.ts").write_text("@Controller('cats')")
        assert finder.detect(str(d)) == "NestJS"

    def test_detect_springboot(self, tmp_path, finder):
        d = tmp_path / "spring_project"
        d.mkdir()
        (d / "Application.java").write_text("@SpringBootApplication")
        assert finder.detect(str(d)) == "SpringBoot"

    def test_detect_unknown_ml_script(self, tmp_path, finder):
        d = tmp_path / "ml_project"
        d.mkdir()
        (d / "train.py").write_text("import pandas as pd\nimport sklearn")
        assert finder.detect(str(d)) == "Unknown"

    def test_detect_unknown_cpp(self, tmp_path, finder):
        d = tmp_path / "cpp_project"
        d.mkdir()
        (d / "main.cpp").write_text("#include <iostream>\nint main() { return 0; }")
        assert finder.detect(str(d)) == "Unknown"
