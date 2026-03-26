API_METHODS =  {"get", "post", "put", "patch", "delete", "options", "head"}

DECORATOR_TYPE_MAP = {
    # Java Spring
    "getmapping": "GET", "postmapping": "POST", "putmapping": "PUT",
    "deletemapping": "DELETE", "patchmapping": "PATCH",
    "requestmapping": "GET",
    # C# ASP.NET
    "httpget": "GET", "httppost": "POST", "httpput": "PUT",
    "httpdelete": "DELETE", "httppatch": "PATCH", "httpoptions": "OPTIONS",
    "httphead": "HEAD",
    # TypeScript/NestJS
    "get": "GET", "post": "POST", "put": "PUT",
    "delete": "DELETE", "patch": "PATCH", "options": "OPTIONS",
    "head": "HEAD", "all": "ALL",
}