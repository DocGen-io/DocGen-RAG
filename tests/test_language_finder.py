from src.components.LanguageFinder import LanguageFinder

class TestLanguageFinder:
    def test_detect_python(self):
        finder = LanguageFinder()
        assert finder.detect("test.py") == "python"

    def test_detect_typescript(self):
        finder = LanguageFinder()
        assert finder.detect("component.ts") == "typescript"

    def test_detect_java(self):
        finder = LanguageFinder()
        assert finder.detect("Service.java") == "java"

    def test_detect_unknown(self):
        finder = LanguageFinder()
        assert finder.detect("readme.md") == "unknown"
