import pytest
from src.core.security import SecurityAnalyzer

def test_security_analyzer_http():
    alerts = SecurityAnalyzer.analyze_endpoint("/test", "GET", full_url="http://api.example.com/test")
    assert any("using HTTP" in a for a in alerts)

def test_security_analyzer_https():
    alerts = SecurityAnalyzer.analyze_endpoint("/test", "GET", full_url="https://api.example.com/test")
    assert not any("using HTTP" in a for a in alerts)

def test_security_analyzer_token_in_path():
    alerts = SecurityAnalyzer.analyze_endpoint("/users/{token}", "GET")
    assert any("passing a 'token'" in a for a in alerts)

def test_security_analyzer_secret_in_path():
    alerts = SecurityAnalyzer.analyze_endpoint("/api/{client_secret}/data", "POST")
    assert any("passing a 'secret'" in a for a in alerts)

def test_security_analyzer_clean_path():
    alerts = SecurityAnalyzer.analyze_endpoint("/users/{id}", "GET")
    assert len(alerts) == 0
