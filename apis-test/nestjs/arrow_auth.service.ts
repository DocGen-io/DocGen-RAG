// @ts-nocheck
import { Injectable } from '@nestjs/common';

@Injectable()
export class ArrowAuthService {
    login = (credentials: any) => {
        return { token: 'mock-jwt-token', user: { id: 1, email: credentials.email } };
    }

    signup = async (userData: any) => {
        return { id: 2, ...userData };
    }

    // Mixed: regular method
    async validateUser(email: string, password: string) {
        return { id: 1, email };
    }
}
