package com.example.demo.auth;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/auth")
public class AuthController {

    @Autowired
    private AuthService authService;

    @PostMapping("/login")
    public Map<String, Object> login(@RequestBody Map<String, String> body) {
        return authService.login(body);
    }

    @PostMapping("/signup")
    public Map<String, Object> signup(@RequestBody Map<String, String> body) {
        return authService.signup(body);
    }
}
