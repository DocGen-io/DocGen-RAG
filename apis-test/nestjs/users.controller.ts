// @ts-nocheck
import { Controller, Get, Param, Put, Body, UseGuards } from '@nestjs/common';
import { UsersService } from './users.service';

@Controller('users')
export class UsersController {
    constructor(private readonly usersService: UsersService) { }

    @Get(':id')
    async findOne(@Param('id') id: string) {
        return this.usersService.findOne(id);
    }

    @Get()
    async findAll() {
        return this.usersService.findAll();
    }

    @Put('profile/update')
    async updateProfile(@Body() body: any) {
        // Assuming userId is extracted from token or body for this example
        const userId = body.userId || '1';
        return this.usersService.updateProfile(userId, body);
    }
}
