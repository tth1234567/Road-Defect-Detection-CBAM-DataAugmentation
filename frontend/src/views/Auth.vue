<template>
  <div class="auth-wrap">
    <el-card class="auth-card" shadow="hover">
      <div class="auth-brand">
        <div class="logo-icon">🛣</div>
        <div>
          <div class="brand-title">智巡 SmartInspect</div>
          <div class="brand-sub">请登录或注册</div>
        </div>
      </div>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" label-width="80px" @submit.prevent="onLogin">
            <el-form-item label="用户名">
              <el-input v-model="loginForm.username" autocomplete="username" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="loginForm.password" type="password" show-password autocomplete="current-password" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="busy" style="width:100%" @click="onLogin">登录</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="注册" name="register">
          <el-form :model="regForm" label-width="100px" @submit.prevent="onRegister">
            <el-form-item label="用户名">
              <el-input v-model="regForm.username" autocomplete="username" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="regForm.password" type="password" show-password autocomplete="new-password" />
            </el-form-item>
            <el-form-item label="确认密码">
              <el-input v-model="regForm.password_confirm" type="password" show-password autocomplete="new-password" />
            </el-form-item>
            <el-form-item label="角色">
              <el-radio-group v-model="regForm.role">
                <el-radio value="inspector">巡检员</el-radio>
                <el-radio value="admin">管理员</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item v-if="regForm.role === 'admin'" label="管理员注册码">
              <el-input v-model="regForm.admin_code" placeholder="请输入注册码" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="busy" style="width:100%" @click="onRegister">注册</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <el-alert type="info" :closable="false" show-icon style="margin-top:8px">
        <template #title>默认管理员</template>
        系统首次启动会创建账号 <strong>admin</strong> / 密码 <strong>Admin@123</strong>；管理员注册需使用库内注册码（默认 <code>ADMIN-INIT-2025</code>）。
      </el-alert>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, register } from '../api/http.js'

const route = useRoute()
const router = useRouter()
const activeTab = ref('login')
const busy = ref(false)

const loginForm = ref({ username: '', password: '' })
const regForm = ref({
  username: '',
  password: '',
  password_confirm: '',
  role: 'inspector',
  admin_code: '',
})

function goAfterAuth() {
  const r = route.query.redirect
  const target = Array.isArray(r) ? r[0] : r
  if (typeof target === 'string' && target.startsWith('/')) {
    router.push(target)
    return
  }
  router.push('/dashboard')
}

async function onLogin() {
  busy.value = true
  try {
    await login({
      username: loginForm.value.username,
      password: loginForm.value.password,
    })
    ElMessage.success('登录成功')
    goAfterAuth()
  } catch {
    // 拦截器已提示
  } finally {
    busy.value = false
  }
}

async function onRegister() {
  busy.value = true
  try {
    await register({
      username: regForm.value.username,
      password: regForm.value.password,
      password_confirm: regForm.value.password_confirm,
      role: regForm.value.role,
      admin_code: regForm.value.role === 'admin' ? regForm.value.admin_code : null,
    })
    ElMessage.success('注册成功，已自动登录')
    goAfterAuth()
  } catch {
    // 拦截器已提示
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.auth-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(160deg, #e8eef6 0%, #cfe2ff 100%);
  padding: 24px;
}
.auth-card {
  width: 100%;
  max-width: 460px;
}
.auth-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.logo-icon { font-size: 36px; }
.brand-title { font-size: 18px; font-weight: 700; color: #1a1a2e; }
.brand-sub { font-size: 12px; color: #8c8c8c; margin-top: 2px; }
</style>
