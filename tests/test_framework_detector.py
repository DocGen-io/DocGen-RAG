import os
from src.services.framework_detector import FrameworkDetector

def test_framework_detector_nestjs(tmp_path):
    (tmp_path / "nest-cli.json").touch()
    assert FrameworkDetector.detect(str(tmp_path)) == "NestJS"

def test_framework_detector_springboot(tmp_path):
    (tmp_path / "pom.xml").touch()
    assert FrameworkDetector.detect(str(tmp_path)) == "SpringBoot"

def test_framework_detector_unknown(tmp_path):
    (tmp_path / "random_file.txt").touch()
    assert FrameworkDetector.detect(str(tmp_path)) == "Unknown"
