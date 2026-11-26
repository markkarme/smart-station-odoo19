# Smart Station - User & Access Rights Management

## 📍 Where to Find the Menu

After installing the `smart_station_api` module, you will see a new top-level menu:

```
Smart Station (📱 icon in the main menu bar)
│
├── Website Users
│   ├── Users          ← Main menu to manage all users and access rights
│   └── Access Rights  ← Configure available access rights
│
└── Configuration
```

## 👥 Managing Users and Access Rights

### Method 1: From the Website Users Menu

1. **Go to:** `Smart Station → Website Users → Users`

2. **You will see three views:**
   - **Kanban View** 📊: Visual cards showing users with their access rights as colored tags
   - **Tree View** 📋: List view showing all users with access rights column
   - **Form View** 📝: Detailed user form with full access rights configuration

3. **To add access rights to a user:**
   - Click on a user to open their form
   - Go to the **"Access Rights"** tab
   - Check/uncheck the rights you want to assign
   - Save

### Method 2: From Employee Form

1. **Go to:** `Employees → Employees`

2. **Select an employee**

3. **Click the "Create Website User" button** (smart action button)

4. **In the wizard:**
   - Enter login email
   - Set password
   - **Select Access Rights** from the dropdown
   - Click "Create User"

### Method 3: Bulk Edit (from Tree View)

1. **Go to:** `Smart Station → Website Users → Users`

2. **Switch to Tree View**

3. **Select multiple users** (checkboxes)

4. **Click on the Access Rights column**

5. **Add/remove access rights** for all selected users at once

## 🔐 Access Rights Management

### Viewing Available Access Rights

**Go to:** `Smart Station → Website Users → Access Rights`

Here you can:
- See all available access rights
- Create new access rights
- Edit existing rights
- Configure permissions (attendance, leave, request, employee, student, admin)
- Set categories and colors

### Access Right Categories

The system includes these categories:

- **Attendance**: View/submit attendance, adjustments
- **Leave**: Create/view leaves
- **Request**: Create/view general requests
- **Employee**: View/edit employee info, view payslips
- **Student**: View/edit student info, view fees, pay fees
- **Admin**: Full administrative access

### Default Access Rights

The system comes with pre-configured access rights:

1. **Portal User**: Basic portal access (view attendance, submit attendance, view leaves)
2. **Employee**: Standard employee access (all attendance + request features)
3. **Manager**: Manager access (employee features + employee management)
4. **Admin**: Full access (all permissions enabled)
5. **Student Portal**: Student-specific access (view student info, view fees)
6. **Parent Portal**: Parent access (view student info for children)

## 🎨 Visual Features

### In Tree View:
- **Access Rights Column**: Shows colored tags for each user's rights
- **Multi-edit**: Select multiple users and bulk-assign rights
- **Active Toggle**: Quickly activate/deactivate users

### In Kanban View:
- **User Cards**: Show avatar, name, login, employee, and access rights
- **Colored Tags**: Access rights displayed as colored tags by category
- **Active Toggle**: Visual toggle button

### In Form View:
- **Access Rights Tab**: Checkboxes for each available right
- **Permissions Summary Tab**: Overview of assigned rights with instructions
- **Token Statistics**: See active token count
- **Action Buttons**: Reset password, view tokens, invalidate tokens

## 🔍 Search & Filters

Available filters in the search bar:

- **Active/Inactive**: Filter by user status
- **Has Admin Rights**: Show only administrators
- **Portal Users**: Show only portal users
- **Group By**: 
  - Company
  - Department
  - Access Rights (see users grouped by their permissions)

## 📝 Creating a New Website User

### From Employee:
1. `Employees → Employees → Select Employee`
2. Click **"Create Website User"** button
3. Fill in the wizard (login, password, access rights)
4. Click **"Create User"**

### From Website Users Menu:
1. `Smart Station → Website Users → Users`
2. Click **"Create"** button
3. Fill in the form:
   - Name
   - Login (email)
   - Link to Employee
   - Select Access Rights from the "Access Rights" tab
4. Click **"Save"**
5. Click **"Reset Password"** to set a password

## 🔒 Security Features

- Passwords are hashed using SHA-256
- Token-based authentication with refresh tokens
- Password reset functionality
- Token invalidation for security
- Activity tracking and logging

## 💡 Tips

1. **Always assign at least one access right** to a user, otherwise they won't be able to log in to the website
2. **Use the Kanban view** for a quick visual overview of user permissions
3. **Use Group By: Access Rights** to see which users have similar permissions
4. **Use the wizard from employee form** for the quickest way to create users
5. **Check the "Permissions Summary" tab** in user form to see what the user can do

## 🔄 Workflow Example

**Creating a new employee with portal access:**

1. Create the employee: `Employees → Employees → Create`
2. Fill in employee details and save
3. Click **"Create Website User"** button
4. In wizard:
   - Login: `john.doe@company.com`
   - Password: `(set secure password)`
   - Access Rights: Select "Portal User" and "Employee"
5. Click **"Create User"**
6. Done! The employee can now log in to the external website

**Modifying access rights later:**

1. `Smart Station → Website Users → Users`
2. Find and click on the user
3. Go to **"Access Rights"** tab
4. Check/uncheck rights as needed
5. **Save**

---

## 📊 Dashboard (Coming Soon)

The dashboard will show:
- Total users
- Active users
- Admin users
- New users today
- Active tokens count

Access it from: `Smart Station` (main menu)
