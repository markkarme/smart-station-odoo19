# Smart Station API - Separate User Management

REST API module for Smart Station with **separate website user management system**.

## ✨ New User Management System

This module uses a **completely separate user model** (`website.user`) that is independent from Odoo's `res.users`. This allows you to:

- 📝 **Control users from Odoo** - Manage website users directly from Odoo interface
- 🔐 **Custom access rights** - Define granular permissions for what users can do on the website
- 👥 **Link to employees** - Each website user is linked to an hr.employee record
- ⚙️ **Configure permissions** - Use menu items to configure access rights

## 🏗️ Architecture

```
Odoo (Backend)                    Website (Frontend)
─────────────                    ───────────────────
hr.employee ←──────────────────→ Authentication
    ↓                                    ↓
website.user ←───── JWT Token ──────→ API Calls
    ↓
website.access.right (Permissions)
```

## 📦 Models

### 1. `website.user`
- **Purpose**: Website login credentials and profile
- **Fields**:
  - `name`: User full name
  - `login`: Email address for login
  - `password`: Hashed password (SHA-256)
  - `employee_id`: Linked employee (required)
  - `access_right_ids`: Access rights granted to user
  - `active`: Enable/disable user
  - `last_login`: Track last login time

### 2. `website.access.right`
- **Purpose**: Define what users can do on the website
- **Categories**:
  - 🏢 Attendance permissions
  - 🏖️ Leave permissions
  - 📝 Request permissions
  - 👤 Employee permissions
  - 🎓 Student management permissions
  - 👑 Admin permissions

### 3. `api.access.token` & `api.refresh.token`
- **Purpose**: JWT token management
- **Features**:
  - Access token (1 hour expiry)
  - Refresh token (30 days expiry)
  - Automatic cleanup via cron

## 🚀 How to Use

### 1. Install the Module

```bash
# In Odoo:
# Apps → Update Apps List → Search "Smart Station API" → Install
```

### 2. Configure Access Rights

Go to: **Smart Station → Website Users → Access Rights**

**Default Access Rights Created**:
- Portal User (basic access)
- Portal Admin (admin access)
- Attendance Admin
- Exam Admin
- Mold Admin
- Fee Admin
- Misconduct Admin

You can modify existing rights or create new ones.

### 3. Create Website User from Employee

**Method 1: From Employee Form**
```
1. Go to: Employees → Employees
2. Open employee record
3. Click: "Create Website User" button
4. Fill in:
   - Name (auto-filled)
   - Login/Email (auto-filled from work_email)
   - Password
   - Confirm Password
   - Select Access Rights
5. Click: "Create User"
```

**Method 2: Directly**
```
1. Go to: Smart Station → Website Users → Users
2. Click: Create
3. Fill in all fields
4. Save
```

### 4. Manage Users

**View Users:**
- Smart Station → Website Users → Users

**Actions Available:**
- 🔄 Reset Password
- 👁️ View Tokens
- 🚫 Invalidate All Tokens
- ✅ Activate/Deactivate

**Employee View:**
- "View Website User" button appears on employee form when user exists

## 🔐 Access Rights Configuration

### Available Permissions

#### Attendance Category
- ✅ View Own Attendance
- ✅ Submit Attendance
- ✅ View All Attendance

#### Leave Category
- ✅ Create Leave Request
- ✅ Cancel Own Leave
- ✅ View Own Leaves
- ✅ Approve Leave Requests

#### Request Category
- ✅ Create General Request
- ✅ Create Attendance Adjustment
- ✅ Approve Requests

#### Employee Category
- ✅ View Own Profile
- ✅ Update Own Profile
- ✅ View All Employees
- ✅ Manage Employees

#### Student Category
- ✅ Manage Student Attendance
- ✅ Manage Student Exams
- ✅ Manage School Molds
- ✅ Manage Fee Plans
- ✅ Manage Violations

#### Admin
- ✅ Administrator Access

### Example: Create Custom Access Right

```
Name: Department Manager
Code: dept_manager
Category: Employee

Permissions:
☑ View Own Attendance
☑ Submit Attendance
☑ View All Attendance
☑ Create Leave Request
☑ View Own Leaves
☑ Approve Leave Requests
☑ Approve Requests
☑ View All Employees
```

## 🔌 API Integration

### Authentication Flow

1. **Login:**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "login": "employee@company.com",
  "password": "password123"
}

Response:
{
  "success": true,
  "data": {
    "access_token": "...",
    "refresh_token": "...",
    "user": {
      "user_id": 1,
      "employee_id": 5,
      "name": "John Doe",
      "access_rights": [...],
      "permissions": {...}
    }
  }
}
```

2. **Use Token:**
```http
GET /api/v1/attendance/me
Authorization: Bearer {access_token}
```

3. **Refresh Token:**
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "..."
}
```

## 🔒 Security Features

### Password Security
- SHA-256 hashing
- Minimum 6 characters
- Confirmation required
- Reset password wizard

### Token Security
- Short-lived access tokens (1 hour)
- Long-lived refresh tokens (30 days)
- Token invalidation on logout
- Device tracking
- IP address logging

### Access Control
- Permission-based endpoints
- Company-based data filtering
- Employee-based data isolation

## 📊 Reports & Monitoring

### User Statistics
- Active users count
- Last login tracking
- Active tokens count
- Device tracking

### Token Management
- View all tokens per user
- Invalidate specific tokens
- Automatic cleanup of expired tokens

## 🔧 Configuration

### System Parameters
- `smart_station_api.access_token_expiry_hours` (default: 1)
- `smart_station_api.refresh_token_expiry_days` (default: 30)

### Cron Jobs
- **Cleanup Expired Access Tokens**: Daily
- **Cleanup Expired Refresh Tokens**: Daily

## 📋 Menu Structure

```
Smart Station
├── Website Users
│   ├── Users (website.user)
│   └── Access Rights (website.access.right)
└── Configuration
```

## 🆚 Comparison with res.users

| Feature | website.user | res.users |
|---------|-------------|-----------|
| Independent from Odoo | ✅ Yes | ❌ No |
| Custom permissions | ✅ Yes | Limited |
| Managed from Odoo | ✅ Yes | Complex |
| Portal access impact | ✅ None | ❌ Conflicts |
| Simple password reset | ✅ Yes | Complex |
| Token management | ✅ Built-in | Manual |

## 💡 Benefits

1. **Separation of Concerns**
   - Website users are separate from internal Odoo users
   - No conflict with portal module
   - Clear distinction

2. **Easy Management**
   - Simple UI to manage users
   - Visual access rights configuration
   - Direct from employee records

3. **Flexible Permissions**
   - Create custom access rights
   - Mix and match permissions
   - Fine-grained control

4. **Better Security**
   - Separate authentication
   - Token-based access
   - Easy to revoke access

## 🧪 Testing

### Test User Creation

1. Create employee
2. Set work email
3. Click "Create Website User"
4. Set password and access rights
5. Try logging in from website

### Test Permissions

1. Create user with limited permissions
2. Login from website
3. Verify only allowed features are accessible

### Test Token Management

1. Login multiple times
2. View tokens in Odoo
3. Invalidate specific token
4. Verify token is invalid

## 📚 Additional Resources

- **Frontend Integration**: See `smart-station-website/README.md`
- **Setup Guide**: See `/SETUP_GUIDE.md`
- **Project Summary**: See `/PROJECT_SUMMARY.md`

## 🆘 Support

For issues or questions:
1. Check access rights configuration
2. Verify user is active
3. Check token expiry
4. Review Odoo logs
5. Contact development team

## 📝 License

LGPL-3
