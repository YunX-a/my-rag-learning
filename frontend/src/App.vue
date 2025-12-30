<template>
  <div class="container">
    <div v-if="!token" class="login-box">
      <h2>RAG 知识库助手</h2>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="登录" name="login">
          <el-form>
            <el-form-item>
              <el-input v-model="form.username" placeholder="用户名" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="form.password" type="password" placeholder="密码" />
            </el-form-item>
            <el-button type="primary" @click="handleLogin" :loading="loading" style="width:100%">
              登录
            </el-button>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="注册" name="register">
          <el-form>
            <el-form-item>
              <el-input v-model="form.username" placeholder="设置用户名" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="form.password" type="password" placeholder="设置密码" />
            </el-form-item>
            <el-button type="success" @click="handleRegister" :loading="loading" style="width:100%">
              注册并登录
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>

    <div v-else class="chat-layout">
      <div class="sidebar">
        <el-tabs v-model="sideTab" class="sidebar-tabs" stretch>
          <el-tab-pane label="💬 历史" name="history">
            <div class="list-container">
              <ul class="history-list">
                <li 
                  v-for="chat in historyList" 
                  :key="chat.id"
                  @click="loadHistory(chat.id)"
                  :class="{ active: currentChatId === chat.id }"
                >
                  <div class="history-content">
                    <span class="title">{{ chat.title || '无标题会话' }}</span>
                    <span class="date">{{ formatDate(chat.created_at) }}</span>
                  </div>

                  <el-button
                    class="delete-btn"
                    type="danger"
                    link
                    :icon="Delete"
                    @click.stop="confirmDelete(chat.id)"
                  ></el-button>
                </li>
              </ul>
              <div v-if="historyList.length === 0" class="empty-tip">暂无历史记录</div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="📂 文件" name="files">
            <div class="upload-area">
              <el-upload
                class="upload-demo"
                action="#"
                :http-request="customUpload"
                :show-file-list="false"
              >
                <el-button type="primary" size="small" :icon="Upload">上传 PDF</el-button>
              </el-upload>
            </div>
            <div class="list-container">
              <ul class="file-list">
                <li v-for="file in fileList" :key="file">
                  <el-icon><Document /></el-icon>
                  <span class="filename" :title="file">{{ file }}</span>
                </li>
              </ul>
            </div>
          </el-tab-pane>
        </el-tabs>

        <div class="new-chat-btn">
          <el-button @click="resetChat" round block>+ 新开启对话</el-button>
        </div>
        <div class="logout-area" style="padding: 10px 15px; border-top: 1px solid #444;">
           <el-button type="danger" link @click="handleLogout" style="width: 100%">退出登录</el-button>
        </div>
      </div>

      <div class="main-chat">
        <div class="chat-header" v-if="currentChatId">
          当前回顾模式(ID: {{ currentChatId }})
          <el-button link type="primary" @click="resetChat">退出</el-button>
        </div>
        
        <div class="chat-history" ref="chatBox">
          <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
            <div class="bubble" :class="msg.role">
              <div class="markdown-content" v-html="renderMarkdown(msg.content)"></div>

              <div v-if="msg.sources && msg.sources.length" class="sources">
                <p>📚 参考来源:</p>
                <ul>
                  <li v-for="(src, i) in msg.sources" :key="i">
                    {{ src.source }} (页码: {{ src.page !== undefined ? src.page + 1 : '未知' }})
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <div class="input-area">
          <el-input
            v-model="inputQuestion"
            placeholder="请输入您的问题..."
            @keyup.enter="sendMessage"
            :disabled="isTalking"
          >
            <template #append>
              <el-button @click="sendMessage" :loading="isTalking">发送</el-button>
            </template>
          </el-input>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Document, Delete } from '@element-plus/icons-vue'
import { marked } from 'marked'

// --- 基础配置 ---
// 确保你的后端地址正确，如果使用 uv 管理的 python 后端，默认 8001 端口
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

// --- 接口定义 ---
interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{ source: string; page?: number }>
  id?: number
}

interface HistoryItem {
  id: number
  title: string
  created_at: string
}

// --- 状态定义 ---
const token = ref(localStorage.getItem('access_token') || '')
const activeTab = ref('login')
const sideTab = ref('history')
const loading = ref(false)
const isTalking = ref(false)
const inputQuestion = ref('')
const chatBox = ref<HTMLElement | null>(null)

// 数据存储
const fileList = ref<string[]>([])
const historyList = ref<HistoryItem[]>([])
const currentChatId = ref<number | null>(null)

const form = ref({ username: '', password: '' })

const messages = ref<ChatMessage[]>([
  { role: 'assistant', content: '你好！我是你的 AI 助手，请问有什么可以帮你？' }
])

// --- 初始化逻辑 ---
const initData = async () => {
  if (!token.value) return
  await Promise.all([fetchFiles(), fetchHistory()])
}

onMounted(() => {
  if (token.value) initData()
})

// --- API 方法 ---
const fetchFiles = async () => {
  if (!token.value) return
  try {
    const res = await axios.get(`${API_URL}/rag/files`, {
      headers: { Authorization: `Bearer ${token.value}` }
    })
    fileList.value = res.data
  } catch (e) {
    console.error('获取文件失败', e)
  }
}

const fetchHistory = async () => {
  if (!token.value) return
  try {
    const res = await axios.get(`${API_URL}/history/conversations`, { 
      headers: { Authorization: `Bearer ${token.value}` } 
    })
    historyList.value = res.data
  } catch (e: any) { 
    //  如果 Token 失效，自动登出
    if (e.response && e.response.status === 401) {
      handleLogout()
      ElMessage.error('登录已过期，请重新登录')
    }
  }
}
// --- 删除历史方法 ---
const confirmDelete = (chatId: number) => {
  ElMessageBox.confirm(
    '确定要删除这段对话历史吗？该操作不可恢复。',
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    handleDelete(chatId)
  }).catch(() => {})
}

const handleDelete = async (chatId: number) => {
  try {
    await axios.delete(`${API_URL}/history/conversations/${chatId}`, {
      headers: { Authorization: `Bearer ${token.value}` }
    })
    
    ElMessage.success('删除成功')
    
    // 1. 从本地列表中移除
    historyList.value = historyList.value.filter(item => item.id !== chatId)
    
    // 2. 如果删除的是当前正在查看的对话，则重置聊天窗口
    if (currentChatId.value === chatId) {
      resetChat()
    }
  } catch (e) {
    ElMessage.error('删除失败，请稍后再试')
    console.error('Delete error:', e)
  }
}

// --- 退出登录 ---
const handleLogout = () => {
  token.value = ''
  localStorage.removeItem('access_token')
  activeTab.value = 'login'
  // 清空数据
  historyList.value = []
  messages.value = [{ role: 'assistant', content: '你好！我是你的 AI 助手，请问有什么可以帮你？' }]
  currentChatId.value = null
  ElMessage.info('已退出登录')
}

const loadHistory = async (chatId: number) => {
  try {
    const res = await axios.get(`${API_URL}/history/conversations/${chatId}/messages`, {
      headers: { Authorization: `Bearer ${token.value}` }
    })
    messages.value = res.data
    currentChatId.value = chatId
    scrollToBottom()
  } catch (e) {
    ElMessage.error('加载历史失败')
  }
}


const resetChat = () => {
  currentChatId.value = null
  messages.value = [{ role: 'assistant', content: '你好！我是你的 AI 助手，请问有什么可以帮你？' }]
  // 这里可能需要刷新一下历史列表以确保最新状态
  fetchHistory()
}

// --- 登录/注册/上传 ---
const handleLogin = async () => {
  try {
    loading.value = true
    // 注意：表单数据通常建议使用 x-www-form-urlencoded 格式用于 OAuth2，但这里保持 JSON 格式
    const res = await axios.post(`${API_URL}/users/token`, form.value)
    token.value = res.data.access_token
    localStorage.setItem('access_token', token.value)
    ElMessage.success('登录成功')
    await initData()
  } catch (e) {
    ElMessage.error('登录失败，请检查用户名或密码')
  } finally {
    loading.value = false
  }
}

const handleRegister = async () => {
  try {
    loading.value = true
    await axios.post(`${API_URL}/users/register`, form.value)
    ElMessage.success('注册成功，登录中...')
    await handleLogin()
  } catch (e: any) {
    ElMessage.error('注册失败')
  } finally {
    loading.value = false
  }
}

const customUpload = async (options: any) => {
  const formData = new FormData()
  formData.append('file', options.file)
  try {
    ElMessage.info('处理中...')
    const res = await axios.post(`${API_URL}/rag/upload`, formData, {
      headers: { 
        'Content-Type': 'multipart/form-data', 
        'Authorization': `Bearer ${token.value}` 
      }
    })
    ElMessage.success(`成功提取 ${res.data.chunks} 个片段`)
    await fetchFiles()
  } catch (e) {
    ElMessage.error('上传失败')
  }
}

// --- 聊天发送 (流式处理) ---
const sendMessage = async () => {
  
  console.log("[DEBUG] 1. 用户点击了发送按钮！")
  console.log("[DEBUG] 2. 当前输入内容:", inputQuestion.value)
  if (!inputQuestion.value.trim()) return
  // 如果当前在查看旧历史，发送新消息则转为新对话
  if (currentChatId.value) { 
    resetChat(); 
    await nextTick(); 
  }

  const question = inputQuestion.value
  messages.value.push({ role: 'user', content: question })
  console.log("[DEBUG] 3. 准备向后端发起 fetch 请求...")
  inputQuestion.value = ''
  isTalking.value = true

  // 添加一个空的助手消息用于流式接收
  const botMsgIndex = messages.value.push({ role: 'assistant', content: '', sources: [] }) - 1

  try {
    // 使用 fetch 获取流式响应
    const response = await fetch(`${API_URL}/agent/chat`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json', 
        'Authorization': `Bearer ${token.value}` 
      },
      body: JSON.stringify({ question })
    })

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    if (reader) {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        const text = decoder.decode(value, { stream: true })
        
        // 简单的流式解析逻辑，处理可能存在的 ---SOURCES--- 分隔符
        if (text.includes('---SOURCES---')) {
          const parts = text.split('---SOURCES---')
          messages.value[botMsgIndex].content += parts[0]
          buffer += parts[1] // 剩余部分通常是来源 JSON 字符串
        } else if (buffer) {
          // 如果 buffer 非空，说明已经进入来源部分，继续累积
          buffer += text
        } else {
          // 正常对话内容
          messages.value[botMsgIndex].content += text
        }
        scrollToBottom()
      }
    }

    // 处理来源数据
    if (buffer) {
      try {
        // 假设来源是以换行符分隔的 JSON 对象
        const sources = buffer.trim().split('\n')
          .filter(Boolean)
          .map(s => {
             try { return JSON.parse(s) } catch { return null }
          })
          .filter(Boolean)
        
        messages.value[botMsgIndex].sources = sources
      } catch (e) {
        console.error('解析来源失败', e)
      }
    }
    // 对话结束后刷新历史列表
    fetchHistory()
  } catch (e) {
    messages.value[botMsgIndex].content += '\n[连接出错，请稍后再试]'
  } finally {
    isTalking.value = false
    scrollToBottom()
  }
}

const scrollToBottom = () => {
  nextTick(() => { 
    if (chatBox.value) {
      chatBox.value.scrollTop = chatBox.value.scrollHeight 
    }
  })
}

// 简单的 Markdown 渲染
const renderMarkdown = (text: string) => {
  try { 
    // marked.parse 返回 string | Promise，这里强制转换为 string (同步模式)
    return marked.parse(text) as string
  } catch { 
    return text 
  }
}

const formatDate = (str: string) => {
  return new Date(str).toLocaleString('zh-CN', { 
    month: 'numeric', 
    day: 'numeric', 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}
</script>

<style scoped>
/* 全局容器 */
.container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #eceff1;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', Arial, sans-serif;
}

/* 登录框 */
.login-box {
  width: 400px;
  padding: 40px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

/* 聊天布局 */
.chat-layout {
  display: flex;
  flex-direction: row;
  width: 95vw;
  max-width: 1400px;
  height: 90vh;
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.1);
}

/* --- 侧边栏 --- */
.sidebar {
  width: 300px;
  background-color: #202123;
  color: #ececf1;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #444;
  flex-shrink: 0;
}

/* Tabs 样式覆盖 - 使用 :deep 而不是 : deep */
:deep(.el-tabs__header) {
  margin: 0;
  background-color: #343541;
  border-bottom: 1px solid #4d4d4f;
}
:deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background-color: #4d4d4f;
}
:deep(.el-tabs__item) {
  color: #8e8ea0 !important;
  height: 50px;
  line-height: 50px;
}
:deep(.el-tabs__item.is-active) {
  color: #fff !important;
  font-weight: bold;
}
:deep(.el-tabs__active-bar) {
  background-color: #10a37f;
}

.list-container {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}
.list-container::-webkit-scrollbar {
  width: 6px;
}
.list-container::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 3px;
}

/* --- 列表基础样式 --- */
.history-list, .file-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

/* 1. 文件列表保持原样 (纵向排列) */
.file-list li {
  padding: 12px;
  margin-bottom: 8px;
  border-radius: 6px;
  cursor: pointer;
  color: #ececf1;
  transition: background 0.2s;
  display: flex;
  flex-direction: row; /* 文件图标和名字横向 */
  align-items: center;
}

/* 2. 历史列表修改 (改为横向布局，以便右侧放删除按钮) */
.history-list li {
  padding: 12px;
  margin-bottom: 8px;
  border-radius: 6px;
  cursor: pointer;
  color: #ececf1;
  transition: background 0.2s;
  display: flex;
  flex-direction: row;    /* 修改：改为横向，包裹内容和删除键 */
  align-items: center;
  justify-content: space-between;
  position: relative;
}

.history-list li:hover {
  background-color: #2a2b32;
}

.history-list li.active {
  background-color: #343541;
  border: 1px solid #565869;
}

/* 历史列表左侧文字区域 */
.history-list li .history-content {
  flex: 1;
  display: flex;
  flex-direction: column; /* 文字依然是标题在上日期在下 */
  overflow: hidden;
}

.history-list li .title {
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.history-list li .date {
  font-size: 12px;
  color: #8e8ea0;
}

/* --- 3. 新增：删除按钮样式 --- */
.delete-btn {
  display: none; /* 默认隐藏 */
  padding: 4px;
  color: #8e8ea0;
}

.delete-btn:hover {
  color: #f56c6c !important; /* 悬停变红 */
}

/* 鼠标移动到 li 上时，显示该 li 内部的删除按钮 */
.history-list li:hover .delete-btn {
  display: inline-flex;
}

.file-list li {
  flex-direction: row;
  align-items: center;
}
.file-list li .el-icon {
  margin-right: 8px;
}
.file-list li .filename {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.upload-area, .new-chat-btn {
  padding: 15px;
  border-top: 1px solid #444;
  background-color: #202123;
}
.empty-tip {
  text-align: center;
  color: #666;
  font-size: 13px;
  margin-top: 30px;
}

/* --- 主聊天区 --- */
.main-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
  position: relative;
  min-width: 0;
}

.chat-header {
  padding: 12px 24px;
  background: #f7f7f8;
  border-bottom: 1px solid #e5e5e5;
  font-size: 14px;
  color: #666;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-history {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  background-color: #f7f7f8;
}

.message {
  margin-bottom: 24px;
  display: flex;
  width: 100%;
}
.message.user {
  justify-content: flex-end;
}
.message.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 80%;
  padding: 16px 20px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 15px;
  position: relative;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}
.message.user .bubble {
  background-color: #95ec69;
  color: #000;
  border-top-right-radius: 2px;
}
.message.assistant .bubble {
  background-color: #ffffff;
  color: #333;
  border: 1px solid #e5e5e5;
  border-top-left-radius: 2px;
}

.sources {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #eee;
  font-size: 13px;
  color: #666;
}
.sources p {
  margin: 0 0 5px;
  font-weight: bold;
}
.sources ul {
  padding-left: 20px;
  margin: 0;
}

.input-area {
  padding: 24px;
  background: white;
  border-top: 1px solid #e5e5e5;
}

/* Markdown 样式 */
:deep(.markdown-content) {
  font-size: 15px;
  color: #374151;
}
:deep(.markdown-content pre) {
  background: #f6f8fa;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
}
:deep(.markdown-content p) {
  margin: 8px 0;
}
</style>