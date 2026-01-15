using Microsoft.AspNetCore.Mvc;
using MyApi.Services;

namespace MyApi.Controllers
{
    [ApiController]
    [Route("users")]
    public class UserController : ControllerBase
    {
        private readonly UserService _userService;

        public UserController(UserService userService)
        {
            _userService = userService;
        }

        [HttpGet("{id}")]
        public IActionResult GetUser(string id)
        {
            return Ok(_userService.GetUser(id));
        }

        [HttpGet]
        public IActionResult ListUsers()
        {
            return Ok(_userService.ListUsers());
        }

        [HttpPut("profile/update")]
        public IActionResult UpdateProfile([FromBody] dynamic body)
        {
            // Simplistic extraction as C# dynamic binding logic might vary
            string userId = "1"; 
            try { userId = (string)body.userId; } catch {}
            
            return Ok(_userService.UpdateProfile(userId, body));
        }
    }
}
