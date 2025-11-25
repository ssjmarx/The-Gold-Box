"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.User = void 0;
const sequelize_1 = require("sequelize");
const sequelize_2 = require("../sequelize");
const bcryptjs_1 = __importDefault(require("bcryptjs"));
const crypto_1 = __importDefault(require("crypto"));
const logger_1 = require("../utils/logger");
// Check if we're using the memory store
const isMemoryStore = process.env.DB_TYPE === 'memory';
class User extends sequelize_1.Model {
    // Memory store methods
    static async findOne(options) {
        if (isMemoryStore) {
            if (options.where && options.where.apiKey) {
                return sequelize_2.sequelize.getUser(options.where.apiKey);
            }
            if (options.where && options.where.email) {
                const users = Array.from(sequelize_2.sequelize.users.values());
                return users.find(u => u.email === options.where.email) || null;
            }
            return null;
        }
        return super.findOne(options);
    }
    static async create(data) {
        if (isMemoryStore) {
            const memoryStore = sequelize_2.sequelize;
            if (memoryStore.users.has(data.email)) {
                throw new Error('User already exists');
            }
            const user = {
                id: memoryStore.users.size + 1,
                email: data.email,
                password: data.password,
                apiKey: data.apiKey || crypto_1.default.randomBytes(16).toString('hex'),
                requestsThisMonth: data.requestsThisMonth || 0,
                requestsToday: data.requestsToday || 0,
                lastRequestDate: data.lastRequestDate || null,
                subscriptionStatus: data.subscriptionStatus || 'free',
                createdAt: new Date(),
                updatedAt: new Date(),
                getDataValue: function (key) {
                    return this[key];
                },
                setDataValue: function (key, value) {
                    this[key] = value;
                }
            };
            memoryStore.users.set(data.email, user);
            memoryStore.apiKeys.set(user.apiKey, data.email);
            return user;
        }
        return super.create(data);
    }
    static async findAll(options) {
        if (isMemoryStore) {
            const memoryStore = sequelize_2.sequelize;
            if (options.where && options.where.apiKey) {
                const user = memoryStore.getUser(options.where.apiKey);
                return user ? [user] : [];
            }
            return Array.from(memoryStore.users.values());
        }
        return super.findAll(options);
    }
}
exports.User = User;
// Initialize with Sequelize if not using memory store
if (!isMemoryStore) {
    User.init({
        id: {
            type: sequelize_1.DataTypes.INTEGER,
            autoIncrement: true,
            primaryKey: true
        },
        email: {
            type: sequelize_1.DataTypes.STRING,
            allowNull: false,
            unique: true,
            validate: {
                isEmail: true
            }
        },
        password: {
            type: sequelize_1.DataTypes.STRING,
            allowNull: false
        },
        apiKey: {
            type: sequelize_1.DataTypes.STRING,
            allowNull: false,
            unique: true,
            defaultValue: () => crypto_1.default.randomBytes(16).toString('hex')
        },
        requestsThisMonth: {
            type: sequelize_1.DataTypes.INTEGER,
            defaultValue: 0
        },
        requestsToday: {
            type: sequelize_1.DataTypes.INTEGER,
            defaultValue: 0
        },
        lastRequestDate: {
            type: sequelize_1.DataTypes.DATEONLY,
            allowNull: true
        },
        stripeCustomerId: {
            type: sequelize_1.DataTypes.STRING,
            allowNull: true
        },
        subscriptionStatus: {
            type: sequelize_1.DataTypes.STRING,
            allowNull: true,
            defaultValue: 'free'
        },
        subscriptionId: {
            type: sequelize_1.DataTypes.STRING,
            allowNull: true
        },
        subscriptionEndsAt: {
            type: sequelize_1.DataTypes.DATE,
            allowNull: true
        }
    }, {
        sequelize: sequelize_2.sequelize,
        modelName: 'User',
        tableName: 'Users',
        hooks: {
            beforeCreate: async (user) => {
                if (user.getDataValue('password')) {
                    const salt = await bcryptjs_1.default.genSalt(10);
                    const hashedPassword = await bcryptjs_1.default.hash(user.getDataValue('password'), salt);
                    user.setDataValue('password', hashedPassword);
                }
            },
            beforeUpdate: async (user) => {
                if (user.changed('password')) {
                    logger_1.log.debug('Updating password for user', { email: user.getDataValue('email') });
                    const salt = await bcryptjs_1.default.genSalt(10);
                    const hashedPassword = await bcryptjs_1.default.hash(user.getDataValue('password'), salt);
                    user.setDataValue('password', hashedPassword);
                }
            }
        }
    });
}
exports.default = User;
