import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue')
  },
  // 测试页面 - 登录成功后跳转
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/TestDashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('@/views/admin/KnowledgeView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/tools',
    name: 'Tools',
    component: () => import('@/views/ToolsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { requiresAuth: true }
  },
  // 修改密码页面（首次登录）
  {
    path: '/change-password',
    name: 'ChangePassword',
    component: () => import('@/views/ChangePasswordView.vue')
  },
  // 管理员界面
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      {
        path: '',
        redirect: '/admin/dashboard'
      },
      {
        path: 'dashboard',
        name: 'AdminDashboard',
        component: () => import('@/views/admin/Dashboard.vue')
      },
      {
        path: 'pending-users',
        name: 'PendingUsers',
        component: () => import('@/views/admin/PendingUsers.vue')
      },
      {
        path: 'pending-resets',
        name: 'PendingResets',
        component: () => import('@/views/admin/PwdResetRequests.vue')
      },
      {
        path: 'users',
        name: 'UsersView',
        component: () => import('@/views/admin/UsersView.vue')
      },
      {
        path: 'models',
        name: 'ModelsView',
        component: () => import('@/views/admin/ModelsView.vue')
      },
      {
        path: 'agent',
        name: 'AgentSettings',
        component: () => import('@/views/admin/AgentSettings.vue')
      },
      {
        path: 'system',
        name: 'SystemConfig',
        component: () => import('@/views/admin/SystemConfig.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const user = JSON.parse(localStorage.getItem('user') || '{}')

  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.meta.requiresAdmin && user.role !== 'admin') {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
