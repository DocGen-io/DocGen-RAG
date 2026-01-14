package com.example.demo.auth;

import org.springframework.stereotype.Service;
import java.util.Map;
import java.util.HashMap;

@Service
public class AuthService {

    public Map<String, Object> login(Map<String, String> credentials) {
        Map<String, Object> response = new HashMap<>();
        response.put("token", "mock-jwt-token");
        response.put("user", Map.of("id", 1, "email", credentials.get("email")));
        return response;
    }

    public Map<String, Object> signup(Map<String, String> userData) {
        Map<String, Object> response = new HashMap<>(userData);
        response.put("id", 2);
        return response;
    }
}
