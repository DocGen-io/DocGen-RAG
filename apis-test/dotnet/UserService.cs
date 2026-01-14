using System.Collections.Generic;

namespace MyApi.Services
{
    public class UserService
    {
        public object GetUser(string id)
        {
            return new { Id = id, Name = "John Doe", Email = "john@example.com" };
        }

        public IEnumerable<object> ListUsers()
        {
            return new List<object>
            {
                new { Id = 1, Name = "John Doe" },
                new { Id = 2, Name = "Jane Doe" }
            };
        }

        public object UpdateProfile(string userId, dynamic data)
        {
            return new { Id = userId, Data = data, Updated = true };
        }
    }
}
