package com.example.demo.users;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/users")
public class UserController {

    @Autowired
    private UserService userService;

    @GetMapping("/{id}")
    public Map<String, Object> findOne(@PathVariable String id) {
        return userService.findOne(id);
    }

    @GetMapping
    public List<Map<String, Object>> findAll() {
        return userService.findAll();
    }

    @PutMapping("/profile/update")
    public Map<String, Object> updateProfile(@RequestBody Map<String, Object> body) {
        // Assuming userId is passed in body for simplicity or extracted from context
        String userId = (String) body.getOrDefault("userId", "1");
        return userService.updateProfile(userId, body);
    }
}
