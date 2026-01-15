// @ts-nocheck
import { Injectable } from '@nestjs/common';

@Injectable()
export class UsersService {
    async findOne(id: string) {
        return { id, name: 'John Doe', email: 'john@example.com' };
    }

    async findAll() {
        return [
            { id: 1, name: 'John Doe' },
            { id: 2, name: 'Jane Doe' },
        ];
    }

    async updateProfile(userId: string, updateData: any) {
        return { id: userId, ...updateData, updated: true };
    }
}
