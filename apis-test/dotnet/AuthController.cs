using Microsoft.AspNetCore.Mvc;
using MyApi.Services;

namespace MyApi.Controllers
{
    [ApiController]
    [Route("auth")]
    public class AuthController : ControllerBase
    {
        private readonly AuthService _authService;

        public AuthController(AuthService authService)
        {
            _authService = authService;
        }

        [HttpPost("login")]
        public IActionResult Login([FromBody] dynamic body)
        {
            return Ok(_authService.Login(body));
        }

        [HttpPost("signup")]
        public IActionResult Signup([FromBody] dynamic body)
        {
            return Ok(_authService.Signup(body));
        }
    }
}
