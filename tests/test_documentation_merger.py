"""Tests for DocumentationMerger component and builders."""
import pytest, json, os, tempfile, shutil

# Fixtures
@pytest.fixture
def sample_swagger():
    return {"summary": "Get Posts", "path": "/posts", "parameters": [{"name": "limit", "in": "query", "type": "integer"}],
            "responses": [{"code": 200, "description": "Success"}]}

@pytest.fixture
def sample_postman():
    return {"name": "Get Posts", "method": "GET", "url": "/posts", "header": []}

@pytest.fixture
def sample_login_swagger():
    return {"summary": "Login", "path": "/auth/login", "parameters": [{"in": "body", "name": "user"}],
            "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
            "responses": [{"code": 200, "description": "OK"}]}

@pytest.fixture
def sample_login_postman():
    return {"name": "Login", "method": "POST", "url": "/auth/login", 
            "header": [{"name": "Content-Type", "value": "application/json"}],
            "body": {"mode": "raw", "raw": "{}"}}

@pytest.fixture
def temp_output_dir(sample_swagger, sample_postman, sample_login_swagger, sample_login_postman):
    tmpdir = tempfile.mkdtemp()
    for name, sw, pm in [("getAllPosts", sample_swagger, sample_postman), ("login", sample_login_swagger, sample_login_postman)]:
        d = os.path.join(tmpdir, name)
        os.makedirs(d)
        json.dump(sw, open(os.path.join(d, "swagger.json"), "w"))
        json.dump(pm, open(os.path.join(d, "postman.json"), "w"))
    yield tmpdir
    shutil.rmtree(tmpdir)

@pytest.fixture
def empty_output_dir():
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir)


class TestSwaggerBuilder:
    def test_build_valid_structure(self, sample_swagger):
        from src.utils.output_format_builders import SwaggerBuilder
        result = SwaggerBuilder(title="Test", version="1.0.0").build([{"method_name": "test", "http_method": "GET", "data": sample_swagger}])
        assert all(k in result for k in ["openapi", "info", "paths"])
        assert result["openapi"].startswith("3.")
    
    def test_groups_by_path(self, sample_swagger, sample_login_swagger):
        from src.utils.output_format_builders import SwaggerBuilder
        result = SwaggerBuilder(title="Test", version="1.0.0").build([
            {"method_name": "get", "http_method": "GET", "data": sample_swagger},
            {"method_name": "login", "http_method": "POST", "data": sample_login_swagger}])
        assert "/posts" in result["paths"] and "/auth/login" in result["paths"]
    
    def test_converts_responses(self, sample_swagger):
        from src.utils.output_format_builders import SwaggerBuilder
        result = SwaggerBuilder(title="Test", version="1.0.0").build([{"method_name": "t", "http_method": "GET", "data": sample_swagger}])
        assert isinstance(result["paths"]["/posts"]["get"]["responses"], dict)
        assert "200" in result["paths"]["/posts"]["get"]["responses"]
    
    def test_includes_parameters(self, sample_swagger):
        from src.utils.output_format_builders import SwaggerBuilder
        result = SwaggerBuilder(title="Test", version="1.0.0").build([{"method_name": "t", "http_method": "GET", "data": sample_swagger}])
        assert any(p["name"] == "limit" for p in result["paths"]["/posts"]["get"].get("parameters", []))
    
    def test_request_body(self, sample_login_swagger):
        from src.utils.output_format_builders import SwaggerBuilder
        result = SwaggerBuilder(title="Test", version="1.0.0").build([{"method_name": "login", "http_method": "POST", "data": sample_login_swagger}])
        assert "requestBody" in result["paths"]["/auth/login"]["post"]
    
    def test_empty_endpoints(self):
        from src.utils.output_format_builders import SwaggerBuilder
        result = SwaggerBuilder(title="Test", version="1.0.0").build([])
        assert result["paths"] == {}
    
    def test_servers_config(self):
        from src.utils.output_format_builders import SwaggerBuilder
        result = SwaggerBuilder(title="Test", version="1.0.0", base_url="http://api.example.com").build([])
        assert result["servers"][0]["url"] == "http://api.example.com"


class TestPostmanCollectionBuilder:
    def test_build_valid_structure(self, sample_postman):
        from src.utils.output_format_builders import PostmanCollectionBuilder
        result = PostmanCollectionBuilder(collection_name="Test").build([{"method_name": "test", "data": sample_postman}])
        assert all(k in result for k in ["info", "item"])
        assert "v2.1.0" in result["info"]["schema"]
    
    def test_creates_items(self, sample_postman, sample_login_postman):
        from src.utils.output_format_builders import PostmanCollectionBuilder
        result = PostmanCollectionBuilder(collection_name="Test").build([
            {"method_name": "p", "data": sample_postman}, {"method_name": "l", "data": sample_login_postman}])
        assert len(result["item"]) == 2
    
    def test_request_structure(self, sample_postman):
        from src.utils.output_format_builders import PostmanCollectionBuilder
        result = PostmanCollectionBuilder(collection_name="Test").build([{"method_name": "t", "data": sample_postman}])
        req = result["item"][0]["request"]
        assert all(k in req for k in ["method", "url", "header"])
    
    def test_body_preserved(self, sample_login_postman):
        from src.utils.output_format_builders import PostmanCollectionBuilder
        result = PostmanCollectionBuilder(collection_name="Test").build([{"method_name": "l", "data": sample_login_postman}])
        assert result["item"][0]["request"]["body"]["mode"] == "raw"


class TestDocumentationMerger:
    def test_creates_files(self, temp_output_dir):
        from src.components.DocumentationMerger import DocumentationMerger
        result = DocumentationMerger().run(output_dir=temp_output_dir)
        assert os.path.exists(result["swagger_path"]) and os.path.exists(result["postman_path"])
        assert result["endpoints_merged"] == 2
    
    def test_empty_dir(self, empty_output_dir):
        from src.components.DocumentationMerger import DocumentationMerger
        assert DocumentationMerger().run(output_dir=empty_output_dir)["endpoints_merged"] == 0
    
    def test_swagger_valid(self, temp_output_dir):
        from src.components.DocumentationMerger import DocumentationMerger
        result = DocumentationMerger().run(output_dir=temp_output_dir)
        data = json.load(open(result["swagger_path"]))
        assert all(k in data for k in ["openapi", "paths"])
    
    def test_postman_valid(self, temp_output_dir):
        from src.components.DocumentationMerger import DocumentationMerger
        result = DocumentationMerger().run(output_dir=temp_output_dir)
        data = json.load(open(result["postman_path"]))
        assert all(k in data for k in ["info", "item"])


class TestIntegration:
    @pytest.fixture
    def real_output_dir(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
        if not os.path.exists(path):
            pytest.skip("No output dir")
        return path
    
    def test_real_merge(self, real_output_dir):
        from src.components.DocumentationMerger import DocumentationMerger
        result = DocumentationMerger().run(output_dir=real_output_dir)
        assert result["endpoints_merged"] > 0
        swagger = json.load(open(result["swagger_path"]))
        assert swagger["openapi"].startswith("3.")
