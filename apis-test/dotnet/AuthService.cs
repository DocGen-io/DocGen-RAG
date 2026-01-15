using System.Collections.Generic;

namespace MyApi.Services
{
    public class AuthService
    {
        public object Login(dynamic credentials)
        {
            return new 
            {
                Token = "mock-jwt-token",
                User = new { Id = 1, Email = credentials.email }
            };
        }

        public object Signup(dynamic userData)
        {
            return new { Id = 2, userData };
        }
    }
}
