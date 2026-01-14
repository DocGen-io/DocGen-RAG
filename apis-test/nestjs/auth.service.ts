// @ts-nocheck
import { Injectable } from '@nestjs/common';

@Injectable()
export class AuthService {
    async login(credentials: any) {
        return { token: 'mock-jwt-token', user: { id: 1, email: credentials.email } };
    }

    async signup(userData: any) {
        return { id: 2, ...userData };
    }
}
