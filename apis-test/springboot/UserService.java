package com.example.demo.users;

import org.springframework.stereotype.Service;
import java.util.List;
import java.util.Map;
import java.util.HashMap;

@Service
public class UserService {

    public Map<String, Object> findOne(String id) {
        return Map.of("id", id, "name", "John Doe", "email", "john@example.com");
    }

    public List<Map<String, Object>> findAll() {
        return List.of(
            Map.of("id", 1, "name", "John Doe"),
            Map.of("id", 2, "name", "Jane Doe")
        );
    }

    public Map<String, Object> updateProfile(String userId, Map<String, Object> updateData) {
        Map<String, Object> response = new HashMap<>(updateData);
        response.put("id", userId);
        response.put("updated", true);
        return response;
    }
}
